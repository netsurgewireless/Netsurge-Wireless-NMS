"""Desktop launcher application for Network Monitor."""

import sys
import os
import threading
import subprocess
import logging
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


class NetworkMonitorLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Netsurge Wireless NMS - Network Monitor")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        self.server_process = None
        self.client_process = None
        self.running = False
        
        self._setup_ui()
        self._setup_styles()
        
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Header.TLabel', font=('Arial', 14, 'bold'), foreground='#00d9ff')
        style.configure('Status.TLabel', font=('Arial', 10))
        style.configure('Start.TButton', font=('Arial', 11, 'bold'), padding=10)
        style.configure('Stop.TButton', font=('Arial', 11), padding=10)
        
    def _setup_ui(self):
        header_frame = Frame(self.root, bg='#16213e', height=80)
        header_frame.pack(fill=X)
        header_frame.pack_propagate(False)
        
        title_label = Label(
            header_frame,
            text="Netsurge Wireless NMS",
            font=('Arial', 20, 'bold'),
            fg='#00d9ff',
            bg='#16213e'
        )
        title_label.pack(pady=20)
        
        main_frame = Frame(self.root, bg='#1a1a2e')
        main_frame.pack(fill=BOTH, expand=True)
        
        left_panel = Frame(main_frame, bg='#1a1a2e')
        left_panel.pack(side=LEFT, fill=Y, padx=20, pady=20)
        
        server_frame = LabelFrame(
            left_panel,
            text="Server Application",
            font=('Arial', 12, 'bold'),
            fg='#eee',
            bg='#1a1a2e',
            bd=2,
            relief=RIDGE
        )
        server_frame.pack(fill=X, pady=10)
        
        self.server_status_label = Label(
            server_frame,
            text="Status: Stopped",
            font=('Arial', 10),
            fg='#ff1744',
            bg='#1a1a2e',
            pady=10
        )
        self.server_status_label.pack()
        
        self.start_server_btn = ttk.Button(
            server_frame,
            text="Start Server",
            style='Start.TButton',
            command=self.start_server
        )
        self.start_server_btn.pack(pady=5, padx=20, fill=X)
        
        self.stop_server_btn = ttk.Button(
            server_frame,
            text="Stop Server",
            style='Stop.TButton',
            command=self.stop_server,
            state=DISABLED
        )
        self.stop_server_btn.pack(pady=5, padx=20, fill=X)
        
        ttk.Button(
            server_frame,
            text="Open Dashboard",
            command=self.open_dashboard
        ).pack(pady=5, padx=20, fill=X)
        
        client_frame = LabelFrame(
            left_panel,
            text="Client Application",
            font=('Arial', 12, 'bold'),
            fg='#eee',
            bg='#1a1a2e',
            bd=2,
            relief=RIDGE
        )
        client_frame.pack(fill=X, pady=10)
        
        self.client_status_label = Label(
            client_frame,
            text="Status: Not Running",
            font=('Arial', 10),
            fg='#888',
            bg='#1a1a2e',
            pady=10
        )
        self.client_status_label.pack()
        
        self.start_client_btn = ttk.Button(
            client_frame,
            text="Start Client",
            style='Start.TButton',
            command=self.start_client
        )
        self.start_client_btn.pack(pady=5, padx=20, fill=X)
        
        self.stop_client_btn = ttk.Button(
            client_frame,
            text="Stop Client",
            style='Stop.TButton',
            command=self.stop_client,
            state=DISABLED
        )
        self.stop_client_btn.pack(pady=5, padx=20, fill=X)
        
        right_panel = Frame(main_frame, bg='#1a1a2e')
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True, padx=20, pady=20)
        
        log_frame = LabelFrame(
            right_panel,
            text="Application Log",
            font=('Arial', 12, 'bold'),
            fg='#eee',
            bg='#1a1a2e',
            bd=2,
            relief=RIDGE
        )
        log_frame.pack(fill=BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=('Consolas', 9),
            bg='#0d1117',
            fg='#c9d1d9',
            state=DISABLED,
            wrap=WORD
        )
        self.log_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        status_bar = Frame(self.root, bg='#16213e', height=30)
        status_bar.pack(fill=X, side=BOTTOM)
        status_bar.pack_propagate(False)
        
        self.status_bar = Label(
            status_bar,
            text="Ready",
            font=('Arial', 9),
            fg='#888',
            bg='#16213e'
        )
        self.status_bar.pack(pady=5)
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state=NORMAL)
        
        color = '#c9d1d9'
        if level == "ERROR":
            color = '#ff6b6b'
        elif level == "WARNING":
            color = '#ffd93d'
        elif level == "SUCCESS":
            color = '#6bcf6b'
            
        self.log_text.insert(END, f"[{timestamp}] {message}\n", level)
        self.log_text.tag_config(level, foreground=color)
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)
        
        logger.log(getattr(logging, level), message)
        
        self.status_bar.config(text=message)

    def start_server(self):
        self.log("Starting Network Monitor Server...", "INFO")
        
        try:
            self.server_process = subprocess.Popen(
                [sys.executable, "-m", "src.server"],
                cwd=str(Path(__file__).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.running = True
            
            self.server_status_label.config(text="Status: Running", fg="#00c853")
            self.start_server_btn.config(state=DISABLED)
            self.stop_server_btn.config(state=NORMAL)
            
            self.log("Server started successfully on port 8080", "SUCCESS")
            self.log("Dashboard available at http://localhost:8080", "INFO")
            
            threading.Thread(target=self._monitor_server_output, daemon=True).start()
            
        except Exception as e:
            self.log(f"Failed to start server: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to start server: {e}")

    def _monitor_server_output(self):
        while self.running:
            if self.server_process:
                line = self.server_process.stdout.readline()
                if line:
                    self.log(line.strip(), "INFO")
                    
                if self.server_process.poll() is not None:
                    self.running = False
                    self.root.after(0, self._server_stopped)
                    break

    def _server_stopped(self):
        self.server_status_label.config(text="Status: Stopped", fg="#ff1744")
        self.start_server_btn.config(state=NORMAL)
        self.stop_server_btn.config(state=DISABLED)
        self.log("Server stopped", "WARNING")

    def stop_server(self):
        if self.server_process:
            self.log("Stopping server...", "WARNING")
            self.server_process.terminate()
            self.running = False
            
            try:
                self.server_process.wait(timeout=5)
            except:
                self.server_process.kill()
            
            self.log("Server stopped", "SUCCESS")
            self._server_stopped()

    def open_dashboard(self):
        webbrowser.open("http://localhost:8080")

    def start_client(self):
        self.log("Starting Client Application...", "INFO")
        
        try:
            self.client_process = subprocess.Popen(
                [sys.executable, "-m", "src.client", "--server", "http://localhost:8080"],
                cwd=str(Path(__file__).parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.client_status_label.config(text="Status: Running", fg="#00c853")
            self.start_client_btn.config(state=DISABLED)
            self.stop_client_btn.config(state=NORMAL)
            
            self.log("Client started successfully", "SUCCESS")
            
        except Exception as e:
            self.log(f"Failed to start client: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to start client: {e}")

    def stop_client(self):
        if self.client_process:
            self.log("Stopping client...", "WARNING")
            self.client_process.terminate()
            
            try:
                self.client_process.wait(timeout=5)
            except:
                self.client_process.kill()
            
            self.client_status_label.config(text="Status: Not Running", fg="#888")
            self.start_client_btn.config(state=NORMAL)
            self.stop_client_btn.config(state=DISABLED)
            self.log("Client stopped", "SUCCESS")

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            if self.server_process:
                self.stop_server()
            if self.client_process:
                self.stop_client()
            self.root.destroy()


def main():
    root = Tk()
    
    try:
        root.iconbitmap(default=None)
    except:
        pass
    
    app = NetworkMonitorLauncher(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
