"""Device CLI module for remote command execution and troubleshooting."""

import logging
import subprocess
import re
from typing import Optional, dict, list, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import socket
import paramiko
from pathlib import Path

logger = logging.getLogger(__name__)


class AccessMethod(Enum):
    SSH = "ssh"
    TELNET = "telnet"
    HTTP = "http"
    HTTPS = "https"
    SNMP = "snmp"
    WINRM = "winrm"
    API = "api"


class DeviceVendor(Enum):
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    CISCO_WLC = "cisco_wlc"
    JUNIPER = "juniper"
    UBIQUITI = "ubiquiti"
    MIKROTIK = "mikrotik"
    HPE = "hpe"
    DELL = "dell"
    FORTINET = "fortinet"
    PANOS = "panos"
    ARISTA = "arista"
    LINUX = "linux"
    WINDOWS = "windows"


@dataclass
class CLICommand:
    command: str
    description: str
    requires_privilege: bool = False
    requires_config_mode: bool = False
    category: str = "general"
    timeout: int = 30


@dataclass
class CLISession:
    host: str
    vendor: DeviceVendor
    username: str
    password: str
    method: AccessMethod
    port: int = 22
    connected: bool = False
    session: Any = None
    last_output: str = ""
    last_error: str = ""


@dataclass
class CommandResult:
    success: bool
    output: str
    error: Optional[str]
    execution_time: float
    timestamp: datetime


class VendorCommands:
    COMMANDS = {
        DeviceVendor.CISCO_IOS: {
            "show_version": CLICommand(
                "show version",
                "Display system hardware and software version",
                category="system"
            ),
            "show_ip_interface_brief": CLICommand(
                "show ip interface brief",
                "Display IP interface status",
                category="interfaces"
            ),
            "show_interface": CLICommand(
                "show interface",
                "Display interface status and statistics",
                category="interfaces"
            ),
            "show_ip_route": CLICommand(
                "show ip route",
                "Display IP routing table",
                category="routing"
            ),
            "show_cdp_neighbors": CLICommand(
                "show cdp neighbors",
                "Display CDP neighbor information",
                category="discovery"
            ),
            "show_running_config": CLICommand(
                "show running-config",
                "Display running configuration",
                requires_privilege=True,
                category="config"
            ),
            "show_arp": CLICommand(
                "show arp",
                "Display ARP table",
                category="network"
            ),
            "show_logging": CLICommand(
                "show logging",
                "Display system logs",
                category="system"
            ),
            "show_processes_cpu": CLICommand(
                "show processes cpu",
                "Display CPU utilization",
                category="performance"
            ),
            "show_memory": CLICommand(
                "show memory",
                "Display memory utilization",
                category="performance"
            ),
            "show_interface_errors": CLICommand(
                "show interface",
                "Display interface errors",
                category="troubleshooting"
            ),
            "ping": CLICommand(
                "ping {target}",
                "Ping a target host",
                category="troubleshooting"
            ),
            "traceroute": CLICommand(
                "traceroute {target}",
                "Trace route to target",
                category="troubleshooting"
            ),
            "reload": CLICommand(
                "reload",
                "Reload the device",
                requires_privilege=True,
                category="system"
            ),
        },
        DeviceVendor.CISCO_NXOS: {
            "show_version": CLICommand(
                "show version",
                "Display system version",
                category="system"
            ),
            "show_interface": CLICommand(
                "show interface status",
                "Display interface status",
                category="interfaces"
            ),
            "show_ip_route": CLICommand(
                "show ip route",
                "Display routing table",
                category="routing"
            ),
            "show_cdp_neighbors": CLICommand(
                "show cdp neighbors",
                "Display neighbors",
                category="discovery"
            ),
            "show_lldp_neighbors": CLICommand(
                "show lldp neighbors",
                "Display LLDP neighbors",
                category="discovery"
            ),
            "show_running_config": CLICommand(
                "show running-config",
                "Display running config",
                requires_privilege=True,
                category="config"
            ),
        },
        DeviceVendor.JUNIPER: {
            "show_version": CLICommand(
                "show version",
                "Display software version",
                category="system"
            ),
            "show_interface": CLICommand(
                "show interface terse",
                "Display interface status",
                category="interfaces"
            ),
            "show_route": CLICommand(
                "show route",
                "Display routing table",
                category="routing"
            ),
            "show_chassis_routing-engine": CLICommand(
                "show chassis routing-engine",
                "Display routing engine status",
                category="system"
            ),
            "show_chassis_fabric": CLICommand(
                "show chassis fabric",
                "Display fabric status",
                category="hardware"
            ),
            "show_logical-systems": CLICommand(
                "show logical-systems",
                "Display logical systems",
                category="config"
            ),
            "show_ospf_neighbor": CLICommand(
                "show ospf neighbor",
                "Display OSPF neighbors",
                category="routing"
            ),
            "show_bgp_summary": CLICommand(
                "show bgp summary",
                "Display BGP summary",
                category="routing"
            ),
            "show_chassis_alarms": CLICommand(
                "show chassis alarms",
                "Display system alarms",
                category="system"
            ),
            "ping": CLICommand(
                "ping {target} rapid",
                "Ping target host",
                category="troubleshooting"
            ),
            "traceroute": CLICommand(
                "traceroute {target}",
                "Trace route to target",
                category="troubleshooting"
            ),
        },
        DeviceVendor.UBIQUITI: {
            "show_version": CLICommand(
                "show version",
                "Display device version",
                category="system"
            ),
            "show_airmax": CLICommand(
                "show airmax",
                "Display AirMax status",
                category="wireless"
            ),
            "show_wireless": CLICommand(
                "show wireless",
                "Display wireless status",
                category="wireless"
            ),
            "show_interfaces": CLICommand(
                "show interfaces",
                "Display interface stats",
                category="interfaces"
            ),
            "show_ip_route": CLICommand(
                "show ip route",
                "Display routing table",
                category="routing"
            ),
            "show_dhcp": CLICommand(
                "show dhcp",
                "Display DHCP bindings",
                category="network"
            ),
            "show_log": CLICommand(
                "show log",
                "Display system log",
                category="system"
            ),
        },
        DeviceVendor.MIKROTIK: {
            "/system/resource/print": CLICommand(
                "/system/resource/print",
                "Display system resources",
                category="system"
            ),
            "/interface/print": CLICommand(
                "/interface/print",
                "Display interfaces",
                category="interfaces"
            ),
            "/ip/address/print": CLICommand(
                "/ip address print",
                "Display IP addresses",
                category="network"
            ),
            "/ip/route/print": CLICommand(
                "/ip route print",
                "Display routes",
                category="routing"
            ),
            "/system/health/print": CLICommand(
                "/system health print",
                "Display health info",
                category="hardware"
            ),
            "/tool/ping": CLICommand(
                "/tool ping count=5 {target}",
                "Ping target",
                category="troubleshooting"
            ),
            "/tool/traceroute": CLICommand(
                "/tool traceroute {target}",
                "Trace route",
                category="troubleshooting"
            ),
            "/log/print": CLICommand(
                "/log print",
                "Display system log",
                category="system"
            ),
        },
        DeviceVendor.LINUX: {
            "uptime": CLICommand(
                "uptime",
                "Display system uptime and load",
                category="system"
            ),
            "free": CLICommand(
                "free -h",
                "Display memory usage",
                category="system"
            ),
            "df": CLICommand(
                "df -h",
                "Display disk usage",
                category="storage"
            ),
            "ifconfig": CLICommand(
                "ip addr show",
                "Display network interfaces",
                category="network"
            ),
            "netstat": CLICommand(
                "ss -tunapl",
                "Display network connections",
                category="network"
            ),
            "arp": CLICommand(
                "ip neigh show",
                "Display ARP table",
                category="network"
            ),
            "route": CLICommand(
                "ip route show",
                "Display routing table",
                category="routing"
            ),
            "top": CLICommand(
                "top -bn1",
                "Display processes",
                category="performance"
            ),
            "dmesg": CLICommand(
                "dmesg | tail -50",
                "Display kernel messages",
                category="system"
            ),
            "ping": CLICommand(
                "ping -c 5 {target}",
                "Ping target",
                category="troubleshooting"
            ),
            "traceroute": CLICommand(
                "traceroute {target}",
                "Trace route",
                category="troubleshooting"
            ),
            "nslookup": CLICommand(
                "nslookup {target}",
                "DNS lookup",
                category="troubleshooting"
            ),
        },
        DeviceVendor.WINDOWS: {
            "systeminfo": CLICommand(
                "systeminfo",
                "Display system information",
                category="system"
            ),
            "ipconfig": CLICommand(
                "ipconfig /all",
                "Display IP configuration",
                category="network"
            ),
            "netstat": CLICommand(
                "netstat -an",
                "Display network connections",
                category="network"
            ),
            "route_print": CLICommand(
                "route print",
                "Display routing table",
                category="routing"
            ),
            "arp_a": CLICommand(
                "arp -a",
                "Display ARP table",
                category="network"
            ),
            "nslookup": CLICommand(
                "nslookup {target}",
                "DNS lookup",
                category="troubleshooting"
            ),
            "ping": CLICommand(
                "ping -n 5 {target}",
                "Ping target",
                category="troubleshooting"
            ),
            "tracert": CLICommand(
                "tracert {target}",
                "Trace route",
                category="troubleshooting"
            ),
            "tasklist": CLICommand(
                "tasklist",
                "Display processes",
                category="performance"
            ),
            "get_eventlog": CLICommand(
                "Get-EventLog -Newest 50 -LogName System",
                "Display system event log",
                category="system"
            ),
        },
        DeviceVendor.FORTINET: {
            "get_system_status": CLICommand(
                "get system status",
                "Display system status",
                category="system"
            ),
            "get_system_info": CLICommand(
                "get system info",
                "Display system info",
                category="system"
            ),
            "diagnose_ip_route": CLICommand(
                "diagnose ip route list",
                "Display routing table",
                category="routing"
            ),
            "diagnose_firewall_session": CLICommand(
                "diagnose firewall session list",
                "Display firewall sessions",
                category="security"
            ),
            "get_interface": CLICommand(
                "get system interface",
                "Display interfaces",
                category="interfaces"
            ),
            "diagnoseHardware": CLICommand(
                "diagnose hardware info",
                "Display hardware info",
                category="hardware"
            ),
        },
    }

    @classmethod
    def get_commands(cls, vendor: DeviceVendor) -> dict:
        return cls.COMMANDS.get(vendor, {})

    @classmethod
    def get_command(cls, vendor: DeviceVendor, command_name: str) -> Optional[CLICommand]:
        return cls.COMMANDS.get(vendor, {}).get(command_name)

    @classmethod
    def get_all_vendors(cls) -> list[str]:
        return [v.value for v in DeviceVendor]

    @classmethod
    def get_categories(cls, vendor: DeviceVendor) -> list[str]:
        commands = cls.COMMANDS.get(vendor, {})
        categories = set(cmd.category for cmd in commands.values())
        return sorted(categories)


class DeviceCLI:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._sessions: dict[str, CLISession] = {}

    def connect(self, host: str, vendor: DeviceVendor, username: str, password: str,
                method: AccessMethod = AccessMethod.SSH, port: int = None) -> bool:
        if port is None:
            port = 22 if method == AccessMethod.SSH else 23

        session = CLISession(
            host=host,
            vendor=vendor,
            username=username,
            password=password,
            method=method,
            port=port
        )

        try:
            if method == AccessMethod.SSH:
                session.session = self._ssh_connect(host, port, username, password)
                session.connected = True
            elif method == AccessMethod.TELNET:
                session.session = self._telnet_connect(host, port, username, password)
                session.connected = True
            
            self._sessions[host] = session
            return True

        except Exception as e:
            session.last_error = str(e)
            logger.error(f"Failed to connect to {host}: {e}")
            return False

    def _ssh_connect(self, host: str, port: int, username: str, password: str):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            client.connect(
                hostname=host,
                port=port,
                username=username,
                password=password,
                timeout=self.timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            return client
        except paramiko.AuthenticationException:
            raise Exception("Authentication failed")
        except Exception as e:
            raise Exception(f"SSH connection failed: {e}")

    def _telnet_connect(self, host: str, port: int, username: str, password: str):
        import telnetlib
        tn = telnetlib.Telnet(host, port, self.timeout)
        
        tn.read_until(b"login:", self.timeout)
        tn.write(f"{username}\n".encode())
        
        if password:
            tn.read_until(b"Password:", self.timeout)
            tn.write(f"{password}\n".encode())
        
        return tn

    def execute(self, host: str, command: str, timeout: int = None) -> CommandResult:
        if timeout is None:
            timeout = self.timeout

        if host not in self._sessions:
            return CommandResult(
                success=False,
                output="",
                error="Not connected to host",
                execution_time=0,
                timestamp=datetime.now()
            )

        session = self._sessions[host]
        start_time = datetime.now()

        try:
            if session.method == AccessMethod.SSH:
                output = self._ssh_execute(session.session, command, timeout)
            elif session.method == AccessMethod.TELNET:
                output = self._telnet_execute(session.session, command, timeout)
            else:
                output = ""

            execution_time = (datetime.now() - start_time).total_seconds()

            return CommandResult(
                success=True,
                output=output,
                error=None,
                execution_time=execution_time,
                timestamp=datetime.now()
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return CommandResult(
                success=False,
                output="",
                error=str(e),
                execution_time=execution_time,
                timestamp=datetime.now()
            )

    def _ssh_execute(self, client, command: str, timeout: int) -> str:
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        return output if output else error

    def _telnet_execute(self, tn, command: str, timeout: int) -> str:
        tn.write(f"{command}\n".encode())
        output = tn.read_until(b"\n", timeout).decode('utf-8', errors='ignore')
        return output

    def disconnect(self, host: str):
        if host in self._sessions:
            session = self._sessions[host]
            if session.session:
                try:
                    if session.method == AccessMethod.SSH:
                        session.session.close()
                    elif session.method == AccessMethod.TELNET:
                        session.session.close()
                except:
                    pass
            del self._sessions[host]

    def disconnect_all(self):
        for host in list(self._sessions.keys()):
            self.disconnect(host)

    def get_available_commands(self, vendor: DeviceVendor) -> list[dict]:
        commands = VendorCommands.get_commands(vendor)
        
        return [
            {
                "name": name,
                "command": cmd.command,
                "description": cmd.description,
                "requires_privilege": cmd.requires_privilege,
                "category": cmd.category,
            }
            for name, cmd in commands.items()
        ]


class QuickDiagnostic:
    @staticmethod
    def run_diagnostic(cli: DeviceCLI, host: str, vendor: DeviceVendor) -> dict:
        results = {
            "host": host,
            "vendor": vendor.value,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        basic_commands = [
            ("ping_local", "127.0.0.1"),
            ("check_connectivity", "8.8.8.8"),
        ]

        if vendor == DeviceVendor.CISCO_IOS:
            basic_commands = [
                ("version", "show version"),
                ("interfaces", "show ip interface brief"),
                ("cpu", "show processes cpu | head"),
                ("memory", "show memory summary"),
            ]
        elif vendor == DeviceVendor.JUNIPER:
            basic_commands = [
                ("version", "show version"),
                ("interfaces", "show interface terse"),
                ("chassis", "show chassis hardware"),
            ]
        elif vendor == DeviceVendor.MIKROTIK:
            basic_commands = [
                ("resource", "/system resource print"),
                ("interface", "/interface print"),
                ("address", "/ip address print"),
            ]
        elif vendor == DeviceVendor.LINUX:
            basic_commands = [
                ("uptime", "uptime"),
                ("memory", "free -h"),
                ("disk", "df -h"),
                ("load", "cat /proc/loadavg"),
            ]

        for check_name, command in basic_commands:
            result = cli.execute(host, command)
            results["checks"][check_name] = {
                "success": result.success,
                "output": result.output[:500] if result.output else "",
                "error": result.error,
                "execution_time": result.execution_time,
            }

        return results
