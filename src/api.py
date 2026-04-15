"""REST API for network monitor."""

import json
from flask import Flask, jsonify, request
from datetime import datetime

from src.config import Config
from src.storage import Database
from src.alerts import AlertManager


def create_app(config: Config, database: Database, alert_manager: AlertManager) -> Flask:
    app = Flask(__name__)
    
    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

    @app.route("/api/targets", methods=["GET"])
    def get_targets():
        return jsonify({"targets": config.targets})

    @app.route("/api/targets/<target_id>/metrics", methods=["GET"])
    def get_metrics(target_id):
        limit = request.args.get("limit", 100, type=int)
        metrics = database.get_metrics(target_id, limit=limit)
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
        metric = database.get_latest_metrics(target_id)
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

    @app.route("/api/alerts", methods=["GET"])
    def get_alerts():
        active_only = request.args.get("active_only", "false").lower() == "true"
        alerts = database.get_alerts(active_only=active_only)
        return jsonify({
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
        if alert_manager.acknowledge_alert(alert_id):
            return jsonify({"success": True})
        return jsonify({"error": "Alert not found"}), 404

    return app
