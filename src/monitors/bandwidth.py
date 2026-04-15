"""Network bandwidth monitoring using SNMP with speed detection."""

import re
from datetime import datetime
from typing import Optional, Tuple, List

from pysnmp.hlapi import *
from src.models import Metric, Status, CheckType, MonitorTarget, NetworkSpeed


BANDWIDTH_OIDS = {
    "ifInOctets": "1.3.6.1.2.1.2.2.1.10",
    "ifOutOctets": "1.3.6.1.2.1.2.2.1.16",
    "ifInBitsPerSec": "1.3.6.1.2.1.2.2.1.14",
    "ifOutBitsPerSec": "1.3.6.1.2.1.2.2.1.20",
    "ifSpeed": "1.3.6.1.2.1.2.2.1.5",
    "ifHighSpeed": "1.3.6.1.2.1.2.2.1.62",
    "ifAlias": "1.3.6.1.2.1.2.2.1.18",
    "ifAdminStatus": "1.3.6.1.2.1.2.2.1.7",
    "ifOperStatus": "1.3.6.1.2.1.2.2.1.8",
}


class BandwidthMonitor:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout
        self._last_values = {}
        self._link_speeds = {}
        self._speed_baseline = {}

    def check(self, target: MonitorTarget) -> Metric:
        interface_index = target.interface_index or target.port or 1
        
        try:
            in_octets = self._snmp_get(target.host, target.snmp_community, f"{BANDWIDTH_OIDS['ifInOctets']}.{interface_index}")
            out_octets = self._snmp_get(target.host, target.snmp_community, f"{BANDWIDTH_OIDS['ifOutOctets']}.{interface_index}")
            link_speed = self._get_link_speed(target.host, target.snmp_community, interface_index)
            
            if in_octets is None or out_octets is None:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.BANDWIDTH,
                    value=0.0,
                    status=Status.DOWN,
                    error="Could not retrieve interface counters",
                )
            
            key = f"{target.host}:{interface_index}"
            now = datetime.now()
            
            if link_speed:
                self._link_speeds[key] = link_speed
            
            if key in self._last_values:
                last_time, last_in, last_out = self._last_values[key]
                time_diff = (now - last_time).total_seconds()
                
                if time_diff > 0:
                    in_bps = (int(in_octets) - int(last_in)) * 8 / time_diff
                    out_bps = (int(out_octets) - int(last_out)) * 8 / time_diff
                    
                    in_mbps = in_bps / 1_000_000
                    out_mbps = out_bps / 1_000_000
                    total_mbps = in_mbps + out_mbps
                    
                    self._last_values[key] = (now, in_octets, out_octets)
                    
                    status = Status.UP
                    error_msg = None
                    
                    if link_speed:
                        speed_limit_mbps = link_speed.to_mbps() / 1_000
                        utilization = (total_mbps / speed_limit_mbps) * 100
                        
                        if utilization > 95:
                            status = Status.DEGRADED
                            error_msg = f"High utilization: {utilization:.1f}%"
                        elif utilization > 90:
                            status = Status.DEGRADED
                        
                        latency_val = utilization
                    else:
                        latency_val = in_mbps
                    
                    return Metric(
                        target_id=target.id,
                        timestamp=now,
                        check_type=CheckType.BANDWIDTH,
                        value=total_mbps,
                        status=status,
                        latency_ms=latency_val,
                        error=error_msg,
                    )
            
            self._last_values[key] = (now, in_octets, out_octets)
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.BANDWIDTH,
                value=0.0,
                status=Status.UP,
                error="Initial measurement",
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

    def _get_link_speed(self, host: str, community: str, interface_index: int) -> Optional[NetworkSpeed]:
        try:
            high_speed = self._snmp_get(host, community, f"{BANDWIDTH_OIDS['ifHighSpeed']}.{interface_index}")
            
            if high_speed:
                mbps = int(high_speed)
                return NetworkSpeed.from_mbps(mbps)
            
            speed = self._snmp_get(host, community, f"{BANDWIDTH_OIDS['ifSpeed']}.{interface_index}")
            
            if speed:
                mbps = int(speed) // 1_000_000
                return NetworkSpeed.from_mbps(mbps)
                
        except:
            pass
        
        return None

    def _snmp_get(self, host: str, community: str, oid: str) -> Optional[str]:
        try:
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, 161), timeout=self.timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                return None
            
            for varBind in varBinds:
                return str(varBind[1])
        except:
            pass
        
        return None

    def get_interface_list(self, host: str, community: str = "public") -> List[dict]:
        interfaces = []
        
        try:
            iterator = nextCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, 161), timeout=self.timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity("1.3.6.1.2.1.2.2.1.2")),
                lexicographicMode=False
            )
            
            for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                if errorIndication:
                    break
                
                for varBind in varBinds:
                    oid = str(varBind[0])
                    index = oid.split(".")[-1]
                    name = str(varBind[1])
                    
                    high_speed = self._snmp_get(host, community, f"{BANDWIDTH_OIDS['ifHighSpeed']}.{index}")
                    speed_mbps = int(high_speed) if high_speed else 0
                    speed_label = NetworkSpeed.from_mbps(speed_mbps).value if speed_mbps else "Unknown"
                    
                    interfaces.append({
                        "index": index,
                        "name": name,
                        "speed": speed_label,
                        "speed_mbps": speed_mbps,
                    })
                    
                if len(interfaces) >= 50:
                    break
                    
        except:
            pass
        
        return interfaces

    def get_all_interface_speeds(self, host: str, community: str = "public") -> dict:
        speeds = {}
        interfaces = self.get_interface_list(host, community)
        
        for iface in interfaces:
            speeds[iface["index"]] = {
                "name": iface["name"],
                "speed": iface["speed"],
                "speed_mbps": iface["speed_mbps"],
            }
        
        return speeds

    def set_baseline(self, target_id: str, speed: float):
        self._speed_baseline[target_id] = speed

    def check_speed_change(self, host: str, interface_index: int) -> Optional[str]:
        key = f"{host}:{interface_index}"
        
        if key not in self._link_spepeeds:
            return None
        
        current_speed = self._link_speeds[key]
        
        if key in self._speed_baseline:
            baseline = self._speed_baseline[key]
            
            if current_speed != baseline:
                return f"Link speed changed from {baseline.value} to {current_speed.value}"
        
        self._speed_baseline[key] = current_speed
        return None
