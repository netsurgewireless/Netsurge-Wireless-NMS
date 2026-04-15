"""Scalable sensor scheduler for unlimited monitoring."""

import logging
import threading
from typing import Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.models import Metric, MonitorTarget, Status, CheckType, DeviceType

logger = logging.getLogger(__name__)


@dataclass
class SensorConfig:
    monitor_class: str
    priority: int = 5
    timeout: int = 10
    retry_count: int = 3
    retry_delay: int = 5


@dataclass
class SensorState:
    target: MonitorTarget
    consecutive_failures: int = 0
    last_metric: Optional[Metric] = None
    last_check: Optional[datetime] = None
    enabled: bool = True
    job = None


class SensorRegistry:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.sensors: dict[str, SensorConfig] = {}
        self._register_default_sensors()

    def _register_default_sensors(self):
        self.register("ping", "PingMonitor", priority=1)
        self.register("port", "PortMonitor", priority=2)
        self.register("snmp", "SNMPMonitor", priority=3)
        self.register("http", "HTTPMonitor", priority=3)
        self.register("https", "HTTPMonitor", priority=3)
        self.register("ssl", "SSLMonitor", priority=4)
        self.register("nginx", "NginxMonitor", priority=4)
        self.register("wmi", "WMIMonitor", priority=3)
        self.register("bandwidth", "BandwidthMonitor", priority=5)

    def register(self, check_type: str, monitor_class: str, **kwargs):
        self.sensors[check_type] = SensorConfig(
            monitor_class=monitor_class,
            **kwargs
        )

    def get_config(self, check_type: str) -> Optional[SensorConfig]:
        return self.sensors.get(check_type)


class SensorScheduler:
    def __init__(self, monitor_instances: dict, max_workers: int = 50):
        self.monitor_instances = monitor_instances
        self.max_workers = max_workers
        self.states: dict[str, SensorState] = {}
        self.scheduler = BackgroundScheduler()
        self._lock = threading.Lock()
        self._running = False

    def add_target(self, target: MonitorTarget) -> bool:
        with self._lock:
            if target.id in self.states:
                return False
            
            monitor = self.monitor_instances.get(target.check_type)
            if not monitor:
                logger.error(f"No monitor found for {target.check_type}")
                return False

            state = SensorState(target=target, enabled=target.enabled)
            self.states[target.id] = state

            if target.enabled:
                self._schedule_target(target)
            
            return True

    def remove_target(self, target_id: str) -> bool:
        with self._lock:
            if target_id not in self.states:
                return False
            
            state = self.states[target_id]
            if state.job:
                state.job.remove()
            
            del self.states[target_id]
            return True

    def _schedule_target(self, target: MonitorTarget):
        job = self.scheduler.add_job(
            self._run_check,
            trigger=IntervalTrigger(seconds=target.interval),
            id=target.id,
            args=[target.id],
            name=f"{target.name} ({target.check_type.value})",
            replace_existing=True,
        )
        
        if target.id in self.states:
            self.states[target.id].job = job

    def _run_check(self, target_id: str):
        with self._lock:
            if target_id not in self.states:
                return
            
            state = self.states[target_id]
            if not state.enabled:
                return

        monitor = self.monitor_instances.get(state.target.check_type)
        if not monitor:
            return

        try:
            metric = monitor.check(state.target)
            state.last_metric = metric
            state.last_check = datetime.now()

            if metric.status == Status.DOWN:
                state.consecutive_failures += 1
            else:
                state.consecutive_failures = 0

            return metric, state.consecutive_failures
        except Exception as e:
            logger.error(f"Sensor error for {target_id}: {e}")
            state.consecutive_failures += 1
            return None, state.consecutive_failures

    def run_batch(self, targets: list[MonitorTarget], callback=None):
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            
            for target in targets:
                if not target.enabled:
                    continue
                
                monitor = self.monitor_instances.get(target.check_type)
                if not monitor:
                    continue
                
                future = executor.submit(monitor.check, target)
                futures[future] = target
            
            for future in as_completed(futures):
                target = futures[future]
                try:
                    metric = future.result()
                    results.append((target, metric))
                    if callback:
                        callback(target, metric)
                except Exception as e:
                    logger.error(f"Batch check error for {target.id}: {e}")
        
        return results

    def get_state(self, target_id: str) -> Optional[SensorState]:
        return self.states.get(target_id)

    def get_all_states(self) -> dict[str, SensorState]:
        return self.states.copy()

    def get_status_summary(self) -> dict:
        total = len(self.states)
        up = down = degraded = disabled = 0
        
        for state in self.states.values():
            if not state.enabled:
                disabled += 1
            elif state.last_metric:
                if state.last_metric.status == Status.UP:
                    up += 1
                elif state.last_metric.status == Status.DOWN:
                    down += 1
                else:
                    degraded += 1
        
        return {
            "total": total,
            "up": up,
            "down": down,
            "degraded": degraded,
            "disabled": disabled,
        }

    def start(self):
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Sensor scheduler started")

    def stop(self):
        if self._running:
            self.scheduler.shutdown(wait=True)
            self._running = False
            logger.info("Sensor scheduler stopped")

    def pause_target(self, target_id: str):
        with self._lock:
            if target_id in self.states:
                self.states[target_id].enabled = False
                if self.states[target_id].job:
                    self.states[target_id].job.pause()

    def resume_target(self, target_id: str):
        with self._lock:
            if target_id in self.states:
                self.states[target_id].enabled = True
                if self.states[target_id].job:
                    self.states[target_id].job.resume()

    def update_target(self, target: MonitorTarget):
        with self._lock:
            if target.id in self.states:
                old_state = self.states[target.id]
                
                if target.enabled != old_state.enabled:
                    if target.enabled:
                        self.resume_target(target.id)
                    else:
                        self.pause_target(target.id)
                
                old_state.target = target
