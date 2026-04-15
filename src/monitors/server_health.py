"""Server health monitoring for Linux and Windows systems."""

import subprocess
import platform
import re
from datetime import datetime
from typing import Optional
import json

from src.models import Metric, Status, CheckType, MonitorTarget


class ServerHealthMonitor:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        try:
            if target.device_type.value in ["windows", "wmi"]:
                return self._check_windows(target)
            else:
                return self._check_linux(target)
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.WMI,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _check_linux(self, target: MonitorTarget) -> Metric:
        ssh_host = target.host
        
        try:
            cpu_cmd = f"ssh -o ConnectTimeout={self.timeout} {ssh_host} top -bn1 | grep 'Cpu(s)' | awk '{{print $2}}'"
            mem_cmd = f"ssh -o ConnectTimeout={self.timeout} {ssh_host} free | grep Mem"
            disk_cmd = f"ssh -o ConnectTimeout={self.timeout} {ssh_host} df -h /"
            
            cpu_result = subprocess.run(
                cpu_cmd, shell=True, capture_output=True, text=True, timeout=self.timeout
            )
            cpu_idle = float(cpu_result.stdout.strip().replace('%', '')) or 0.0
            cpu_used = 100.0 - cpu_idle
            
            mem_result = subprocess.run(
                mem_cmd, shell=True, capture_output=True, text=True, timeout=self.timeout
            )
            mem_parts = mem_result.stdout.split()
            mem_total = float(mem_parts[1])
            mem_used = float(mem_parts[2])
            mem_percent = (mem_used / mem_total) * 100 if mem_total > 0 else 0
            
            disk_result = subprocess.run(
                disk_cmd, shell=True, capture_output=True, text=True, timeout=self.timeout
            )
            disk_percent = float(re.search(r'(\d+)%', disk_result.stdout).group(1))
            
            health_score = 100.0 - ((cpu_used + mem_percent + disk_percent) / 3)
            
            status = Status.UP
            if health_score < 50:
                status = Status.DEGRADED
            if health_score < 25:
                status = Status.DOWN
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.WMI,
                value=health_score,
                status=status,
                latency_ms=cpu_used,
            )
        except subprocess.TimeoutExpired:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.WMI,
                value=0.0,
                status=Status.DOWN,
                error="SSH timeout",
            )

    def _check_windows(self, target: MonitorTarget) -> Metric:
        try:
            ps_script = f"""
            $cpu = (Get-Counter '\\Processor(_Total)\\% Processor Time' -SampleInterval 1 -MaxSamples 1).CounterSamples.CookedValue
            $mem = (Get-Counter '\\Memory\\% Committed Bytes In Use' -SampleInterval 1 -MaxSamples 1).CounterSamples.CookedValue
            $disk = (Get-Counter '\\LogicalDisk(C:)\\% Free Space' -SampleInterval 1 -MaxSamples 1).CounterSamples.CookedValue
            @{{cpu=$cpu; mem=$mem; disk=$disk}} | ConvertTo-Json
            """
            
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=self.timeout + 5,
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                cpu_used = float(data.get("cpu", 0))
                mem_percent = float(data.get("mem", 0))
                disk_free = float(data.get("disk", 0))
                disk_used = 100.0 - disk_free
                
                health_score = 100.0 - ((cpu_used + mem_percent + disk_used) / 3)
                
                status = Status.UP
                if health_score < 50:
                    status = Status.DEGRADED
                if health_score < 25:
                    status = Status.DOWN
                
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.WMI,
                    value=health_score,
                    status=status,
                    latency_ms=cpu_used,
                )
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.WMI,
                value=0.0,
                status=Status.DOWN,
                error="WMI query failed",
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.WMI,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )


class PacketLossMonitor:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self._last_results = {}

    def check(self, target: MonitorTarget) -> Metric:
        ping_count = target.port or 4
        
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["ping", "-n", str(ping_count), "-w", str(self.timeout * 1000), target.host],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 5,
                )
            else:
                result = subprocess.run(
                    ["ping", "-c", str(ping_count), "-W", str(self.timeout), target.host],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout + 5,
                )
            
            loss = self._parse_packet_loss(result.stdout)
            status = Status.UP
            
            if loss > 0:
                if loss < 25:
                    status = Status.DEGRADED
                else:
                    status = Status.DOWN
            
            key = f"{target.id}"
            previous_loss = self._last_results.get(key, 0)
            self._last_results[key] = loss
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PING,
                value=float(100 - loss),
                status=status,
                latency_ms=float(loss),
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PING,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _parse_packet_loss(self, output: str) -> float:
        match = re.search(r'(\d+)% packet loss', output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        
        match = re.search(r'(\d+)/(\d+)\s*received', output)
        if match:
            received = int(match.group(1))
            total = int(match.group(2))
            if total > 0:
                return float(((total - received) / total) * 100)
        
        return 0.0


class NetworkSpeedMonitor:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self._baseline = {}
        self._last_check = {}

    def check(self, target: MonitorTarget) -> Metric:
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["netsh", "interface", "show", "interface"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                speed = self._parse_windows_speed(result.stdout, target.host)
            else:
                result = subprocess.run(
                    ["ip", "link", "show"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
                speed = self._parse_linux_speed(result.stdout, target.host)
            
            if speed is None:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.BANDWIDTH,
                    value=0.0,
                    status=Status.DOWN,
                    error="Could not determine network speed",
                )
            
            key = f"{target.host}"
            baseline = self._baseline.get(key, speed)
            speed_change = abs(speed - baseline) / baseline * 100 if baseline > 0 else 0
            
            status = Status.UP
            if speed_change > 50:
                status = Status.DEGRADED
            elif speed_change > 80:
                status = Status.DOWN
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.BANDWIDTH,
                value=float(speed),
                status=status,
                latency_ms=float(speed_change),
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.BANDWIDTH,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _parse_windows_speed(self, output: str, host: str) -> Optional[int]:
        match = re.search(r'(\d+)\s*(Mbps|Gbps)', output, re.IGNORECASE)
        if match:
            speed = int(match.group(1))
            unit = match.group(2).upper()
            return speed * 1000 if unit == "GBPS" else speed
        return None

    def _parse_linux_speed(self, output: str, host: str) -> Optional[int]:
        match = re.search(r'mtu\s+\d+\s+state\s+(\w+).*?(\d+)\s*(Mbps|Gbps)', output, re.DOTALL)
        if match:
            state = match.group(1)
            if state == "UP":
                speed = int(match.group(2))
                unit = match.group(3).upper()
                return speed * 1000 if unit == "GBPS" else speed
        return None

    def set_baseline(self, target_id: str, speed: float):
        self._baseline[target_id] = speed
