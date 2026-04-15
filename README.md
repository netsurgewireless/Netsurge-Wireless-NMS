# Network Monitor Pro v2.0

A comprehensive network monitoring system with AI-powered device discovery, SNMP monitoring, CLI access, and IPMI support for servers. Enhanced with cloud monitoring, database health checks, automated remediation, and enterprise-grade alerting.

## What's New in v2.0

- **Cloud Monitoring**: AWS, Azure, GCP service health monitoring
- **Database Monitoring**: MySQL, PostgreSQL, MongoDB, Redis, Memcached health checks
- **DNS Monitoring**: DNS resolution, SPF, DMARC, DNSSEC validation
- **Metrics Exporters**: Prometheus, InfluxDB, Graphite, DataDog, Elasticsearch, MQTT
- **Enhanced Dashboard**: Analytics, performance metrics, reporting
- **Security**: API keys, JWT tokens, role-based access, TLS support
- **Remediation**: Automated self-healing actions and playbooks
- **New Alert Channels**: Telegram, Discord, PagerDuty, OpsGenie, Matrix, Gotify

## Features

### Monitoring
- **SNMP Monitoring** - Cisco, Juniper, Ubiquiti, MikroTik, HPE, Dell, Fortinet, Palo Alto, Aruba
- **Ping/Port Monitoring** - ICMP and TCP connectivity checks
- **HTTP/HTTPS/SSL** - Web service monitoring with certificate expiry checks
- **Bandwidth Monitoring** - Interface throughput via SNMP
- **Wireless Monitoring** - Signal strength, TX power, channel for PtP links
- **Server Health** - CPU, memory, disk monitoring via WMI/SSH
- **IPMI Support** - Temperature, voltage, fan, power supply monitoring
- **DNS Monitoring** - Full DNS validation including SPF, DMARC, DNSSEC
- **Database Monitoring** - MySQL, PostgreSQL, MongoDB, Redis, Memcached
- **Cloud Monitoring** - AWS EC2/RDS/S3/Lambda, Azure VMs, GCP Compute

### Device Support
- **Vendors**: Cisco, Juniper, Ubiquiti, MikroTik, HPE, Dell, Fortinet, Palo Alto, Aruba, AWS, Azure, GCP
- **Device Types**: Routers, Switches, Firewalls, Wireless APs, Servers, Cloud Resources
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
- **Telegram** notifications
- **Discord** notifications
- **PagerDuty** integration
- **OpsGenie** integration
- **Matrix** notifications
- **Gotify** notifications
- SMS (Twilio)
- Configurable thresholds

### Metrics Export
- **Prometheus** exporter (port 9090)
- **InfluxDB** exporter
- **Graphite** exporter
- **DataDog** exporter
- **OpenTSDB** exporter
- **Elasticsearch** exporter
- **MQTT** exporter
- **NATS** exporter

### Security
- API key authentication
- JWT token auth
- Role-based access control
- Rate limiting
- TLS/SSL support
- Action allowlist (block dangerous commands)

### Automated Remediation
- Self-healing actions
- Playbook system
- Healing policies
- Failure prediction
- Health scoring

### Web Dashboard
- Real-time status monitoring
- **Analytics dashboard** with trends
- Performance metrics (avg latency, P95, packet loss, jitter)
- Interactive device cards
- Network discovery scanner
- Alert management
- CSV/PDF report generation

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
GET  /api/alerts            - Get alerts
POST /api/alerts/{id}/ack    - Acknowledge alert
GET  /api/discovery/scan     - Network scan
GET  /api/ai/analyze        - AI device analysis
POST /api/cli/execute       - Execute CLI command
POST /api/ipmi/sensors      - Get IPMI sensors
GET  /api/analytics        - Analytics data
GET  /metrics              - Prometheus metrics endpoint
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
    },
    {
      "id": "web-ssl",
      "name": "Web Server SSL",
      "host": "example.com",
      "check_type": "ssl",
      "ssl_check_expiry": true,
      "interval": 3600
    },
    {
      "id": "db-primary",
      "name": "Primary Database",
      "host": "db.example.com",
      "check_type": "database",
      "device_type": "mysql",
      "port": 3306,
      "snmp_community": "root",
      "model": "password",
      "interval": 60
    },
    {
      "id": "aws-ec2",
      "name": "AWS EC2",
      "host": "aws",
      "check_type": "cloud",
      "snmp_community": "aws",
      "snmp_oid": "your-access-key",
      "firmware": "your-secret-key",
      "http_url": "ec2",
      "model": "us-east-1",
      "interval": 300
    }
  ],
  "api_port": 8080
}
```

### Alert Handler Configuration

```json
{
  "alert_handlers": {
    "slack": {
      "webhook_url": "https://hooks.slack.com/services/..."
    },
    "telegram": {
      "bot_token": "your-bot-token",
      "chat_id": "your-chat-id"
    },
    "discord": {
      "webhook_url": "https://discord.com/api/webhooks/..."
    },
    "pagerduty": {
      "api_key": "your-api-key",
      "service_id": "your-service-id"
    }
  }
}
```

### Metrics Export Configuration

```json
{
  "exporters": {
    "prometheus": {
      "enabled": true,
      "port": 9090
    },
    "influxdb": {
      "enabled": true,
      "url": "http://localhost:8086",
      "token": "your-token",
      "org": "your-org",
      "bucket": "network-monitor"
    }
  }
}
```

## New Check Types

- `ping` - ICMP ping checks
- `port` - TCP port checks
- `snmp` - SNMP polling
- `http/https` - HTTP health checks
- `ssl` - SSL certificate checks
- `bandwidth` - Interface bandwidth
- `wmi` - Windows WMI
- `dns` - DNS resolution and validation
- `database` - Database health checks
- `cloud` - Cloud service health
- `ntp` - NTP sync
- `nginx` - Nginx stats

## Requirements

- Python 3.8+
- Flask
- pysnmp
- cryptography
- requests
- apscheduler
- paramiko
- dnspython
- pymysql
- psycopg2-binary
- pymongo
- redis
- boto3
- azure-mgmt-*
- google-cloud-monitoring
- influxdb-client
- paho-mqtt

## License

MIT