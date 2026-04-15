# Network Monitor Pro

A comprehensive network monitoring system with AI-powered device discovery, SNMP monitoring, CLI access, and IPMI support for servers.

## Features

### Monitoring
- **SNMP Monitoring** - Cisco, Juniper, Ubiquiti, MikroTik, HPE, Dell, Fortinet, Palo Alto
- **Ping/Port Monitoring** - ICMP and TCP connectivity checks
- **HTTP/HTTPS/SSL** - Web service monitoring with certificate expiry checks
- **Bandwidth Monitoring** - Interface throughput via SNMP
- **Wireless Monitoring** - Signal strength, TX power, channel for PtP links
- **Server Health** - CPU, memory, disk monitoring via WMI/SSH
- **IPMI Support** - Temperature, voltage, fan, power supply monitoring

### Device Support
- **Vendors**: Cisco, Juniper, Ubiquiti, MikroTik, HPE, Dell, Fortinet, Palo Alto, Aruba, Linux, Windows
- **Device Types**: Routers, Switches, Firewalls, Wireless APs, Servers
- **Network Speeds**: 10Mbps - 800Gbps + Wireless (2.4GHz, 5GHz, 6GHz, 60GHz)

### AI Integration
- Automatic vendor/device detection from SNMP
- Smart OID recommendations per vendor
- Issue prediction from metrics history
- CVE vulnerability lookup
- Configuration validation
- Daily database sync (MAC vendors, OIDs, CVEs)

### CLI Access
- SSH/Telnet remote command execution
- Vendor-specific command libraries
- Quick diagnostic tools
- Troubleshooting commands

### Alerting
- Email notifications
- Webhook support
- Slack notifications
- SMS (Twilio)
- Configurable thresholds

### Web Dashboard
- Real-time status monitoring
- Interactive device cards
- Network discovery scanner
- Alert management

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python -m src.server
```

## Running the Client

```bash
python -m src.client --server http://your-server:8080
```

## API Endpoints

```
GET  /api/health              - Server health
GET  /api/status             - Monitoring status
GET  /api/targets            - List all targets
POST /api/targets            - Add target
GET  /api/targets/{id}/metrics - Get metrics
GET  /api/alerts             - Get alerts
POST /api/alerts/{id}/ack   - Acknowledge alert
GET  /api/discovery/scan     - Network scan
GET  /api/ai/analyze         - AI device analysis
POST /api/cli/execute        - Execute CLI command
POST /api/ipmi/sensors       - Get IPMI sensors
```

## Configuration

Edit `config.json` to add monitoring targets:

```json
{
  "targets": [
    {
      "id": "router-1",
      "name": "Main Router",
      "host": "192.168.1.1",
      "check_type": "snmp",
      "device_type": "cisco",
      "snmp_community": "public",
      "interval": 60
    }
  ],
  "api_port": 8080
}
```

## Requirements

- Python 3.8+
- Flask
- pysnmp
- cryptography
- requests
- apscheduler
- paramiko (for CLI)
- Pillow (for client tray)

## License

MIT
