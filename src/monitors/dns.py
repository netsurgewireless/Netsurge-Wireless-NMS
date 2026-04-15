"""DNS monitoring module."""

import logging
import socket
import time
from typing import Optional
from datetime import datetime

import dns.resolver
import dns.exception
import dns.query
import dns.tsigkeyring

from src.models import MonitorTarget, Metric, Status, CheckType

logger = logging.getLogger(__name__)


class DNSMonitor:
    def __init__(self):
        self.default_dns_servers = ["8.8.8.8", "1.1.1.1"]
        self.default_timeout = 5
    
    def check(self, target: MonitorTarget) -> Metric:
        start_time = time.time()
        
        domain = target.http_url or target.host
        record_type = target.wmi_query or "A"
        dns_server = target.model
        
        try:
            resolver = dns.resolver.Resolver()
            resolver.timeout = target.timeout
            resolver.lifetime = target.timeout
            
            if dns_server:
                resolver.nameservers = [dns_server]
            
            answers = resolver.resolve(domain, record_type)
            
            latency_ms = (time.time() - start_time) * 1000
            
            if answers:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.DNS,
                    value=len(answers),
                    status=Status.UP,
                    latency_ms=latency_ms,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.DNS,
                    value=0,
                    status=Status.DOWN,
                    latency_ms=latency_ms,
                    error="No DNS records found",
                )
                
        except dns.resolver.NXDOMAIN:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.DNS,
                value=0,
                status=Status.DOWN,
                latency_ms=(time.time() - start_time) * 1000,
                error="Domain does not exist (NXDOMAIN)",
            )
        except dns.resolver.NoNameservers:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.DNS,
                value=0,
                status=Status.DOWN,
                latency_ms=(time.time() - start_time) * 1000,
                error="No nameservers available",
            )
        except dns.exception.Timeout:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.DNS,
                value=0,
                status=Status.DOWN,
                latency_ms=(time.time() - start_time) * 1000,
                error="DNS query timeout",
            )
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.DNS,
                value=0,
                status=Status.DOWN,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
    
    def check_mx(self, domain: str, dns_server: Optional[str] = None) -> dict:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            
            mx_records = resolver.resolve(domain, "MX")
            
            return {
                "exists": True,
                "mx_records": [
                    {"priority": r.preference, "host": str(r.exchange).rstrip(".")}
                    for r in mx_records
                ],
            }
        except dns.resolver.NXDOMAIN:
            return {"exists": False, "error": "Domain not found"}
        except dns.resolver.NoAnswer:
            return {"exists": False, "error": "No MX records"}
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def check_txt(self, domain: str, dns_server: Optional[str] = None) -> dict:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            
            txt_records = resolver.resolve(domain, "TXT")
            
            return {
                "exists": True,
                "txt_records": [str(r).strip('"') for r in txt_records],
            }
        except dns.resolver.NXDOMAIN:
            return {"exists": False, "error": "Domain not found"}
        except dns.resolver.NoAnswer:
            return {"exists": False, "error": "No TXT records"}
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def check_ns(self, domain: str, dns_server: Optional[str] = None) -> dict:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            
            ns_records = resolver.resolve(domain, "NS")
            
            return {
                "exists": True,
                "ns_records": [str(r).rstrip(".") for r in ns_records],
            }
        except dns.resolver.NXDOMAIN:
            return {"exists": False, "error": "Domain not found"}
        except dns.resolver.NoAnswer:
            return {"exists": False, "error": "No NS records"}
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def check_soa(self, domain: str, dns_server: Optional[str] = None) -> dict:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            
            soa_record = resolver.resolve(domain, "SOA")
            
            return {
                "exists": True,
                "soa": {
                    "mname": str(soa_record[0].mname).rstrip("."),
                    "rname": str(soa_record[0].rname).rstrip("."),
                    "serial": soa_record[0].serial,
                    "refresh": soa_record[0].refresh,
                    "retry": soa_record[0].retry,
                    "expire": soa_record[0].expire,
                    "minimum": soa_record[0].minimum,
                },
            }
        except dns.resolver.NXDOMAIN:
            return {"exists": False, "error": "Domain not found"}
        except dns.resolver.NoAnswer:
            return {"exists": False, "error": "No SOA record"}
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def check_spf(self, domain: str, dns_server: Optional[str] = None) -> dict:
        result = self.check_txt(domain, dns_server)
        
        if result.get("exists"):
            for txt in result.get("txt_records", []):
                if txt.startswith("v=spf1"):
                    return {
                        "exists": True,
                        "spf_record": txt,
                        "valid": True,
                    }
        
        return {"exists": False, "spf_record": None, "valid": False}
    
    def check_dmarc(self, domain: str, dns_server: Optional[str] = None) -> dict:
        result = self.check_txt(f"_dmarc.{domain}", dns_server)
        
        if result.get("exists"):
            for txt in result.get("txt_records", []):
                if txt.startswith("v=DMARC1"):
                    return {
                        "exists": True,
                        "dmarc_record": txt,
                        "valid": True,
                    }
        
        return {"exists": False, "dmarc_record": None, "valid": False}
    
    def check_dnssec(self, domain: str, dns_server: Optional[str] = None) -> dict:
        result = self.check_ds(domain, dns_server)
        
        return {
            "domain": domain,
            "ds_records": result.get("ds_records", []),
            "keys": result.get("keys", []),
            "secured": len(result.get("ds_records", [])) > 0,
        }
    
    def check_ds(self, domain: str, dns_server: Optional[str] = None) -> dict:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            
            ds_records = resolver.resolve(domain, "DS")
            
            return {
                "exists": True,
                "ds_records": [
                    {
                        "key_tag": r.key_tag,
                        "algorithm": r.algorithm,
                        "digest_type": r.digest_type,
                        "digest": r.digest.hex(),
                    }
                    for r in ds_records
                ],
            }
        except dns.resolver.NXDOMAIN:
            return {"exists": False, "error": "Domain not found"}
        except dns.resolver.NoAnswer:
            return {"exists": False, "ds_records": []}
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def check_caa(self, domain: str, dns_server: Optional[str] = None) -> dict:
        try:
            resolver = dns.resolver.Resolver()
            if dns_server:
                resolver.nameservers = [dns_server]
            
            caa_records = resolver.resolve(domain, "CAA")
            
            return {
                "exists": True,
                "caa_records": [
                    {
                        "flags": r.flags,
                        "tag": r.tag,
                        "value": r.value,
                    }
                    for r in caa_records
                ],
            }
        except dns.resolver.NXDOMAIN:
            return {"exists": False, "error": "Domain not found"}
        except dns.resolver.NoAnswer:
            return {"exists": False, "caa_records": []}
        except Exception as e:
            return {"exists": False, "error": str(e)}