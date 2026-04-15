"""Alerting system for network monitor."""

import logging
from datetime import datetime
from typing import Callable, Optional
from uuid import uuid4

from src.models import Alert, Metric, MonitorTarget, Status

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self):
        self.alerts: list[Alert] = []
        self.handlers: list[Callable[[Alert], None]] = []

    def register_handler(self, handler: Callable[[Alert], None]):
        self.handlers.append(handler)

    def check_and_alert(
        self,
        target: MonitorTarget,
        metric: Metric,
        consecutive_failures: int,
    ) -> Optional[Alert]:
        if metric.status == Status.DOWN:
            if consecutive_failures >= target.threshold:
                existing = self._get_active_alert(target.id)
                if not existing:
                    alert = self._create_alert(
                        target, f"Target {target.name} is DOWN", "critical"
                    )
                    self.alerts.append(alert)
                    self._notify_handlers(alert)
                    return alert
        elif metric.status == Status.UP:
            existing = self._get_active_alert(target.id)
            if existing:
                logger.info(f"Target {target.name} is back UP")

        return None

    def _get_active_alert(self, target_id: str) -> Optional[Alert]:
        for alert in self.alerts:
            if alert.target_id == target_id and not alert.acknowledged:
                return alert
        return None

    def _create_alert(self, target: MonitorTarget, message: str, severity: str) -> Alert:
        return Alert(
            id=str(uuid4()),
            target_id=target.id,
            timestamp=datetime.now(),
            message=message,
            severity=severity,
            acknowledged=False,
        )

    def _notify_handlers(self, alert: Alert):
        for handler in self.handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now()
                return True
        return False

    def get_active_alerts(self) -> list[Alert]:
        return [a for a in self.alerts if not a.acknowledged]

    def get_all_alerts(self, limit: int = 100) -> list[Alert]:
        return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]
