"""AI-powered network database integration for enhanced support."""

import logging
import json
import requests
from typing import Optional, dict, list, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    MAC_VENDOR_DB = "mac_vendor"
    OID_DB = "oid_repository"
    VULNERABILITY_DB = "cve"
    DEVICE_COMPATIBILITY_DB = "compatibility"
    NETWORK_PROTOCOLS_DB = "protocols"


@dataclass
class VendorLookupResult:
    vendor_name: str
    mac_prefix: str
    description: str
    confidence: float


@dataclass
class OIDLookupResult:
    oid: str
    name: str
    description: str
    vendor: str
    mib: str
    access: str
    data_type: str


@dataclass
class DeviceCompatibilityInfo:
    vendor: str
    model: str
    supported_protocols: list[str]
    snmp_oids: dict
    known_issues: list[dict]
    firmware_versions: list[dict]


class OpenSourceDBIntegrator:
    IEEE_OUI_URL = "https://standards-oui.ieee.org/oui/oui.csv"
    WIKIPEDIA_MAC_URL = "https://en.wikipedia.org/wiki/Organizational_Unique_Identifier"
    
    SNMP_OID_REPOSITORIES = [
        "https://oidref.com",
        "http://www.oid-info.com",
    ]
    
    CVE_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, cache_dir: str = None):
        self._mac_cache: dict[str, VendorLookupResult] = {}
        self._oid_cache: dict[str, OIDLookupResult] = {}
        self._compatibility_cache: dict[str, DeviceCompatibilityInfo] = {}
        self._cache_expiry = 86400

    def lookup_mac_vendor(self, mac_address: str) -> Optional[VendorLookupResult]:
        mac_clean = mac_address.replace(":", "").replace("-", "").upper()
        mac_prefix = mac_clean[:6]
        
        if mac_prefix in self._mac_cache:
            return self._mac_cache[mac_prefix]
        
        try:
            response = requests.get(
                f"https://api.macvendors.com/{mac_prefix}",
                timeout=5
            )
            
            if response.status_code == 200:
                vendor = response.text.strip()
                result = VendorLookupResult(
                    vendor_name=vendor,
                    mac_prefix=mac_prefix,
                    description="IEEE registered vendor",
                    confidence=0.95,
                )
                self._mac_cache[mac_prefix] = result
                return result
                
        except Exception as e:
            logger.debug(f"MAC vendor lookup failed: {e}")
        
        return self._lookup_mac_local(mac_prefix)

    def _lookup_mac_local(self, mac_prefix: str) -> Optional[VendorLookupResult]:
        local_db = {
            "000C29": "VMware",
            "005056": "VMware",
            "001A2B": " MikroTik",
            "002315": "Ubiquiti",
            "002721": "Ubiquiti",
            "0024E8": "MikroTik",
            "4CDFA5": "Ubiquiti",
            "6CB8E5": "Ubiquiti",
            "F48E38": "Ubiquiti",
            "001122": "Cisco",
            "000E08": "Cisco",
            "001A2B": "MikroTik",
            "001B21": "MikroTik",
            "002315": "Ubiquiti Networks",
            "503EAA": "TP-Link",
            "50C7BF": "TP-Link",
            "A42B95": "Raspberry Pi",
            "D863FF": "Xiaomi",
            "64B473": "Hewlett-Packard",
            "00155D": "Microsoft",
            "001F3B": "Dell",
            "0021F6": "Apple",
            "F0DEF1": "Apple",
            "3C22FB": "Apple",
        }
        
        vendor = local_db.get(mac_prefix)
        
        if vendor:
            result = VendorLookupResult(
                vendor_name=vendor,
                mac_prefix=mac_prefix,
                description="Local MAC database",
                confidence=0.7,
            )
            self._mac_cache[mac_prefix] = result
            return result
        
        return VendorLookupResult(
            vendor_name="Unknown",
            mac_prefix=mac_prefix,
            description="Vendor not in local database",
            confidence=0.0,
        )

    def lookup_oid(self, oid: str) -> Optional[OIDLookupResult]:
        oid_clean = oid.strip()
        
        if oid_clean in self._oid_cache:
            return self._oid_cache[oid_clean]
        
        result = self._lookup_oid_online(oid_clean)
        
        if result:
            self._oid_cache[oid_clean] = result
            return result
        
        return self._lookup_oid_local(oid_clean)

    def _lookup_oid_online(self, oid: str) -> Optional[OIDLookupResult]:
        try:
            response = requests.get(
                f"https://oidref.com/{oid}",
                timeout=10,
                headers={"User-Agent": "NetworkMonitor/1.0"}
            )
            
            if response.status_code == 200:
                return self._parse_oid_response(oid, response.text)
                
        except Exception as e:
            logger.debug(f"OID lookup failed: {e}")
        
        return None

    def _parse_oid_response(self, oid: str, html: str) -> Optional[OIDLookupResult]:
        import re
        
        name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        desc_match = re.search(r'<dd[^>]*>([^<]+)</dd>', html)
        
        if name_match:
            return OIDLookupResult(
                oid=oid,
                name=name_match.group(1).strip(),
                description=desc_match.group(1).strip() if desc_match else "",
                vendor="Unknown",
                mib="Unknown",
                access="read-write",
                data_type="counter",
            )
        
        return None

    def _lookup_oid_local(self, oid: str) -> Optional[OIDLookupResult]:
        oid_db = {
            "1.3.6.1.2.1.1.1.0": OIDLookupResult(
                oid="1.3.6.1.2.1.1.1.0",
                name="sysDescr",
                description="System description",
                vendor="SNMP",
                mib="SNMPv2-MIB",
                access="read-only",
                data_type="displaystring",
            ),
            "1.3.6.1.2.1.1.3.0": OIDLookupResult(
                oid="1.3.6.1.2.1.1.3.0",
                name="sysUpTime",
                description="System uptime in timeticks",
                vendor="SNMP",
                mib="SNMPv2-MIB",
                access="read-only",
                data_type="timeticks",
            ),
            "1.3.6.1.2.1.1.5.0": OIDLookupResult(
                oid="1.3.6.1.2.1.1.5.0",
                name="sysName",
                description="System name",
                vendor="SNMP",
                mib="SNMPv2-MIB",
                access="read-write",
                data_type="displaystring",
            ),
            "1.3.6.1.2.1.2.2.1.10": OIDLookupResult(
                oid="1.3.6.1.2.1.2.2.1.10",
                name="ifInOctets",
                description="Inbound octets on interface",
                vendor="SNMP",
                mib="IF-MIB",
                access="read-only",
                data_type="counter",
            ),
            "1.3.6.1.2.1.2.2.1.16": OIDLookupResult(
                oid="1.3.6.1.2.1.2.2.1.16",
                name="ifOutOctets",
                description="Outbound octets on interface",
                vendor="SNMP",
                mib="IF-MIB",
                access="read-only",
                data_type="counter",
            ),
            "1.3.6.1.4.1.9.9.109.1.1.1.1.5": OIDLookupResult(
                oid="1.3.6.1.4.1.9.9.109.1.1.1.1.5",
                name="ciscoCPUTotal5min",
                description="Cisco CPU 5 minute average",
                vendor="Cisco",
                mib="CISCO-PROCESS-MIB",
                access="read-only",
                data_type="gauge",
            ),
            "1.3.6.1.4.1.2636.3.1.2.1.6": OIDLookupResult(
                oid="1.3.6.1.4.1.2636.3.1.2.1.6",
                name="jnxOperatingCPU",
                description="Juniper CPU utilization",
                vendor="Juniper",
                mib="JUNIPER-MIB",
                access="read-only",
                data_type="gauge",
            ),
            "1.3.6.1.4.1.14988.1.1.1.2.0": OIDLookupResult(
                oid="1.3.6.1.4.1.14988.1.1.1.2.0",
                name="mtxrCpuLoad",
                description="MikroTik CPU load",
                vendor="MikroTik",
                mib="MIKROTIK-MIB",
                access="read-only",
                data_type="gauge",
            ),
            "1.3.6.1.4.1.41112.1.4.1.0": OIDLookupResult(
                oid="1.3.6.1.4.1.41112.1.4.1.0",
                name="ubntGenericUptime",
                description="Ubiquiti device uptime",
                vendor="Ubiquiti",
                mib="UBNT-MIB",
                access="read-only",
                data_type="timeticks",
            ),
        }
        
        return oid_db.get(oid)

    def lookup_cve(self, vendor: str, product: str) -> list[dict]:
        results = []
        
        try:
            query = f"keywordSearch:{vendor}+AND+{product}"
            response = requests.get(
                f"{self.CVE_API_BASE}?keywordSearch={vendor}+{product}&resultsPerPage=5",
                timeout=10,
                headers={"User-Agent": "NetworkMonitor/1.0"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data.get("vulnerabilities", []):
                    cve = item.get("cve", {})
                    results.append({
                        "id": cve.get("id"),
                        "description": cve.get("descriptions", [{}])[0].get("value", "")[:200],
                        "severity": cve.get("metrics", {}).get("cvssMetricV31", [{}])[0].get("cvssData", {}).get("baseSeverity", "UNKNOWN"),
                    })
                    
        except Exception as e:
            logger.debug(f"CVE lookup failed: {e}")
        
        return results[:5]

    def get_device_compatibility(self, vendor: str, model: str) -> Optional[DeviceCompatibilityInfo]:
        cache_key = f"{vendor}:{model}"
        
        if cache_key in self._compatibility_cache:
            return self._compatibility_cache[cache_key]
        
        compatibility_data = self._fetch_compatibility_from_api(vendor, model)
        
        if compatibility_data:
            self._compatibility_cache[cache_key] = compatibility_data
            return compatibility_data
        
        return None

    def _fetch_compatibility_from_api(self, vendor: str, model: str) -> Optional[DeviceCompatibilityInfo]:
        vendor_lower = vendor.lower()
        
        if "cisco" in vendor_lower:
            return DeviceCompatibilityInfo(
                vendor="Cisco",
                model=model,
                supported_protocols=["SNMP v1", "SNMP v2c", "SNMP v3", "NETCONF", "RESTCONF", "SSH", "Telnet"],
                snmp_oids={
                    "cpu": "1.3.6.1.4.1.9.9.109.1.1.1.1.5",
                    "memory": "1.3.6.1.4.1.9.9.48.1.1.5",
                    "interface": "1.3.6.1.2.1.2.2.1.10",
                    "temperature": "1.3.6.1.4.1.9.9.13.1.5.1.3",
                    "fan": "1.3.6.1.4.1.9.9.13.1.4.1.2",
                },
                known_issues=[
                    {"issue": "SNMPv3 auth", "description": "Use SHA auth for Cisco IOS"},
                    {"issue": "High CPU", "description": "Check for SPAN traffic"},
                ],
                firmware_versions=[],
            )
        
        elif "juniper" in vendor_lower:
            return DeviceCompatibilityInfo(
                vendor="Juniper",
                model=model,
                supported_protocols=["SNMP v1", "SNMP v2c", "SNMP v3", "NETCONF", "SSH", "J-Web"],
                snmp_oids={
                    "cpu": "1.3.6.1.4.1.2636.3.1.2.1.6",
                    "memory": "1.3.6.1.4.1.2636.3.1.2.1.7",
                    "temperature": "1.3.6.1.4.1.2636.3.1.2.1.9",
                    "fan": "1.3.6.1.4.1.2636.3.1.7.1.1.2",
                },
                known_issues=[],
                firmware_versions=[],
            )
        
        elif "ubiquiti" in vendor_lower:
            return DeviceCompatibilityInfo(
                vendor="Ubiquiti",
                model=model,
                supported_protocols=["SNMP v2c", "SSH", "HTTP", "HTTPS"],
                snmp_oids={
                    "signal": "1.3.6.1.4.1.41112.1.5.1.1",
                    "txpower": "1.3.6.1.4.1.41112.1.5.2.1.3",
                    "channel": "1.3.6.1.4.1.41112.1.5.2.1.4",
                    "uptime": "1.3.6.1.4.1.41112.1.4.1.0",
                },
                known_issues=[
                    {"issue": "AirMax", "description": "Requires AirMax enabled for P2P"},
                ],
                firmware_versions=[],
            )
        
        elif "mikrotik" in vendor_lower:
            return DeviceCompatibilityInfo(
                vendor="MikroTik",
                model=model,
                supported_protocols=["SNMP v1", "SNMP v2c", "SNMP v3", "API", "SSH", "Winbox"],
                snmp_oids={
                    "cpu": "1.3.6.1.4.1.14988.1.1.1.2.0",
                    "memory": "1.3.6.1.4.1.14988.1.1.1.3.0",
                    "temperature": "1.3.6.1.4.1.14988.1.1.1.7.0",
                    "voltage": "1.3.6.1.4.1.14988.1.1.1.8.0",
                },
                known_issues=[],
                firmware_versions=[],
            )
        
        return None

    def get_protocol_info(self, protocol: str) -> dict:
        protocols = {
            "snmp": {
                "name": "Simple Network Management Protocol",
                "ports": [161, 162],
                "versions": ["v1", "v2c", "v3"],
                "security": ["community", "user-based"],
            },
            "netconf": {
                "name": "Network Configuration Protocol",
                "port": 830,
                "transport": ["SSH", "TLS"],
            },
            "ssh": {
                "name": "Secure Shell",
                "port": 22,
                "versions": ["SSHv1", "SSHv2"],
            },
            "http": {
                "name": "HyperText Transfer Protocol",
                "port": 80,
            },
            "https": {
                "name": "HTTP Secure",
                "port": 443,
            },
        }
        
        return protocols.get(protocol.lower(), {})

    def suggest_oid_for_metric(self, vendor: str, metric: str) -> Optional[str]:
        vendor_lower = vendor.lower()
        
        oid_map = {
            "cpu": {
                "cisco": "1.3.6.1.4.1.9.9.109.1.1.1.1.5",
                "juniper": "1.3.6.1.4.1.2636.3.1.2.1.6",
                "mikrotik": "1.3.6.1.4.1.14988.1.1.1.2.0",
                "ubiquiti": "1.3.6.1.4.1.41112.1.4.2.0",
                "hpe": "1.3.6.1.4.1.11.2.14.11.5.1.1.1",
            },
            "memory": {
                "cisco": "1.3.6.1.4.1.9.9.48.1.1.5",
                "juniper": "1.3.6.1.4.1.2636.3.1.2.1.7",
                "mikrotik": "1.3.6.1.4.1.14988.1.1.1.3.0",
            },
            "temperature": {
                "cisco": "1.3.6.1.4.1.9.9.13.1.5.1.3",
                "juniper": "1.3.6.1.4.1.2636.3.1.2.1.9",
                "mikrotik": "1.3.6.1.4.1.14988.1.1.1.7.0",
            },
            "bandwidth": {
                "generic": "1.3.6.1.2.1.2.2.1.10",
            },
        }
        
        metric_lower = metric.lower()
        
        if metric_lower in oid_map:
            for v, oid in oid_map[metric_lower].items():
                if v in vendor_lower:
                    return oid
            
            if "generic" in oid_map[metric_lower]:
                return oid_map[metric_lower]["generic"]
        
        return None
