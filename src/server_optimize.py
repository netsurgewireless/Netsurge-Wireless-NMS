"""OS-specific performance optimizations for server deployment."""

import os
import sys
import platform
import logging
import threading
import resource
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class OSConfig:
    max_workers: int = 50
    worker_threads: int = 20
    io_workers: int = 10
    connection_pool_size: int = 100
    socket_timeout: int = 10
    buffer_size: int = 8192
    enable_multiprocessing: bool = False
    process_priority: str = "normal"
    cpu_affinity: Optional[list[int]] = None
    nice_value: Optional[int] = None
    oom_score_adj: Optional[int] = None


class OSPlatform:
    @staticmethod
    def get_platform() -> str:
        return platform.system().lower()

    @staticmethod
    def is_linux() -> bool:
        return platform.system() == "Linux"

    @staticmethod
    def is_windows() -> bool:
        return platform.system() == "Windows"

    @staticmethod
    def is_macos() -> bool:
        return platform.system() == "Darwin"


class ProcessOptimizer:
    def __init__(self):
        self.platform = OSPlatform()
        self._original_priority = None

    def optimize_for_server(self, config: OSConfig = None) -> OSConfig:
        if config is None:
            config = self._get_default_config()
        
        self._set_process_priority(config.process_priority)
        
        if config.cpu_affinity:
            self._set_cpu_affinity(config.cpu_affinity)
        
        if self.platform.is_linux():
            self._optimize_linux(config)
        elif self.platform.is_windows():
            self._optimize_windows(config)
        
        self._configure_threading(config)
        self._configure_network(config)
        
        logger.info(f"Applied server optimizations: {config}")
        return config

    def _get_default_config(self) -> OSConfig:
        cpu_count = os.cpu_count() or 4
        memory_gb = self._get_memory_gb()
        
        if memory_gb >= 16 and cpu_count >= 4:
            return OSConfig(
                max_workers=100,
                worker_threads=50,
                io_workers=20,
                connection_pool_size=200,
                process_priority="high",
            )
        elif memory_gb >= 8 and cpu_count >= 2:
            return OSConfig(
                max_workers=50,
                worker_threads=25,
                io_workers=10,
                connection_pool_size=100,
                process_priority="normal",
            )
        else:
            return OSConfig(
                max_workers=20,
                worker_threads=10,
                io_workers=5,
                connection_pool_size=50,
                process_priority="normal",
            )

    def _get_memory_gb(self) -> float:
        try:
            if self.platform.is_windows():
                import ctypes
                kernel32 = ctypes.windll.kernel32
                c_ulong = ctypes.c_ulong
                class MEMORYSTATUS(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", c_ulong),
                        ("dwMemoryLoad", c_ulong),
                        ("dwTotalPhys", c_ulong),
                        ("dwAvailPhys", c_ulong),
                        ("dwTotalPageFile", c_ulong),
                        ("dwAvailPageFile", c_ulong),
                        ("dwTotalVirtual", c_ulong),
                        ("dwAvailVirtual", c_ulong),
                    ]
                stat = MEMORYSTATUS()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUS)
                kernel32.GlobalMemoryStatus(ctypes.byref(stat))
                return stat.dwTotalPhys / (1024**3)
            else:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            return int(line.split()[1]) / (1024**2)
        except:
            pass
        return 4.0

    def _set_process_priority(self, priority: str):
        try:
            if self.platform.is_windows():
                import ctypes
                from ctypes import wintypes
                
                priorities = {
                    "idle": 4,
                    "below_normal": 6,
                    "normal": 2,
                    "above_normal": 1,
                    "high": -1,
                    "realtime": -15,
                }
                
                priority_class = priorities.get(priority.lower(), 2)
                kernel32 = ctypes.windll.kernel32
                kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), priority_class)
                logger.info(f"Set Windows process priority to {priority}")
                
            elif self.platform.is_linux():
                nice_values = {
                    "idle": 19,
                    "below_normal": 10,
                    "normal": 0,
                    "above_normal": -5,
                    "high": -10,
                    "realtime": -20,
                }
                
                nice_val = nice_values.get(priority.lower(), 0)
                os.nice(nice_val)
                logger.info(f"Set Linux process nice value to {nice_val}")
                
        except Exception as e:
            logger.warning(f"Could not set process priority: {e}")

    def _set_cpu_affinity(self, cpus: list[int]):
        try:
            if self.platform.is_windows():
                import ctypes
                from ctypes import wintypes
                
                kernel32 = ctypes.windll.kernel32
                process = kernel32.GetCurrentProcess()
                
                if hasattr(kernel32, "SetProcessAffinityMask"):
                    mask = sum(1 << cpu for cpu in cpus)
                    kernel32.SetProcessAffinityMask(process, mask)
                    logger.info(f"Set Windows CPU affinity to {cpus}")
                    
            elif self.platform.is_linux():
                pid = os.getpid()
                with open(f"/proc/{pid}/status", "r") as f:
                    for line in f:
                        if line.startswith("Cpus_allowed:"):
                            pass
                
                os.sched_setaffinity(0, set(cpus))
                logger.info(f"Set Linux CPU affinity to {cpus}")
                
        except Exception as e:
            logger.warning(f"Could not set CPU affinity: {e}")

    def _optimize_linux(self, config: OSConfig):
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            resource.setrlimit(resource.RLIMIT_NOFILE, (hard, hard))
            
            soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
            resource.setrlimit(resource.RLIMIT_NPROC, (hard, hard))
            
            logger.info("Optimized Linux resource limits")
        except Exception as e:
            logger.warning(f"Could not optimize Linux resources: {e}")

    def _optimize_windows(self, config: OSConfig):
        try:
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            
            WSAServiceLookup = kernel32.WSAServiceLookup
            WSAServiceLookup.restype = wintypes.BOOL
            
            IoPriority = 2
            if hasattr(kernel32, "SetPriorityClass"):
                process = kernel32.GetCurrentProcess()
                kernel32.SetPriorityClass(process, IoPriority)
                
            logger.info("Optimized Windows settings")
        except Exception as e:
            logger.warning(f"Could not optimize Windows settings: {e}")

    def _configure_threading(self, config: OSConfig):
        thread_count = min(config.worker_threads + config.io_workers, 100)
        
        threading.current_thread().setName("Main")
        
        for thread in threading.enumerate():
            if thread.name.startswith("Thread-"):
                thread.daemon = True
        
        logger.info(f"Configured threading for {thread_count} workers")

    def _configure_network(self, config: OSConfig):
        try:
            import socket
            
            default_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(config.socket_timeout)
            
            if hasattr(socket, 'TCP_NODELAY'):
                pass
            
            logger.info(f"Configured network timeout to {config.socket_timeout}s")
        except Exception as e:
            logger.warning(f"Could not configure network: {e}")


class ConnectionPool:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self._pool = []
        self._lock = threading.Lock()
        self._semaphore = threading.Semaphore(max_size)

    def acquire(self):
        self._semaphore.acquire()
        with self._lock:
            if self._pool:
                return self._pool.pop()
        return None

    def release(self, conn):
        with self._lock:
            if len(self._pool) < self.max_size:
                self._pool.append(conn)
        self._semaphore.release()

    def close_all(self):
        with self._lock:
            for conn in self._pool:
                try:
                    conn.close()
                except:
                    pass
            self._pool.clear()


def get_optimal_workers() -> int:
    cpu_count = os.cpu_count() or 4
    memory_gb = get_memory_gb()
    
    if memory_gb >= 32 and cpu_count >= 8:
        return min(200, cpu_count * 25)
    elif memory_gb >= 16 and cpu_count >= 4:
        return min(100, cpu_count * 15)
    elif memory_gb >= 8 and cpu_count >= 2:
        return min(50, cpu_count * 10)
    else:
        return min(20, cpu_count * 5)


def get_memory_gb() -> float:
    try:
        if OSPlatform.is_windows():
            import ctypes
            kernel32 = ctypes.windll.kernel32
            class MEMORYSTATUS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("dwTotalPhys", ctypes.c_ulong),
                ]
            stat = MEMORYSTATUS()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUS)
            kernel32.GlobalMemoryStatus(ctypes.byref(stat))
            return stat.dwTotalPhys / (1024**3)
        else:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / (1024**2)
    except:
        pass
    return 4.0
