"""Web dashboard templates and routes."""

from flask import Flask, jsonify, request, render_template_string
from datetime import datetime, timedelta

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Network Monitor Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; }
        .header { background: #16213e; padding: 20px; display: flex; justify-content: space-between; align-items: center; }
        .header h1 { font-size: 24px; color: #00d9ff; }
        .stats { display: flex; gap: 30px; }
        .stat { text-align: center; }
        .stat-value { font-size: 32px; font-weight: bold; }
        .stat-label { font-size: 12px; color: #888; }
        .up { color: #00c853; }
        .down { color: #ff1744; }
        .degraded { color: #ffab00; }
        .container { padding: 20px; }
        .filters { margin-bottom: 20px; display: flex; gap: 10px; }
        .filters select, .filters input { padding: 8px 12px; background: #16213e; border: 1px solid #333; color: #fff; border-radius: 4px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }
        .card { background: #16213e; border-radius: 8px; padding: 20px; border: 1px solid #333; }
        .card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .card-title { font-size: 18px; font-weight: 600; }
        .card-type { font-size: 12px; color: #888; background: #0f3460; padding: 4px 8px; border-radius: 4px; }
        .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status-up { background: rgba(0,200,83,0.2); color: #00c853; }
        .status-down { background: rgba(255,23,68,0.2); color: #ff1744; }
        .status-degraded { background: rgba(255,171,0,0.2); color: #ffab00; }
        .metric { display: flex; justify-content: space-between; margin: 8px 0; padding: 8px 0; border-bottom: 1px solid #333; }
        .metric-label { color: #888; }
        .metric-value { font-weight: 600; }
        .chart-container { height: 150px; margin-top: 15px; }
        .tabs { display: flex; border-bottom: 1px solid #333; margin-bottom: 20px; }
        .tab { padding: 12px 24px; cursor: pointer; border-bottom: 2px solid transparent; }
        .tab.active { border-bottom-color: #00d9ff; color: #00d9ff; }
        .alert-list { background: #16213e; border-radius: 8px; }
        .alert-item { padding: 15px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
        .alert-critical { border-left: 4px solid #ff1744; }
        .alert-warning { border-left: 4px solid #ffab00; }
        .alert-info { border-left: 4px solid #00d9ff; }
        .btn { padding: 8px 16px; background: #00d9ff; color: #000; border: none; border-radius: 4px; cursor: pointer; }
        .btn:hover { opacity: 0.9; }
        .refresh { font-size: 12px; color: #888; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Network Monitor</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-value" id="total-targets">0</div>
                <div class="stat-label">Total Targets</div>
            </div>
            <div class="stat">
                <div class="stat-value up" id="up-count">0</div>
                <div class="stat-label">Online</div>
            </div>
            <div class="stat">
                <div class="stat-value down" id="down-count">0</div>
                <div class="stat-label">Offline</div>
            </div>
            <div class="stat">
                <div class="stat-value degraded" id="degraded-count">0</div>
                <div class="stat-label">Degraded</div>
            </div>
        </div>
        <span class="refresh" id="last-update">Last update: --</span>
    </div>
    
    <div class="container">
        <div class="tabs">
            <div class="tab active" onclick="switchTab('dashboard')">Dashboard</div>
            <div class="tab" onclick="switchTab('alerts')">Alerts</div>
            <div class="tab" onclick="switchTab('discovery')">Discovery</div>
        </div>
        
        <div id="dashboard-view">
            <div class="filters">
                <select id="status-filter">
                    <option value="all">All Status</option>
                    <option value="up">Up</option>
                    <option value="down">Down</option>
                    <option value="degraded">Degraded</option>
                </select>
                <select id="type-filter">
                    <option value="all">All Types</option>
                    <option value="ping">Ping</option>
                    <option value="port">Port</option>
                    <option value="http">HTTP</option>
                    <option value="snmp">SNMP</option>
                    <option value="bandwidth">Bandwidth</option>
                </select>
            </div>
            <div class="grid" id="targets-grid"></div>
        </div>
        
        <div id="alerts-view" style="display:none;">
            <div class="alert-list" id="alerts-list"></div>
        </div>
        
        <div id="discovery-view" style="display:none;">
            <div class="card">
                <h3>Network Scan</h3>
                <div style="margin: 15px 0;">
                    <input type="text" id="scan-network" placeholder="Network (e.g. 192.168.1.0/24)" value="192.168.1.0/24">
                    <button class="btn" onclick="startScan()">Scan Network</button>
                </div>
                <div id="scan-results"></div>
            </div>
        </div>
    </div>

    <script>
        let targets = [];
        let alerts = [];
        let charts = {};
        
        async function fetchData() {
            try {
                const [targetsRes, alertsRes] = await Promise.all([
                    fetch('/api/targets').then(r => r.json()),
                    fetch('/api/alerts').then(r => r.json())
                ]);
                targets = targetsRes.targets || [];
                alerts = alertsRes.alerts || [];
                updateDashboard();
                updateAlerts();
                document.getElementById('last-update').textContent = 'Last update: ' + new Date().toLocaleTimeString();
            } catch(e) {
                console.error(e);
            }
        }
        
        function updateDashboard() {
            const statusFilter = document.getElementById('status-filter').value;
            const typeFilter = document.getElementById('type-filter').value;
            
            let filtered = targets.filter(t => {
                return (statusFilter === 'all' || t.status === statusFilter) &&
                       (typeFilter === 'all' || t.check_type === typeFilter);
            });
            
            let up = 0, down = 0, degraded = 0;
            targets.forEach(t => {
                if(t.status === 'up') up++;
                else if(t.status === 'down') down++;
                else if(t.status === 'degraded') degraded++;
            });
            
            document.getElementById('total-targets').textContent = targets.length;
            document.getElementById('up-count').textContent = up;
            document.getElementById('down-count').textContent = down;
            document.getElementById('degraded-count').textContent = degraded;
            
            const grid = document.getElementById('targets-grid');
            grid.innerHTML = filtered.map(t => `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">${t.name}</div>
                            <div style="color:#888;font-size:12px;">${t.host}${t.port ? ':'+t.port : ''}</div>
                        </div>
                        <span class="status-badge status-${t.status}">${t.status.toUpperCase()}</span>
                    </div>
                    <div class="card-type">${t.check_type.toUpperCase()}</div>
                    <div class="metric">
                        <span class="metric-label">Response Time</span>
                        <span class="metric-value">${t.latency_ms ? t.latency_ms.toFixed(1) + ' ms' : '--'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Last Check</span>
                        <span class="metric-value">${t.last_check ? new Date(t.last_check).toLocaleTimeString() : '--'}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Uptime</span>
                        <span class="metric-value">${t.uptime || '--'}</span>
                    </div>
                </div>
            `).join('');
        }
        
        function updateAlerts() {
            const list = document.getElementById('alerts-list');
            list.innerHTML = alerts.map(a => `
                <div class="alert-item alert-${a.severity}">
                    <div>
                        <div style="font-weight:600">${a.message}</div>
                        <div style="color:#888;font-size:12px;">${a.target_id} - ${new Date(a.timestamp).toLocaleString()}</div>
                    </div>
                    ${a.acknowledged ? '<span style="color:#888">Acknowledged</span>' : 
                      '<button class="btn" onclick="ackAlert(\''+a.id+'\')">Acknowledge</button>'}
                </div>
            `).join('');
        }
        
        async function ackAlert(id) {
            await fetch('/api/alerts/'+id+'/acknowledge', {method:'POST'});
            fetchData();
        }
        
        async function startScan() {
            const network = document.getElementById('scan-network').value;
            document.getElementById('scan-results').innerHTML = 'Scanning...';
            
            const res = await fetch('/api/discovery/scan?network='+network);
            const data = await res.json();
            
            document.getElementById('scan-results').innerHTML = data.hosts.map(h => 
                '<div style="padding:8px;border-bottom:1px solid #333;">'+h.host+' - '+h.status+'</div>'
            ).join('');
        }
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            document.getElementById('dashboard-view').style.display = tab === 'dashboard' ? 'block' : 'none';
            document.getElementById('alerts-view').style.display = tab === 'alerts' ? 'block' : 'none';
            document.getElementById('discovery-view').style.display = tab === 'discovery' ? 'block' : 'none';
        }
        
        document.getElementById('status-filter').addEventListener('change', updateDashboard);
        document.getElementById('type-filter').addEventListener('change', updateDashboard);
        
        fetchData();
        setInterval(fetchData, 30000);
    </script>
</body>
</html>
"""


def add_dashboard_routes(app: Flask):
    @app.route("/")
    def dashboard():
        return render_template_string(DASHBOARD_HTML)

    @app.route("/api/discovery/scan")
    def discovery_scan():
        from src.monitors.discovery import NetworkDiscovery
        
        network = request.args.get("network", "192.168.1.0/24")
        discovery = NetworkDiscovery()
        hosts = discovery.scan_network(network)
        return jsonify({"hosts": hosts})
