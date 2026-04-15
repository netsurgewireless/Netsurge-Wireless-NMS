"""NTP server monitoring module."""

import socket
import struct
import time
from datetime import datetime, timedelta
from typing import Optional
import logging

from src.models import Metric, Status, CheckType, MonitorTarget

logger = logging.getLogger(__name__)


class NTPProtocol:
    NTP_PORT = 123
    NTP_SERVER = "pool.ntp.org"
    NTP_TIMEOUT = 5
    
    NTP_MODE_CLIENT = 3
    NTP_MODE_SERVER = 4
    NTP_VERSION = 4
    
    NTP_OFFSET = 2208988800

    @staticmethod
    def _to_int(dt: datetime) -> int:
        return int(dt.timestamp()) + NTPProtocol.NTP_OFFSET

    @staticmethod
    def _from_int(timestamp: int) -> datetime:
        return datetime.fromtimestamp(timestamp - NTPProtocol.NTP_OFFSET)

    @staticmethod
    def _pack_packet() -> bytes:
        data = bytes(48)
        data = bytes([NTPProtocol.NTP_VERSION << 3 | NTPProtocol.NTP_MODE_CLIENT])
        return data

    @staticmethod
    def _unpack_packet(data: bytes) -> Optional[dict]:
        if len(data) < 48:
            return None
        
        stratum = data[1]
        poll = data[2]
        precision = data[3]
        
        ref_time = struct.unpack("!I", data[16:20])[0]
        orig_time = struct.unpack("!I", data[24:28])[0]
        recv_time = struct.unpack("!I", data[32:36])[0]
        trans_time = struct.unpack("!I", data[40:44])[0]
        
        if trans_time == 0:
            return None
        
        try:
            t_origin = NTPProtocol._from_int(orig_time - NTPProtocol.NTP_OFFSET)
            t_recv = NTPProtocol._from_int(recv_time - NTPProtocol.NTP_OFFSET)
            t_trans = NTPProtocol._from_int(trans_time - NTPProtocol.NTP_OFFSET)
            
            return {
                "stratum": stratum,
                "poll": poll,
                "precision": precision,
                "reference_time": t_origin,
                "receive_time": t_recv,
                "transmit_time": t_trans,
            }
        except:
            return None


class NTPClient:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def get_time(self, server: str = None) -> Optional[datetime]:
        server = server or NTPProtocol.NTP_SERVER
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(self.timeout)
            sock.sendto(NTPProtocol._pack_packet(), (server, NTPProtocol.NTP_PORT))
            data, addr = sock.recvfrom(48)
            sock.close()
            
            result = NTPProtocol._unpack_packet(data)
            if result:
                return result.get("transmit_time")
        except Exception as e:
            logger.debug(f"NTP request to {server} failed: {e}")
        
        return None


class NTPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 123):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.stratum = 2
        self.reference_time = datetime.now()

    def start(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.settimeout(1)
            self.running = True
            logger.info(f"NTP server started on {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to start NTP server: {e}")
            return False

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("NTP server stopped")

    def handle_request(self) -> Optional[bytes]:
        try:
            data, addr = self.socket.recvfrom(48)
            
            version = (data[0] >> 3) & 0x07
            mode = data[0] & 0x07
            
            if mode != NTPProtocol.NTP_MODE_CLIENT:
                return None
            
            packet = bytearray(48)
            
            packet[0] = (NTPProtocol.NTP_VERSION << 3) | NTPProtocol.NTP_MODE_SERVER
            packet[1] = self.stratum
            
            now = datetime.now()
            ref_timestamp = int(now.timestamp()) + NTPProtocol.NTP_OFFSET
            trans_timestamp = ref_timestamp
            
            packet[16:20] = struct.pack("!I", ref_timestamp)
            packet[24:28] = struct.pack("!I", int(now.timestamp()))
            packet[32:36] = struct.pack("!I", int(now.timestamp()))
            packet[40:44] = struct.pack("!I", trans_timestamp)
            
            return bytes(packet)
            
        except socket.timeout:
            return None
        except Exception as e:
            logger.debug(f"NTP request handling error: {e}")
            return None


class NTPHealthCheck:
    def __init__(self):
        self.client = NTPClient()
        self._ntp_servers = []
        self._offset_history = []

    def add_ntp_server(self, host: str):
        self._ntp_servers.append(host)

    def check(self, target: MonitorTarget) -> Metric:
        server = target.host
        
        start_time = time.time()
        
        try:
            ntp_time = self.client.get_time(server)
            
            if ntp_time:
                local_time = datetime.now()
                offset = (ntp_time - local_time).total_seconds()
                
                self._offset_history.append({
                    "server": server,
                    "offset": offset,
                    "timestamp": datetime.now()
                })
                
                if len(self._offset_history) > 100:
                    self._offset_history = self._offset_history[-100:]
                
                status = Status.UP
                if abs(offset) > 1.0:
                    status = Status.DEGRADED
                if abs(offset) > 5.0:
                    status = Status.DOWN
                
                elapsed = (time.time() - start_time) * 1000
                
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.PORT,
                    value=offset,
                    status=status,
                    latency_ms=elapsed,
                )
            else:
                return Metric(
                    target_id=target.id,
                    timestamp=datetime.now(),
                    check_type=CheckType.PORT,
                    value=0.0,
                    status=Status.DOWN,
                    error="No NTP response",
                )
                
        except Exception as e:
            return Metric(
                target_id=target.id,
                timestamp=datetime.now(),
                check_type=CheckType.PORT,
                value=0.0,
                status=Status.DOWN,
                error=str(e),
            )

    def get_offset_stats(self) -> dict:
        if not self._offset_history:
            return {}
        
        offsets = [h["offset"] for h in self._offset_history]
        
        return {
            "current": offsets[-1] if offsets else 0,
            "min": min(offsets) if offsets else 0,
            "max": max(offsets) if offsets else 0,
            "avg": sum(offsets) / len(offsets) if offsets else 0,
            "samples": len(offsets),
        }


class NTPMonitor:
    def __init__(self):
        self.health_check = NTPHealthCheck()

    def check(self, target: MonitorTarget) -> Metric:
        return self.health_check.check(target)
