"""Unified AI integration module combining assistant and database capabilities."""

import logging
from typing import Optional, dict, list, Any
from dataclasses import dataclass

from src.ai_assistant import (
    AIDeviceAnalyzer, AIDiscoveryAssistant, AIConfigAssistant,
    AIIssue, DeviceAnalysis, IssueSeverity, IssueCategory
)
from src.ai_database import OpenSourceDBIntegrator

logger = logging.getLogger(__name__)


class NetworkAI:
    def __init__(self):
        self.discovery_assistant = AIDiscoveryAssistant()
        self.config_assistant = AIConfigAssistant()
        self.db_integrator = OpenSourceDBIntegrator()

    def analyze_device(self, host: str, snmp_data: dict, mac_address: str = None) -> dict:
        result = self.discovery_assistant.enhance_discovery(host, snmp_data)
        
        if mac_address:
            vendor_info = self.db_integrator.lookup_mac_vendor(mac_address)
            if vendor_info:
                result["mac_vendor"] = vendor_info.vendor_name
                result["mac_confidence"] = vendor_info.confidence
        
        if snmp_data.get("sysDescr"):
            compat_info = self.db_integrator.get_device_compatibility(
                result.get("vendor_detected", "unknown"),
                result.get("model", "")
            )
            if compat_info:
                result["compatibility"] = {
                    "protocols": compat_info.supported_protocols,
                    "snmp_oids": compat_info.snmp_oids,
                    "known_issues": compat_info.known_issues,
                }
        
        return result

    def resolve_device_issue(self, device_info: dict, issue_type: str) -> dict:
        return self.discovery_assistant.resolve_conflict(device_info, issue_type)

    def predict_issues(self, metrics_history: list[dict]) -> list[dict]:
        return self.discovery_assistant.predict_issues(metrics_history)

    def suggest_config(self, device_type: str, vendor: str) -> dict:
        return self.config_assistant.suggest_monitoring_config(device_type, vendor)

    def validate_config(self, config: dict) -> list[dict]:
        return self.config_assistant.validate_target_config(config)

    def lookup_oid(self, oid: str) -> Optional[dict]:
        result = self.db_integrator.lookup_oid(oid)
        if result:
            return {
                "oid": result.oid,
                "name": result.name,
                "description": result.description,
                "vendor": result.vendor,
                "mib": result.mib,
                "access": result.access,
                "data_type": result.data_type,
            }
        return None

    def lookup_cve(self, vendor: str, product: str) -> list[dict]:
        return self.db_integrator.lookup_cve(vendor, product)

    def suggest_oid(self, vendor: str, metric: str) -> Optional[str]:
        return self.db_integrator.suggest_oid_for_metric(vendor, metric)

    def get_protocol_info(self, protocol: str) -> dict:
        return self.db_integrator.get_protocol_info(protocol)

    def full_diagnostic(self, host: str, snmp_data: dict, mac_address: str = None) -> dict:
        analysis = self.analyze_device(host, snmp_data, mac_address)
        
        suggestions = self.suggest_config(
            analysis.get("device_type", "generic"),
            analysis.get("vendor_detected", "generic")
        )
        analysis["recommended_config"] = suggestions
        
        config_issues = self.validate_config(suggestions)
        if config_issues:
            analysis["config_warnings"] = config_issues
        
        if snmp_data.get("sysDescr"):
            cve_results = self.lookup_cve(
                analysis.get("vendor_detected", ""),
                analysis.get("model", "")
            )
            if cve_results:
                analysis["cve_advisories"] = cve_results
        
        return analysis


def create_ai_routes(app, ai_instance: NetworkAI):
    from flask import Flask, jsonify, request
    
    @app.route("/api/ai/analyze", methods=["POST"])
    def ai_analyze_device():
        data = request.get_json()
        host = data.get("host", "")
        snmp_data = data.get("snmp_data", {})
        mac = data.get("mac_address")
        
        result = ai_instance.analyze_device(host, snmp_data, mac)
        return jsonify(result)

    @app.route("/api/ai/diagnostic", methods=["POST"])
    def ai_diagnostic():
        data = request.get_json()
        result = ai_instance.full_diagnostic(
            data.get("host", ""),
            data.get("snmp_data", {}),
            data.get("mac_address")
        )
        return jsonify(result)

    @app.route("/api/ai/resolve", methods=["POST"])
    def ai_resolve():
        data = request.get_json()
        result = ai_instance.resolve_device_issue(
            data.get("device_info", {}),
            data.get("issue_type", "")
        )
        return jsonify(result)

    @app.route("/api/ai/oid/<oid>", methods=["GET"])
    def ai_lookup_oid(oid):
        result = ai_instance.lookup_oid(oid)
        if result:
            return jsonify(result)
        return jsonify({"error": "OID not found"}), 404

    @app.route("/api/ai/cve", methods=["GET"])
    def ai_lookup_cve():
        vendor = request.args.get("vendor", "")
        product = request.args.get("product", "")
        result = ai_instance.lookup_cve(vendor, product)
        return jsonify({"cves": result})

    @app.route("/api/ai/suggest-oid", methods=["GET"])
    def ai_suggest_oid():
        vendor = request.args.get("vendor", "")
        metric = request.args.get("metric", "")
        result = ai_instance.suggest_oid(vendor, metric)
        if result:
            return jsonify({"oid": result, "vendor": vendor, "metric": metric})
        return jsonify({"error": "No suggestion available"}), 404

    @app.route("/api/ai/config", methods=["GET"])
    def ai_suggest_config():
        device_type = request.args.get("device_type", "generic")
        vendor = request.args.get("vendor", "generic")
        result = ai_instance.suggest_config(device_type, vendor)
        return jsonify(result)

    @app.route("/api/ai/protocol/<protocol>", methods=["GET"])
    def ai_protocol_info(protocol):
        result = ai_instance.get_protocol_info(protocol)
        return jsonify(result)
