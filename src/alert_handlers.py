"""Advanced alerting handlers."""

import logging
import smtplib
import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from abc import ABC, abstractmethod

from src.models import Alert, MonitorTarget

logger = logging.getLogger(__name__)


class AlertHandler(ABC):
    @abstractmethod
    def send(self, alert: Alert, target: MonitorTarget, config: dict):
        pass


class EmailHandler(AlertHandler):
    def __init__(self):
        self.config = {}

    def send(self, alert: Alert, target: MonitorTarget, config: dict):
        if not all(config.get(k) for k in ["smtp_host", "smtp_port", "from_email", "to_email"]):
            logger.warning("Email configuration incomplete")
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = config["from_email"]
            msg["To"] = config["to_email"]
            msg["Subject"] = f"[{alert.severity.upper()}] {alert.message}"

            body = f"""
Alert Details:
- Target: {target.name} ({target.host})
- Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Severity: {alert.severity}
- Message: {alert.message}

Target ID: {target.id}
Check Type: {target.check_type.value}
            """
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
                if config.get("use_tls", True):
                    server.starttls()
                if config.get("smtp_user") and config.get("smtp_password"):
                    server.login(config["smtp_user"], config["smtp_password"])
                server.send_message(msg)

            logger.info(f"Email alert sent for {target.name}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def set_config(self, config: dict):
        self.config = config


class WebhookHandler(AlertHandler):
    def __init__(self):
        self.config = {}

    def send(self, alert: Alert, target: MonitorTarget, config: dict):
        if not config.get("url"):
            logger.warning("Webhook URL not configured")
            return

        payload = {
            "alert_id": alert.id,
            "target_id": target.id,
            "target_name": target.name,
            "target_host": target.host,
            "message": alert.message,
            "severity": alert.severity,
            "timestamp": alert.timestamp.isoformat(),
            "check_type": target.check_type.value,
        }

        try:
            response = requests.post(
                config["url"],
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            logger.info(f"Webhook alert sent for {target.name}")
        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")

    def set_config(self, config: dict):
        self.config = config


class SlackHandler(AlertHandler):
    def __init__(self):
        self.config = {}

    def send(self, alert: Alert, target: MonitorTarget, config: dict):
        if not config.get("webhook_url"):
            logger.warning("Slack webhook not configured")
            return

        color = {"critical": "#FF0000", "warning": "#FFA500", "info": "#008000"}.get(
            alert.severity, "#008000"
        )

        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"[{alert.severity.upper()}] {alert.message}",
                    "fields": [
                        {"title": "Target", "value": f"{target.name} ({target.host})", "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "short": True},
                        {"title": "Check Type", "value": target.check_type.value, "short": True},
                    ],
                }
            ]
        }

        try:
            response = requests.post(
                config["webhook_url"],
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Slack alert sent for {target.name}")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    def set_config(self, config: dict):
        self.config = config


class SMSHandler(AlertHandler):
    def __init__(self):
        self.config = {}

    def send(self, alert: Alert, target: MonitorTarget, config: dict):
        if not all(config.get(k) for k in ["api_key", "from_number", "to_number"]):
            logger.warning("SMS configuration incomplete")
            return

        message = f"[{alert.severity.upper()}] {alert.message}"

        payload = {
            "api_key": config["api_key"],
            "from": config["from_number"],
            "to": config["to_number"],
            "message": message,
        }

        try:
            response = requests.post(
                "https://api.twilio.com/2010-04-01/Messages.json",
                auth=(config["account_sid"], config["auth_token"]),
                data=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"SMS alert sent for {target.name}")
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")

    def set_config(self, config: dict):
        self.config = config


def get_handlers(config: dict) -> list[AlertHandler]:
    handlers = []

    if config.get("email_enabled"):
        h = EmailHandler()
        h.set_config(config.get("email", {}))
        handlers.append(h)

    if config.get("webhook_enabled"):
        h = WebhookHandler()
        h.set_config(config.get("webhook", {}))
        handlers.append(h)

    if config.get("slack_enabled"):
        h = SlackHandler()
        h.set_config(config.get("slack", {}))
        handlers.append(h)

    if config.get("sms_enabled"):
        h = SMSHandler()
        h.set_config(config.get("sms", {}))
        handlers.append(h)

    return handlers
