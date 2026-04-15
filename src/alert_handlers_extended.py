"""Extended alert handlers for various notification channels."""

import logging
import json
import requests
from typing import Optional
from dataclasses import dataclass

from src.models import Alert, MonitorTarget

logger = logging.getLogger(__name__)


@dataclass
class AlertPayload:
    title: str
    message: str
    severity: str
    target_id: str
    target_name: str
    target_host: str
    timestamp: str
    metric_value: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class TelegramHandler:
    def __init__(self, bot_token: str = None, chat_id: str = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}/"
    
    def send(self, alert: AlertPayload) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram handler not configured")
            return False
        
        emoji = {
            "critical": "🔴",
            "warning": "⚠️",
            "info": "ℹ️",
        }.get(alert.severity, "ℹ️")
        
        message = f"{emoji} *{alert.title}*\n\n"
        message += f"*{alert.target_name}* ({alert.target_host})\n"
        message += f"Status: {alert.severity.upper()}\n"
        
        if alert.latency_ms is not None:
            message += f"Latency: {alert.latency_ms:.1f}ms\n"
        
        if alert.error:
            message += f"Error: `{alert.error}`\n"
        
        message += f"\n_{alert.timestamp}_"
        
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        
        try:
            response = requests.post(
                f"{self.api_url}sendMessage",
                json=payload,
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
    
    def send_file(self, alert: AlertPayload, file_path: str, caption: str = None) -> bool:
        if not self.bot_token or not self.chat_id:
            return False
        
        try:
            with open(file_path, "rb") as f:
                files = {"document": f}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption or alert.message,
                }
                response = requests.post(
                    f"{self.api_url}sendDocument",
                    data=data,
                    files=files,
                    timeout=30,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram file: {e}")
            return False


class DiscordHandler:
    def __init__(self, webhook_url: str = None):
        self.webhook_url = webhook_url
    
    def send(self, alert: AlertPayload) -> bool:
        if not self.webhook_url:
            logger.warning("Discord webhook not configured")
            return False
        
        colors = {
            "critical": 16711680,
            "warning": 16776960,
            "info": 3447003,
        }
        
        embed = {
            "title": alert.title,
            "description": alert.message,
            "color": colors.get(alert.severity, 3447003),
            "fields": [
                {"name": "Target", "value": f"**{alert.target_name}** ({alert.target_host})", "inline": True},
                {"name": "Status", "value": alert.severity.upper(), "inline": True},
            ],
            "timestamp": alert.timestamp,
        }
        
        if alert.latency_ms is not None:
            embed["fields"].append({
                "name": "Latency",
                "value": f"{alert.latency_ms:.1f}ms",
                "inline": True,
            })
        
        if alert.error:
            embed["fields"].append({
                "name": "Error",
                "value": f"```\n{alert.error}\n```",
                "inline": False,
            })
        
        payload = {
            "embeds": [embed],
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False
    
    def send_webhook(self, payload: dict) -> bool:
        if not self.webhook_url:
            return False
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to send Discord webhook: {e}")
            return False


class PagerDutyHandler:
    def __init__(self, api_key: str = None, service_id: str = None):
        self.api_key = api_key
        self.service_id = service_id
        self.api_url = "https://events.pagerduty.com/v2/enqueue"
        self.api_url_incidents = "https://api.pagerduty.com"
    
    def send(self, alert: AlertPayload) -> bool:
        if not self.api_key or not self.service_id:
            logger.warning("PagerDuty handler not configured")
            return False
        
        payload = {
            "routing_key": self.service_id,
            "event_action": "trigger",
            "payload": {
                "summary": f"{alert.title}: {alert.target_name}",
                "severity": alert.severity,
                "source": alert.target_host,
                "timestamp": alert.timestamp,
                "custom_details": {
                    "target_id": alert.target_id,
                    "target_name": alert.target_name,
                    "target_host": alert.target_host,
                    "message": alert.message,
                },
            },
        }
        
        try:
            headers = {
                "Authorization": f"Token token={self.api_key}",
                "Content-Type": "application/json",
            }
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10,
            )
            return response.status_code in [200, 202]
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")
            return False
    
    def create_incident(self, title: str, service_id: str, urgency: str = "high", body: str = None) -> Optional[str]:
        if not self.api_key:
            return None
        
        payload = {
            "incident": {
                "type": "incident",
                "title": title,
                "service": {"id": service_id, "type": "service_reference"},
                "urgency": urgency,
                "body": {"type": "incidentBody", "details": body} if body else None,
            },
        }
        
        try:
            headers = {
                "Authorization": f"Token token={self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.pagerduty+json;version=2",
            }
            response = requests.post(
                f"{self.api_url_incidents}/incidents",
                json=payload,
                headers=headers,
                timeout=10,
            )
            if response.status_code == 201:
                return response.json().get("incident", {}).get("id")
        except Exception as e:
            logger.error(f"Failed to create PagerDuty incident: {e}")
        
        return None
    
    def resolve_incident(self, incident_id: str) -> bool:
        if not self.api_key:
            return False
        
        try:
            headers = {
                "Authorization": f"Token token={self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.pagerduty+json;version=2",
            }
            payload = {
                "incident": {
                    "type": "incident_reference",
                    "status": "resolved",
                },
            }
            response = requests.put(
                f"{self.api_url_incidents}/incidents/{incident_id}",
                json=payload,
                headers=headers,
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to resolve PagerDuty incident: {e}")
            return False


class SlackHandler:
    def __init__(self, webhook_url: str = None, token: str = None, channel: str = None):
        self.webhook_url = webhook_url
        self.token = token
        self.channel = channel
        self.api_url = "https://slack.com/api"
    
    def send(self, alert: AlertPayload) -> bool:
        if not self.webhook_url:
            logger.warning("Slack webhook not configured")
            return False
        
        colors = {
            "critical": "danger",
            "warning": "warning",
            "info": "#3399ff",
        }
        
        attachment = {
            "color": colors.get(alert.severity, "#3399ff"),
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{alert.title}*\n{alert.message}",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Target:*\n{alert.target_name} ({alert.target_host})"},
                        {"type": "mrkdwn", "text": f"*Status:*\n{alert.severity.upper()}"},
                    ],
                },
            ],
        }
        
        if alert.error:
            attachment["blocks"].append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Error:*\n```\n{alert.error}\n```",
                },
            })
        
        payload = {
            "attachments": [attachment],
        }
        
        if self.channel:
            payload["channel"] = self.channel
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def send_message(self, text: str, channel: str = None) -> bool:
        if not self.token:
            return False
        
        payload = {
            "text": text,
            "channel": channel or self.channel,
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/chat.postMessage",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            return response.status_code == 200 and response.json().get("ok")
        except Exception as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False


class OpsGenieHandler:
    def __init__(self, api_key: str = None, team_id: str = None):
        self.api_key = api_key
        self.team_id = team_id
        self.api_url = "https://api.opsgenie.com/v2/alerts"
    
    def send(self, alert: AlertPayload) -> bool:
        if not self.api_key:
            logger.warning("OpsGenie handler not configured")
            return False
        
        priority = {
            "critical": "P1",
            "warning": "P2",
            "info": "P4",
        }.get(alert.severity, "P3")
        
        payload = {
            "message": f"[{priority}] {alert.title}",
            "description": f"{alert.message}\n\nTarget: {alert.target_name} ({alert.target_host})\n{alert.timestamp}",
            "alias": f"nms-{alert.target_id}",
            "entity": alert.target_host,
            "priority": priority,
        }
        
        if self.team_id:
            payload["team"] = {"id": self.team_id}
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={
                    "Authorization": f"GenieKey {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Failed to send OpsGenie alert: {e}")
            return False
    
    def close_alert(self, alert_id: str) -> bool:
        if not self.api_key:
            return False
        
        try:
            response = requests.get(
                f"{self.api_url}/{alert_id}/close",
                headers={
                    "Authorization": f"GenieKey {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Failed to close OpsGenie alert: {e}")
            return False


class MatrixHandler:
    def __init__(self, homeserver: str = None, access_token: str = None, room_id: str = None):
        self.homeserver = homeserver
        self.access_token = access_token
        self.room_id = room_id
    
    def send(self, alert: AlertPayload) -> bool:
        if not self.homeserver or not self.access_token or not self.room_id:
            logger.warning("Matrix handler not configured")
            return False
        
        message = f"**{alert.title}**\n\n"
        message += f"**{alert.target_name}** ({alert.target_host})\n"
        message += f"Status: {alert.severity.upper()}\n"
        
        if alert.error:
            message += f"Error: `{alert.error}`\n"
        
        message += f"\n_{alert.timestamp}_"
        
        payload = {
            "msgtype": "m.text",
            "body": message,
        }
        
        try:
            response = requests.post(
                f"{self.homeserver}/_matrix/client/r0/rooms/{self.room_id}/send/m.room.message",
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Matrix alert: {e}")
            return False


class GotifyHandler:
    def __init__(self, url: str = None, app_token: str = None):
        self.url = url
        self.app_token = app_token
    
    def send(self, alert: AlertPayload) -> bool:
        if not self.url or not self.app_token:
            logger.warning("Gotify handler not configured")
            return False
        
        priority = {
            "critical": 8,
            "warning": 5,
            "info": 1,
        }.get(alert.severity, 3)
        
        payload = {
            "title": alert.title,
            "message": f"{alert.message}\n\nTarget: {alert.target_name} ({alert.target_host})",
            "priority": priority,
        }
        
        try:
            response = requests.post(
                f"{self.url}/message",
                json=payload,
                headers={
                    "X-Gotify-Key": self.app_token,
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Gotify alert: {e}")
            return False