"""Database monitoring module."""

import logging
import time
from datetime import datetime
from typing import Optional

from src.models import MonitorTarget, Metric, Status, CheckType

logger = logging.getLogger(__name__)

try:
    import pymysql
    from pymysql.cursors import DictCursor
    PYMysql_AVAILABLE = True
except ImportError:
    PYMysql_AVAILABLE = False

try:
    import psycopg2
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    import pymemcache
    from pymemcache.client.base import Client as MemcacheClient
    PYMEMCACHE_AVAILABLE = True
except ImportError:
    PYMEMCACHE_AVAILABLE = False


class DatabaseMonitor:
    def __init__(self):
        self.supported_types = ["mysql", "postgresql", "mongodb", "redis", "memcached", "mariadb"]
    
    def check(self, target: MonitorTarget) -> Metric:
        start_time = time.time()
        
        db_type = target.device_type.value.lower() if target.device_type else "mysql"
        
        try:
            if db_type in ["mysql", "mariadb"]:
                result = self._check_mysql(target)
            elif db_type == "postgresql":
                result = self._check_postgresql(target)
            elif db_type == "mongodb":
                result = self._check_mongodb(target)
            elif db_type == "redis":
                result = self._check_redis(target)
            elif db_type == "memcached":
                result = self._check_memcached(target)
            else:
                result = {"status": "down", "error": f"Unsupported database type: {db_type}"}
            
            latency_ms = (time.time() - start_time) * 1000
            
            if result.get("status") == "up":
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.DATABASE,
                    value=result.get("value", 1),
                    status=Status.UP,
                    latency_ms=latency_ms,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.DATABASE,
                    value=0,
                    status=Status.DOWN,
                    latency_ms=latency_ms,
                    error=result.get("error", "Unknown error"),
                )
                
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.DATABASE,
                value=0,
                status=Status.DOWN,
                latency_ms=(time.time() - start_time) * 1000,
                error=str(e),
            )
    
    def _check_mysql(self, target: MonitorTarget) -> dict:
        if not PYMysql_AVAILABLE:
            return {"status": "down", "error": "pymysql not installed"}
        
        try:
            conn = pymysql.connect(
                host=target.host,
                port=target.port or 3306,
                user=target.snmp_community or "root",
                password=target.model or "",
                database=target.http_url or "mysql",
                connect_timeout=target.timeout,
                cursorclass=DictCursor,
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as result")
                cursor.fetchone()
                
                cursor.execute("SHOW STATUS")
                status = dict(cursor.fetchall())
                
                uptime = int(status.get("Uptime", 0))
                connections = int(status.get("Threads_connected", 0))
            
            conn.close()
            
            return {
                "status": "up",
                "value": uptime,
                "connections": connections,
            }
            
        except pymysql.Error as e:
            return {"status": "down", "error": str(e)}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def _check_postgresql(self, target: MonitorTarget) -> dict:
        if not PSYCOPG_AVAILABLE:
            return {"status": "down", "error": "psycopg2 not installed"}
        
        try:
            conn = psycopg2.connect(
                host=target.host,
                port=target.port or 5432,
                user=target.snmp_community or "postgres",
                password=target.model or "",
                database=target.http_url or "postgres",
                connect_timeout=target.timeout,
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as result")
                cursor.fetchone()
                
                cursor.execute("SHOW server_version")
                version = cursor.fetchone()[0]
                
                cursor.execute("SELECT pg_postmaster_start_time()")
                start_time = cursor.fetchone()[0]
                
                cursor.execute("SELECT numbackends FROM pg_stat_database WHERE datname = current_database()")
                connections = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
            
            conn.close()
            
            return {
                "status": "up",
                "value": version,
                "connections": connections,
            }
            
        except psycopg2.Error as e:
            return {"status": "down", "error": str(e)}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def _check_mongodb(self, target: MonitorTarget) -> dict:
        if not PYMONGO_AVAILABLE:
            return {"status": "down", "error": "pymongo not installed"}
        
        try:
            client = MongoClient(
                host=target.host,
                port=target.port or 27017,
                username=target.snmp_community,
                password=target.model,
                serverSelectionTimeoutMS=target.timeout * 1000,
                connectTimeoutMS=target.timeout * 1000,
            )
            
            client.admin.command("ping")
            
            server_status = client.admin.command("serverStatus")
            
            client.close()
            
            return {
                "status": "up",
                "value": server_status.get("version", "unknown"),
                "uptime": server_status.get("uptime", 0),
            }
            
        except ConnectionFailure as e:
            return {"status": "down", "error": str(e)}
        except ServerSelectionTimeoutError as e:
            return {"status": "down", "error": str(e)}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def _check_redis(self, target: MonitorTarget) -> dict:
        if not REDIS_AVAILABLE:
            return {"status": "down", "error": "redis not installed"}
        
        try:
            client = redis.Redis(
                host=target.host,
                port=target.port or 6379,
                password=target.model,
                db=target.http_url or 0,
                socket_timeout=target.timeout,
                socket_connect_timeout=target.timeout,
            )
            
            info = client.info()
            
            client.close()
            
            return {
                "status": "up",
                "value": info.get("uptime_in_seconds", 0),
                "connections": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory_human", "unknown"),
            }
            
        except redis.ConnectionError as e:
            return {"status": "down", "error": str(e)}
        except redis.TimeoutError as e:
            return {"status": "down", "error": str(e)}
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def _check_memcached(self, target: MonitorTarget) -> dict:
        if not PYMEMCACHE_AVAILABLE:
            return {"status": "down", "error": "pymemcache not installed"}
        
        try:
            client = MemcacheClient(
                (target.host, target.port or 11211),
                timeout=target.timeout,
            )
            
            stats = client.get_stats()
            
            client.close()
            
            if stats:
                stats_dict = dict(stats[0][1])
                return {
                    "status": "up",
                    "value": int(stats_dict.get(b"uptime", 0)),
                    "curr_items": int(stats_dict.get(b"curr_items", 0)),
                    "bytes": int(stats_dict.get(b"bytes", 0)),
                }
            
            return {"status": "down", "error": "No stats returned"}
            
        except Exception as e:
            return {"status": "down", "error": str(e)}
    
    def get_mysql_metrics(self, host: str, port: int = 3306, user: str = "root", password: str = "", database: str = "mysql") -> dict:
        if not PYMysql_AVAILABLE:
            return {"error": "pymysql not installed"}
        
        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=5,
                cursorclass=DictCursor,
            )
            
            metrics = {}
            
            with conn.cursor() as cursor:
                cursor.execute("SHOW GLOBAL STATUS")
                status = dict(cursor.fetchall())
                
                metrics["queries"] = int(status.get("Questions", 0))
                metrics["connections"] = int(status.get("Threads_connected", 0))
                metrics["connections_max"] = int(status.get("Max_used_connections", 0))
                metrics["bytes_sent"] = int(status.get("Bytes_sent", 0))
                metrics["bytes_received"] = int(status.get("Bytes_received", 0))
                metrics["innodb_buffer_pool_size"] = int(status.get("Innodb_buffer_pool_size", 0))
                metrics["key_buffer_size"] = int(status.get("Key_buffer_size", 0))
                metrics["query_cache_size"] = int(status.get("Query_cache_size", 0))
                metrics["table_open_cache"] = int(status.get("Table_open_cache", 0))
                
                cursor.execute("SHOW GLOBAL VARIABLES")
                variables = dict(cursor.fetchall())
                
                metrics["max_connections"] = int(variables.get("max_connections", 0))
                metrics["version"] = variables.get("version", "unknown")
                metrics["datadir"] = variables.get("datadir", "unknown")
            
            conn.close()
            return metrics
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_postgresql_metrics(self, host: str, port: int = 5432, user: str = "postgres", password: str = "", database: str = "postgres") -> dict:
        if not PSYCOPG_AVAILABLE:
            return {"error": "psycopg2 not installed"}
        
        try:
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                connect_timeout=5,
            )
            
            metrics = {}
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT version()")
                metrics["version"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT pg_postmaster_start_time()")
                metrics["start_time"] = str(cursor.fetchone()[0])
                
                cursor.execute("SELECT pg_current_xlog_location()")
                metrics["xlog_location"] = str(cursor.fetchone()[0])
                
                cursor.execute("SELECT count(*) FROM pg_stat_database WHERE datname = current_database()")
                metrics["connections"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT sum(numbackends) FROM pg_stat_database")
                metrics["total_connections"] = cursor.fetchone()[0] or 0
            
            conn.close()
            return metrics
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_mongodb_metrics(self, host: str, port: int = 27017, username: str = None, password: str = None) -> dict:
        if not PYMONGO_AVAILABLE:
            return {"error": "pymongo not installed"}
        
        try:
            client = MongoClient(
                host=host,
                port=port,
                username=username,
                password=password,
                serverSelectionTimeoutMS=5000,
            )
            
            server_status = client.admin.command("serverStatus")
            db_stats = client.admin.command("dbStats")
            
            metrics = {
                "version": server_status.get("version"),
                "uptime": server_status.get("uptime"),
                "connections": server_status.get("connections", {}).get("current"),
                "memory_resident": server_status.get("mem", {}).get("resident"),
                "memory_virtual": server_status.get("mem", {}).get("virtual"),
                "storage_engine": server_status.get("StorageEngine"),
                "db_total_size": db_stats.get("dataSize"),
                "db_total_indexes": db_stats.get("indexCount"),
                "db_collections": db_stats.get("collections"),
            }
            
            client.close()
            return metrics
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_redis_metrics(self, host: str, port: int = 6379, password: str = None, db: int = 0) -> dict:
        if not REDIS_AVAILABLE:
            return {"error": "redis not installed"}
        
        try:
            client = redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                socket_timeout=5,
            )
            
            info = client.info()
            
            metrics = {
                "version": info.get("redis_version"),
                "uptime": info.get("uptime_in_seconds"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory"),
                "used_memory_peak": info.get("used_memory_peak"),
                "total_connections": info.get("total_connections_received"),
                "total_commands": info.get("total_commands_processed"),
                "keyspace_hits": info.get("keyspace_hits"),
                "keyspace_misses": info.get("keyspace_misses"),
                "instantaneous_ops": info.get("instantaneous_ops_per_sec"),
            }
            
            client.close()
            return metrics
            
        except Exception as e:
            return {"error": str(e)}