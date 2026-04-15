"""Configuration management for network monitor."""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from src.models import CheckType


@dataclass
class Config:
    targets: list[dict] = field(default_factory=list)
    check_interval: int = 60
    retention_days: int = 30
    alert_retention_days: int = 90
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    log_level: str = "INFO"

    def add_target(
        self,
        id: str,
        name: str,
        host: str,
        check_type: CheckType,
        port: Optional[int] = None,
        interval: int = 60,
        timeout: int = 5,
        threshold: int = 3,
    ):
        target = {
            "id": id,
            "name": name,
            "host": host,
            "check_type": check_type.value,
            "port": port,
            "interval": interval,
            "timeout": timeout,
            "threshold": threshold,
            "enabled": True,
        }
        self.targets.append(target)
        return target

    def save(self, path: Path):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "Config":
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                return cls(**data)
        return cls()


DEFAULT_TARGETS = [
    {"id": "google-dns", "name": "Google DNS", "host": "8.8.8.8", "check_type": "ping", "interval": 30, "timeout": 5, "threshold": 3, "enabled": True},
    {"id": "cloudflare-dns", "name": "Cloudflare DNS", "host": "1.1.1.1", "check_type": "ping", "interval": 30, "timeout": 5, "threshold": 3, "enabled": True},
    {"id": "web-server", "name": "Web Server", "host": "example.com", "check_type": "port", "port": 443, "interval": 60, "timeout": 5, "threshold": 3, "enabled": True},
]
