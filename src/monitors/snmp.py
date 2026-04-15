"""SNMP monitoring module."""

import socket
from datetime import datetime
from typing import Optional, Tuple

from pysnmp.hlapi import *
from src.models import Metric, Status, CheckType, MonitorTarget


class SNMPMonitor:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        if not target.snmp_oid:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SNMP,
                value=0.0,
                status=Status.DOWN,
                error="No SNMP OID specified",
            )

        try:
            community = target.snmp_community or "public"
            result = self._snmp_get(target.host, community, target.snmp_oid)
            
            if result is not None:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.SNMP,
                    value=float(result) if isinstance(result, (int, float)) else 1.0,
                    status=Status.UP,
                    latency_ms=self.timeout * 1000,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.SNMP,
                    value=0.0,
                    status=Status.DOWN,
                    error="SNMP timeout or no response",
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

    def _snmp_get(self, host: str, community: str, oid: str) -> Optional[str]:
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
        
        return None

    def get_bulk(self, host: str, community: str, oid_prefix: str, count: int = 10) -> dict:
        results = {}
        
        iterator = bulkCmd(
            SnmpEngine(),
            CommunityData(community, mpModel=0),
            UdpTransportTarget((host, 161), timeout=self.timeout, retries=1),
            ContextData(),
            0, count,
            ObjectType(ObjectIdentity(oid_prefix))
        )
        
        errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
        
        if errorIndication:
            return results
        
        for varBind in varBinds:
            oid = str(varBind[0])
            value = str(varBind[1])
            results[oid] = value
        
        return results
