"""Network Monitor Server Application - Core monitoring engine."""

import logging
import signal
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

from src.config import Config, DEFAULT_TARGETS
from src.models import MonitorTarget, CheckType, DeviceType
from src.monitors import (
    PingMonitor, PortMonitor, SNMPMonitor, HTTPMonitor,
    SSLMonitor, WMIMonitor, BandwidthMonitor, NetworkDiscovery,
    NginxMonitor, ServerHealthMonitor, PacketLossMonitor,
    NetworkSpeedMonitor, WirelessMonitor
)
from src.storage import Database
from src.alerts import AlertManager
from src.alert_handlers import get_handlers
from src.server_api import create_server_app
from src.dashboard import add_dashboard_routes
from src.ai_unified import NetworkAI, create_ai_routes
from src.ai_sync import AISyncManager
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NetworkMonitorServer:
    def __init__(self, config: Config, db_path: Path):
        self.config = config
        self.database = Database(db_path)
        self.alert_manager = AlertManager()
        self.running = False
        self.threads = {}
        self.consecutive_failures = {}

        self.monitors = {
            CheckType.PING: PingMonitor(),
            CheckType.PORT: PortMonitor(),
            CheckType.SNMP: SNMPMonitor(),
            CheckType.HTTP: HTTPMonitor(),
            CheckType.HTTPS: HTTPMonitor(),
            CheckType.SSL: SSLMonitor(),
            CheckType.WMI: WMIMonitor(),
            CheckType.BANDWIDTH: BandwidthMonitor(),
            CheckType.NGINX: NginxMonitor(),
        }

        self._register_default_handlers()

    def _register_default_handlers(self):
        def log_handler(alert):
            logger.warning(f"ALERT: {alert.message}")

        self.alert_manager.register_handler(log_handler)

    def _create_target(self, target_data: dict) -> MonitorTarget:
        return MonitorTarget(
            id=target_data["id"],
            name=target_data["name"],
            host=target_data["host"],
            check_type=CheckType(target_data["check_type"]),
            port=target_data.get("port"),
            interval=target_data.get("interval", 60),
            timeout=target_data.get("timeout", 5),
            threshold=target_data.get("threshold", 3),
            enabled=target_data.get("enabled", True),
            device_type=DeviceType(target_data.get("device_type", "generic")),
            snmp_community=target_data.get("snmp_community"),
            snmp_oid=target_data.get("snmp_oid"),
            http_url=target_data.get("http_url"),
            http_method=target_data.get("http_method", "GET"),
            http_expected_status=target_data.get("http_expected_status", 200),
            ssl_check_expiry=target_data.get("ssl_check_expiry", False),
            wmi_query=target_data.get("wmi_query"),
            wmi_namespace=target_data.get("wmi_namespace"),
            location=target_data.get("location"),
            vendor=target_data.get("vendor"),
            model=target_data.get("model"),
            firmware=target_data.get("firmware"),
        )

    def add_target(self, target_data: dict) -> bool:
        target = self._create_target(target_data)
        
        if target.id in self.threads:
            return False
        
        self.config.targets.append(target_data)
        
        if target.enabled:
            self.consecutive_failures[target.id] = 0
            thread = threading.Thread(
                target=self._monitor_loop,
                args=(target,),
                daemon=True,
            )
            thread.start()
            self.threads[target.id] = thread
            logger.info(f"Added monitoring for {target.name} ({target.host})")
        
        return True

    def remove_target(self, target_id: str) -> bool:
        if target_id not in self.threads:
            return False
        
        self.config.targets = [t for t in self.config.targets if t.get("id") != target_id]
        
        if target_id in self.threads:
            del self.threads[target_id]
        if target_id in self.consecutive_failures:
            del self.consecutive_failures[target_id]
        
        logger.info(f"Removed target {target_id}")
        return True

    def update_target(self, target_id: str, target_data: dict) -> bool:
        self.remove_target(target_id)
        return self.add_target(target_data)

    def start(self):
        self.running = True
        logger.info("Starting network monitor server...")

        for target_data in self.config.targets:
            target = self._create_target(target_data)
            if target.enabled:
                self.consecutive_failures[target.id] = 0
                thread = threading.Thread(
                    target=self._monitor_loop,
                    args=(target,),
                    daemon=True,
                )
                thread.start()
                self.threads[target.id] = thread
                logger.info(f"Started monitoring {target.name} ({target.host})")

        logger.info(f"Monitoring {len(self.threads)} targets")

    def stop(self):
        self.running = False
        logger.info("Stopping network monitor server...")
        for thread in self.threads.values():
            thread.join(timeout=5)
        logger.info("Network monitor server stopped")

    def _monitor_loop(self, target: MonitorTarget):
        while self.running:
            self._check_target(target)
            time.sleep(target.interval)

    def _check_target(self, target: MonitorTarget):
        monitor = self.monitors.get(target.check_type)
        if not monitor:
            logger.error(f"No monitor for type {target.check_type}")
            return

        metric = monitor.check(target)
        self.database.save_metric(metric)

        if metric.status.value == "down":
            self.consecutive_failures[target.id] += 1
        else:
            self.consecutive_failures[target.id] = 0

        alert = self.alert_manager.check_and_alert(
            target, metric, self.consecutive_failures[target.id]
        )
        if alert:
            self.database.save_alert(alert)

    def get_status_summary(self) -> dict:
        total = len(self.threads)
        up = sum(1 for tid in self.threads if self.consecutive_failures.get(tid, 0) == 0)
        down = sum(1 for tid in self.threads if self.consecutive_failures.get(tid, 0) > 0)
        
        return {
            "total": total,
            "up": up,
            "down": down,
            "running": self.running,
        }

    def get_targets_status(self) -> list[dict]:
        result = []
        
        for target_data in self.config.targets:
            target_id = target_data.get("id")
            latest = self.database.get_latest_metrics(target_id)
            
            status = "unknown"
            latency = None
            
            if latest:
                status = latest.status.value
                latency = latest.latency_ms
            
            result.append({
                "id": target_data.get("id"),
                "name": target_data.get("name"),
                "host": target_data.get("host"),
                "check_type": target_data.get("check_type"),
                "port": target_data.get("port"),
                "status": status,
                "latency_ms": latency,
                "enabled": target_data.get("enabled", True),
                "device_type": target_data.get("device_type"),
                "location": target_data.get("location"),
                "vendor": target_data.get("vendor"),
                "model": target_data.get("model"),
            })
        
        return result

    def run_server(self):
        app = create_server_app(self)
        add_dashboard_routes(app)
        
        self.ai = NetworkAI()
        create_ai_routes(app, self.ai)
        
        from src.device_routes import add_all_device_routes
        add_all_device_routes(app)
        
        app.run(host=self.config.api_host, port=self.config.api_port)


def main():
    config_path = Path("config.json")
    db_path = Path("network_monitor.db")

    config = Config.load(config_path)
    if not config.targets:
        for target in DEFAULT_TARGETS:
            config.targets.append(target)
        config.save(config_path)

    server = NetworkMonitorServer(config, db_path)

    ai_sync = AISyncManager()
    ai_sync.start(interval_hours=24)

    def signal_handler(sig, frame):
        print("\nShutting down...")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.start()

    api_thread = threading.Thread(target=server.run_server, daemon=True)
    api_thread.start()
    logger.info(f"API server running on http://{config.api_host}:{config.api_port}")

    try:
        while server.running:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
