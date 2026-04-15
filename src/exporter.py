"""Metrics exporters for Prometheus, InfluxDB, and other systems."""

import logging
import time
import json
import requests
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from src.models import Metric, MonitorTarget
from src.storage import Database

logger = logging.getLogger(__name__)


@dataclass
class PrometheusMetric:
    name: str
    value: float
    labels: dict
    timestamp: Optional[int] = None


class PrometheusExporter:
    def __init__(self, port: int = 9090, endpoint: str = "/metrics"):
        self.port = port
        self.endpoint = endpoint
        self.metrics: dict[str, PrometheusMetric] = {}
        self._labels_blacklist = {"password", "token", "secret", "api_key"}
    
    def export_metric(self, metric: Metric, target: MonitorTarget):
        name = f"network_monitor_{metric.check_type.value}"
        
        labels = {
            "target_id": target.id,
            "target_name": target.name,
            "target_host": target.host,
            "check_type": metric.check_type.value,
            "status": metric.status.value,
        }
        
        if target.location:
            labels["location"] = target.location
        if target.vendor:
            labels["vendor"] = target.vendor
        if target.device_type:
            labels["device_type"] = target.device_type.value
        
        self.metrics[f"{name}{{{{target_id=\"{target.id}\"}}}}"] = PrometheusMetric(
            name=name,
            value=1 if metric.status.value == "up" else 0,
            labels=labels,
            timestamp=int(metric.timestamp.timestamp() * 1000),
        )
        
        if metric.latency_ms is not None:
            latency_name = f"{name}_latency"
            self.metrics[f"{latency_name}{{{{target_id=\"{target.id}\"}}}}"] = PrometheusMetric(
                name=latency_name,
                value=metric.latency_ms,
                labels=labels,
                timestamp=int(metric.timestamp.timestamp() * 1000),
            )
    
    def generate_metrics(self) -> str:
        output = []
        
        for metric_name, metric in self.metrics.items():
            label_str = ",".join(
                f'{k}="{v}"' for k, v in metric.labels.items()
            )
            output.append(f"{metric_name}{{{label_str}}} {metric.value}")
        
        return "\n".join(output)
    
    def generate_prometheus_text(self) -> str:
        output = [
            "# HELP network_monitor_target_status Target status (1=up, 0=down)",
            "# TYPE network_monitor_target_status gauge",
        ]
        
        for metric_name, metric in self.metrics.items():
            if "latency" not in metric_name:
                label_str = ",".join(
                    f'{k}="{v}"' for k, v in metric.labels.items()
                )
                output.append(f"network_monitor_target_status{{{label_str}}} {metric.value}")
        
        output.append("")
        output.append("# HELP network_monitor_target_latency Target response latency in milliseconds")
        output.append("# TYPE network_monitor_target_latency gauge")
        
        for metric_name, metric in self.metrics.items():
            if "latency" in metric_name:
                label_str = ",".join(
                    f'{k}="{v}"' for k, v in metric.labels.items()
                )
                output.append(f"network_monitor_target_latency{{{label_str}}} {metric.value}")
        
        return "\n".join(output)
    
    def start_server(self):
        from flask import Flask, Response
        
        app = Flask(__name__)
        
        @app.route(self.endpoint)
        def metrics():
            return Response(
                self.generate_prometheus_text(),
                mimetype="text/plain; version=0.0.4; charset=utf-8",
            )
        
        @app.route("/health")
        def health():
            return {"status": "healthy", "exporter": "prometheus"}
        
        app.run(host="0.0.0.0", port=self.port)


class InfluxDBExporter:
    def __init__(self, url: str = None, token: str = None, org: str = None, bucket: str = None):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.write_url = f"{url}/api/v2/write"
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not all([self.url, self.token, self.org, self.bucket]):
            logger.warning("InfluxDB not configured")
            return False
        
        measurement = f"network_monitor_{metric.check_type.value}"
        
        tags = [
            f"target_id={target.id}",
            f"target_name={target.name}",
            f"target_host={target.host}",
            f"status={metric.status.value}",
        ]
        
        if target.location:
            tags.append(f"location={target.location}")
        if target.vendor:
            tags.append(f"vendor={target.vendor}")
        if target.device_type:
            tags.append(f"device_type={target.device_type.value}")
        
        fields = [
            f"value={metric.value}",
            f"status_code={1 if metric.status.value == 'up' else 0}",
        ]
        
        if metric.latency_ms is not None:
            fields.append(f"latency_ms={metric.latency_ms}")
        
        if metric.error:
            error_escaped = metric.error.replace(" ", "\\ ").replace(",", "\\,")
            fields.append(f'error="{error_escaped}"')
        
        timestamp = int(metric.timestamp.timestamp() * 1000000000)
        
        line = f"{measurement},{','.join(tags)} {','.join(fields)} {timestamp}"
        
        return self._write_line(line)
    
    def _write_line(self, line: str) -> bool:
        try:
            response = requests.post(
                self.write_url,
                params={
                    "org": self.org,
                    "bucket": self.bucket,
                    "precision": "ns",
                },
                data=line,
                headers={
                    "Authorization": f"Token {self.token}",
                    "Content-Type": "text/plain",
                },
                timeout=10,
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
            return False
    
    def export_batch(self, metrics: list[tuple[Metric, MonitorTarget]]) -> bool:
        if not all([self.url, self.token, self.org, self.bucket]):
            return False
        
        lines = []
        
        for metric, target in metrics:
            measurement = f"network_monitor_{metric.check_type.value}"
            
            tags = [
                f"target_id={target.id}",
                f"target_name={target.name}",
                f"target_host={target.host}",
                f"status={metric.status.value}",
            ]
            
            fields = [
                f"value={metric.value}",
            ]
            
            if metric.latency_ms is not None:
                fields.append(f"latency_ms={metric.latency_ms}")
            
            timestamp = int(metric.timestamp.timestamp() * 1000000000)
            
            lines.append(f"{measurement},{','.join(tags)} {','.join(fields)} {timestamp}")
        
        try:
            response = requests.post(
                self.write_url,
                params={
                    "org": self.org,
                    "bucket": self.bucket,
                    "precision": "ns",
                },
                data="\n".join(lines),
                headers={
                    "Authorization": f"Token {self.token}",
                    "Content-Type": "text/plain",
                },
                timeout=30,
            )
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Failed to write batch to InfluxDB: {e}")
            return False


class GraphiteExporter:
    def __init__(self, host: str = None, port: int = 2003, prefix: str = "network.monitor"):
        self.host = host
        self.port = port
        self.prefix = prefix
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not self.host:
            logger.warning("Graphite not configured")
            return False
        
        metric_path = f"{self.prefix}.{target.id}.{metric.check_type.value}.status"
        value = 1 if metric.status.value == "up" else 0
        timestamp = int(metric.timestamp.timestamp())
        
        line = f"{metric_path} {value} {timestamp}"
        
        if metric.latency_ms is not None:
            latency_path = f"{self.prefix}.{target.id}.{metric.check_type.value}.latency"
            latency_line = f"{latency_path} {metric.latency_ms} {timestamp}"
            line = f"{line}\n{latency_line}"
        
        return self._send(line)
    
    def _send(self, data: str) -> bool:
        try:
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.host, self.port))
            sock.sendall(data.encode())
            sock.close()
            return True
        except Exception as e:
            logger.error(f"Failed to send to Graphite: {e}")
            return False


class DataDogExporter:
    def __init__(self, api_key: str = None, app_key: str = None):
        self.api_key = api_key
        self.app_key = app_key
        self.api_url = "https://api.datadoghq.com/api/v1/series"
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not self.api_key:
            logger.warning("DataDog not configured")
            return False
        
        series = [
            {
                "metric": f"network.monitor.{metric.check_type.value}.status",
                "points": [[int(metric.timestamp.timestamp()), 1 if metric.status.value == "up" else 0]],
                "type": "gauge",
                "tags": [
                    f"target:{target.id}",
                    f"host:{target.host}",
                    f"name:{target.name}",
                ],
            },
        ]
        
        if metric.latency_ms is not None:
            series.append({
                "metric": f"network.monitor.{metric.check_type.value}.latency",
                "points": [[int(metric.timestamp.timestamp()), metric.latency_ms]],
                "type": "gauge",
                "tags": [
                    f"target:{target.id}",
                    f"host:{target.host}",
                ],
            })
        
        payload = {"series": series}
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={
                    "DD-API-KEY": self.api_key,
                    "DD-APPLICATION-KEY": self.app_key or "",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            return response.status_code in [200, 202]
        except Exception as e:
            logger.error(f"Failed to send to DataDog: {e}")
            return False


class OpenTSDBExporter:
    def __init__(self, url: str = None):
        self.url = url
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not self.url:
            logger.warning("OpenTSDB not configured")
            return False
        
        timestamp = int(metric.timestamp.timestamp())
        
        metric_data = {
            "metric": f"network.monitor.{metric.check_type.value}.status",
            "timestamp": timestamp,
            "value": 1 if metric.status.value == "up" else 0,
            "tags": {
                "target_id": target.id,
                "host": target.host,
                "name": target.name,
            },
        }
        
        if metric.latency_ms is not None:
            latency_data = {
                "metric": f"network.monitor.{metric.check_type.value}.latency",
                "timestamp": timestamp,
                "value": metric.latency_ms,
                "tags": {
                    "target_id": target.id,
                    "host": target.host,
                },
            }
            metric_data = [metric_data, latency_data]
        
        try:
            response = requests.post(
                self.url + "/api/put",
                json=metric_data,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send to OpenTSDB: {e}")
            return False


class TimescaleDBExporter:
    def __init__(self, connection_string: str = None):
        self.connection_string = connection_string
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not self.connection_string:
            logger.warning("TimescaleDB not configured")
            return False
        
        try:
            import psycopg2
            
            conn = psycopg2.connect(self.connection_string)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT INTO network_metrics 
                (target_id, target_name, target_host, check_type, status, value, latency_ms, error, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    target.id,
                    target.name,
                    target.host,
                    metric.check_type.value,
                    metric.status.value,
                    metric.value,
                    metric.latency_ms,
                    metric.error,
                    metric.timestamp,
                ),
            )
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Failed to export to TimescaleDB: {e}")
            return False


class ElasticsearchExporter:
    def __init__(self, url: str = None, index: str = "network-metrics", api_key: str = None):
        self.url = url
        self.index = index
        self.api_key = api_key
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not self.url:
            logger.warning("Elasticsearch not configured")
            return False
        
        document = {
            "target_id": target.id,
            "target_name": target.name,
            "target_host": target.host,
            "check_type": metric.check_type.value,
            "status": metric.status.value,
            "value": metric.value,
            "latency_ms": metric.latency_ms,
            "error": metric.error,
            "@timestamp": metric.timestamp.isoformat(),
        }
        
        try:
            response = requests.post(
                f"{self.url}/{self.index}/_doc",
                json=document,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"ApiKey {self.api_key}" if self.api_key else "",
                },
                timeout=10,
            )
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"Failed to export to Elasticsearch: {e}")
            return False


class MQTTExporter:
    def __init__(self, broker: str = None, port: int = 1883, topic: str = "network/monitor", username: str = None, password: str = None):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.username = username
        self.password = password
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not self.broker:
            logger.warning("MQTT not configured")
            return False
        
        payload = {
            "target_id": target.id,
            "target_name": target.name,
            "target_host": target.host,
            "check_type": metric.check_type.value,
            "status": metric.status.value,
            "value": metric.value,
            "latency_ms": metric.latency_ms,
            "error": metric.error,
            "timestamp": metric.timestamp.isoformat(),
        }
        
        try:
            import paho.mqtt.client as mqtt
            
            client = mqtt.Client()
            if self.username and self.password:
                client.username_pw_set(self.username, self.password)
            
            client.connect(self.broker, self.port, 60)
            client.publish(self.topic, json.dumps(payload))
            client.disconnect()
            
            return True
        except ImportError:
            logger.warning("paho-mqtt not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to export to MQTT: {e}")
            return False


class NATSExporter:
    def __init__(self, url: str = None, subject: str = "network.monitor"):
        self.url = url
        self.subject = subject
    
    def export_metric(self, metric: Metric, target: MonitorTarget) -> bool:
        if not self.url:
            logger.warning("NATS not configured")
            return False
        
        payload = {
            "target_id": target.id,
            "target_name": target.name,
            "target_host": target.host,
            "check_type": metric.check_type.value,
            "status": metric.status.value,
            "value": metric.value,
            "latency_ms": metric.latency_ms,
            "timestamp": metric.timestamp.isoformat(),
        }
        
        try:
            import nats
            
            await nats.connect(self.url)
            await nats.publish(self.subject, json.dumps(payload))
            await nats.close()
            
            return True
        except ImportError:
            logger.warning("nats-py not installed")
            return False
        except Exception as e:
            logger.error(f"Failed to export to NATS: {e}")
            return False