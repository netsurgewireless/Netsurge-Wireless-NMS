"""Data storage module using SQLite."""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from src.models import Metric, Alert, Status, CheckType


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    check_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    status TEXT NOT NULL,
                    latency_ms REAL,
                    error TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_target_time
                ON metrics(target_id, timestamp)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    message TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    acknowledged_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_alerts_time ON alerts(timestamp)")

    def save_metric(self, metric: Metric):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO metrics
                (target_id, timestamp, check_type, value, status, latency_ms, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    metric.target_id,
                    metric.timestamp.isoformat(),
                    metric.check_type.value,
                    metric.value,
                    metric.status.value,
                    metric.latency_ms,
                    metric.error,
                ),
            )

    def save_alert(self, alert: Alert):
        with self._get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO alerts
                (id, target_id, timestamp, message, severity, acknowledged, acknowledged_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert.id,
                    alert.target_id,
                    alert.timestamp.isoformat(),
                    alert.message,
                    alert.severity,
                    int(alert.acknowledged),
                    alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                ),
            )

    def get_metrics(
        self,
        target_id: str,
        limit: int = 100,
        since: Optional[datetime] = None,
    ) -> list[Metric]:
        with self._get_conn() as conn:
            query = "SELECT * FROM metrics WHERE target_id = ?"
            params = [target_id]
            if since:
                query += " AND timestamp >= ?"
                params.append(since.isoformat())
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_metric(row) for row in rows]

    def get_latest_metrics(self, target_id: str) -> Optional[Metric]:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM metrics WHERE target_id = ? ORDER BY timestamp DESC LIMIT 1",
                (target_id,),
            ).fetchone()
            return self._row_to_metric(row) if row else None

    def get_alerts(self, limit: int = 100, active_only: bool = False) -> list[Alert]:
        with self._get_conn() as conn:
            query = "SELECT * FROM alerts"
            if active_only:
                query += " WHERE acknowledged = 0"
            query += " ORDER BY timestamp DESC LIMIT ?"
            
            rows = conn.execute(query, (limit,)).fetchall()
            return [self._row_to_alert(row) for row in rows]

    def cleanup_old_data(self, retention_days: int):
        with self._get_conn() as conn:
            cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
            conn.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))

    def _row_to_metric(self, row) -> Metric:
        return Metric(
            target_id=row["target_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            check_type=CheckType(row["check_type"]),
            value=row["value"],
            status=Status(row["status"]),
            latency_ms=row["latency_ms"],
            error=row["error"],
        )

    def _row_to_alert(self, row) -> Alert:
        return Alert(
            id=row["id"],
            target_id=row["target_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            message=row["message"],
            severity=row["severity"],
            acknowledged=bool(row["acknowledged"]),
            acknowledged_at=datetime.fromisoformat(row["acknowledged_at"]) if row["acknowledged_at"] else None,
        )
