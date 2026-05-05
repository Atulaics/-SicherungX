import sys
import os
import time
import socket
import platform
import uuid
import requests
import datetime
import tkinter as tk
from tkinter import messagebox
from threading import Thread, Lock

# Ensure backend imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger
from agent.usb_monitor import USBMonitor
from agent.file_monitor import FileMonitor
from agent.system_monitor import NetworkMonitor

logger = setup_logger('agent_main', 'agent.log')
API_URL = "http://127.0.0.1:5000/api/agent"

# Global Queue for reliability
log_queue = []
queue_lock = Lock()

def queue_log(activity_type, details, username, device_id, files_accessed=0, data_mb=0.0):
    """Safely append to local queue with timestamp"""
    with queue_lock:
        log_queue.append({
            "timestamp": datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            "username": username,
            "device_id": device_id,
            "activity_type": activity_type,
            "details": details,
            "files_accessed": files_accessed,
            "data_transfer_mb": data_mb
        })

# Override log_to_db methods on the imported classes
# This avoids needing to rewrite all 3 monitor files fully.
def usb_log_override(self, activity_type, details):
    queue_log(activity_type, details, self.user_name, self.device_id)
USBMonitor.log_to_db = usb_log_override

def file_log_override(self, files_accessed):
    queue_log('FILE_ACTIVITY', f"Accessed {files_accessed} files in the last minute", self.user_name, self.device_id, files_accessed=files_accessed)
FileMonitor.log_to_db = file_log_override

def net_log_override(self, data_transfer_mb):
    queue_log('NETWORK_ACTIVITY', f"Transferred {data_transfer_mb:.2f} MB in the last minute", self.user_name, self.device_id, data_mb=data_transfer_mb)
NetworkMonitor.log_to_db = net_log_override


class AgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SicherungX Agent - Login")
        self.root.geometry("400x520")
        self.root.configure(bg="#0f172a")
        
        self.device_id = str(uuid.getnode()) # MAC address as simple device ID
        self.device_name = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.device_name)
        self.os_info = f"{platform.system()} {platform.release()}"
        self.system_username = os.getlogin()

        self.setup_ui()

    def setup_ui(self):
        # Header
        tk.Label(self.root, text="SicherungX", font=("Inter", 24, "bold"), fg="#38bdf8", bg="#0f172a").pack(pady=(40, 5))
        tk.Label(self.root, text="Endpoint Security Agent", font=("Inter", 10), fg="#94a3b8", bg="#0f172a").pack(pady=(0, 30))

        # Server URL
        tk.Label(self.root, text="Server Address", font=("Inter", 10), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=40)
        self.server_var = tk.StringVar(value="https://sicherungx.onrender.com")
        tk.Entry(self.root, textvariable=self.server_var, font=("Inter", 12), bg="#1e293b", fg="white", insertbackground="white").pack(fill="x", padx=40, pady=(5, 15), ipady=5)

        # Credentials
        tk.Label(self.root, text="Email or Username", font=("Inter", 10), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=40)
        self.username_var = tk.StringVar()
        tk.Entry(self.root, textvariable=self.username_var, font=("Inter", 12), bg="#1e293b", fg="white", insertbackground="white").pack(fill="x", padx=40, pady=(5, 15), ipady=5)

        tk.Label(self.root, text="Password", font=("Inter", 10), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", padx=40)
        self.password_var = tk.StringVar()
        tk.Entry(self.root, textvariable=self.password_var, show="*", font=("Inter", 12), bg="#1e293b", fg="white", insertbackground="white").pack(fill="x", padx=40, pady=(5, 20), ipady=5)

        # Login button
        self.btn = tk.Button(self.root, text="Connect Device", font=("Inter", 12, "bold"), bg="#0ea5e9", fg="white", activebackground="#0284c7", activeforeground="white", command=self.do_login)
        self.btn.pack(fill="x", padx=40, pady=10, ipady=5)

    def do_login(self):
        username = self.username_var.get()
        password = self.password_var.get()
        server_url = self.server_var.get().strip().rstrip('/')
        
        if not username or not password or not server_url:
            messagebox.showerror("Error", "Please enter all fields")
            return
            
        self.btn.config(text="Connecting...", state="disabled")
        
        # Async login
        def login_task():
            global API_URL
            API_URL = f"{server_url}/api/agent"
            try:
                headers = {'X-Agent-Key': 'my-agent-key-123'}
                res = requests.post(f"{API_URL}/login", json={
                    "username": username,
                    "password": password,
                    "device_id": self.device_id,
                    "device_name": self.device_name,
                    "ip_address": self.ip_address,
                    "os_info": self.os_info,
                    "system_username": self.system_username
                }, headers=headers, timeout=5)
                
                if res.status_code == 200:
                    data = res.json()
                    self.root.after(0, self.on_login_success, data['username'])
                else:
                    self.root.after(0, lambda: self.on_login_fail("Invalid credentials"))
            except Exception as e:
                self.root.after(0, lambda: self.on_login_fail("Cannot connect to server"))
                
        Thread(target=login_task, daemon=True).start()

    def on_login_fail(self, msg):
        messagebox.showerror("Login Failed", msg)
        self.btn.config(text="Connect Device", state="normal")

    def on_login_success(self, registered_username):
        messagebox.showinfo("Success", "Device securely bound. Monitoring will run in the background.")
        self.root.withdraw() # Hide window
        self.start_monitoring(registered_username)

    def start_monitoring(self, username):
        logger.info(f"Agent logged in as {username}. Starting monitors...")
        
        usb_mon = USBMonitor(user_name=username, device_id=self.device_id)
        
        paths = ["C:\\Users\\Public\\Documents"]
        file_mon = FileMonitor(user_name=username, device_id=self.device_id, paths_to_watch=paths)
        
        net_mon = NetworkMonitor(user_name=username, device_id=self.device_id)

        usb_mon.start()
        file_mon.start()
        net_mon.start()

        # Heartbeat & Flush loop (Every 15 seconds)
        def heartbeat_and_flush():
            while True:
                time.sleep(15)
                queue_log("HEARTBEAT", "Device active", username, self.device_id)
                
                # Fetch current queue and clear it safely
                with queue_lock:
                    if not log_queue:
                        continue
                    payload = list(log_queue)
                    log_queue.clear()
                
                try:
                    headers = {'X-Agent-Key': 'my-agent-key-123'}
                    res = requests.post(f"{API_URL}/submit", json=payload, headers=headers, timeout=10)
                    if res.status_code == 201:
                        data = res.json()
                        if data.get('command') == 'isolate':
                            # Lock Workstation immediately
                            import ctypes
                            ctypes.windll.user32.LockWorkStation()
                            
                            # Show an uncloseable isolation screen
                            self.root.after(0, self.show_isolated_screen)
                    else:
                        # If failed, put them back
                        logger.warning(f"Server rejected logs (Code {res.status_code}). Putting back in queue.")
                        with queue_lock:
                            log_queue.extend(payload)
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Connection failed, queuing logs for later: {e}")
                    with queue_lock:
                        log_queue.extend(payload)
                    
        Thread(target=heartbeat_and_flush, daemon=True).start()

    def show_isolated_screen(self):
        self.root.deiconify()
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.configure(bg="#7f1d1d")
        
        for widget in self.root.winfo_children():
            widget.destroy()
            
        tk.Label(self.root, text="DEVICE ISOLATED", font=("Inter", 48, "bold"), fg="white", bg="#7f1d1d").pack(expand=True)
        tk.Label(self.root, text="Administrators have disabled this endpoint due to a severe security violation.", font=("Inter", 16), fg="#fca5a5", bg="#7f1d1d").pack(pady=20)
        
if __name__ == "__main__":
    # If the user provides a flag --hidden, don't show UI
    # In a real scenario, the service would auto-start hidden using saved credentials.
    root = tk.Tk()
    app = AgentApp(root)
    root.mainloop()
