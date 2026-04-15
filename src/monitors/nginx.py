"""Nginx monitoring module via stub_status."""

import re
import requests
from datetime import datetime
from typing import Optional

from src.models import Metric, Status, CheckType, MonitorTarget


class NginxMonitor:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        url = target.http_url or f"http://{target.host}/nginx_status"
        
        if target.port:
            url = f"http://{target.host}:{target.port}/nginx_status"
        
        try:
            start = datetime.now()
            response = requests.get(url, timeout=self.timeout)
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            if response.status_code == 200:
                stats = self._parse_status(response.text)
                if stats:
                    return Metric(
                        target_id=target.id,
                        timestamp=datetime.now(),
                        check_type=CheckType.NGINX,
                        value=float(stats["active_connections"]),
                        status=Status.UP,
                        latency_ms=elapsed,
                    )
            
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.NGINX,
                value=0.0,
                status=Status.DOWN,
                error=f"Unexpected status: {response.status_code}",
            )
        except requests.exceptions.Timeout:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.NGINX,
                value=0.0,
                status=Status.DOWN,
                error="Request timeout",
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.NGINX,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _parse_status(self, text: str) -> Optional[dict]:
        pattern = r"Active connections: (\d+)\s+server accepts handled requests\s+(\d+)\s+(\d+)\s+(\d+)\s+Reading: (\d+)\s+Writing: (\d+)\s+Waiting: (\d+)"
        match = re.search(pattern, text)
        
        if match:
            return {
                "active_connections": int(match.group(1)),
                "accepted_connections": int(match.group(2)),
                "handled_connections": int(match.group(3)),
                "total_requests": int(match.group(4)),
                "reading": int(match.group(5)),
                "writing": int(match.group(6)),
                "waiting": int(match.group(7)),
            }
        return None
