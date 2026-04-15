"""Network auto-discovery module."""

import socket
import subprocess
import ipaddress
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.models import CheckType


class NetworkDiscovery:
    def __init__(self, timeout: int = 2, max_workers: 50):
        self.timeout = timeout
        self.max_workers = max_workers

    def scan_network(self, network: str) -> list[dict]:
        net = ipaddress.ip_network(network, strict=False)
        hosts = list(net.hosts())
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._ping_host, str(host)): host for host in hosts}
            
            for future in as_completed(futures):
                host = futures[future]
                try:
                    if future.result():
                        results.append({
                            "host": str(host),
                            "status": "up",
                            "discovered_at": datetime.now().isoformat(),
                        })
                except:
                    pass
        
        return results

    def _ping_host(self, host: str) -> bool:
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(self.timeout * 1000), host],
                capture_output=True,
                timeout=self.timeout + 1,
            )
            return result.returncode == 0
        except:
            return False

    def scan_ports(self, host: str, ports: list[int] = [22, 80, 443, 3389, 445]) -> list[dict]:
        results = []
        
        for port in ports:
            if self._check_port(host, port):
                service = self._get_service_name(port)
                results.append({
                    "port": port,
                    "service": service,
                    "status": "open",
                })
        
        return results

    def _check_port(self, host: str, port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    def _get_service_name(self, port: int) -> str:
        services = {
            22: "SSH",
            23: "Telnet",
            25: "SMTP",
            53: "DNS",
            80: "HTTP",
            110: "POP3",
            143: "IMAP",
            443: "HTTPS",
            445: "SMB",
            3306: "MySQL",
            3389: "RDP",
            5432: "PostgreSQL",
            8080: "HTTP-Alt",
            8443: "HTTPS-Alt",
        }
        return services.get(port, "Unknown")

    def discover_snmp_devices(self, network: str, community: str = "public") -> list[dict]:
        hosts = self.scan_network(network)
        devices = []
        
        for host_info in hosts:
            host = host_info["host"]
            
            sysDescr = self._snmp_walk(host, community, "1.3.6.1.2.1.1.1.0")
            sysName = self._snmp_walk(host, community, "1.3.6.1.2.1.1.5.0")
            
            if sysDescr:
                devices.append({
                    "host": host,
                    "type": "snmp",
                    "description": sysDescr,
                    "name": sysName,
                    "discovered_at": datetime.now().isoformat(),
                })
        
        return devices

    def _snmp_walk(self, host: str, community: str, oid: str) -> Optional[str]:
        try:
            from pysnmp.hlapi import *
            
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community, mpModel=0),
                UdpTransportTarget((host, 161), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity(oid))
            )
            
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if not errorIndication:
                for varBind in varBinds:
                    return str(varBind[1])
        except:
            pass
        
        return None
