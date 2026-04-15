# Netsurge Wireless NMS - Quick Start Guide

## Quick Installation

### Option 1: Windows Executable (Easiest)
1. Download the installer from releases
2. Run the installer
3. Click "Start Server" on the launcher
4. Open http://localhost:8080

### Option 2: Python Installation
```bash
# Clone the repository
git clone https://github.com/netsurgewireless/Netsurge-Wireless-NMS.git
cd Netsurge-Wireless-NMS

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m src.server

# Or use the desktop launcher
python -m src.desktop_launcher
```

### Option 3: Build from Source
```bash
# Install build tools
pip install pyinstaller

# Build the executable
pyinstaller build_installer.py

# The executable will be in dist/ folder
```

## First Run Setup

### 1. Start the Application
Double-click `NetworkMonitor.bat` or run:
```bash
python -m src.desktop_launcher
```

### 2. Start Server
Click "Start Server" in the launcher. The server will start on port 8080.

### 3. Access Dashboard
Click "Open Dashboard" or go to http://localhost:8080

## Adding Devices

### Via API
```bash
curl -X POST http://localhost:8080/api/targets \
  -H "Content-Type: application/json" \
  -d '{
    "id": "router-1",
    "name": "Main Router",
    "host": "192.168.1.1",
    "check_type": "snmp",
    "device_type": "cisco",
    "snmp_community": "public"
  }'
```

### Via Dashboard
Navigate to Settings or use the API to add devices.

## Supported Devices

### Network Equipment
- **Cisco** (IOS, NX-OS, WLC)
- **Juniper** (JUNOS)
- **Ubiquiti** (AirMAX, UniFi)
- **MikroTik** (RouterOS)
- **HPE** (ProCurve, Aruba)
- **Dell** (Force10, iOM)
- **Fortinet** (FortiGate)
- **Palo Alto** (PAN-OS)

### Server Monitoring
- **Windows** (WMI)
- **Linux** (SSH)
- **IPMI** (BMC sensors)

## Common Commands

### CLI Access
```bash
# Connect to device
curl -X POST http://localhost:8080/api/cli/connect \
  -H "Content-Type: application/json" \
  -d '{"host":"192.168.1.1","vendor":"cisco_ios","username":"admin","password":"pass"}'

# Execute command
curl -X POST http://localhost:8080/api/cli/execute \
  -H "Content-Type: application/json" \
  -d '{"host":"192.168.1.1","command":"show version"}'
```

### IPMI Access
```bash
# Get server sensors
curl -X POST http://localhost:8080/api/ipmi/sensors \
  -H "Content-Type: application/json" \
  -d '{"host":"192.168.1.100","username":"ADMIN","password":"ADMIN"}'
```

## Troubleshooting

### Server won't start
- Check port 8080 is available
- Verify Python dependencies installed

### Can't connect to device
- Check network connectivity
- Verify SNMP community string
- Check firewall allows port 161 (SNMP)

### Dashboard not loading
- Ensure server is running
- Check browser can reach http://localhost:8080

## Configuration File

Edit `config.json` in the application directory:
```json
{
  "targets": [
    {
      "id": "my-device",
      "name": "My Device",
      "host": "192.168.1.1",
      "check_type": "ping",
      "interval": 60
    }
  ],
  "api_port": 8080,
  "log_level": "INFO"
}
```

## Support

- GitHub: https://github.com/netsurgewireless/Netsurge-Wireless-NMS
- Issues: https://github.com/netsurgewireless/Netsurge-Wireless-NMS/issues
