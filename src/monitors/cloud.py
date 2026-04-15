"""Cloud services monitoring module."""

import logging
import time
import socket
from datetime import datetime
from typing import Optional

from src.models import MonitorTarget, Metric, Status, CheckType

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

try:
    from azure.identity import ClientSecretCredential
    from azure.mgmt.compute import ComputeManagementClient
    from azure.mgmt.network import NetworkManagementClient
    from azure.mgmt.monitor import MonitorManagementClient
    from azure.core.exceptions import ResourceNotFoundError, AzureError
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False

try:
    from google.cloud import monitoring_v3
    from google.cloud.monitoring_v3 import MetricServiceClient
    from google.api_core.exceptions import GoogleAPIError
    GCloud_AVAILABLE = True
except ImportError:
    GCloud_AVAILABLE = False


class CloudMonitor:
    def __init__(self):
        self.supported_providers = ["aws", "azure", "gcp"]
    
    def check(self, target: MonitorTarget) -> Metric:
        start_time = time.time()
        
        provider = target.snmp_community or "aws"
        
        try:
            if provider == "aws":
                result = self._check_aws(target)
            elif provider == "azure":
                result = self._check_azure(target)
            elif provider == "gcp":
                result = self._check_gcp(target)
            else:
                result = {"status": "down", "error": f"Unsupported provider: {provider}"}
            
            latency_ms = (time.time() - start_time) * 1000
            
            if result.get("status") == "up":
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.CLOUD,
                    value=result.get("value", 1),
                    status=Status.UP,
                    latency_ms=latency_ms,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.CLOUD,
                    value=0,
                    status=Status.DOWN,
                    latency_ms=latency_ms,
                    error=result.get("error", "Unknown error"),
                )
                
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.CLOUD,
                value=0,
                status=Status.DOWN,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
    
    def _check_aws(self, target: MonitorTarget) -> dict:
        if not BOTO3_AVAILABLE:
            return {"status": "down", "error": "boto3 not installed"}
        
        try:
            service = target.http_url or "ec2"
            region = target.model or "us-east-1"
            
            session = boto3.Session(
                aws_access_key_id=target.snmp_oid,
                aws_secret_access_key=target.firmware,
                region_name=region,
            )
            
            if service == "ec2":
                ec2 = session.client("ec2")
                response = ec2.describe_instances()
                instances = 0
                for reservation in response.get("Reservations", []):
                    instances += len(reservation.get("Instances", []))
                
                return {"status": "up", "value": instances, "service": "ec2"}
            
            elif service == "rds":
                rds = session.client("rds")
                response = rds.describe_db_instances()
                instances = len(response.get("DBInstances", []))
                
                return {"status": "up", "value": instances, "service": "rds"}
            
            elif service == "elb":
                elb = session.client("elbv2")
                response = elb.describe_load_balancers()
                instances = len(response.get("LoadBalancers", []))
                
                return {"status": "up", "value": instances, "service": "elb"}
            
            elif service == "s3":
                s3 = session.client("s3")
                response = s3.list_buckets()
                buckets = len(response.get("Buckets", []))
                
                return {"status": "up", "value": buckets, "service": "s3"}
            
            elif service == "lambda":
                lambda_client = session.client("lambda")
                response = lambda_client.list_functions()
                functions = len(response.get("Functions", []))
                
                return {"status": "up", "value": functions, "service": "lambda"}
            
            return {"status": "down", "error": f"Unknown AWS service: {service}"}
            
        except ClientError as e:
            return {"status": "down", "error": str(e)}
        except BotoCoreError as e:
            return {"status": "down", "error": str(e)}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def _check_azure(self, target: MonitorTarget) -> dict:
        if not AZURE_AVAILABLE:
            return {"status": "down", "error": "azure-mgmt not installed"}
        
        try:
            subscription_id = target.snmp_oid
            tenant_id = target.http_url
            client_id = target.firmware
            client_secret = target.wmi_query
            
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            
            service = target.http_method.lower() if target.http_method else "vm"
            
            if service == "vm":
                compute_client = ComputeManagementClient(
                    credential=credential,
                    subscription_id=subscription_id,
                )
                vms = list(compute_client.virtual_machines.list_all())
                
                return {"status": "up", "value": len(vms), "service": "vm"}
            
            elif service == "network":
                network_client = NetworkManagementClient(
                    credential=credential,
                    subscription_id=subscription_id,
                )
                nics = list(network_client.network_interfaces.list_all())
                
                return {"status": "up", "value": len(nics), "service": "network"}
            
            elif service == "storage":
                from azure.mgmt.storage import StorageManagementClient
                storage_client = StorageManagementClient(
                    credential=credential,
                    subscription_id=subscription_id,
                )
                accounts = list(storage_client.storage_accounts.list())
                
                return {"status": "up", "value": len(accounts), "service": "storage"}
            
            return {"status": "down", "error": f"Unknown Azure service: {service}"}
            
        except AzureError as e:
            return {"status": "down", "error": str(e)}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def _check_gcp(self, target: MonitorTarget) -> dict:
        if not GCloud_AVAILABLE:
            return {"status": "down", "error": "google-cloud-monitoring not installed"}
        
        try:
            project_id = target.snmp_oid
            credentials_path = target.http_url
            service = target.http_method.lower() if target.http_method else "compute"
            
            if credentials_path:
                credentials = None
            else:
                credentials = None
            
            client = MetricServiceClient()
            
            now = time.time()
            seconds = 60
            window = {"start": now - seconds, "end": now}
            
            if service == "compute":
                project_name = client.project_path(project_id)
                metric_type = "compute.googleapis.com/instance/cpu/utilization"
                
                return {"status": "up", "value": 1, "service": "compute"}
            
            elif service == "storage":
                return {"status": "up", "value": 1, "service": "storage"}
            
            return {"status": "down", "error": f"Unknown GCP service: {service}"}
            
        except GoogleAPIError as e:
            return {"status": "down", "error": str(e)}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def check_aws_health(self, region: str = "us-east-1") -> dict:
        if not BOTO3_AVAILABLE:
            return {"error": "boto3 not installed"}
        
        try:
            session = boto3.Session(region_name=region)
            health = session.client("health")
            
            response = health.describe_events(
                filter={
                    "eventStatusCodes": ["open", "closed"],
                }
            )
            
            return {
                "events": [
                    {
                        "arn": e.get("arn"),
                        "service": e.get("service"),
                        "eventTypeCode": e.get("eventTypeCode"),
                        "status": e.get("eventStatusCode"),
                        "region": e.get("region"),
                        "startTime": str(e.get("startTime")),
                    }
                    for e in response.get("events", [])
                ]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def check_aws_pricing(self, service: str, region: str = "us-east-1") -> dict:
        if not BOTO3_AVAILABLE:
            return {"error": "boto3 not installed"}
        
        try:
            session = boto3.Session(region_name=region)
            pricing = session.client("pricing", region_name="us-east-1")
            
            response = pricing.get_products(
                ServiceCode=service,
                Filters=[
                    {"Type": "TERM_MATCH", "Field": "location", "Value": region},
                ],
                MaxResults=1,
            )
            
            if response.get("PriceList"):
                import json
                return json.loads(response["PriceList"][0])
            
            return {"error": "No pricing data found"}
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_azure_vm_metrics(self, subscription_id: str, resource_group: str, vm_name: str, tenant_id: str, client_id: str, client_secret: str) -> dict:
        if not AZURE_AVAILABLE:
            return {"error": "azure-mgmt not installed"}
        
        try:
            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            
            compute_client = ComputeManagementClient(
                credential=credential,
                subscription_id=subscription_id,
            )
            
            vm = compute_client.virtual_machines.get(resource_group, vm_name)
            
            return {
                "name": vm.name,
                "id": vm.id,
                "location": vm.location,
                "vm_size": vm.size,
                "provisioning_state": vm.provisioning_state,
                "tags": vm.tags,
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_gcp_instance_metrics(self, project_id: str, zone: str, instance_name: str) -> dict:
        if not GCloud_AVAILABLE:
            return {"error": "google-cloud-monitoring not installed"}
        
        try:
            from google.cloud import compute_v1
            
            instances_client = compute_v1.InstancesClient()
            instance = instances_client.get(project=project_id, zone=zone, instance=instance_name)
            
            return {
                "name": instance.name,
                "status": instance.status,
                "machine_type": instance.machine_type,
                "zone": instance.zone,
                "network_interfaces": len(instance.network_interfaces),
                "internal_ip": instance.network_interfaces[0].network_ip if instance.network_interfaces else None,
            }
            
        except Exception as e:
            return {"error": str(e)}