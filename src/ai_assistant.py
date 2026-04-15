"""AI-powered assistant for network monitoring."""

import re
import logging
from typing import Optional, dict, list, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    SUGGESTION = "suggestion"


class IssueCategory(Enum):
    COMPATIBILITY = "compatibility"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    SECURITY = "security"
    PERFORMANCE = "performance"
    HARDWARE = "hardware"


@dataclass
class AIIssue:
    id: str
    category: IssueCategory
    severity: IssueSeverity
    title: str
    description: str
    affected_device: str
    fix_suggestion: Optional[str] = None
    auto_fixable: bool = False
    confidence: float = 0.0
    related_oids: list[str] = field(default_factory=list)


@dataclass
class DeviceAnalysis:
    device_id: str
    device_type: str
    vendor: str
    model: str
    firmware: str
    detected_issues: list[AIIssue] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    compatibility_score: float = 0.0
    health_score: float = 0.0


class AIDeviceAnalyzer:
    VENDOR_PATTERNS = {
        "cisco": ["cisco", "ios", "nxos", "nexus", "catalyst", "ios-xe"],
        "juniper": ["juniper", "junos", "mx", "ex", "srx"],
        "ubiquiti": ["ubiquiti", "unifi", "airmax", "edge", " nanostation"],
        "mikrotik": ["mikrotik", "routeros", "routerboard"],
        "netonix": ["netonix", "switch"],
        "hpe": ["hpe", "procurve", "aruba", "comware"],
        "dell": ["dell", "force10", "iom", "networking"],
        "fortinet": ["fortinet", "fortigate", "fortios"],
        "palo alto": ["palo alto", "panos", "pan-os"],
        "aruba": ["aruba", "airwave", "central"],
    }

    DEVICE_TYPE_KEYWORDS = {
        "router": ["router", "gateway", "core"],
        "switch": ["switch", "layer", "stack"],
        "firewall": ["firewall", "security", "fortigate", "srx", "palo"],
        "wireless": ["wireless", "wifi", "ap", "access point", "airmax", "bullet"],
        "server": ["server", "host", "vmware", "hyper-v"],
        "firewall": ["firewall", "security"],
    }

    SNMP_COMPATIBILITY_MAP = {
        "cisco": {
            "community": "public",
            "snmp_version": "v2c",
            "typical_oids": [
                "1.3.6.1.2.1.1.1.0",
                "1.3.6.1.2.1.1.5.0",
                "1.3.6.1.4.1.9.9.109.1.1.1.1.5",
            ],
        },
        "juniper": {
            "community": "public",
            "snmp_version": "v2c",
            "typical_oids": [
                "1.3.6.1.2.1.1.1.0",
                "1.3.6.1.2.1.1.5.0",
                "1.3.6.1.4.1.2636.3.1.2.1.6",
            ],
        },
        "ubiquiti": {
            "community": "ubiquiti",
            "snmp_version": "v2c",
            "typical_oids": [
                "1.3.6.1.4.1.41112.1.4.1.0",
                "1.3.6.1.4.1.41112.1.4.2.0",
            ],
        },
        "mikrotik": {
            "community": "public",
            "snmp_version": "v2c",
            "typical_oids": [
                "1.3.6.1.2.1.1.1.0",
                "1.3.6.1.4.1.14988.1.1.1.1.0",
            ],
        },
    }

    def __init__(self):
        self.issue_history: list[AIIssue] = []
        self.device_patterns: dict = {}

    def analyze_device(self, sys_descr: str, vendor: str = None) -> DeviceAnalysis:
        detected_vendor = vendor or self.detect_vendor(sys_descr)
        device_type = self.detect_device_type(sys_descr)
        
        analysis = DeviceAnalysis(
            device_id="",
            device_type=device_type,
            vendor=detected_vendor,
            model=self.extract_model(sys_descr),
            firmware=self.extract_firmware(sys_descr),
        )
        
        self._check_compatibility(analysis)
        self._check_performance(analysis)
        self._generate_recommendations(analysis)
        
        return analysis

    def detect_vendor(self, sys_descr: str) -> str:
        descr_lower = sys_descr.lower()
        
        for vendor, patterns in self.VENDOR_PATTERNS.items():
            for pattern in patterns:
                if pattern in descr_lower:
                    return vendor
        
        return "generic"

    def detect_device_type(self, sys_descr: str) -> str:
        descr_lower = sys_descr.lower()
        
        for dtype, keywords in self.DEVICE_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in descr_lower:
                    return dtype
        
        return "unknown"

    def extract_model(self, sys_descr: str) -> str:
        patterns = [
            r'(?:Model|Catalyst|Switch|Router)\s+(\S+)',
            r'(\w+\s+\d+\S+)',
            r'([A-Z]{2,}\d+[A-Z]*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sys_descr, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Unknown"

    def extract_firmware(self, sys_descr: str) -> str:
        patterns = [
            r'Version\s+(\S+)',
            r'Firmware\s+(\S+)',
            r'IOS\s+(\S+)',
            r'JUNOS\s+(\S+)',
            r'RouterOS\s+v?(\S+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, sys_descr, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Unknown"

    def _check_compatibility(self, analysis: DeviceAnalysis):
        vendor = analysis.vendor
        issues = []
        
        if vendor in self.SNMP_COMPATIBILITY_MAP:
            config = self.SNMP_COMPATIBILITY_MAP[vendor]
            
            if config["snmp_version"] == "v2c":
                issues.append(AIIssue(
                    id=f"compat-{vendor}-1",
                    category=IssueCategory.COMPATIBILITY,
                    severity=IssueSeverity.INFO,
                    title=f"SNMP v2c for {vendor}",
                    description=f"Use SNMP community '{config['community']}' for {vendor} devices",
                    affected_device=analysis.device_id,
                    fix_suggestion=f"Set SNMP community to '{config['community']}'",
                    confidence=0.9,
                ))
            
            analysis.compatibility_score = 0.85
        else:
            analysis.compatibility_score = 0.5
            issues.append(AIIssue(
                id=f"compat-{vendor}-unknown",
                category=IssueCategory.COMPATIBILITY,
                severity=IssueSeverity.WARNING,
                title=f"Unknown vendor: {vendor}",
                description=f"Vendor '{vendor}' not in known compatibility list",
                affected_device=analysis.device_id,
                fix_suggestion="Try using generic SNMP settings",
                confidence=0.7,
            ))
        
        analysis.detected_issues.extend(issues)

    def _check_performance(self, analysis: DeviceAnalysis):
        issues = []
        
        if analysis.vendor == "cisco":
            issues.append(AIIssue(
                id=f"perf-{analysis.vendor}-cpu",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.SUGGESTION,
                title="CPU monitoring for Cisco",
                description="Monitor CPU using OID 1.3.6.1.4.1.9.9.109.1.1.1.1.5",
                affected_device=analysis.device_id,
                related_oids=["1.3.6.1.4.1.9.9.109.1.1.1.1.5"],
            ))
        
        elif analysis.vendor == "juniper":
            issues.append(AIIssue(
                id=f"perf-{analysis.vendor}-cpu",
                category=IssueCategory.PERFORMANCE,
                severity=IssueSeverity.SUGGESTION,
                title="CPU monitoring for Juniper",
                description="Monitor CPU using OID 1.3.6.1.4.1.2636.3.1.2.1.6",
                affected_device=analysis.device_id,
                related_oids=["1.3.6.1.4.1.2636.3.1.2.1.6"],
            ))
        
        analysis.detected_issues.extend(issues)
        analysis.health_score = 0.8

    def _generate_recommendations(self, analysis: DeviceAnalysis):
        recs = []
        
        if analysis.vendor == "ubiquiti":
            recs.append("Use Ubiquiti-specific OIDs for signal strength monitoring")
            recs.append("Enable AirMax for PtP links")
        
        elif analysis.vendor == "mikrotik":
            recs.append("Monitor wireless registration table for client info")
            recs.append("Use RouterOS API for detailed metrics")
        
        elif analysis.vendor == "cisco":
            recs.append("Enable CDP/LLDP for auto-discovery")
            recs.append("Use VTP monitoring for VLAN changes")
        
        analysis.recommendations = recs


class AIDiscoveryAssistant:
    def __init__(self):
        self.analyzer = AIDeviceAnalyzer()
        self.discovery_history: list[dict] = []

    def enhance_discovery(self, host: str, snmp_data: dict) -> dict:
        sys_descr = snmp_data.get("sysDescr", "")
        sys_name = snmp_data.get("sysName", "")
        
        if not sys_descr:
            return {
                "host": host,
                "vendor_detected": "unknown",
                "device_type": "unknown",
                "issues": [],
                "recommendations": ["No SNMP data received - check connectivity"],
            }
        
        analysis = self.analyzer.analyze_device(sys_descr)
        analysis.device_id = host
        
        return {
            "host": host,
            "vendor_detected": analysis.vendor,
            "device_type": analysis.device_type,
            "model": analysis.model,
            "firmware": analysis.firmware,
            "issues": [
                {
                    "id": i.id,
                    "title": i.title,
                    "description": i.description,
                    "severity": i.severity.value,
                    "fix_suggestion": i.fix_suggestion,
                    "auto_fixable": i.auto_fixable,
                }
                for i in analysis.detected_issues
            ],
            "recommendations": analysis.recommendations,
            "compatibility_score": analysis.compatibility_score,
            "health_score": analysis.health_score,
        }

    def get_compatible_oids(self, vendor: str) -> list[dict]:
        return AIDeviceAnalyzer.SNMP_COMPATIBILITY_MAP.get(vendor, {}).get("typical_oids", [])

    def resolve_conflict(self, device_info: dict, issue_type: str) -> dict:
        resolution = {
            "issue": issue_type,
            "actions": [],
            "confidence": 0.0,
        }
        
        if issue_type == "snmp_timeout":
            resolution["actions"] = [
                "Increase SNMP timeout to 10 seconds",
                "Check firewall rules for UDP port 161",
                "Verify SNMP community string",
                "Try SNMP v1 instead of v2c",
            ]
            resolution["confidence"] = 0.85
        
        elif issue_type == "vendor_mismatch":
            detected = device_info.get("vendor_detected", "unknown")
            specified = device_info.get("device_type", "")
            
            resolution["actions"] = [
                f"Update device type to '{detected}'",
                "Re-run discovery to confirm",
                "Clear device cache and retry",
            ]
            resolution["confidence"] = 0.7
        
        elif issue_type == "bandwidth_anomaly":
            resolution["actions"] = [
                "Check interface errors",
                "Verify duplex mismatch",
                "Monitor for traffic spikes",
                "Check for spanning tree issues",
            ]
            resolution["confidence"] = 0.8
        
        return resolution

    def predict_issues(self, metrics_history: list[dict]) -> list[dict]:
        predictions = []
        
        if len(metrics_history) < 5:
            return predictions
        
        latency_values = [m.get("latency_ms", 0) for m in metrics_history]
        
        if latency_values and all(latency_values[-1] > lat * 1.5 for lat in latency_values[:-1]):
            predictions.append({
                "issue": "latency_spike",
                "probability": 0.75,
                "description": "Latency has been increasing significantly",
                "action": "Check network congestion or device CPU",
            })
        
        packet_loss = [100 - m.get("value", 100) for m in metrics_history]
        if packet_loss and packet_loss[-1] > 5:
            predictions.append({
                "issue": "packet_loss_increase",
                "probability": 0.8,
                "description": "Packet loss detected",
                "action": "Check physical connections and interface errors",
            })
        
        return predictions


class AIConfigAssistant:
    @staticmethod
    def suggest_monitoring_config(device_type: str, vendor: str) -> dict:
        configs = {
            "cisco": {
                "check_type": "snmp",
                "snmp_oids": {
                    "cpu": "1.3.6.1.4.1.9.9.109.1.1.1.1.5",
                    "memory": "1.3.6.1.4.1.9.9.48.1.1.5",
                    "interface": "1.3.6.1.2.1.2.2.1.10",
                },
                "interval": 60,
                "timeout": 10,
            },
            "juniper": {
                "check_type": "snmp",
                "snmp_oids": {
                    "cpu": "1.3.6.1.4.1.2636.3.1.2.1.6",
                    "memory": "1.3.6.1.4.1.2636.3.1.2.1.7",
                    "temperature": "1.3.6.1.4.1.2636.3.1.2.1.9",
                },
                "interval": 60,
                "timeout": 10,
            },
            "ubiquiti": {
                "check_type": "snmp",
                "snmp_oids": {
                    "signal": "1.3.6.1.4.1.41112.1.5.1.1",
                    "txpower": "1.3.6.1.4.1.41112.1.5.2.1.3",
                    "channel": "1.3.6.1.4.1.41112.1.5.2.1.4",
                },
                "interval": 30,
                "timeout": 5,
            },
            "mikrotik": {
                "check_type": "snmp",
                "snmp_oids": {
                    "cpu": "1.3.6.1.4.1.14988.1.1.1.2.0",
                    "memory": "1.3.6.1.4.1.14988.1.1.1.3.0",
                    "temperature": "1.3.6.1.4.1.14988.1.1.1.7.0",
                },
                "interval": 60,
                "timeout": 5,
            },
        }
        
        return configs.get(vendor, {
            "check_type": "ping",
            "interval": 60,
            "timeout": 5,
        })

    @staticmethod
    def validate_target_config(config: dict) -> list[dict]:
        issues = []
        
        if config.get("check_type") == "snmp" and not config.get("snmp_community"):
            issues.append({
                "field": "snmp_community",
                "severity": "error",
                "message": "SNMP community required for SNMP monitoring",
            })
        
        if config.get("check_type") == "snmp" and config.get("timeout", 0) < 3:
            issues.append({
                "field": "timeout",
                "severity": "warning",
                "message": "SNMP timeout should be at least 3 seconds",
            })
        
        if config.get("interval", 0) < 10:
            issues.append({
                "field": "interval",
                "severity": "warning",
                "message": "Interval below 10 seconds may cause network load",
            })
        
        return issues
