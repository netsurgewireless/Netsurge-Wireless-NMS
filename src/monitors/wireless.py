"""Wireless/P2P radio monitoring for point-to-point links."""

import re
import subprocess
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from src.models import Metric, Status, CheckType, MonitorTarget


@dataclass
class WirelessMetrics:
    ssid: Optional[str] = None
    signal_strength: Optional[int] = None
    tx_power: Optional[int] = None
    channel_width: Optional[int] = None
    frequency: Optional[float] = None
    link_quality: Optional[int] = None
    noise_floor: Optional[int] = None
    tx_rate: Optional[int] = None
    rx_rate: Optional[int] = None
    connected: bool = False
    uptime_seconds: Optional[int] = None


class WirelessMonitor:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        device_type = target.device_type.value
        
        if device_type in ["ubiquiti", "ubiquiti_edgeswitch", "ubiquiti_unifi"]:
            return self._check_ubiquiti(target)
        elif device_type == "mikrotik":
            return self._check_mikrotik(target)
        elif device_type == "cisco":
            return self._check_cisco_wireless(target)
        else:
            return self._check_generic_wireless(target)

    def _check_ubiquiti(self, target: MonitorTarget) -> Metric:
        try:
            community = target.snmp_community or "public"
            
            signal_oid = "1.3.6.1.4.1.41112.1.5.1.1"
            txpower_oid = "1.3.6.1.4.1.41112.1.5.2.1.3"
            channel_oid = "1.3.6.1.4.1.41112.1.5.2.1.4"
            freq_oid = "1.3.6.1.4.1.41112.1.5.2.1.5"
            
            from pysnmp.hlapi import *
            
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((target.host, 161), timeout=self.timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(signal_oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            signal = -75
            if not errorIndication:
                for varBind in varBinds:
                    signal = int(str(varBind[1]))
            
            status = Status.UP
            if signal < -85:
                status = Status.DEGRADED
            if signal < -90 or signal == 0:
                status = Status.DOWN
            
            health_score = self._calculate_wireless_health(signal)
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=float(health_score),
                status=status,
                latency_ms=float(signal),
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _check_mikrotik(self, target: MonitorTarget) -> Metric:
        try:
            community = target.snmp_community or "public"
            
            signal_oid = "1.3.6.1.4.1.14988.1.1.3.1.2.1"
            txpower_oid = "1.3.6.1.4.1.14988.1.1.3.1.2.2"
            freq_oid = "1.3.6.1.4.1.14988.1.1.3.1.2.3"
            
            from pysnmp.hlapi import *
            
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((target.host, 161), timeout=self.timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(signal_oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            signal = -75
            if not errorIndication:
                for varBind in varBinds:
                    signal = int(str(varBind[1]))
            
            status = Status.UP
            if signal < -80:
                status = Status.DEGRADED
            if signal < -90:
                status = Status.DOWN
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=float(signal),
                status=status,
                latency_ms=float(signal),
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _check_cisco_wireless(self, target: MonitorTarget) -> Metric:
        try:
            community = target.snmp_community or "public"
            
            ap_join_time = "1.3.6.1.4.1.9.9.513.1.1.1.1.3"
            client_count = "1.3.6.1.4.1.9.9.513.1.1.2.1.3"
            
            from pysnmp.hlapi import *
            
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((target.host, 161), timeout=self.timeout, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(ap_join_time))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.SNMP,
                    value=0.0,
                    status=Status.DOWN,
                    error="No SNMP response",
                )
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=100.0,
                status=Status.UP,
                latency_ms=0.0,
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _check_generic_wireless(self, target: MonitorTarget) -> Metric:
        try:
            result = subprocess.run(
                ["iwconfig"],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            
            signal = -75
            for line in result.stdout.split('\n'):
                if target.host.lower() in line.lower() or 'wlan' in line.lower():
                    sig_match = re.search(r'Signal level[=:](\-?\d+)', line)
                    if sig_match:
                        signal = int(sig_match.group(1))
            
            status = Status.UP
            if signal < -80:
                status = Status.DEGRADED
            if signal < -90:
                status = Status.DOWN
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=float(signal),
                status=status,
                latency_ms=float(signal),
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _calculate_wireless_health(self, signal: int) -> float:
        if signal >= -60:
            return 100.0
        elif signal >= -70:
            return 80.0
        elif signal >= -75:
            return 60.0
        elif signal >= -80:
            return 40.0
        elif signal >= -85:
            return 20.0
        else:
            return 0.0


class WirelessChangeDetector:
    def __init__(self):
        self._previous_state = {}
        self._history = {}

    def check_changes(self, target: MonitorTarget, metrics: WirelessMetrics) -> list[str]:
        changes = []
        key = target.id
        
        if key in self._previous_state:
            prev = self._previous_state[key]
            
            if prev.signal_strength != metrics.signal_strength:
                diff = abs(metrics.signal_strength - prev.signal_strength)
                if diff > 5:
                    changes.append(f"Signal changed by {diff} dBm: {prev.signal_strength} -> {metrics.signal_strength}")
            
            if prev.tx_power != metrics.tx_power:
                changes.append(f"TX Power changed: {prev.tx_power} -> {metrics.tx_power} dBm")
            
            if prev.channel_width != metrics.channel_width:
                changes.append(f"Channel width changed: {prev.channel_width} -> {metrics.channel_width} MHz")
            
            if prev.frequency != metrics.frequency:
                changes.append(f"Frequency changed: {prev.frequency} -> {metrics.frequency} MHz")
            
            if prev.connected != metrics.connected:
                if metrics.connected:
                    changes.append("Link established")
                else:
                    changes.append("Link lost - CRITICAL")
        
        self._previous_state[key] = metrics
        return changes

    def get_history(self, target_id: str) -> list[WirelessMetrics]:
        return self._history.get(target_id, [])

    def add_to_history(self, target_id: str, metrics: WirelessMetrics):
        if target_id not in self._history:
            self._history[target_id] = []
        
        self._history[target_id].append(metrics)
        
        if len(self._history[target_id]) > 100:
            self._history[target_id] = self._history[target_id][-100:]
