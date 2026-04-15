"""Network Monitor Client - Desktop application for Windows/macOS connecting to server."""

import os
import sys
import threading
import time
import logging
import json
import platform
import socket
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

import requests
from requests.auth import HTTPBasicAuth

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False

try:
    from plyer import notification
    HAS_NOTIFICATIONS = True
except ImportError:
    HAS_NOTIFICATIONS = False


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class ClientConfig:
    server_url: str = "http://localhost:8080"
    api_key: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    refresh_interval: int = 30
    show_notifications: bool = True
    minimize_to_tray: bool = True
    start_minimized: bool = False
    auto_reconnect: bool = True
    reconnect_interval: int = 60


@dataclass
class TargetStatus:
    id: str
    name: str
    host: str
    status: str = "unknown"
    latency_ms: Optional[float] = None
    last_check: Optional[datetime] = None
    check_type: str = "ping"
    device_type: Optional[str] = None
    location: Optional[str] = None
    uptime: Optional[str] = None


class NetworkMonitorClient:
    def __init__(self, config: ClientConfig):
        self.config = config
        self.targets: list[TargetStatus] = []
        self.alerts: list[dict] = []
        self.server_status: dict = {}
        self._running = False
        self._connected = False
        self._icon = None

    def _get_auth(self):
        if self.config.username and self.config.password:
            return HTTPBasicAuth(self.config.username, self.config.password)
        return None

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[dict]:
        url = f"{self.config.server_url}{endpoint}"
        auth = self._get_auth()
        
        kwargs.setdefault("timeout", 10)
        kwargs.setdefault("verify", False)
        
        if auth:
            kwargs["auth"] = auth
        elif self.config.api_key:
            kwargs.setdefault("headers", {})
            kwargs["headers"]["X-API-Key"] = self.config.api_key
        
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            self._connected = False
            logger.warning(f"Cannot connect to server: {self.config.server_url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None

    def connect(self) -> bool:
        try:
            result = self._make_request("GET", "/api/health")
            if result:
                self._connected = True
                logger.info(f"Connected to server: {self.config.server_url}")
                return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
        
        self._connected = False
        return False

    def fetch_status(self) -> bool:
        if not self._connected:
            if not self.connect():
                return False
        
        targets_result = self._make_request("GET", "/api/targets")
        if targets_result:
            self._process_targets(targets_result.get("targets", []))
        
        status_result = self._make_request("GET", "/api/status")
        if status_result:
            self.server_status = status_result
        
        alerts_result = self._make_request("GET", "/api/alerts?active_only=true")
        if alerts_result:
            self._process_alerts(alerts_result.get("alerts", []))
        
        return True

    def _process_targets(self, targets_data: list):
        self.targets = []
        
        for t in targets_data:
            status = t.get("status", "unknown")
            
            if status == "unknown" and t.get("latency_ms") is not None:
                status = "up"
            
            target = TargetStatus(
                id=t.get("id", ""),
                name=t.get("name", ""),
                host=t.get("host", ""),
                status=status,
                latency_ms=t.get("latency_ms"),
                check_type=t.get("check_type", "ping"),
                device_type=t.get("device_type"),
                location=t.get("location"),
            )
            self.targets.append(target)
            
            self._check_for_alerts(target)

    def _process_alerts(self, alerts_data: list):
        new_alerts = []
        
        for a in alerts_data:
            if not a.get("acknowledged"):
                new_alerts.append(a)
                
                if self.config.show_notifications:
                    self._send_notification(
                        f"Alert: {a.get('severity', 'warning').upper()}",
                        a.get("message", "Unknown alert"),
                        a.get("severity", "warning")
                    )
        
        self.alerts = new_alerts

    def _check_for_alerts(self, target: TargetStatus):
        pass

    def _send_notification(self, title: str, message: str, level: str = "info"):
        if not HAS_NOTIFICATIONS:
            return
        
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Network Monitor",
                timeout=10,
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

    def acknowledge_alert(self, alert_id: str) -> bool:
        result = self._make_request(
            "POST", 
            f"/api/alerts/{alert_id}/acknowledge"
        )
        return result is not None

    def trigger_check(self, target_id: str) -> Optional[dict]:
        return self._make_request("POST", f"/api/targets/{target_id}/check")

    def get_target_history(self, target_id: str, hours: int = 24) -> Optional[list]:
        result = self._make_request(
            "GET", 
            f"/api/targets/{target_id}/history?hours={hours}"
        )
        if result:
            return result.get("history", [])
        return None

    def add_target(self, target_data: dict) -> bool:
        result = self._make_request("POST", "/api/targets", json=target_data)
        return result is not None

    def remove_target(self, target_id: str) -> bool:
        result = self._make_request("DELETE", f"/api/targets/{target_id}")
        return result is not None

    def start(self):
        logger.info(f"Starting client, connecting to: {self.config.server_url}")
        
        if not self.connect():
            logger.warning("Initial connection failed, will retry...")
        
        self._running = True
        
        fetch_thread = threading.Thread(target=self._fetch_loop, daemon=True)
        fetch_thread.start()

    def _fetch_loop(self):
        while self._running:
            if self.fetch_status():
                self._update_tray_icon()
            
            time.sleep(self.config.refresh_interval)

    def _update_tray_icon(self):
        if not HAS_PYSTRAY or not self._icon:
            return
        
        down_count = sum(1 for t in self.targets if t.status == "down")
        
        if down_count > 0:
            color = (255, 23, 68)
        else:
            color = (0, 200, 83)
        
        try:
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), color=(26, 26, 46))
            draw = ImageDraw.Draw(image)
            
            draw.ellipse([8, 8, 56, 56], fill=color, outline=(255, 255, 255), width=2)
            
            center = width // 2
            draw.polygon([(center, 20), (center + 10, 35), (center - 10, 35)], fill=(255, 255, 255))
            
            self._icon.image = image
        except:
            pass

    def stop(self):
        self._running = False
        logger.info("Client stopped")


class TrayIconClient(NetworkMonitorClient):
    def __init__(self, config: ClientConfig):
        super().__init__(config)
        self._tray_icon = None

    def create_tray(self):
        if not HAS_PYSTRAY:
            logger.warning("pystray not available")
            return

        def create_image():
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), color=(26, 26, 46))
            draw = ImageDraw.Draw(image)
            draw.ellipse([8, 8, 56, 56], fill=(0, 217, 255), outline=(0, 180, 200), width=2)
            draw.polygon([(32, 20), (42, 35), (22, 35)], fill=(0, 200, 83))
            return image

        def create_menu():
            menu = []
            
            up_count = sum(1 for t in self.targets if t.status == "up")
            down_count = sum(1 for t in self.targets if t.status == "down")
            
            menu.append(pystray.MenuItem(f"Online: {up_count}", None, enabled=False))
            menu.append(pystray.MenuItem(f"Offline: {down_count}", None, enabled=False))
            menu.append(pystray.MenuItem(f"Total: {len(self.targets)}", None, enabled=False))
            
            if self.targets:
                menu.append(pystray.Menu.SEPARATOR)
                for target in self.targets[:5]:
                    status_icon = "✓" if target.status == "up" else "✗"
                    label = f"{status_icon} {target.name}"
                    menu.append(pystray.MenuItem(label, None, enabled=False))
            
            menu.append(pystray.Menu.SEPARATOR)
            menu.append(pystray.MenuItem("Open Dashboard", self._on_open_dashboard))
            menu.append(pystray.MenuItem("Refresh Now", self._on_refresh))
            menu.append(pystray.MenuItem("Exit", self._on_exit))
            
            return pystray.Menu(*menu)

        def on_open_dashboard(icon, item):
            webbrowser.open(self.config.server_url)

        def on_refresh(icon, item):
            self.fetch_status()

        def on_exit(icon, item):
            self.stop()
            if self._tray_icon:
                self._tray_icon.stop()

        self._tray_icon = pystray.Icon(
            "NetworkMonitor",
            create_image(),
            "Network Monitor",
            create_menu()
        )

    def start(self):
        self.create_tray()
        super().start()
        
        if self._tray_icon:
            self._icon = self._tray_icon
            self._tray_icon.run()
        else:
            while self._running:
                time.sleep(1)

    def _check_for_alerts(self, target: TargetStatus):
        if target.status == "down" and self.config.show_notifications:
            self._send_notification(
                "Device Offline",
                f"{target.name} ({target.host}) is not responding",
                "warning"
            )


def run_client():
    import argparse
    
    parser = argparse.ArgumentParser(description="Network Monitor Client")
    parser.add_argument("--server", default="http://localhost:8080", help="Server URL")
    parser.add_argument("--api-key", help="API Key for authentication")
    parser.add_argument("--username", help="Username for basic auth")
    parser.add_argument("--password", help="Password for basic auth")
    parser.add_argument("--refresh-interval", type=int, default=30, help="Refresh interval in seconds")
    parser.add_argument("--no-notifications", action="store_true", help="Disable notifications")
    parser.add_argument("--console", action="store_true", help="Run in console mode (no tray)")
    
    args = parser.parse_args()
    
    config = ClientConfig(
        server_url=args.server,
        api_key=args.api_key,
        username=args.username,
        password=args.password,
        refresh_interval=args.refresh_interval,
        show_notifications=not args.no_notifications,
    )
    
    if args.console:
        client = NetworkMonitorClient(config)
    else:
        client = TrayIconClient(config)
    
    try:
        client.start()
    except KeyboardInterrupt:
        client.stop()


if __name__ == "__main__":
    run_client()
