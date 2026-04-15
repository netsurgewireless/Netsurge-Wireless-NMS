"""Ping monitoring module."""

import subprocess
import re
from datetime import datetime
from typing import Optional

from src.models import Metric, Status, CheckType, MonitorTarget


class PingMonitor:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        try:
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(self.timeout * 1000), target.host],
                capture_output=True,
                text=True,
                timeout=self.timeout + 2,
            )
            
            if result.returncode == 0:
                latency = self._parse_latency(result.stdout)
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.PING,
                    value=1.0,
                    status=Status.UP,
                    latency_ms=latency,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.PING,
                    value=0.0,
                    status=Status.DOWN,
                    error=result.stdout or "Ping failed",
                )
        except subprocess.TimeoutExpired:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PING,
                value=0.0,
                status=Status.DOWN,
                error="Ping timeout",
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PING,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def _parse_latency(self, output: str) -> Optional[float]:
        match = re.search(r"time[=<](\d+(?:\.\d+)?)\s*ms", output, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
