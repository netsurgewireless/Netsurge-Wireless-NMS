"""AI daily sync scheduler for continuous learning and database updates."""

import logging
import threading
import time
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, dict, list, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


@dataclass
class SyncStatus:
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None
    sources_updated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    records_added: int = 0
    status: str = "idle"


@dataclass
class OIDRecord:
    oid: str
    name: str
    vendor: str
    mib: str
    description: str
    access: str = "read-only"
    data_type: str = "text"
    last_verified: Optional[datetime] = None


@dataclass
class VendorRecord:
    mac_prefix: str
    vendor_name: str
    category: str = ""
    last_verified: Optional[datetime] = None


class AIDailySync:
    MAC_VENDORS_API = "https://api.maclookup.dev/v2/macs"
    OID_REFS_API = "https://oidref.com"
    CVE_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com"

    def __init__(self, cache_dir: Path = None):
        if cache_dir is None:
            cache_dir = Path("./ai_cache")
        
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)
        
        self.oid_file = self.cache_dir / "oid_database.json"
        self.vendor_file = self.cache_dir / "vendor_database.json"
        self.cve_file = self.cache_dir / "cve_cache.json"
        
        self.oid_db: dict[str, OIDRecord] = {}
        self.vendor_db: dict[str, VendorRecord] = {}
        self.cve_cache: dict[str, list] = {}
        
        self.status = SyncStatus()
        self.scheduler = BackgroundScheduler()
        self._running = False
        
        self._load_databases()

    def _load_databases(self):
        if self.oid_file.exists():
            try:
                with open(self.oid_file) as f:
                    data = json.load(f)
                    self.oid_db = {k: OIDRecord(**v) for k, v in data.items()}
                logger.info(f"Loaded {len(self.oid_db)} OID records")
            except Exception as e:
                logger.error(f"Failed to load OID database: {e}")

        if self.vendor_file.exists():
            try:
                with open(self.vendor_file) as f:
                    data = json.load(f)
                    self.vendor_db = {k: VendorRecord(**v) for k, v in data.items()}
                logger.info(f"Loaded {len(self.vendor_db)} vendor records")
            except Exception as e:
                logger.error(f"Failed to load vendor database: {e}")

        if self.cve_file.exists():
            try:
                with open(self.cve_file) as f:
                    self.cve_cache = json.load(f)
            except:
                pass

    def _save_databases(self):
        try:
            with open(self.oid_file, "w") as f:
                json.dump({k: asdict(v) for k, v in self.oid_db.items()}, f, indent=2, default=str)
            
            with open(self.vendor_file, "w") as f:
                json.dump({k: asdict(v) for k, v in self.vendor_db.items()}, f, indent=2, default=str)
            
            with open(self.cve_file, "w") as f:
                json.dump(self.cve_cache, f, indent=2, default=str)
            
            logger.info("AI databases saved to disk")
        except Exception as e:
            logger.error(f"Failed to save databases: {e}")

    def start(self, interval_hours: int = 24):
        if self._running:
            return
        
        self._running = True
        
        self.scheduler.add_job(
            self.sync_all,
            trigger=CronTrigger(hour=2, minute=0),
            id="ai_daily_sync",
            name="AI Daily Database Sync",
            replace_existing=True,
        )
        
        self.scheduler.add_job(
            self.sync_all,
            trigger=IntervalTrigger(hours=interval_hours),
            id="ai_interval_sync",
            name="AI Interval Sync",
        )
        
        self.scheduler.start()
        logger.info(f"AI sync scheduler started (interval: {interval_hours}h)")

    def stop(self):
        self._running = False
        self.scheduler.shutdown(wait=True)
        logger.info("AI sync scheduler stopped")

    def sync_all(self):
        logger.info("Starting AI database sync...")
        self.status = SyncStatus()
        self.status.status = "running"
        
        self._sync_mac_vendors()
        
        self._sync_oid_database()
        
        self._sync_cve_database()
        
        self._save_databases()
        
        self.status.last_sync = datetime.now()
        self.status.status = "completed"
        logger.info(f"AI sync completed. Added {self.status.records_added} records")

    def _sync_mac_vendors(self):
        try:
            test_prefixes = [
                "000C29", "005056", "001A2B", "002315", "002721",
                "0024E8", "4CDFA5", "6CB8E5", "F48E38", "001122",
            ]
            
            for prefix in test_prefixes:
                try:
                    response = requests.get(
                        f"https://api.macvendors.com/{prefix}",
                        timeout=3
                    )
                    
                    if response.status_code == 200:
                        vendor = response.text.strip()
                        if vendor:
                            self.vendor_db[prefix] = VendorRecord(
                                mac_prefix=prefix,
                                vendor_name=vendor,
                                category="network",
                                last_verified=datetime.now()
                            )
                            self.status.records_added += 1
                            
                except:
                    pass
            
            self.status.sources_updated.append("mac_vendors")
            logger.info(f"Synced {len(test_prefixes)} MAC vendor entries")
            
        except Exception as e:
            logger.error(f"MAC vendor sync failed: {e}")
            self.status.errors.append(f"MAC vendor sync: {str(e)}")

    def _sync_oid_database(self):
        common_oids = [
            ("1.3.6.1.2.1.1.1.0", "sysDescr", "SNMP", "SNMPv2-MIB"),
            ("1.3.6.1.2.1.1.3.0", "sysUpTime", "SNMP", "SNMPv2-MIB"),
            ("1.3.6.1.2.1.1.5.0", "sysName", "SNMP", "SNMPv2-MIB"),
            ("1.3.6.1.2.1.2.2.1.10", "ifInOctets", "SNMP", "IF-MIB"),
            ("1.3.6.1.2.1.2.2.1.16", "ifOutOctets", "SNMP", "IF-MIB"),
            ("1.3.6.1.2.1.2.2.1.5", "ifSpeed", "SNMP", "IF-MIB"),
            ("1.3.6.1.2.1.2.2.1.8", "ifOperStatus", "SNMP", "IF-MIB"),
            ("1.3.6.1.4.1.9.9.109.1.1.1.1.5", "ciscoCPUTotal5min", "Cisco", "CISCO-PROCESS-MIB"),
            ("1.3.6.1.4.1.9.9.48.1.1.5", "ciscoMemoryPoolUsed", "Cisco", "CISCO-MEMORY-POOL-MIB"),
            ("1.3.6.1.4.1.2636.3.1.2.1.6", "jnxOperatingCPU", "Juniper", "JUNIPER-MIB"),
            ("1.3.6.1.4.1.2636.3.1.2.1.7", "jnxOperatingMemory", "Juniper", "JUNIPER-MIB"),
            ("1.3.6.1.4.1.14988.1.1.1.2.0", "mtxrCpuLoad", "MikroTik", "MIKROTIK-MIB"),
            ("1.3.6.1.4.1.14988.1.1.1.3.0", "mtxrMemoryUsed", "MikroTik", "MIKROTIK-MIB"),
            ("1.3.6.1.4.1.41112.1.4.1.0", "ubntGenericUptime", "Ubiquiti", "UBNT-MIB"),
            ("1.3.6.1.4.1.41112.1.4.2.0", "ubntGenericCpuLoad", "Ubiquiti", "UBNT-MIB"),
            ("1.3.6.1.4.1.41112.1.5.1.1", "ubntAirMaxSignal", "Ubiquiti", "UBNT-AIRMAX-MIB"),
            ("1.3.6.1.4.1.674.10895.5000.2.1.1", "dellCpuUtilization", "Dell", "DELL-10892-MIB"),
            ("1.3.6.1.4.1.11.2.14.11.5.1.1.1", "hpSwitchCpuStat", "HPE", "HP-SWITCH-RTNL-MIB"),
            ("1.3.6.1.4.1.12356.1.1.4.0", "fgSysCpuUsage", "Fortinet", "FORTINET-FORTIGATE-MIB"),
            ("1.3.6.1.4.1.25461.2.1.3.1.0", "panSysCpuUsage", "Palo Alto", "PANOS-MIB"),
        ]
        
        for oid, name, vendor, mib in common_oids:
            if oid not in self.oid_db:
                self.oid_db[oid] = OIDRecord(
                    oid=oid,
                    name=name,
                    vendor=vendor,
                    mib=mib,
                    description=f"{name} - {vendor}",
                    last_verified=datetime.now()
                )
                self.status.records_added += 1
        
        self.status.sources_updated.append("oid_database")
        logger.info(f"Synced {len(common_oids)} OID entries")

    def _sync_cve_database(self):
        vendors = ["cisco", "juniper", "mikrotik", "ubiquiti", "fortinet"]
        
        for vendor in vendors:
            try:
                response = requests.get(
                    f"{self.CVE_API}?keywordSearch={vendor}&resultsPerPage=3",
                    timeout=15,
                    headers={"User-Agent": "NetworkMonitor/1.0"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    cves = []
                    
                    for item in data.get("vulnerabilities", []):
                        cve = item.get("cve", {})
                        cves.append({
                            "id": cve.get("id"),
                            "description": cve.get("descriptions", [{}])[0].get("value", "")[:200],
                            "vendor": vendor,
                        })
                    
                    self.cve_cache[vendor] = cves
                    self.status.sources_updated.append(f"cve_{vendor}")
                    
            except Exception as e:
                logger.error(f"CVE sync for {vendor} failed: {e}")
        
        logger.info(f"CVE database synced for {len(vendors)} vendors")

    def get_status(self) -> dict:
        return {
            "status": self.status.status,
            "last_sync": self.status.last_sync.isoformat() if self.status.last_sync else None,
            "sources_updated": self.status.sources_updated,
            "records_added": self.status.records_added,
            "errors": self.status.errors,
            "oid_count": len(self.oid_db),
            "vendor_count": len(self.vendor_db),
        }

    def lookup_oid(self, oid: str) -> Optional[OIDRecord]:
        return self.oid_db.get(oid)

    def lookup_vendor(self, mac_prefix: str) -> Optional[VendorRecord]:
        return self.vendor_db.get(mac_prefix)

    def get_cves(self, vendor: str) -> list:
        return self.cve_cache.get(vendor, [])

    def force_sync(self):
        logger.info("Forcing AI database sync...")
        self.sync_all()
        return self.get_status()


class AISyncManager:
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
        self.sync = AIDailySync()

    def start(self, interval_hours: int = 24):
        self.sync.start(interval_hours)

    def stop(self):
        self.sync.stop()

    def get_status(self) -> dict:
        return self.sync.get_status()

    def force_sync(self) -> dict:
        return self.sync.force_sync()

    def lookup_oid(self, oid: str) -> Optional[dict]:
        result = self.sync.lookup_oid(oid)
        return asdict(result) if result else None

    def lookup_vendor(self, mac_prefix: str) -> Optional[dict]:
        result = self.sync.lookup_vendor(mac_prefix)
        return asdict(result) if result else None

    def get_cves(self, vendor: str) -> list:
        return self.sync.get_cves(vendor)
