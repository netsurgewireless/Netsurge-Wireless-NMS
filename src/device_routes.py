"""CLI and IPMI API routes integration."""

from flask import Flask, jsonify, request
from src.device_cli import DeviceCLI, DeviceVendor, VendorCommands, QuickDiagnostic, AccessMethod
from src.monitors.ipmi import IPMIMonitor, IPMICommand


def add_cli_routes(app):
    cli = DeviceCLI()

    @app.route("/api/cli/connect", methods=["POST"])
    def cli_connect():
        data = request.get_json()
        
        try:
            vendor = DeviceVendor(data.get("vendor", "cisco_ios"))
            method = AccessMethod(data.get("method", "ssh"))
            
            success = cli.connect(
                host=data["host"],
                vendor=vendor,
                username=data.get("username", "admin"),
                password=data.get("password", ""),
                method=method,
                port=data.get("port"),
            )
            
            if success:
                return jsonify({"success": True, "message": f"Connected to {data['host']}"})
            return jsonify({"success": False, "error": "Connection failed"}), 500
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/cli/disconnect", methods=["POST"])
    def cli_disconnect():
        data = request.get_json()
        host = data.get("host")
        
        if host:
            cli.disconnect(host)
        
        return jsonify({"success": True})

    @app.route("/api/cli/execute", methods=["POST"])
    def cli_execute():
        data = request.get_json()
        host = data.get("host")
        command = data.get("command", "")
        timeout = data.get("timeout", 30)
        
        if not host or not command:
            return jsonify({"error": "Missing host or command"}), 400
        
        result = cli.execute(host, command, timeout)
        
        return jsonify({
            "host": host,
            "command": command,
            "success": result.success,
            "output": result.output,
            "error": result.error,
            "execution_time": result.execution_time,
            "timestamp": result.timestamp.isoformat(),
        })

    @app.route("/api/cli/commands/<vendor>", methods=["GET"])
    def cli_get_commands(vendor):
        try:
            vendor_enum = DeviceVendor(vendor)
            commands = cli.get_available_commands(vendor_enum)
            return jsonify({"vendor": vendor, "commands": commands})
        except ValueError:
            return jsonify({"error": f"Unknown vendor: {vendor}"}), 404

    @app.route("/api/cli/vendors", methods=["GET"])
    def cli_get_vendors():
        return jsonify({"vendors": VendorCommands.get_all_vendors()})

    @app.route("/api/cli/diagnostic", methods=["POST"])
    def cli_diagnostic():
        data = request.get_json()
        
        host = data.get("host")
        vendor = data.get("vendor")
        
        if not host or not vendor:
            return jsonify({"error": "Missing host or vendor"}), 400
        
        try:
            vendor_enum = DeviceVendor(vendor)
            results = QuickDiagnostic.run_diagnostic(cli, host, vendor_enum)
            return jsonify(results)
        except ValueError:
            return jsonify({"error": f"Unknown vendor: {vendor}"}), 404


def add_ipmi_routes(app):
    @app.route("/api/ipmi/connect", methods=["POST"])
    def ipmi_connect():
        data = request.get_json()
        
        monitor = IPMIMonitor(
            host=data.get("host"),
            username=data.get("username", "ADMIN"),
            password=data.get("password", "ADMIN"),
            timeout=data.get("timeout", 10),
        )
        
        bmc_info = monitor.get_bmc_info()
        
        return jsonify({
            "success": bool(bmc_info),
            "bmc_info": bmc_info,
        })

    @app.route("/api/ipmi/sensors", methods=["POST"])
    def ipmi_sensors():
        data = request.get_json()
        
        monitor = IPMIMonitor(
            host=data.get("host"),
            username=data.get("username", "ADMIN"),
            password=data.get("password", "ADMIN"),
        )
        
        sensors = monitor.get_sensor_data()
        
        return jsonify({
            "sensors": [
                {
                    "name": s.name,
                    "value": s.value,
                    "unit": s.unit,
                    "status": s.status,
                    "type": s.sensor_type.value,
                }
                for s in sensors
            ]
        })

    @app.route("/api/ipmi/chassis", methods=["POST"])
    def ipmi_chassis():
        data = request.get_json()
        
        monitor = IPMIMonitor(
            host=data.get("host"),
            username=data.get("username", "ADMIN"),
            password=data.get("password", "ADMIN"),
        )
        
        chassis = monitor.get_chassis_status()
        
        if chassis:
            return jsonify({
                "power_state": chassis.power_state,
                "intrusion": chassis.intrusion,
                "front_panel_lock": chassis.front_panel_lock,
                "boot_device": chassis.boot_device,
            })
        
        return jsonify({"error": "Failed to get chassis status"}), 500

    @app.route("/api/ipmi/sel", methods=["POST"])
    def ipmi_sel():
        data = request.get_json()
        
        monitor = IPMIMonitor(
            host=data.get("host"),
            username=data.get("username", "ADMIN"),
            password=data.get("password", "ADMIN"),
        )
        
        entries = data.get("entries", 10)
        sel = monitor.get_sel(entries)
        
        return jsonify({"sel": sel})

    @app.route("/api/ipmi/fru", methods=["POST"])
    def ipmi_fru():
        data = request.get_json()
        
        monitor = IPMIMonitor(
            host=data.get("host"),
            username=data.get("username", "ADMIN"),
            password=data.get("password", "ADMIN"),
        )
        
        fru = monitor.get_fru_info()
        
        return jsonify({"fru": fru})

    @app.route("/api/ipmi/health", methods=["POST"])
    def ipmi_health():
        data = request.get_json()
        
        monitor = IPMIMonitor(
            host=data.get("host"),
            username=data.get("username", "ADMIN"),
            password=data.get("password", "ADMIN"),
        )
        
        health = monitor.check_health()
        
        return jsonify(health)

    @app.route("/api/ipmi/commands", methods=["GET"])
    def ipmi_commands():
        return jsonify({"commands": IPMICommand.get_available_commands()})


def add_all_device_routes(app):
    add_cli_routes(app)
    add_ipmi_routes(app)
