"""Desktop client application for end users."""

import sys
import os
import threading
import subprocess
import logging
import requests
import socket
from pathlib import Path
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext
import webbrowser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NetworkMonitorClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Netsurge Wireless NMS - Client Monitor")
        self.root.geometry("900x650")
        self.root.minsize(900, 650)
        
        self.server_url = "http://localhost:8080"
        self.connected = False
        self.targets = []
        self.alerts = []
        self.refresh_interval = 30
        
        self._setup_ui()
        self._check_server_connection()
        
    def _setup_ui(self):
        header_frame = Frame(self.root, bg='#16213e', height=80)
        header_frame.pack(fill=X)
        header_frame.pack_propagate(False)
        
        title_label = Label(
            header_frame,
            text="Netsurge Wireless NMS - Client Dashboard",
            font=('Arial', 16, 'bold'),
            fg='#00d9ff',
            bg='#16213e'
        )
        title_label.pack(pady=20)
        
        control_frame = Frame(self.root, bg='#1a1a2e')
        control_frame.pack(fill=X, padx=20, pady=10)
        
        Label(control_frame, text="Server URL:", fg='#eee', bg='#1a1a2e').pack(side=LEFT)
        
        self.server_entry = Entry(control_frame, width=30, font=('Arial', 10))
        self.server_entry.insert(0, self.server_url)
        self.server_entry.pack(side=LEFT, padx=10)
        
        ttk.Button(control_frame, text="Connect", command=self.connect_to_server).pack(side=LEFT, padx=5)
        ttk.Button(control_frame, text="Refresh", command=self.refresh_data).pack(side=LEFT, padx=5)
        ttk.Button(control_frame, text="Open Full Dashboard", command=self.open_dashboard).pack(side=LEFT, padx=20)
        
        main_frame = Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=10)
        
        stats_frame = Frame(main_frame, bg='#1a1a2e')
        stats_frame.pack(fill=X, pady=(0, 10))
        
        self.total_label = self._create_stat_label(stats_frame, "Total: 0", 0)
        self.up_label = self._create_stat_label(stats_frame, "Up: 0", 1)
        self.down_label = self._create_stat_label(stats_frame, "Down: 0", 2)
        self.alert_label = self._create_stat_label(stats_frame, "Alerts: 0", 3)
        
        notebk = ttk.Notebook(main_frame)
        notebk.pack(fill=BOTH, expand=True)
        
        devices_tab = Frame(notebk, bg='#1a1a2e')
        notebk.add(devices_tab, text="Devices")
        notebk.select(devices_tab)
        
        tree_scroll_y = Scrollbar(devices_tab)
        tree_scroll_y.pack(side=RIGHT, fill=Y)
        
        tree_scroll_x = Scrollbar(devices_tab, orient=HORIZONTAL)
        tree_scroll_x.pack(side=BOTTOM, fill=X)
        
        self.devices_tree = ttk.Treeview(
            devices_tab,
            columns=('name', 'host', 'type', 'status', 'latency', 'last_check'),
            show='tree headings',
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        
        self.devices_tree.pack(fill=BOTH, expand=True)
        
        tree_scroll_y.config(command=self.devices_tree.yview)
        tree_scroll_x.config(command=self.devices_tree.xview)
        
        self.devices_tree.heading('#0', text='ID')
        self.devices_tree.heading('name', text='Name')
        self.devices_tree.heading('host', text='Host')
        self.devices_tree.heading('type', text='Type')
        self.devices_tree.heading('status', text='Status')
        self.devices_tree.heading('latency', text='Latency')
        self.devices_tree.heading('last_check', text='Last Check')
        
        self.devices_tree.column('#0', width=100)
        self.devices_tree.column('name', width=150)
        self.devices_tree.column('host', width=120)
        self.devices_tree.column('type', width=100)
        self.devices_tree.column('status', width=80)
        self.devices_tree.column('latency', width=80)
        self.devices_tree.column('last_check', width=120)
        
        alerts_tab = Frame(notebk, bg='#1a1a2e')
        notebk.add(alerts_tab, text="Alerts")
        
        self.alerts_tree = ttk.Treeview(
            alerts_tab,
            columns=('target', 'message', 'severity', 'time'),
            show='headings'
        )
        self.alerts_tree.pack(fill=BOTH, expand=True)
        
        self.alerts_tree.heading('target', text='Target')
        self.alerts_tree.heading('message', text='Message')
        self.alerts_tree.heading('severity', text='Severity')
        self.alerts_tree.heading('time', text='Time')
        
        self.alerts_tree.column('target', width=100)
        self.alerts_tree.column('message', width=300)
        self.alerts_tree.column('severity', width=80)
        self.alerts_tree.column('time', width=150)
        
        status_bar = Frame(self.root, bg='#16213e', height=30)
        status_bar.pack(fill=X, side=BOTTOM)
        status_bar.pack_propagate(False)
        
        self.status_label = Label(
            status_bar,
            text="Not connected",
            font=('Arial', 9),
            fg='#888',
            bg='#16213e'
        )
        self.status_label.pack(pady=5)

    def _create_stat_label(self, parent, text, column):
        label = Label(
            parent,
            text=text,
            font=('Arial', 12, 'bold'),
            fg='#eee',
            bg='#1a1a2e',
            padx=20,
            pady=10
        )
        label.pack(side=LEFT, padx=10)
        return label

    def connect_to_server(self):
        self.server_url = self.server_entry.get().strip()
        
        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=5)
            
            if response.status_code == 200:
                self.connected = True
                self.status_label.config(text=f"Connected to {self.server_url}", fg="#00c853")
                self.refresh_data()
                self._start_auto_refresh()
            else:
                messagebox.showerror("Error", f"Server returned status {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Error", f"Cannot connect to {self.server_url}")
            self.status_label.config(text="Connection failed", fg="#ff1744")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _check_server_connection(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', 8080))
            sock.close()
            
            if result == 0:
                self.server_url = "http://localhost:8080"
                self.server_entry.delete(0, END)
                self.server_entry.insert(0, self.server_url)
                self.connect_to_server()
        except:
            pass

    def refresh_data(self):
        if not self.connected:
            return
        
        try:
            targets_response = requests.get(f"{self.server_url}/api/targets", timeout=10)
            if targets_response.status_code == 200:
                data = targets_response.json()
                self.targets = data.get('targets', [])
                self._update_devices_tree()
                self._update_stats()
            
            alerts_response = requests.get(f"{self.server_url}/api/alerts?active_only=true", timeout=10)
            if alerts_response.status_code == 200:
                data = alerts_response.json()
                self.alerts = data.get('alerts', [])
                self._update_alerts_tree()
                
        except Exception as e:
            logger.error(f"Failed to refresh data: {e}")

    def _update_devices_tree(self):
        for item in self.devices_tree.get_children():
            self.devices_tree.delete(item)
        
        for target in self.targets:
            status = target.get('status', 'unknown')
            
            status_colors = {
                'up': '#00c853',
                'down': '#ff1744',
                'degraded': '#ffab00',
                'unknown': '#888'
            }
            
            self.devices_tree.insert(
                '',
                END,
                text=target.get('id', ''),
                values=(
                    target.get('name', ''),
                    target.get('host', ''),
                    target.get('check_type', ''),
                    status.upper(),
                    f"{target.get('latency_ms', 0):.1f} ms" if target.get('latency_ms') else '-',
                    '-'
                )
            )

    def _update_stats(self):
        total = len(self.targets)
        up = sum(1 for t in self.targets if t.get('status') == 'up')
        down = sum(1 for t in self.targets if t.get('status') == 'down')
        alerts = len(self.alerts)
        
        self.total_label.config(text=f"Total: {total}")
        self.up_label.config(text=f"Up: {up}")
        self.down_label.config(text=f"Down: {down}")
        self.alert_label.config(text=f"Alerts: {alerts}")

    def _update_alerts_tree(self):
        for item in self.alerts_tree.get_children():
            self.alerts_tree.delete(item)
        
        for alert in self.alerts:
            self.alerts_tree.insert(
                '',
                END,
                values=(
                    alert.get('target_id', ''),
                    alert.get('message', ''),
                    alert.get('severity', '').upper(),
                    alert.get('timestamp', '')[:19]
                )
            )

    def _start_auto_refresh(self):
        def auto_refresh():
            while self.connected:
                self.root.after(0, self.refresh_data)
                threading.Event().wait(self.refresh_interval)
        
        thread = threading.Thread(target=auto_refresh, daemon=True)
        thread.start()

    def open_dashboard(self):
        if self.connected:
            webbrowser.open(self.server_url)
        else:
            messagebox.showwarning("Warning", "Please connect to server first")

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to exit?"):
            self.connected = False
            self.root.destroy()


def main():
    root = Tk()
    app = NetworkMonitorClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
