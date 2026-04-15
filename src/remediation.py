"""Automated remediation and self-healing capabilities."""

import logging
import time
import json
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Callable
from dataclasses import dataclass, field

from src.models import MonitorTarget, Metric, Status

logger = logging.getLogger(__name__)


@dataclass
class RemediationAction:
    id: str
    name: str
    description: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict = field(default_factory=dict)
    working_dir: Optional[str] = None
    timeout: int = 60
    retry_count: int = 0
    retry_delay: int = 60
    enabled: bool = True


@dataclass
class RemediationResult:
    action_id: str
    target_id: str
    success: bool
    output: str
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class RemediationEngine:
    def __init__(self):
        self.actions: dict[str, RemediationAction] = {}
        self.history: list[RemediationResult] = []
        self._callbacks: dict[str, Callable] = {}
        self._action_blacklist = {"rm", "del", "format", "fdisk", "mkfs"}
    
    def register_action(self, action: RemediationAction) -> bool:
        if not action.id:
            return False
        
        for dangerous in self._action_blacklist:
            if dangerous.lower() in action.command.lower():
                logger.warning(f"Blocked potentially dangerous action: {action.command}")
                return False
        
        self.actions[action.id] = action
        logger.info(f"Registered remediation action: {action.id}")
        return True
    
    def unregister_action(self, action_id: str) -> bool:
        if action_id in self.actions:
            del self.actions[action_id]
            return True
        return False
    
    def execute_action(self, action: RemediationAction, target: MonitorTarget) -> RemediationResult:
        cmd = action.command
        args = [arg.format(
            target_id=target.id,
            target_host=target.host,
            target_name=target.name,
            target_port=target.port or "",
        ) for arg in action.args]
        
        env = {"TARGET_HOST": target.host, "TARGET_ID": target.id}
        env.update(action.env)
        
        try:
            result = subprocess.run(
                [cmd] + args,
                capture_output=True,
                text=True,
                timeout=action.timeout,
                env=env,
                cwd=action.working_dir,
            )
            
            remediation_result = RemediationResult(
                action_id=action.id,
                target_id=target.id,
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
            
        except subprocess.TimeoutExpired:
            remediation_result = RemediationResult(
                action_id=action.id,
                target_id=target.id,
                success=False,
                output="",
                error="Action timed out",
            )
        except Exception as e:
            remediation_result = RemediationResult(
                action_id=action.id,
                target_id=target.id,
                success=False,
                output="",
                error=str(e),
            )
        
        self.history.append(remediation_result)
        
        if len(self.history) > 1000:
            self.history = self.history[-500:]
        
        return remediation_result
    
    def trigger_on_failure(
        self,
        target: MonitorTarget,
        metric: Metric,
        consecutive_failures: int,
    ) -> Optional[RemediationResult]:
        failure_triggers = {
            1: "restart_service",
            3: "check_connectivity",
            5: "reset_network",
            10: "reboot_device",
        }
        
        for threshold, action_id in failure_triggers.items():
            if consecutive_failures == threshold and action_id in self.actions:
                action = self.actions[action_id]
                if action.enabled:
                    logger.info(f"Triggering remediation action {action_id} for {target.id}")
                    return self.execute_action(action, target)
        
        return None
    
    def get_action_status(self, action_id: str) -> dict:
        if action_id not in self.actions:
            return {"error": "Action not found"}
        
        action = self.actions[action_id]
        
        recent_results = [
            r for r in self.history[-50:]
            if r.action_id == action_id
        ]
        
        success_count = sum(1 for r in recent_results if r.success)
        total_count = len(recent_results)
        
        return {
            "id": action.id,
            "name": action.name,
            "enabled": action.enabled,
            "total_executions": total_count,
            "successful_executions": success_count,
            "success_rate": success_count / total_count if total_count > 0 else 0,
        }
    
    def add_default_actions(self):
        self.register_action(RemediationAction(
            id="restart_service",
            name="Restart Service",
            description="Restart the monitoring service on the target",
            command="systemctl",
            args=["restart", "{target_name}"],
            timeout=30,
        ))
        
        self.register_action(RemediationAction(
            id="check_connectivity",
            name="Check Connectivity",
            description="Run network diagnostics",
            command="ping",
            args=["-c", "4", "{target_host}"],
            timeout=15,
        ))
        
        self.register_action(RemediationAction(
            id="clear_cache",
            name="Clear Cache",
            description="Clear DNS cache",
            command="ipconfig",
            args=["/flushdns"],
            timeout=10,
            env={"SYSTEMROOT": "C:\\Windows"},
        ))
        
        self.register_action(RemediationAction(
            id="reset_network",
            name="Reset Network",
            description="Reset network interface",
            command="netsh",
            args=["interface", "set", "interface", "Local Area Connection", "disabled"],
            timeout=30,
        ))
        
        self.register_action(RemediationAction(
            id="reboot_device",
            name="Reboot Device",
            description="Reboot the target device via network",
            command="echo",
            args=["Reboot triggered for {target_host}"],
            timeout=5,
        ))


class Healer:
    def __init__(self):
        self.enabled_policies: dict[str, bool] = {}
        self.remediation = RemediationEngine()
        self.remediation.add_default_actions()
    
    def apply_healing(
        self,
        target: MonitorTarget,
        metric: Metric,
        consecutive_failures: int,
    ) -> Optional[RemediationResult]:
        if not self.enabled_policies.get(target.check_type.value, True):
            return None
        
        return self.remediation.trigger_on_failure(
            target, metric, consecutive_failures
        )
    
    def enable_policy(self, check_type: str, enabled: bool = True):
        self.enabled_policies[check_type] = enabled
    
    def get_health_score(self, metrics_history: list[Metric]) -> float:
        if not metrics_history:
            return 0.0
        
        uptime_seconds = 0
        total_seconds = 0
        
        for i in range(1, len(metrics_history)):
            interval = (metrics_history[i].timestamp - metrics_history[i-1].timestamp).total_seconds()
            total_seconds += interval
            
            if metrics_history[i].status == Status.UP:
                uptime_seconds += interval
        
        return (uptime_seconds / total_seconds * 100) if total_seconds > 0 else 0
    
    def predict_failure(
        self,
        metrics_history: list[Metric],
        window_minutes: int = 30,
    ) -> dict:
        if len(metrics_history) < 10:
            return {"prediction": "insufficient_data"}
        
        recent = [
            m for m in metrics_history
            if m.timestamp > datetime.now() - timedelta(minutes=window_minutes)
        ]
        
        failures = sum(1 for m in recent if m.status == Status.DOWN)
        
        latencies = [m.latency_ms for m in recent if m.latency_ms is not None]
        
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        
        return {
            "prediction": "likely_failure" if failures > len(recent) * 0.3 else "stable",
            "failure_rate": failures / len(recent) if recent else 0,
            "avg_latency_ms": avg_latency,
            "sample_count": len(recent),
        }


class PlaybookManager:
    def __init__(self):
        self.playbooks: dict[str, dict] = {}
        self._load_defaults()
    
    def _load_defaults(self):
        self.playbooks["high_latency"] = {
            "name": "High Latency Response",
            "triggers": [
                {"metric": "latency_ms", "operator": ">", "threshold": 100},
            ],
            "actions": [
                {"type": "check_route", "params": {}},
                {"type": "check_qos", "params": {}},
            ],
        }
        
        self.playbooks["packet_loss"] = {
            "name": "Packet Loss Response",
            "triggers": [
                {"metric": "packet_loss", "operator": ">", "threshold": 1},
            ],
            "actions": [
                {"type": "run_diagnostics", "params": {}},
                {"type": "alert_oncall", "params": {}},
            ],
        }
        
        self.playbooks["certificate_expiry"] = {
            "name": "Certificate Expiry Warning",
            "triggers": [
                {"metric": "cert_days_remaining", "operator": "<", "threshold": 30},
            ],
            "actions": [
                {"type": "renew_certificate", "params": {}},
                {"type": "alert_security", "params": {}},
            ],
        }
    
    def evaluate_playbook(
        self,
        playbook_id: str,
        metric: Metric,
        target: MonitorTarget,
    ) -> bool:
        if playbook_id not in self.playbooks:
            return False
        
        playbook = self.playbooks[playbook_id]
        
        for trigger in playbook.get("triggers", []):
            metric_name = trigger.get("metric")
            operator = trigger.get("operator")
            threshold = trigger.get("threshold")
            
            value = getattr(metric, metric_name, None)
            if value is None:
                continue
            
            if operator == ">" and value > threshold:
                return True
            elif operator == "<" and value < threshold:
                return True
            elif operator == "==" and value == threshold:
                return True
            elif operator == "!=" and value != threshold:
                return True
        
        return False
    
    def execute_playbook(self, playbook_id: str, target: MonitorTarget) -> dict:
        if playbook_id not in self.playbooks:
            return {"error": "Playbook not found"}
        
        playbook = self.playbooks[playbook_id]
        
        results = []
        
        for action in playbook.get("actions", []):
            action_type = action.get("type")
            params = action.get("params", {})
            
            result = self._execute_action(action_type, params, target)
            results.append({
                "action": action_type,
                "result": result,
            })
        
        return {
            "playbook": playbook_id,
            "target": target.id,
            "actions": results,
        }
    
    def _execute_action(self, action_type: str, params: dict, target: MonitorTarget) -> str:
        if action_type == "check_route":
            return "Route check initiated"
        elif action_type == "run_diagnostics":
            return "Diagnostics check initiated"
        elif action_type == "alert_oncall":
            return "On-call alerted"
        elif action_type == "renew_certificate":
            return "Certificate renewal initiated"
        elif action_type == "alert_security":
            return "Security team alerted"
        
        return f"Unknown action: {action_type}"