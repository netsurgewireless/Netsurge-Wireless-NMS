"""HTTP/HTTPS monitoring module."""

import ssl
import socket
import requests
import urllib3
from datetime import datetime
from typing import Optional
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from src.models import Metric, Status, CheckType, MonitorTarget

urllib3.disable_warnings()


class HTTPMonitor:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        url = target.http_url or f"http://{target.host}"
        
        if target.port:
            url = url.replace(f"://{target.host}", f"://{target.host}:{target.port}")
        
        try:
            start = datetime.now()
            response = requests.request(
                method=target.http_method,
                url=url,
                timeout=self.timeout,
                verify=False,
                allow_redirects=True,
            )
            elapsed = (datetime.now() - start).total_seconds() * 1000
            
            if response.status_code == target.http_expected_status:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.HTTP,
                    value=1.0,
                    status=Status.UP,
                    latency_ms=elapsed,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.HTTP,
                    value=0.0,
                    status=Status.DEGRADED,
                    error=f"Expected {target.http_expected_status}, got {response.status_code}",
                )
        except requests.exceptions.Timeout:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.HTTP,
                value=0.0,
                status=Status.DOWN,
                error="Request timeout",
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.HTTP,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )


class SSLMonitor:
    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def check(self, target: MonitorTarget) -> Metric:
        port = target.port or 443
        
        try:
            context = ssl.create_default_context()
            start = datetime.now()
            
            with socket.create_connection((target.host, port), timeout=self.timeout) as sock:
                with context.wrap_socket(sock, server_hostname=target.host) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())
                    
                    days_until_expiry = (cert.not_valid_after_utc - datetime.now().replace(tzinfo=None)).days
                    elapsed = (datetime.now() - start).total_seconds() * 1000
                    
                    if target.ssl_check_expiry:
                        if days_until_expiry < 0:
                            return Metric(
                                target_id=target.id,
                                timestamp=datetime.now(),
                                check_type=CheckType.SSL,
                                value=0.0,
                                status=Status.DOWN,
                                error=f"Certificate expired {abs(days_until_expiry)} days ago",
                            )
                        elif days_until_expiry < 30:
                            return Metric(
                                target_id=target.id,
                                timestamp=datetime.now(),
                                check_type=CheckType.SSL,
                                value=float(days_until_expiry),
                                status=Status.DEGRADED,
                                latency_ms=elapsed,
                            )
                    
                    return Metric(
                        target_id=target.id,
                        timestamp=datetime.now(),
                        check_type=CheckType.SSL,
                        value=float(days_until_expiry),
                        status=Status.UP,
                        latency_ms=elapsed,
                    )
        except ssl.SSLError as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SSL,
                value=0.0,
                status=Status.DOWN,
                error=f"SSL error: {str(e)}",
            )
        except socket.timeout:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SSL,
                value=0.0,
                status=Status.DOWN,
                error="Connection timeout",
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.SSL,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )
