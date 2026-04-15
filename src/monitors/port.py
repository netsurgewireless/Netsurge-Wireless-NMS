"""Port monitoring module."""

import socket
from datetime import datetime
from typing import Optional

from src.models import Metric, Status, CheckType, MonitorTarget


class PortMonitor:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        port = target.port
        if not port:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PORT,
                value=0.0,
                status=Status.DOWN,
                error="No port specified",
            )

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            start = datetime.now()
            result = sock.connect_ex((target.host, port))
            elapsed = (datetime.now() - start).total_seconds() * 1000
            sock.close()

            if result == 0:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.PORT,
                    value=1.0,
                    status=Status.UP,
                    latency_ms=elapsed,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.PORT,
                    value=0.0,
                    status=Status.DOWN,
                    error=f"Connection refused (code {result})",
                )
        except socket.timeout:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PORT,
                value=0.0,
                status=Status.DOWN,
                error="Connection timeout",
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PORT,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )
