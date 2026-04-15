"""WMI monitoring module for Windows systems."""

import subprocess
from datetime import datetime
from typing import Optional
import json

from src.models import Metric, Status, CheckType, MonitorTarget


class WMIMonitor:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        query = target.wmi_query
        namespace = target.wmi_namespace or r"root\cimv2"
        
        if not query:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.WMI,
                value=0.0,
                status=Status.DOWN,
                error="No WMI query specified",
            )

        try:
            start = datetime.now()
            result = self._run_wmi_query(target.host, namespace, query)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            if result is not None:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.WMI,
                    value=float(result),
                    status=Status.UP,
                    latency_ms=elapsed,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.WMI,
                    value=0.0,
                    status=Status.DOWN,
                    error="WMI query returned no results",
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

    def _run_wmi_query(self, host: str, namespace: str, query: str) -> Optional[float]:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-WmiObject -Namespace '{namespace}' -ComputerName '{host}' -Query '{query}' | ConvertTo-Json -Compress"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return float(data.get("Value", data.get("Data", 0)))
        except (subprocess.TimeoutExpired, json.JSONDecodeError, ValueError):
            pass
        
        return None

    def get_cpu_usage(self, host: str) -> Optional[float]:
        query = "SELECT LoadPercentage FROM Win32_Processor"
        return self._run_wmi_query(host, r"root\cimv2", query)

    def get_memory_usage(self, host: str) -> Optional[float]:
        query = "SELECT FreePhysicalMemory,TotalVisibleMemorySize FROM Win32_OperatingSystem"
        
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-WmiObject -ComputerName '{host}' -Query '{query}' | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=self.timeout
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                free = float(data.get("FreePhysicalMemory", 0))
                total = float(data.get("TotalVisibleMemorySize", 1))
                used_percent = ((total - free) / total) * 100
                return used_percent
        except:
            pass
        
        return None

    def get_disk_usage(self, host: str, drive: str = "C:") -> Optional[float]:
        query = f"SELECT Size,FreeSpace FROM Win32_LogicalDisk WHERE DeviceID='{drive}'"
        
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-WmiObject -ComputerName '{host}' -Query '{query}' | ConvertTo-Json -Compress"],
                capture_output=True, text=True, timeout=self.timeout
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                size = float(data.get("Size", 0))
                free = float(data.get("FreeSpace", 0))
                if size > 0:
                    used_percent = ((size - free) / size) * 100
                    return used_percent
        except:
            pass
        
        return None
