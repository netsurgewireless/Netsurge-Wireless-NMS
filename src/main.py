"""Main network monitor application."""

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
from src.api import create_app
from src.dashboard import add_dashboard_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class NetworkMonitor:
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

    def start(self):
        self.running = True
        logger.info("Starting network monitor...")

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
        logger.info("Stopping network monitor...")
        for thread in self.threads.values():
            thread.join(timeout=5)
        logger.info("Network monitor stopped")

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

    def run_api(self):
        app = create_app(self.config, self.database, self.alert_manager)
        add_dashboard_routes(app)
        app.run(host=self.config.api_host, port=self.config.api_port)


def main():
    config_path = Path("config.json")
    db_path = Path("network_monitor.db")

    config = Config.load(config_path)
    if not config.targets:
        for target in DEFAULT_TARGETS:
            config.targets.append(target)
        config.save(config_path)

    monitor = NetworkMonitor(config, db_path)

    def signal_handler(sig, frame):
        print("\nShutting down...")
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    monitor.start()

    api_thread = threading.Thread(target=monitor.run_api, daemon=True)
    api_thread.start()
    logger.info(f"API server running on http://{config.api_host}:{config.api_port}")

    try:
        while monitor.running:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()


if __name__ == "__main__":
    main()
