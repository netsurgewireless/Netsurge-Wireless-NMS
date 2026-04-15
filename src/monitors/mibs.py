"""SNMP MIB definitions for various network vendors."""

from typing import Optional
from dataclasses import dataclass
from enum import Enum


class MIBSupported(Enum):
    STANDARD = "standard"
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    JUNIPER_JUNOS = "juniper_junos"
    UBIQUITI_EDGESWITCH = "ubiquiti_edgeswitch"
    UBIQUITI_UNIFI = "ubiquiti_unifi"
    NETONIX = "netonix"
    MIKROTIK_ROUTEROS = "mikrotik_routeros"
    HPE_PROCURVE = "hpe_procurve"
    DELL_IOM = "dell_iom"
    FORTINET_FORTIOS = "fortinet_fortios"
    PANOS_PANOS = "panos_panos"


@dataclass
class MIBOID:
    name: str
    oid: str
    description: str
    unit: str = ""


STANDARD_MIBS = {
    "sysDescr": MIBOID("sysDescr", "1.3.6.1.2.1.1.1.0", "System description"),
    "sysUpTime": MIBOID("sysUpTime", "1.3.6.1.2.1.1.3.0", "System uptime", "ticks"),
    "sysContact": MIBOID("sysContact", "1.3.6.1.2.1.1.4.0", "System contact"),
    "sysName": MIBOID("sysName", "1.3.6.1.2.1.1.5.0", "System name"),
    "sysLocation": MIBOID("sysLocation", "1.3.6.1.2.1.1.6.0", "System location"),
    "ifNumber": MIBOID("ifNumber", "1.3.6.1.2.1.2.1.0", "Number of interfaces"),
    "ifIndex": MIBOID("ifIndex", "1.3.6.1.2.1.2.2.1.1", "Interface index"),
    "ifDescr": MIBOID("ifDescr", "1.3.6.1.2.1.2.2.1.2", "Interface description"),
    "ifType": MIBOID("ifType", "1.3.6.1.2.1.2.2.1.3", "Interface type"),
    "ifSpeed": MIBOID("ifSpeed", "1.3.6.1.2.1.2.2.1.5", "Interface speed", "bps"),
    "ifInOctets": MIBOID("ifInOctets", "1.3.6.1.2.1.2.2.1.10", "Inbound octets"),
    "ifOutOctets": MIBOID("ifOutOctets", "1.3.6.1.2.1.2.2.1.16", "Outbound octets"),
    "ifInUcastPkts": MIBOID("ifInUcastPkts", "1.3.6.1.2.1.2.2.1.11", "Inbound unicast packets"),
    "ifOutUcastPkts": MIBOID("ifOutUcastPkts", "1.3.6.1.2.1.2.2.1.17", "Outbound unicast packets"),
    "ifInErrors": MIBOID("ifInErrors", "1.3.6.1.2.1.2.2.1.14", "Inbound errors"),
    "ifOutErrors": MIBOID("ifOutErrors", "1.3.6.1.2.1.2.2.1.20", "Outbound errors"),
    "ifInDiscards": MIBOID("ifInDiscards", "1.3.6.1.2.1.2.2.1.13", "Inbound discards"),
    "ifOutDiscards": MIBOID("ifOutDiscards", "1.3.6.1.2.1.2.2.1.19", "Outbound discards"),
    "hrDeviceDescr": MIBOID("hrDeviceDescr", "1.3.6.1.2.1.25.3.2.1.3", "Device description"),
    "hrProcessorLoad": MIBOID("hrProcessorLoad", "1.3.6.1.2.1.25.3.3.1.2", "CPU load", "%"),
    "hrMemorySize": MIBOID("hrMemorySize", "1.3.6.1.2.1.25.2.2.0", "Memory size", "KB"),
    "hrStorageSize": MIBOID("hrStorageSize", "1.3.6.1.2.1.25.2.3.1.5", "Storage size", "KB"),
    "hrStorageUsed": MIBOID("hrStorageUsed", "1.3.6.1.2.1.25.2.3.1.6", "Storage used", "KB"),
}


CISCO_MIBS = {
    **STANDARD_MIBS,
    "ciscoEnvMonTemperatureStatusValue": MIBOID("ciscoEnvMonTemperatureStatusValue", "1.3.6.1.4.1.9.9.13.1.5.1.3", "Temperature sensor", "C"),
    "ciscoEnvMonFanStatus": MIBOID("ciscoEnvMonFanStatus", "1.3.6.1.4.1.9.9.13.1.4.1.2", "Fan status"),
    "ciscoEnvMonPowerSupplyStatus": MIBOID("ciscoEnvMonPowerSupplyStatus", "1.3.6.1.4.1.9.9.13.1.5.1.2", "Power supply status"),
    "ciscoMemoryPoolUsed": MIBOID("ciscoMemoryPoolUsed", "1.3.6.1.4.1.9.9.48.1.1.5", "Memory used", "KB"),
    "ciscoMemoryPoolFree": MIBOID("ciscoMemoryPoolFree", "1.3.6.1.4.1.9.9.48.1.1.6", "Memory free", "KB"),
    "ciscoCPUTotal5min": MIBOID("ciscoCPUTotal5min", "1.3.6.1.4.1.9.9.109.1.1.1.1.5", "CPU 5min avg", "%"),
    "ciscoCPUTotal1min": MIBOID("ciscoCPUTotal1min", "1.3.6.1.4.1.9.9.109.1.1.1.1.2", "CPU 1min avg", "%"),
    "ciscoEnvMonVoltageStatusValue": MIBOID("ciscoEnvMonVoltageStatusValue", "1.3.6.1.4.1.9.9.13.1.3.1.4", "Voltage", "V"),
    "ciscoInterface喘tate": MIBOID("ciscoInterface喘tate", "1.3.6.1.4.1.9.9.276.1.2.1.1", "Interface state"),
    "ciscoStackOperMode": MIBOID("ciscoStackOperMode", "1.3.6.1.4.1.9.9.286.1.1.1.0", "Stack operation mode"),
    "cbgpPeerState": MIBOID("cbgpPeerState", "1.3.6.1.4.1.9.9.122.1.16.2.1.3", "BGP peer state"),
    "ospfNbrState": MIBOID("ospfNbrState", "1.3.6.1.2.1.14.10.1.1.1", "OSPF neighbor state"),
}


JUNIPER_MIBS = {
    **STANDARD_MIBS,
    "jnxBoxDescr": MIBOID("jnxBoxDescr", "1.3.6.1.4.1.2636.1.1.1.2.1.0", "Chassis description"),
    "jnxOperatingDescr": MIBOID("jnxOperatingDescr", "1.3.6.1.4.1.2636.3.1.2.1.5", "Operating unit description"),
    "jnxOperatingCPU": MIBOID("jnxOperatingCPU", "1.3.6.1.4.1.2636.3.1.2.1.6", "CPU utilization", "%"),
    "jnxOperatingMemory": MIBOID("jnxOperatingMemory", "1.3.6.1.4.1.2636.3.1.2.1.7", "Memory utilization", "%"),
    "jnxOperatingTemp": MIBOID("jnxOperatingTemp", "1.3.6.1.4.1.2636.3.1.2.1.9", "Temperature", "C"),
    "jnxFanSpeed": MIBOID("jnxFanSpeed", "1.3.6.1.4.1.2636.3.1.7.1.1.2", "Fan speed", "RPM"),
    "jnxPowerSupplyStatus": MIBOID("jnxPowerSupplyStatus", "1.3.6.1.4.1.2636.3.1.8.1.1.2", "Power supply status"),
    "jnxLicenseOnline": MIBOID("jnxLicenseOnline", "1.3.6.1.4.1.2636.3.52.1.1.2", "License status"),
    "jnxVpnTunnelIndex": MIBOID("jnxVpnTunnelIndex", "1.3.6.1.4.1.2636.3.5.1.1.1", "VPN tunnel index"),
    "jnxVpnTunnelState": MIBOID("jnxVpnTunnelState", "1.3.6.1.4.1.2636.3.5.1.1.5", "VPN tunnel state"),
}


UBIQUITI_MIBS = {
    **STANDARD_MIBS,
    "ubntGenericUptime": MIBOID("ubntGenericUptime", "1.3.6.1.4.1.41112.1.4.1.0", "Device uptime", "seconds"),
    "ubntGenericCpuLoad": MIBOID("ubntGenericCpuLoad", "1.3.6.1.4.1.41112.1.4.2.0", "CPU load", "%"),
    "ubntGenericMemUsed": MIBOID("ubntGenericMemUsed", "1.3.6.1.4.1.41112.1.4.3.0", "Memory used", "KB"),
    "ubntGenericMemTotal": MIBOID("ubntGenericMemTotal", "1.3.6.1.4.1.41112.1.4.4.0", "Memory total", "KB"),
    "ubntAirMaxCapacity": MIBOID("ubntAirMaxCapacity", "1.3.6.1.4.1.41112.1.5.1.1", "AirMax capacity"),
    "ubntAirMaxChannel": MIBOID("ubntAirMaxChannel", "1.3.6.1.4.1.41112.1.5.2.1.2", "AirMax channel"),
    "ubntWifiStations": MIBOID("ubntWifiStations", "1.3.6.1.4.1.41112.1.6.1.1", "WiFi stations"),
    "ubntWifiRxBytes": MIBOID("ubntWifiRxBytes", "1.3.6.1.4.1.41112.1.6.1.2", "WiFi RX bytes"),
    "ubntWifiTxBytes": MIBOID("ubntWifiTxBytes", "1.3.6.1.4.1.41112.1.6.1.3", "WiFi TX bytes"),
    "ubntSystemStats": MIBOID("ubntSystemStats", "1.3.6.1.4.1.41112.1.8.1.1", "System statistics"),
}


NETONIX_MIBS = {
    **STANDARD_MIBS,
    "netonixCpuLoad": MIBOID("netonixCpuLoad", "1.3.6.1.4.1.46242.1.1", "CPU load", "%"),
    "netonixMemoryUsed": MIBOID("netonixMemoryUsed", "1.3.6.1.4.1.46242.1.2", "Memory used", "%"),
    "netonixPowerSupplyStatus": MIBOID("netonixPowerSupplyStatus", "1.3.6.1.4.1.46242.2.1", "PSU status"),
    "netonixFanSpeed": MIBOID("netonixFanSpeed", "1.3.6.1.4.1.46242.3.1", "Fan speed", "RPM"),
    "netonixTemperature": MIBOID("netonixTemperature", "1.3.6.1.4.1.46242.4.1", "Temperature", "C"),
    "netonixPOEStatus": MIBOID("netonixPOEStatus", "1.3.6.1.4.1.46242.5.1", "POE status", "W"),
    "netonixPOEPower": MIBOID("netonixPOEPower", "1.3.6.1.4.1.46242.5.2.1.2", "POE power", "W"),
    "netonixSwitchChip": MIBOID("netonixSwitchChip", "1.3.6.1.4.1.46242.6.1", "Switch chip"),
    "netonixPortStatus": MIBOID("netonixPortStatus", "1.3.6.1.4.1.46242.7.1", "Port status"),
    "netonixPortSpeed": MIBOID("netonixPortSpeed", "1.3.6.1.4.1.46242.7.2", "Port speed", "Mbps"),
    "netonixPortDuplex": MIBOID("netonixPortDuplex", "1.3.6.1.4.1.46242.7.3", "Port duplex"),
}


MIKROTIK_MIBS = {
    **STANDARD_MIBS,
    "mtxrHealth": MIBOID("mtxrHealth", "1.3.6.1.4.1.14988.1.1.1.1.0", "Router health", "%"),
    "mtxrCpuLoad": MIBOID("mtxrCpuLoad", "1.3.6.1.4.1.14988.1.1.1.2.0", "CPU load", "%"),
    "mtxrMemoryUsed": MIBOID("mtxrMemoryUsed", "1.3.6.1.4.1.14988.1.1.1.3.0", "Memory used", "KB"),
    "mtxrMemoryFree": MIBOID("mtxrMemoryFree", "1.3.6.1.4.1.14988.1.1.1.4.0", "Memory free", "KB"),
    "mtxrDiskTotal": MIBOID("mtxrDiskTotal", "1.3.6.1.4.1.14988.1.1.1.5.0", "Disk total", "KB"),
    "mtxrDiskUsed": MIBOID("mtxrDiskUsed", "1.3.6.1.4.1.14988.1.1.1.6.0", "Disk used", "KB"),
    "mtxrTemperature": MIBOID("mtxrTemperature", "1.3.6.1.4.1.14988.1.1.1.7.0", "Temperature", "C"),
    "mtxrVoltage": MIBOID("mtxrVoltage", "1.3.6.1.4.1.14988.1.1.1.8.0", "Voltage", "V"),
    "mtxrPowerSupply": MIBOID("mtxrPowerSupply", "1.3.6.1.4.1.14988.1.1.1.9.0", "Power supply status"),
    "mtxrBoardTemp": MIBOID("mtxrBoardTemp", "1.3.6.1.4.1.14988.1.1.1.10.0", "Board temperature", "C"),
    "mtxrWifiStations": MIBOID("mtxrWifiStations", "1.3.6.1.4.1.14988.1.1.3.1.2", "WiFi stations"),
    "mtxrInterfaceTxBytes": MIBOID("mtxrInterfaceTxBytes", "1.3.6.1.4.1.14988.1.1.2.2.1.10", "TX bytes"),
    "mtxrInterfaceRxBytes": MIBOID("mtxrInterfaceRxBytes", "1.3.6.1.4.1.14988.1.1.2.2.1.16", "RX bytes"),
}


HPE_MIBS = {
    **STANDARD_MIBS,
    "hpSwitchCpuStat": MIBOID("hpSwitchCpuStat", "1.3.6.1.4.1.11.2.14.11.5.1.1.1", "CPU statistics", "%"),
    "hpSwitchMemTotal": MIBOID("hpSwitchMemTotal", "1.3.6.1.4.1.11.2.14.11.5.1.1.2", "Memory total", "KB"),
    "hpSwitchMemFree": MIBOID("hpSwitchMemFree", "1.3.6.1.4.1.11.2.14.11.5.1.1.3", "Memory free", "KB"),
    "hpSwitchPowerSupply": MIBOID("hpSwitchPowerSupply", "1.3.6.1.4.1.11.2.14.11.5.1.2.1", "Power supply"),
    "hpSwitchFanStatus": MIBOID("hpSwitchFanStatus", "1.3.6.1.4.1.11.2.14.11.5.1.3.1", "Fan status"),
    "hpSwitchTempSensor": MIBOID("hpSwitchTempSensor", "1.3.6.1.4.1.11.2.14.11.5.1.4.1", "Temperature", "C"),
}


DELL_IOM_MIBS = {
    **STANDARD_MIBS,
    "dellCpuUtilization": MIBOID("dellCpuUtilization", "1.3.6.1.4.1.674.10895.5000.2.1.1", "CPU utilization", "%"),
    "dellMemoryUsage": MIBOID("dellMemoryUsage", "1.3.6.1.4.1.674.10895.5000.2.1.2", "Memory usage", "%"),
    "dellPowerSupplyStatus": MIBOID("dellPowerSupplyStatus", "1.3.6.1.4.1.674.10895.5000.2.2.1", "Power supply"),
    "dellFanStatus": MIBOID("dellFanStatus", "1.3.6.1.4.1.674.10895.5000.2.3.1", "Fan status"),
    "dellFanSpeed": MIBOID("dellFanSpeed", "1.3.6.1.4.1.674.10895.5000.2.3.2", "Fan speed", "RPM"),
    "dellTemperature": MIBOID("dellTemperature", "1.3.6.1.4.1.674.10895.5000.2.4.1", "Temperature", "C"),
    "dellPortStatus": MIBOID("dellPortStatus", "1.3.6.1.4.1.674.10895.5000.2.5.1", "Port status"),
    "dellPortSpeed": MIBOID("dellPortSpeed", "1.3.6.1.4.1.674.10895.5000.2.5.2", "Port speed", "Mbps"),
}


FORTINET_MIBS = {
    **STANDARD_MIBS,
    "fgSysCpuUsage": MIBOID("fgSysCpuUsage", "1.3.6.1.4.1.12356.1.1.4.0", "System CPU usage", "%"),
    "fgSysMemUsage": MIBOID("fgSysMemUsage", "1.3.6.1.4.1.12356.1.1.5.0", "System memory usage", "%"),
    "fgSysDiskUsage": MIBOID("fgSysDiskUsage", "1.3.6.1.4.1.12356.1.1.6.0", "System disk usage", "%"),
    "fgSysSesCount": MIBOID("fgSysSesCount", "1.3.6.1.4.1.12356.1.1.8.0", "Session count"),
    "fgSysSes6Count": MIBOID("fgSysSes6Count", "1.3.6.1.4.1.12356.1.1.9.0", "IPv6 session count"),
    "fgFwCurrentSessions": MIBOID("fgFwCurrentSessions", "1.3.6.1.4.1.12356.1.2.1.0", "Firewall sessions"),
    "fgFwVdomList": MIBOID("fgFwVdomList", "1.3.6.1.4.1.12356.1.10.1.1", "VDOM list"),
    "fgHaStats": MIBOID("fgHaStats", "1.3.6.1.4.1.12356.1.15.1", "HA statistics"),
    "fgVpnTunnels": MIBOID("fgVpnTunnels", "1.3.6.1.4.1.12356.1.20.1", "VPN tunnels"),
    "fgWifiClients": MIBOID("fgWifiClients", "1.3.6.1.4.1.12356.1.30.1", "WiFi clients"),
}


PANOS_MIBS = {
    **STANDARD_MIBS,
    "panSysCpuUsage": MIBOID("panSysCpuUsage", "1.3.6.1.4.1.25461.2.1.3.1.0", "CPU usage", "%"),
    "panSysMemoryUsage": MIBOID("panSysMemoryUsage", "1.3.6.1.4.1.25461.2.1.3.2.0", "Memory usage", "%"),
    "panSysDiskUsage": MIBOID("panSysDiskUsage", "1.3.6.1.4.1.25461.2.1.3.3.0", "Disk usage", "%"),
    "panSysSessionCount": MIBOID("panSysSessionCount", "1.3.6.1.4.1.25461.2.1.3.4.0", "Session count"),
    "panSysSessionMax": MIBOID("panSysSessionMax", "1.3.6.1.4.1.25461.2.1.3.5.0", "Max sessions"),
    "panSysGPInstalled": MIBOID("panSysGPInstalled", "1.3.6.1.4.1.25461.2.1.3.10", "GlobalProtect installed"),
    "panWifiClients": MIBOID("panWifiClients", "1.3.6.1.4.1.25461.2.1.4.1", "WiFi clients"),
    "panHaActive": MIBOID("panHaActive", "1.3.6.1.4.1.25461.2.1.2.1", "HA active"),
}


VENDOR_MIBS = {
    MIBSupported.CISCO_IOS: CISCO_MIBS,
    MIBSupported.CISCO_NXOS: CISCO_MIBS,
    MIBSupported.JUNIPER_JUNOS: JUNIPER_MIBS,
    MIBSupported.UBIQUITI_EDGESWITCH: UBIQUITI_MIBS,
    MIBSupported.UBIQUITI_UNIFI: UBIQUITI_MIBS,
    MIBSupported.NETONIX: NETONIX_MIBS,
    MIBSupported.MIKROTIK_ROUTEROS: MIKROTIK_MIBS,
    MIBSupported.HPE_PROCURVE: HPE_MIBS,
    MIBSupported.DELL_IOM: DELL_IOM_MIBS,
    MIBSupported.FORTINET_FORTIOS: FORTINET_MIBS,
    MIBSupported.PANOS_PANOS: PANOS_MIBS,
}


def get_mib(vendor: str, oid_name: str) -> Optional[MIBOID]:
    try:
        vendor_enum = MIBSupported(vendor)
    except ValueError:
        return STANDARD_MIBS.get(oid_name)
    
    mibs = VENDOR_MIBS.get(vendor_enum, STANDARD_MIBS)
    return mibs.get(oid_name)


def get_all_oids_for_vendor(vendor: str) -> dict:
    try:
        vendor_enum = MIBSupported(vendor)
    except ValueError:
        return STANDARD_MIBS.copy()
    
    return VENDOR_MIBS.get(vendor_enum, STANDARD_MIBS).copy()


def get_vendor_from_sysdescr(sys_descr: str) -> Optional[MIBSupported]:
    descr = sys_descr.lower()
    
    if "cisco" in descr:
        if "nxos" in descr or "nexus" in descr:
            return MIBSupported.CISCO_NXOS
        return MIBSupported.CISCO_IOS
    elif "juniper" in descr or "junos" in descr:
        return MIBSupported.JUNIPER_JUNOS
    elif "ubiquiti" in descr or "edge" in descr or "unifi" in descr:
        if "unifi" in descr:
            return MIBSupported.UBIQUITI_UNIFI
        return MIBSupported.UBIQUITI_EDGESWITCH
    elif "netonix" in descr:
        return MIBSupported.NETONIX
    elif "mikrotik" in descr or "routeros" in descr:
        return MIBSupported.MIKROTIK_ROUTEROS
    elif "procurve" in descr or "hpe" in descr or "aruba" in descr:
        return MIBSupported.HPE_PROCURVE
    elif "dell" in descr or "force10" in descr or "iom" in descr:
        return MIBSupported.DELL_IOM
    elif "fortinet" in descr or "fortigate" in descr:
        return MIBSupported.FORTINET_FORTIOS
    elif "palo alto" in descr or "panos" in descr:
        return MIBSupported.PANOS_PANOS
    
    return None
