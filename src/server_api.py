"""Server API for network monitor - exposes data for client applications."""

import json
from pathlib import Path
from flask import Flask, jsonify, request, g
from datetime import datetime, timedelta

from src.config import Config
from src.storage import Database
from src.alerts import AlertManager


def create_server_app(server_instance) -> Flask:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'network-monitor-secret-key'
    
    @app.before_request
    def before_request():
        g.server = server_instance
    
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "server_version": "1.0.0"
        })

    @app.route("/api/status", methods=["GET"])
    def status():
        summary = g.server.get_status_summary()
        return jsonify(summary)

    @app.route("/api/targets", methods=["GET"])
    def get_targets():
        targets = g.server.get_targets_status()
        return jsonify({"targets": targets})

    @app.route("/api/targets", methods=["POST"])
    def add_target():
        data = request.get_json()
        
        required = ["id", "name", "host", "check_type"]
        if not all(k in data for k in required):
            return jsonify({"error": "Missing required fields"}), 400
        
        if g.server.add_target(data):
            return jsonify({"success": True, "target_id": data["id"]}), 201
        return jsonify({"error": "Target already exists"}), 409

    @app.route("/api/targets/<target_id>", methods=["PUT"])
    def update_target(target_id):
        data = request.get_json()
        data["id"] = target_id
        
        if g.server.update_target(target_id, data):
            return jsonify({"success": True})
        return jsonify({"error": "Target not found"}), 404

    @app.route("/api/targets/<target_id>", methods=["DELETE"])
    def delete_target(target_id):
        if g.server.remove_target(target_id):
            return jsonify({"success": True})
        return jsonify({"error": "Target not found"}), 404

    @app.route("/api/targets/<target_id>/metrics", methods=["GET"])
    def get_metrics(target_id):
        limit = request.args.get("limit", 100, type=int)
        since = request.args.get("since")
        
        if since:
            since_dt = datetime.fromisoformat(since)
        else:
            since_dt = None
        
        metrics = g.server.database.get_metrics(target_id, limit=limit, since=since_dt)
        return jsonify({
            "target_id": target_id,
            "metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "check_type": m.check_type.value,
                    "value": m.value,
                    "status": m.status.value,
                    "latency_ms": m.latency_ms,
                    "error": m.error,
                }
                for m in metrics
            ],
        })

    @app.route("/api/targets/<target_id>/latest", methods=["GET"])
    def get_latest(target_id):
        metric = g.server.database.get_latest_metrics(target_id)
        if metric:
            return jsonify({
                "timestamp": metric.timestamp.isoformat(),
                "check_type": metric.check_type.value,
                "value": metric.value,
                "status": metric.status.value,
                "latency_ms": metric.latency_ms,
                "error": metric.error,
            })
        return jsonify({"error": "No data found"}), 404

    @app.route("/api/targets/<target_id>/history", methods=["GET"])
    def get_history(target_id):
        hours = request.args.get("hours", 24, type=int)
        since = datetime.now() - timedelta(hours=hours)
        
        metrics = g.server.database.get_metrics(target_id, limit=1000, since=since)
        
        return jsonify({
            "target_id": target_id,
            "period_hours": hours,
            "data_points": len(metrics),
            "history": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "value": m.value,
                    "status": m.status.value,
                    "latency_ms": m.latency_ms,
                }
                for m in metrics
            ],
        })

    @app.route("/api/targets/<target_id>/check", methods=["POST"])
    def trigger_check(target_id):
        target_data = None
        for t in g.server.config.targets:
            if t.get("id") == target_id:
                target_data = t
                break
        
        if not target_data:
            return jsonify({"error": "Target not found"}), 404
        
        from src.models import MonitorTarget, CheckType, DeviceType
        from src.monitors import PingMonitor
        
        target = MonitorTarget(
            id=target_data["id"],
            name=target_data["name"],
            host=target_data["host"],
            check_type=CheckType(target_data["check_type"]),
            port=target_data.get("port"),
            timeout=target_data.get("timeout", 5),
        )
        
        monitor = PingMonitor()
        metric = monitor.check(target)
        g.server.database.save_metric(metric)
        
        return jsonify({
            "target_id": target_id,
            "status": metric.status.value,
            "latency_ms": metric.latency_ms,
            "timestamp": metric.timestamp.isoformat(),
        })

    @app.route("/api/alerts", methods=["GET"])
    def get_alerts():
        active_only = request.args.get("active_only", "false").lower() == "true"
        limit = request.args.get("limit", 100, type=int)
        
        alerts = g.server.database.get_alerts(limit=limit, active_only=active_only)
        return jsonify({
            "count": len(alerts),
            "alerts": [
                {
                    "id": a.id,
                    "target_id": a.target_id,
                    "timestamp": a.timestamp.isoformat(),
                    "message": a.message,
                    "severity": a.severity,
                    "acknowledged": a.acknowledged,
                }
                for a in alerts
            ],
        })

    @app.route("/api/alerts/<alert_id>/acknowledge", methods=["POST"])
    def acknowledge_alert(alert_id):
        if g.server.alert_manager.acknowledge_alert(alert_id):
            return jsonify({"success": True})
        return jsonify({"error": "Alert not found"}), 404

    @app.route("/api/alerts/stats", methods=["GET"])
    def alert_stats():
        alerts = g.server.database.get_alerts(limit=1000)
        
        critical = sum(1 for a in alerts if a.severity == "critical" and not a.acknowledged)
        warning = sum(1 for a in alerts if a.severity == "warning" and not a.acknowledged)
        acknowledged = sum(1 for a in alerts if a.acknowledged)
        
        return jsonify({
            "critical": critical,
            "warning": warning,
            "acknowledged": acknowledged,
            "total": len(alerts),
        })

    @app.route("/api/discovery/scan", methods=["GET"])
    def network_scan():
        network = request.args.get("network", "192.168.1.0/24")
        
        from src.monitors.discovery import NetworkDiscovery
        discovery = NetworkDiscovery()
        hosts = discovery.scan_network(network)
        
        return jsonify({
            "network": network,
            "hosts_found": len(hosts),
            "hosts": hosts,
        })

    @app.route("/api/discovery/snmp", methods=["GET"])
    def snmp_discovery():
        network = request.args.get("network", "192.168.1.0/24")
        community = request.args.get("community", "public")
        
        from src.monitors.discovery import NetworkDiscovery
        discovery = NetworkDiscovery()
        devices = discovery.discover_snmp_devices(network, community)
        
        return jsonify({
            "network": network,
            "devices_found": len(devices),
            "devices": devices,
        })

    @app.route("/api/config", methods=["GET"])
    def get_config():
        return jsonify({
            "targets": g.server.config.targets,
            "check_interval": g.server.config.check_interval,
            "api_host": g.server.config.api_host,
            "api_port": g.server.config.api_port,
        })

    @app.route("/api/config", methods=["POST"])
    def update_config():
        data = request.get_json()
        
        if "check_interval" in data:
            g.server.config.check_interval = data["check_interval"]
        if "targets" in data:
            g.server.config.targets = data["targets"]
        
        g.server.config.save(Path("config.json"))
        
        return jsonify({"success": True})

    @app.route("/api/ai/sync/status", methods=["GET"])
    def ai_sync_status():
        from src.ai_sync import AISyncManager
        sync_manager = AISyncManager()
        return jsonify(sync_manager.get_status())

    @app.route("/api/ai/sync/force", methods=["POST"])
    def ai_force_sync():
        from src.ai_sync import AISyncManager
        sync_manager = AISyncManager()
        return jsonify(sync_manager.force_sync())

    return app
