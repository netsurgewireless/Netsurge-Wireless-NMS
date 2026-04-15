"""Enhanced dashboard with analytics and reporting."""

from flask import Flask, jsonify, request, render_template_string
from datetime import datetime, timedelta
from io import BytesIO
import base64

ANALYTICS_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Network Monitor - Analytics Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; }
        .header { background: #161b22; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #30363d; }
        .header h1 { font-size: 20px; color: #58a6ff; font-weight: 600; }
        .header-logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 32px; height: 32px; background: linear-gradient(135deg, #238636, #2ea043); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; }
        .stats-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 16px; padding: 16px 24px; background: #161b22; border-bottom: 1px solid #30363d; }
        .stat-card { background: #21262d; border-radius: 8px; padding: 16px; border: 1px solid #30363d; }
        .stat-value { font-size: 28px; font-weight: 700; color: #f0f6fc; }
        .stat-value.up { color: #3fb950; }
        .stat-value.down { color: #f85149; }
        .stat-value.warn { color: #d29922; }
        .stat-label { font-size: 12px; color: #8b949e; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
        .stat-trend { font-size: 11px; margin-top: 4px; }
        .trend-up { color: #3fb950; }
        .trend-down { color: #f85149; }
        .container { padding: 24px; }
        .tabs { display: flex; gap: 4px; background: #21262d; padding: 4px; border-radius: 8px; margin-bottom: 24px; width: fit-content; }
        .tab { padding: 8px 16px; cursor: pointer; border-radius: 6px; font-size: 14px; color: #8b949e; transition: all 0.2s; }
        .tab:hover { color: #c9d1d9; }
        .tab.active { background: #30363d; color: #f0f6fc; }
        .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; }
        .panel { background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }
        .panel-header { padding: 12px 16px; background: #21262d; border-bottom: 1px solid #30363d; display: flex; justify-content: space-between; align-items: center; }
        .panel-title { font-size: 14px; font-weight: 600; color: #f0f6fc; }
        .panel-actions { display: flex; gap: 8px; }
        .btn-icon { background: none; border: none; color: #8b949e; cursor: pointer; padding: 4px 8px; border-radius: 4px; }
        .btn-icon:hover { background: #30363d; color: #f0f6fc; }
        .panel-body { padding: 16px; }
        .chart-box { height: 250px; }
        .metric-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; padding: 12px 0; }
        .metric-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #21262d; border-radius: 6px; }
        .metric-name { font-size: 12px; color: #8b949e; }
        .metric-val { font-size: 16px; font-weight: 600; }
        .table { width: 100%; border-collapse: collapse; }
        .table th { text-align: left; padding: 10px 12px; background: #21262d; font-size: 12px; color: #8b949e; font-weight: 500; border-bottom: 1px solid #30363d; }
        .table td { padding: 10px 12px; font-size: 13px; border-bottom: 1px solid #21262d; }
        .table tr:hover { background: #21262d; }
        .status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
        .status-dot.up { background: #3fb950; }
        .status-dot.down { background: #f85149; }
        .status-dot.degraded { background: #d29922; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 500; }
        .badge-success { background: rgba(63,185,80,0.2); color: #3fb950; }
        .badge-danger { background: rgba(248,81,73,0.2); color: #f85149; }
        .badge-warning { background: rgba(210,153,34,0.2); color: #d29922; }
        .badge-info { background: rgba(88,166,255,0.2); color: #58a6ff; }
        .input-date { background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 12px; border-radius: 6px; font-size: 13px; }
        .select-box { background: #0d1117; border: 1px solid #30363d; color: #c9d1d9; padding: 6px 12px; border-radius: 6px; font-size: 13px; }
        .progress-bar { height: 4px; background: #30363d; border-radius: 2px; overflow: hidden; }
        .progress-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
        .progress-fill.up { background: #3fb950; }
        .progress-fill.down { background: #f85149; }
        .progress-fill.warn { background: #d29922; }
        .device-list { max-height: 300px; overflow-y: auto; }
        .device-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-bottom: 1px solid #21262d; }
        .device-item:last-child { border-bottom: none; }
        .device-name { font-weight: 500; }
        .device-host { font-size: 12px; color: #8b949e; }
        @media (max-width: 1200px) { .stats-row { grid-template-columns: repeat(3, 1fr); } .grid-2 { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-logo">
            <div class="logo-icon">N</div>
            <h1>Network Monitor</h1>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
            <input type="date" id="date-from" class="input-date" value="">
            <span style="color: #8b949e;">to</span>
            <input type="date" id="date-to" class="input-date" value="">
            <select id="interval" class="select-box">
                <option value="hour">Hourly</option>
                <option value="day" selected>Daily</option>
                <option value="week">Weekly</option>
            </select>
            <button class="btn-icon" onclick="refreshData()">Refresh</button>
        </div>
    </div>
    
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-value" id="stat-total">0</div>
            <div class="stat-label">Total Targets</div>
        </div>
        <div class="stat-card">
            <div class="stat-value up" id="stat-up">0</div>
            <div class="stat-label">Online</div>
        </div>
        <div class="stat-card">
            <div class="stat-value down" id="stat-down">0</div>
            <div class="stat-label">Offline</div>
        </div>
        <div class="stat-card">
            <div class="stat-value warn" id="stat-degraded">0</div>
            <div class="stat-label">Degraded</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="stat-uptime">0%</div>
            <div class="stat-label">Uptime</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="stat-alerts">0</div>
            <div class="stat-label">Active Alerts</div>
        </div>
    </div>
    
    <div class="container">
        <div class="tabs">
            <div class="tab active" onclick="switchTab('overview')">Overview</div>
            <div class="tab" onclick="switchTab('performance')">Performance</div>
            <div class="tab" onclick="switchTab('devices')">Devices</div>
            <div class="tab" onclick="switchTab('alerts')">Alerts</div>
            <div class="tab" onclick="switchTab('reports')">Reports</div>
        </div>
        
        <div id="overview-view">
            <div class="grid-2">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Availability Trend</div>
                        <div class="panel-actions">
                            <button class="btn-icon" onclick="exportChart('availability')">Export</button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="chart-box"><canvas id="availability-chart"></canvas></div>
                    </div>
                </div>
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Response Time</div>
                        <div class="panel-actions">
                            <button class="btn-icon" onclick="exportChart('latency')">Export</button>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="chart-box"><canvas id="latency-chart"></canvas></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="performance-view" style="display: none;">
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Performance Metrics</div>
                </div>
                <div class="panel-body">
                    <div class="metric-row">
                        <div class="metric-item">
                            <span class="metric-name">Avg Response</span>
                            <span class="metric-val" id="avg-response">--</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-name">P95 Response</span>
                            <span class="metric-val" id="p95-response">--</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-name">Packet Loss</span>
                            <span class="metric-val" id="packet-loss">--</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-name">Jitter</span>
                            <span class="metric-val" id="jitter">--</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="devices-view" style="display: none;">
            <div class="grid-2">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Device Status</div>
                    </div>
                    <div class="panel-body">
                        <div class="device-list" id="device-list"></div>
                    </div>
                </div>
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">By Type</div>
                    </div>
                    <div class="panel-body">
                        <div class="chart-box"><canvas id="type-chart"></canvas></div>
                    </div>
                </div>
            </div>
        </div>
        
        <div id="alerts-view" style="display: none;">
            <div class="panel">
                <div class="panel-header">
                    <div class="panel-title">Recent Alerts</div>
                </div>
                <div class="panel-body" style="padding: 0;">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Target</th>
                                <th>Message</th>
                                <th>Severity</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody id="alerts-table"></tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <div id="reports-view" style="display: none;">
            <div class="grid-3">
                <div class="panel">
                    <div class="panel-header">
                        <div class="panel-title">Export Report</div>
                    </div>
                    <div class="panel-body">
                        <p style="color: #8b949e; margin-bottom: 16px;">Generate a detailed report for the selected time period.</p>
                        <button class="btn-icon" style="background: #238636; color: white; padding: 8px 16px;" onclick="generateReport('pdf')">Download PDF</button>
                        <button class="btn-icon" style="background: #0366d6; color: white; padding: 8px 16px; margin-left: 8px;" onclick="generateReport('csv')">Export CSV</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let overviewChart, latencyChart, typeChart;
        
        function initCharts() {
            const chartOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        type: 'time',
                        grid: { color: '#30363d' },
                        ticks: { color: '#8b949e' }
                    },
                    y: {
                        grid: { color: '#30363d' },
                        ticks: { color: '#8b949e' }
                    }
                }
            };
            
            overviewChart = new Chart(document.getElementById('availability-chart'), {
                type: 'line',
                data: { labels: [], datasets: [{ data: [], borderColor: '#3fb950', backgroundColor: 'rgba(63,185,80,0.1)', fill: true, tension: 0.4 }] },
                options: chartOptions
            });
            
            latencyChart = new Chart(document.getElementById('latency-chart'), {
                type: 'line',
                data: { labels: [], datasets: [{ data: [], borderColor: '#58a6ff', backgroundColor: 'rgba(88,166,255,0.1)', fill: true, tension: 0.4 }] },
                options: chartOptions
            });
            
            typeChart = new Chart(document.getElementById('type-chart'), {
                type: 'doughnut',
                data: { labels: [], datasets: [{ data: [], backgroundColor: ['#3fb950','#58a6ff','#d29922','#f85149','#a371f7'] }] },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { color: '#c9d1d9' } } } }
            });
        }
        
        async function fetchAnalytics() {
            try {
                const [statusRes, devicesRes, alertsRes, analyticsRes] = await Promise.all([
                    fetch('/api/status').then(r => r.json()),
                    fetch('/api/targets').then(r => r.json()),
                    fetch('/api/alerts').then(r => r.json()),
                    fetch('/api/analytics').then(r => r.json()).catch(() => ({}))
                ]);
                
                document.getElementById('stat-total').textContent = statusRes.total || 0;
                document.getElementById('stat-up').textContent = statusRes.up || 0;
                document.getElementById('stat-down').textContent = statusRes.down || 0;
                document.getElementById('stat-degraded').textContent = statusRes.degraded || 0;
                document.getElementById('stat-uptime').textContent = (analyticsRes.uptime || 0) + '%';
                document.getElementById('stat-alerts').textContent = (alertsRes.alerts || []).length;
                
                const targets = statusRes.targets || [];
                updateDeviceList(targets);
                updateTypeChart(targets);
                updateAlertTable(alertsRes.alerts || []);
                
                if (analyticsRes.availability) {
                    overviewChart.data.labels = analyticsRes.availability.map(a => a.time);
                    overviewChart.data.datasets[0].data = analyticsRes.availability.map(a => a.value);
                    overviewChart.update();
                }
                
                if (analyticsRes.latency) {
                    latencyChart.data.labels = analyticsRes.latency.map(a => a.time);
                    latencyChart.data.datasets[0].data = analyticsRes.latency.map(a => a.value);
                    latencyChart.update();
                }
            } catch(e) { console.error(e); }
        }
        
        function updateDeviceList(targets) {
            const list = document.getElementById('device-list');
            list.innerHTML = targets.map(t => `
                <div class="device-item">
                    <div>
                        <div class="device-name">${t.name}</div>
                        <div class="device-host">${t.host}</div>
                    </div>
                    <span class="badge badge-${t.status === 'up' ? 'success' : 'danger'}">${t.status}</span>
                </div>
            `).join('');
        }
        
        function updateTypeChart(targets) {
            const counts = {};
            targets.forEach(t => {
                const type = t.check_type || 'unknown';
                counts[type] = (counts[type] || 0) + 1;
            });
            typeChart.data.labels = Object.keys(counts);
            typeChart.data.datasets[0].data = Object.values(counts);
            typeChart.update();
        }
        
        function updateAlertTable(alerts) {
            document.getElementById('alerts-table').innerHTML = alerts.slice(0, 20).map(a => `
                <tr>
                    <td>${new Date(a.timestamp).toLocaleString()}</td>
                    <td>${a.target_id}</td>
                    <td>${a.message}</td>
                    <td><span class="badge badge-${a.severity === 'critical' ? 'danger' : 'warning'}">${a.severity}</span></td>
                    <td>${a.acknowledged ? '<span class="badge badge-info">Ack</span>' : '-'}</td>
                </tr>
            `).join('');
        }
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.querySelectorAll('[id$="-view"]').forEach(v => v.style.display = 'none');
            document.getElementById(tab + '-view').style.display = 'block';
        }
        
        function refreshData() { fetchAnalytics(); }
        
        function exportChart(type) { console.log('Export:', type); }
        
        function generateReport(format) { console.log('Generate:', format); }
        
        initCharts();
        fetchAnalytics();
        setInterval(fetchAnalytics, 30000);
        
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('date-from').value = new Date(Date.now() - 7*24*60*60*1000).toISOString().split('T')[0];
        document.getElementById('date-to').value = today;
    </script>
</body>
</html>
"""


def add_analytics_routes(app: Flask):
    @app.route("/analytics")
    def analytics_dashboard():
        return render_template_string(ANALYTICS_DASHBOARD_HTML)
    
    @app.route("/api/analytics")
    def api_analytics():
        from flask import current_app
        from src.storage import Database
        from src.models import CheckType
        
        db = Database(Path("network_monitor.db"))
        
        now = datetime.now()
        hours_ago = now - timedelta(hours=24)
        
        metrics = db.get_metrics(limit=10000)
        
        up_count = sum(1 for m in metrics if m.status.value == "up")
        uptime = (up_count / len(metrics) * 100) if metrics else 0
        
        latencies = [m.latency_ms for m in metrics if m.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        
        availability_data = []
        for i in range(24):
            hour = now - timedelta(hours=i)
            hour_metrics = [
                m for m in metrics
                if abs((m.timestamp - hour).total_seconds()) < 1800
            ]
            if hour_metrics:
                rate = sum(1 for m in hour_metrics if m.status.value == "up") / len(hour_metrics) * 100
                availability_data.append({"time": hour.isoformat(), "value": rate})
            else:
                availability_data.append({"time": hour.isoformat(), "value": None})
        
        latency_data = []
        for i in range(24):
            hour = now - timedelta(hours=i)
            hour_metrics = [
                m for m in metrics
                if abs((m.timestamp - hour).total_seconds()) < 1800 and m.latency_ms is not None
            ]
            if hour_metrics:
                avg = sum(m.latency_ms for m in hour_metrics) / len(hour_metrics)
                latency_data.append({"time": hour.isoformat(), "value": avg})
        
        return jsonify({
            "uptime": uptime,
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "availability": availability_data,
            "latency": latency_data,
            "total_checks": len(metrics),
        })
    
    @app.route("/api/analytics/availability")
    def api_availability():
        return jsonify({"data": []})
    
    @app.route("/api/analytics/reports", methods=["POST"])
    def generate_report():
        from src.storage import Database
        import csv
        from io import StringIO
        
        data = request.get_json() or {}
        format_type = data.get("format", "csv")
        date_from = data.get("from", (datetime.now() - timedelta(days=7)).isoformat())
        date_to = data.get("to", datetime.now().isoformat())
        
        db = Database(Path("network_monitor.db"))
        metrics = db.get_metrics(limit=10000)
        
        if format_type == "csv":
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["timestamp", "target_id", "check_type", "status", "latency_ms", "value", "error"])
            
            for m in metrics:
                writer.writerow([
                    m.timestamp.isoformat(),
                    m.target_id,
                    m.check_type.value,
                    m.status.value,
                    m.latency_ms,
                    m.value,
                    m.error or "",
                ])
            
            return output.getvalue(), 200, {
                "Content-Type": "text/csv",
                "Content-Disposition": "attachment; filename=network_report.csv",
            }
        
        return jsonify({"error": "Unsupported format"}), 400


def enhance_dashboard_routes(app: Flask):
    add_analytics_routes(app)
    
    @app.route("/api/status")
    def api_status():
        from flask import current_app
        
        if hasattr(current_app, "network_monitor"):
            server = current_app.network_monitor
            status = server.get_status_summary()
            targets = server.get_targets_status()
            status["targets"] = targets
            return jsonify(status)
        
        return jsonify({"total": 0, "up": 0, "down": 0, "degraded": 0, "targets": []})
    
    @app.route("/api/metrics/export", methods=["POST"])
    def export_metrics():
        data = request.get_json() or {}
        format_type = data.get("format", "json")
        
        if format_type == "prometheus":
            from src.exporter import PrometheusExporter
            exporter = PrometheusExporter()
            return exporter.generate_prometheus_text(), 200, {
                "Content-Type": "text/plain",
            }
        
        return jsonify({"error": "Unsupported format"}), 400