"""Data models for network monitoring system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class Status(Enum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"


class CheckType(Enum):
    PING = "ping"
    PORT = "port"
    SNMP = "snmp"
    HTTP = "http"
    HTTPS = "https"
    SSL = "ssl"
    BANDWIDTH = "bandwidth"
    WMI = "wmi"
    BANDWIDTH_IN = "bandwidth_in"
    BANDWIDTH_OUT = "bandwidth_out"
    NGINX = "nginx"
    NTP = "ntp"


class DeviceType(Enum):
    GENERIC = "generic"
    
    WIRED = "wired"
    WIRELESS = "wireless"
    P2P = "point_to_point"
    P2MP = "point_to_multipoint"
    
    CISCO = "cisco"
    JUNIPER = "juniper"
    UBIQUITI = "ubiquiti"
    UBIQUITI_AIRMAX = "ubiquiti_airmax"
    UBIQUITI_5G = "ubiquiti_5g"
    NETONIX = "netonix"
    MIKROTIK = "mikrotik"
    MIKROTIK_WIRELESS = "mikrotik_wireless"
    HPE = "hpe"
    DELL = "dell"
    FORTINET = "fortinet"
    PANOS = "panos"
    LINUX = "linux"
    WINDOWS = "windows"
    NGINX = "nginx"
    ARUBA = "aruba"
    ARUBA_WIRELESS = "aruba_wireless"
    EXTREME = "extreme"
    PALO_ALTO = "palo_alto"
    VMWARE = "vmware"
    HYPERV = "hyperv"

    @classmethod
    def is_wireless(cls, device_type: "DeviceType") -> bool:
        wireless_types = {
            cls.WIRELESS,
            cls.P2P,
            cls.P2MP,
            cls.UBIQUITI,
            cls.UBIQUITI_AIRMAX,
            cls.UBIQUITI_5G,
            cls.MIKROTIK_WIRELESS,
            cls.ARUBA_WIRELESS,
        }
        return device_type in wireless_types

    @classmethod
    def is_p2p(cls, device_type: "DeviceType") -> bool:
        return device_type in {cls.P2P, cls.P2MP}

    @classmethod
    def get_supported_speeds(cls, device_type: "DeviceType") -> list[str]:
        if cls.is_wireless(device_type):
            return NetworkSpeed.__members__.keys()
        
        wired_speeds = [
            "SPEED_10M", "SPEED_100M", "SPEED_1G", "SPEED_2_5G",
            "SPEED_5G", "SPEED_10G", "SPEED_25G", "SPEED_40G",
            "SPEED_50G", "SPEED_100G", "SPEED_200G", "SPEED_400G",
            "SPEED_800G", "SPEED_1_6T", "SPEED_3_2T",
        ]
        return wired_speeds


class NetworkSpeed(Enum):
    SPEED_10M = "10Mbps"
    SPEED_100M = "100Mbps"
    SPEED_1G = "1Gbps"
    SPEED_2_5G = "2.5Gbps"
    SPEED_5G = "5Gbps"
    SPEED_10G = "10Gbps"
    SPEED_25G = "25Gbps"
    SPEED_40G = "40Gbps"
    SPEED_50G = "50Gbps"
    SPEED_100G = "100Gbps"
    SPEED_200G = "200Gbps"
    SPEED_400G = "400Gbps"
    SPEED_800G = "800Gbps"
    SPEED_1_6T = "1.6Tbps"
    SPEED_3_2T = "3.2Tbps"

    WIRELESS_11M = "11Mbps"
    WIRELESS_22M = "22Mbps"
    WIRELESS_54M = "54Mbps"
    WIRELESS_150M = "150Mbps"
    WIRELESS_300M = "300Mbps"
    WIRELESS_450M = "450Mbps"
    WIRELESS_600M = "600Mbps"
    WIRELESS_900M = "900Mbps"
    WIRELESS_1G = "1Gbps"
    WIRELESS_1_3G = "1.3Gbps"
    WIRELESS_1_7G = "1.7Gbps"
    WIRELESS_2G = "2Gbps"
    WIRELESS_2_5G = "2.5Gbps"
    WIRELESS_3G = "3Gbps"
    WIRELESS_4G = "4Gbps"
    WIRELESS_5G = "5Gbps"
    WIRELESS_6G = "6Gbps"
    WIRELESS_7G = "7Gbps"
    WIRELESS_8G = "8Gbps"
    WIRELESS_10G = "10Gbps"

    WIRELESS_60G_1_75G = "1.75Gbps"
    WIRELESS_60G_3_5G = "3.5Gbps"
    WIRELESS_60G_4_6G = "4.6Gbps"
    WIRELESS_60G_7G = "7Gbps"

    @classmethod
    def from_value(cls, value: str) -> Optional["NetworkSpeed"]:
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def from_mbps(cls, mbps: int) -> "NetworkSpeed":
        speed_map = {
            10: cls.SPEED_10M,
            100: cls.SPEED_100M,
            1000: cls.SPEED_1G,
            2500: cls.SPEED_2_5G,
            5000: cls.SPEED_5G,
            10000: cls.SPEED_10G,
            25000: cls.SPEED_25G,
            40000: cls.SPEED_40G,
            50000: cls.SPEED_50G,
            100000: cls.SPEED_100G,
            200000: cls.SPEED_200G,
            400000: cls.SPEED_400G,
            800000: cls.SPEED_800G,
            1600000: cls.SPEED_1_6T,
            3200000: cls.SPEED_3_2T,
            11: cls.WIRELESS_11M,
            22: cls.WIRELESS_22M,
            54: cls.WIRELESS_54M,
            150: cls.WIRELESS_150M,
            300: cls.WIRELESS_300M,
            450: cls.WIRELESS_450M,
            600: cls.WIRELESS_600M,
            900: cls.WIRELESS_900M,
            1300: cls.WIRELESS_1_3G,
            1700: cls.WIRELESS_1_7G,
            2000: cls.WIRELESS_2G,
            3000: cls.WIRELESS_3G,
            4000: cls.WIRELESS_4G,
            5000: cls.WIRELESS_5G,
            6000: cls.WIRELESS_6G,
            7000: cls.WIRELESS_7G,
            8000: cls.WIRELESS_8G,
            10000: cls.WIRELESS_10G,
        }
        
        for speed_mbps, enum_val in speed_map.items():
            if mbps <= speed_mbps:
                return enum_val
        
        return cls.SPEED_10G

    def to_mbps(self) -> int:
        speed_map = {
            self.SPEED_10M: 10,
            self.SPEED_100M: 100,
            self.SPEED_1G: 1000,
            self.SPEED_2_5G: 2500,
            self.SPEED_5G: 5000,
            self.SPEED_10G: 10000,
            self.SPEED_25G: 25000,
            self.SPEED_40G: 40000,
            self.SPEED_50G: 50000,
            self.SPEED_100G: 100000,
            self.SPEED_200G: 200000,
            self.SPEED_400G: 400000,
            self.SPEED_800G: 800000,
            self.SPEED_1_6T: 1600000,
            self.SPEED_3_2T: 3200000,
            self.WIRELESS_11M: 11,
            self.WIRELESS_22M: 22,
            self.WIRELESS_54M: 54,
            self.WIRELESS_150M: 150,
            self.WIRELESS_300M: 300,
            self.WIRELESS_450M: 450,
            self.WIRELESS_600M: 600,
            self.WIRELESS_900M: 900,
            self.WIRELESS_1G: 1000,
            self.WIRELESS_1_3G: 1300,
            self.WIRELESS_1_7G: 1700,
            self.WIRELESS_2G: 2000,
            self.WIRELESS_2_5G: 2500,
            self.WIRELESS_3G: 3000,
            self.WIRELESS_4G: 4000,
            self.WIRELESS_5G: 5000,
            self.WIRELESS_6G: 6000,
            self.WIRELESS_7G: 7000,
            self.WIRELESS_8G: 8000,
            self.WIRELESS_10G: 10000,
        }
        return speed_map.get(self, 0)

    @classmethod
    def all_speeds(cls) -> list[str]:
        return [s.value for s in cls]


class WirelessChannel:
    CHANNEL_BANDS = {
        "2.4GHz": {
            1: 2412, 2: 2417, 3: 2422, 4: 2427, 5: 2432,
            6: 2437, 7: 2442, 8: 2447, 9: 2452, 10: 2457,
            11: 2462, 12: 2467, 13: 2472, 14: 2484,
        },
        "5GHz": {
            36: 5180, 40: 5200, 44: 5220, 48: 5240,
            52: 5260, 56: 5280, 60: 5300, 64: 5320,
            100: 5500, 104: 5520, 108: 5540, 112: 5560,
            116: 5580, 120: 5600, 124: 5620, 128: 5640,
            132: 5660, 136: 5680, 140: 5700, 144: 5720,
            149: 5745, 153: 5765, 157: 5785, 161: 5805,
            165: 5825, 169: 5845,
        },
        "5GHz_UB": {
            42: 5210, 43: 5215, 50: 5250, 51: 5255,
            58: 5290, 59: 5295, 66: 5330, 67: 5335,
            74: 5370, 75: 5375, 82: 5410, 83: 5415,
        },
        "6GHz": {
            1: 5955, 5: 5975, 9: 5995, 13: 6015, 17: 6035,
            21: 6055, 25: 6075, 29: 6095, 33: 6115, 37: 6135,
            41: 6155, 45: 6175, 49: 6195, 53: 6215, 57: 6235,
            61: 6255, 65: 6275, 69: 6295, 73: 6315, 77: 6335,
            81: 6355, 85: 6375, 89: 6395, 93: 6415, 97: 6435,
            101: 6455, 105: 6475, 109: 6495, 113: 6515, 117: 6535,
            121: 6555, 125: 6575, 129: 6595, 133: 6615, 137: 6635,
            141: 6655, 145: 6675, 149: 6695, 153: 6715, 157: 6735,
            161: 6755, 165: 6775, 169: 6795, 173: 6815, 177: 6835,
        },
        "60GHz": {
            1: 57040, 2: 57080, 3: 57120, 4: 57160,
            5: 57200, 6: 57240, 7: 57280, 8: 57320,
            9: 57360, 10: 57400, 11: 57440,
        },
        "900MHz": {
            1: 906, 2: 907, 3: 908, 4: 909, 5: 910,
            6: 911, 7: 912, 8: 913, 9: 914, 10: 915,
        },
        "3GHz": {
            1: 3000, 2: 3005, 3: 3010, 4: 3015, 5: 3020,
            6: 3025, 7: 3030, 8: 3035, 9: 3040, 10: 3045,
            11: 3050, 12: 3055, 13: 3060, 14: 3065, 15: 3070,
        },
        "10GHz": {
            1: 10500, 2: 10525, 3: 10550, 4: 10575,
            5: 10600, 6: 10625, 7: 10650, 8: 10675,
            9: 10700, 10: 10725, 11: 10750, 12: 10775,
            13: 10800, 14: 10825, 15: 10850, 16: 10875,
            17: 10900, 18: 10925, 19: 10950, 20: 10975,
        },
        "11GHz": {
            1: 11000, 2: 11025, 3: 11050, 4: 11075,
            5: 11100, 6: 11125, 7: 11150, 8: 11175,
            9: 11200, 10: 11225, 11: 11250, 12: 11275,
            13: 11300, 14: 11325, 15: 11350, 16: 11375,
            17: 11400, 18: 11425, 19: 11450, 20: 11475,
        },
        "24GHz": {
            1: 24250, 2: 24275, 3: 24300, 4: 24325,
            5: 24350, 6: 24375, 7: 24400, 8: 24425,
            9: 24450, 10: 24475, 11: 24500, 12: 24525,
            13: 24550, 14: 24575, 15: 24600, 16: 24625,
        },
        "80GHz": {
            1: 81350, 2: 81425, 3: 81500, 4: 81575,
            5: 81650, 6: 81725, 7: 81800, 8: 81875,
        },
    }

    BAND_FREQUENCIES = {
        "900MHz": (902, 928),
        "2.4GHz": (2400, 2500),
        "3GHz": (3000, 3100),
        "5GHz": (5150, 5850),
        "5.9GHz": (5850, 5925),
        "6GHz": (5925, 7125),
        "10GHz": (10500, 10975),
        "11GHz": (11000, 11475),
        "24GHz": (24250, 24625),
        "60GHz": (57000, 66000),
        "80GHz": (81350, 81875),
    }

    @classmethod
    def get_frequency(cls, channel: int, band: str = "2.4GHz") -> Optional[int]:
        return cls.CHANNEL_BANDS.get(band, {}).get(channel)

    @classmethod
    def get_channel(cls, frequency: int) -> Optional[tuple]:
        for band, channels in cls.CHANNEL_BANDS.items():
            for ch, freq in channels.items():
                if freq == frequency:
                    return (ch, band)
        return None

    @classmethod
    def get_all_channels(cls) -> dict:
        return cls.CHANNEL_BANDS.copy()

    @classmethod
    def get_2g_channels(cls) -> dict:
        return cls.CHANNEL_BANDS.get("2.4GHz", {})

    @classmethod
    def get_5g_channels(cls) -> dict:
        return cls.CHANNEL_BANDS.get("5GHz", {})

    @classmethod
    def get_6g_channels(cls) -> dict:
        return cls.CHANNEL_BANDS.get("6GHz", {})

    @classmethod
    def get_60g_channels(cls) -> dict:
        return cls.CHANNEL_BANDS.get("60GHz", {})

    @classmethod
    def get_900m_channels(cls) -> dict:
        return cls.CHANNEL_BANDS.get("900MHz", {})

    @classmethod
    def get_band_from_frequency(cls, frequency: int) -> Optional[str]:
        for band, channels in cls.CHANNEL_BANDS.items():
            if frequency in channels.values():
                return band
        
        for band_name, (low, high) in cls.BAND_FREQUENCIES.items():
            if low <= frequency <= high:
                return band_name
        
        return None

    @classmethod
    def get_band_info(cls, band: str) -> Optional[dict]:
        return {
            "name": band,
            "range": cls.BAND_FREQUENCIES.get(band),
            "channels": cls.CHANNEL_BANDS.get(band, {}),
        }

    @classmethod
    def get_all_bands(cls) -> list[str]:
        return list(cls.CHANNEL_BANDS.keys())
    def from_value(cls, value: str) -> Optional["NetworkSpeed"]:
        try:
            return cls(value)
        except ValueError:
            return None

    @classmethod
    def from_mbps(cls, mbps: int) -> "NetworkSpeed":
        speed_map = {
            10: cls.SPEED_10M,
            100: cls.SPEED_100M,
            1000: cls.SPEED_1G,
            2500: cls.SPEED_2_5G,
            5000: cls.SPEED_5G,
            10000: cls.SPEED_10G,
            25000: cls.SPEED_25G,
            40000: cls.SPEED_40G,
            50000: cls.SPEED_50G,
            100000: cls.SPEED_100G,
            200000: cls.SPEED_200G,
            400000: cls.SPEED_400G,
            800000: cls.SPEED_800G,
            1600000: cls.SPEED_1_6T,
            3200000: cls.SPEED_3_2T,
        }
        
        for speed_mbps, enum_val in speed_map.items():
            if mbps <= speed_mbps:
                return enum_val
        
        return cls.SPEED_1_6T

    def to_mbps(self) -> int:
        speed_map = {
            self.SPEED_10M: 10,
            self.SPEED_100M: 100,
            self.SPEED_1G: 1000,
            self.SPEED_2_5G: 2500,
            self.SPEED_5G: 5000,
            self.SPEED_10G: 10000,
            self.SPEED_25G: 25000,
            self.SPEED_40G: 40000,
            self.SPEED_50G: 50000,
            self.SPEED_100G: 100000,
            self.SPEED_200G: 200000,
            self.SPEED_400G: 400000,
            self.SPEED_800G: 800000,
            self.SPEED_1_6T: 1600000,
            self.SPEED_3_2T: 3200000,
            self.WIRELESS_11M: 11,
            self.WIRELESS_22M: 22,
            self.WIRELESS_54M: 54,
            self.WIRELESS_150M: 150,
            self.WIRELESS_300M: 300,
            self.WIRELESS_450M: 450,
            self.WIRELESS_600M: 600,
            self.WIRELESS_900M: 900,
            self.WIRELESS_1G: 1000,
            self.WIRELESS_1_3G: 1300,
            self.WIRELESS_1_7G: 1700,
            self.WIRELESS_2G: 2000,
            self.WIRELESS_2_5G: 2500,
            self.WIRELESS_3G: 3000,
            self.WIRELESS_4G: 4000,
            self.WIRELESS_5G: 5000,
            self.WIRELESS_6G: 6000,
            self.WIRELESS_7G: 7000,
            self.WIRELESS_8G: 8000,
            self.WIRELESS_10G: 10000,
        }
        return speed_map.get(self, 0)

    @classmethod
    def all_speeds(cls) -> list[str]:
        return [s.value for s in cls]


@dataclass
class MonitorTarget:
    id: str
    name: str
    host: str
    check_type: CheckType
    port: Optional[int] = None
    interval: int = 60
    timeout: int = 5
    threshold: int = 3
    enabled: bool = True
    device_type: DeviceType = DeviceType.GENERIC
    network_speed: Optional[NetworkSpeed] = None
    snmp_community: Optional[str] = None
    snmp_oid: Optional[str] = None
    http_url: Optional[str] = None
    http_method: str = "GET"
    http_expected_status: int = 200
    ssl_check_expiry: bool = False
    wmi_query: Optional[str] = None
    wmi_namespace: Optional[str] = r"root\cimv2"
    location: Optional[str] = None
    vendor: Optional[str] = None
    model: Optional[str] = None
    firmware: Optional[str] = None
    interface_name: Optional[str] = None
    interface_index: Optional[int] = None
    
    is_wireless: bool = False
    wireless_channel: Optional[int] = None
    wireless_band: Optional[str] = None
    wireless_frequency: Optional[int] = None
    wireless_ssid: Optional[str] = None
    wireless_mode: Optional[str] = None
    wireless_tx_power: Optional[int] = None
    wireless_antenna_gain: Optional[int] = None


@dataclass
class Metric:
    target_id: str
    timestamp: datetime
    check_type: CheckType
    value: float
    status: Status
    latency_ms: Optional[float] = None
    error: Optional[str] = None


@dataclass
class Alert:
    id: str
    target_id: str
    timestamp: datetime
    message: str
    severity: str
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


@dataclass
class MonitorResult:
    target: MonitorTarget
    metrics: list[Metric] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    consecutive_failures: int = 0
