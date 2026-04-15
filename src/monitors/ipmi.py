"""IPMI monitoring module for server hardware management."""

import logging
import subprocess
import re
from typing import Optional, dict, list, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class IPMISensorType(Enum):
    TEMPERATURE = "Temperature"
    VOLTAGE = "Voltage"
    FAN = "Fan"
    POWER_SUPPLY = "Power Supply"
    DISK = "Disk"
    MEMORY = "Memory"
    CPU = "CPU"
    SYSTEM_BOARD = "System Board"


@dataclass
class IPMISensorReading:
    name: str
    value: float
    unit: str
    status: str
    sensor_type: IPMISensorType
    reading_time: datetime


@dataclass
class IPMIChassisStatus:
    power_state: str
    intrusion: str
    front_panel_lock: str
    boot_device: str


@dataclass
class IPMISDRRecord:
    record_id: str
    sensor_name: str
    sensor_number: int
    sensor_type: str
    entity_id: str
    entity_instance: str


class IPMIMonitor:
    def __init__(self, host: str = None, username: str = None, password: str = None, timeout: int = 10):
        self.host = host
        self.username = username
        self.password = password
        self.timeout = timeout

    def _build_command(self, command: list) -> list:
        cmd = ["ipmitool"]
        
        if self.host:
            cmd.extend(["-H", self.host])
        
        if self.username:
            cmd.extend(["-U", self.username])
        
        if self.password:
            cmd.extend(["-P", self.password])
        
        cmd.extend(command)
        
        return cmd

    def get_sensor_data(self) -> list[IPMISensorReading]:
        try:
            cmd = self._build_command(["sdr", "list", "all"])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                logger.error(f"IPMI sensor data failed: {result.stderr}")
                return []
            
            sensors = []
            for line in result.stdout.split('\n'):
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        name = parts[0]
                        value_raw = parts[1]
                        status = parts[2].strip()
                        
                        value_match = re.search(r"([\d.]+)", value_raw)
                        value = float(value_match.group(1)) if value_match else 0.0
                        
                        unit = "unknown"
                        if "degrees C" in value_raw:
                            unit = "°C"
                        elif "Volts" in value_raw:
                            unit = "V"
                        elif "RPM" in value_raw:
                            unit = "RPM"
                        elif "Watts" in value_raw:
                            unit = "W"
                        
                        sensor_type = self._detect_sensor_type(name)
                        
                        sensors.append(IPMISensorReading(
                            name=name,
                            value=value,
                            unit=unit,
                            status=status,
                            sensor_type=sensor_type,
                            reading_time=datetime.now()
                        ))
            
            return sensors
            
        except Exception as e:
            logger.error(f"Failed to get IPMI sensor data: {e}")
            return []

    def _detect_sensor_type(self, name: str) -> IPMISensorType:
        name_lower = name.lower()
        
        if any(x in name_lower for x in ["temp", "temperature"]):
            return IPMISensorType.TEMPERATURE
        elif any(x in name_lower for x in ["volt", "voltage", "vcore"]):
            return IPMISensorType.VOLTAGE
        elif any(x in name_lower for x in ["fan", "rpm"]):
            return IPMISensorType.FAN
        elif any(x in name_lower for x in ["psu", "power", "ps"]):
            return IPMISensorType.POWER_SUPPLY
        elif any(x in name_lower for x in ["cpu"]):
            return IPMISensorType.CPU
        elif any(x in name_lower for x in ["mem", "memory", "dram"]):
            return IPMISensorType.MEMORY
        elif any(x in name_lower for x in ["disk", "hdd", "ssd"]):
            return IPMISensorType.DISK
        else:
            return IPMISensorType.SYSTEM_BOARD

    def get_chassis_status(self) -> Optional[IPMIChassisStatus]:
        try:
            cmd = self._build_command(["chassis", "status"])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                return None
            
            status = IPMIChassisStatus(
                power_state="unknown",
                intrusion="unknown",
                front_panel_lock="unknown",
                boot_device="unknown"
            )
            
            for line in result.stdout.split('\n'):
                if "System Power" in line:
                    status.power_state = "on" if "on" in line.lower() else "off"
                elif "Front Panel Lock" in line:
                    status.front_panel_lock = "locked" if "locked" in line.lower() else "unlocked"
                elif "Boot Device" in line:
                    status.boot_device = line.split(':')[-1].strip()
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get chassis status: {e}")
            return None

    def get_sel(self, entries: int = 10) -> list[dict]:
        try:
            cmd = self._build_command(["sel", "list", str(entries)])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                return []
            
            sel_entries = []
            for line in result.stdout.split('\n'):
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 3:
                        sel_entries.append({
                            "timestamp": parts[0],
                            "sensor": parts[1],
                            "event": parts[2],
                        })
            
            return sel_entries
            
        except Exception as e:
            logger.error(f"Failed to get SEL: {e}")
            return []

    def get_fru_info(self) -> dict:
        try:
            cmd = self._build_command(["fru", "print"])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                return {}
            
            info = {}
            current_key = None
            
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key:
                        info[key] = value
                        current_key = key
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get FRU info: {e}")
            return {}

    def get_bmc_info(self) -> dict:
        try:
            cmd = self._build_command(["mc", "info"])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                return {}
            
            info = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get BMC info: {e}")
            return {}

    def get_all_sensors_summary(self) -> dict:
        sensors = self.get_sensor_data()
        
        summary = {
            "total_sensors": len(sensors),
            "by_type": {},
            "critical": [],
            "warnings": [],
        }
        
        for sensor in sensors:
            type_name = sensor.sensor_type.value
            
            if type_name not in summary["by_type"]:
                summary["by_type"][type_name] = []
            
            summary["by_type"][type_name].append({
                "name": sensor.name,
                "value": sensor.value,
                "unit": sensor.unit,
                "status": sensor.status,
            })
            
            if sensor.status.lower() in ["critical", "nc"]:
                summary["critical"].append({
                    "name": sensor.name,
                    "value": sensor.value,
                    "unit": sensor.unit,
                })
            elif sensor.status.lower() in ["warning", "nc"]:
                summary["warnings"].append({
                    "name": sensor.name,
                    "value": sensor.value,
                    "unit": sensor.unit,
                })
        
        return summary

    def check_health(self) -> dict:
        health = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "chassis": None,
            "sensors": None,
            "sel_events": [],
            "issues": [],
        }
        
        chassis = self.get_chassis_status()
        if chassis:
            health["chassis"] = {
                "power": chassis.power_state,
                "boot_device": chassis.boot_device,
            }
            
            if chassis.power_state != "on":
                health["issues"].append(f"Power state: {chassis.power_state}")
        
        sensor_summary = self.get_all_sensors_summary()
        health["sensors"] = sensor_summary
        
        if sensor_summary["critical"]:
            health["overall_status"] = "critical"
            health["issues"].append(f"{len(sensor_summary['critical'])} critical sensor alerts")
        
        if sensor_summary["warnings"]:
            if health["overall_status"] != "critical":
                health["overall_status"] = "warning"
            health["issues"].append(f"{len(sensor_summary['warnings'])} sensor warnings")
        
        return health


class IPMICommand:
    SUPPORTED_COMMANDS = {
        "sensor_data": {
            "cmd": ["sdr", "list", "all"],
            "description": "Get all sensor readings",
        },
        "sensor_reading": {
            "cmd": ["sensor", "get", "{sensor_name}"],
            "description": "Get specific sensor reading",
        },
        "chassis_status": {
            "cmd": ["chassis", "status"],
            "description": "Get chassis status",
        },
        "chassis_power": {
            "cmd": ["chassis", "power", "{action}"],
            "description": "Power action (on/off/reset/cycle)",
            "params": ["action"]
        },
        "sel_list": {
            "cmd": ["sel", "list"],
            "description": "List SEL entries",
        },
        "sel_clear": {
            "cmd": ["sel", "clear"],
            "description": "Clear SEL",
        },
        "fru_print": {
            "cmd": ["fru", "print"],
            "description": "Print FRU info",
        },
        "fru_read": {
            "cmd": ["fru", "read", "{file}"],
            "description": "Read FRU to file",
            "params": ["file"]
        },
        "mc_info": {
            "cmd": ["mc", "info"],
            "description": "Get BMC info",
        },
        "mc_reset": {
            "cmd": ["mc", "reset", "{action}"],
            "description": "Reset BMC (warm/cold)",
            "params": ["action"]
        },
        "lan_print": {
            "cmd": ["lan", "print"],
            "description": "Print LAN config",
        },
        "user_list": {
            "cmd": ["user", "list"],
            "description": "List BMC users",
        },
        "session_list": {
            "cmd": ["session", "list"],
            "description": "List active sessions",
        },
    }

    @classmethod
    def get_available_commands(cls) -> list[dict]:
        return [
            {
                "name": name,
                "command": " ".join(info["cmd"]),
                "description": info["description"],
                "params": info.get("params", []),
            }
            for name, info in cls.SUPPORTED_COMMANDS.items()
        ]


def create_ipmi_monitor(host: str, username: str = "ADMIN", password: str = "ADMIN") -> IPMIMonitor:
    return IPMIMonitor(host=host, username=username, password=password)
