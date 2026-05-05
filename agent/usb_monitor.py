import wmi
import pythoncom
import time
import threading
import sqlite3
import os
import sys

# Add the parent directory to sys.path so we can import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

logger = setup_logger('usb_monitor', 'agent.log')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'sicherungx.db')

class USBMonitor(threading.Thread):
    def __init__(self, user_name, device_id):
        super().__init__()
        self.user_name = user_name
        self.device_id = device_id
        self.daemon = True
        self.running = True

    def log_to_db(self, activity_type, details):
        import requests
        try:
            payload = {
                'username': self.user_name,
                'device_id': self.device_id,
                'activity_type': activity_type,
                'details': details,
                'files_accessed': 0,
                'data_transfer_mb': 0.0
            }
            # Adjust the URL if the backend runs on a different host/port
            response = requests.post('http://127.0.0.1:5000/api/agent/submit', json=payload)
            if response.status_code == 201:
                logger.info(f"Logged USB activity: {activity_type} - {details}")
            else:
                logger.error(f"Failed to log USB activity via API: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"API Error in USB Monitor: {e}")

    def run(self):
        logger.info("Starting USB Monitor...")
        # We need to initialize COM for this thread
        pythoncom.CoInitialize()
        c = wmi.WMI()
        
        # WMI query to watch for device creation (insertion)
        insertion_watcher = c.Win32_DeviceChangeEvent.watch_for(EventType=2)
        # WMI query to watch for device deletion (removal)
        removal_watcher = c.Win32_DeviceChangeEvent.watch_for(EventType=3)

        # To avoid blocking forever on one watcher, we will use a polling loop
        # But python WMI watcher blocks until event. For simplicity and reliability
        # in a single thread, we poll the Win32_LogicalDisk instead or use short timeouts.
        # However, a simple approach is to keep track of current drives.
        
        current_drives = self.get_removable_drives()
        
        while self.running:
            time.sleep(2)
            new_drives = self.get_removable_drives()
            
            # Check for inserted
            for drive in new_drives:
                if drive not in current_drives:
                    details = f"USB Drive Inserted: {drive}"
                    self.log_to_db("USB_INSERTED", details)
            
            # Check for removed
            for drive in current_drives:
                if drive not in new_drives:
                    details = f"USB Drive Removed: {drive}"
                    self.log_to_db("USB_REMOVED", details)
            
            current_drives = new_drives

        pythoncom.CoUninitialize()

    def get_removable_drives(self):
        # 2 means Removable Disk
        c = wmi.WMI()
        drives = set()
        for disk in c.Win32_LogicalDisk(DriveType=2):
            drives.add(disk.DeviceID)
        return drives

    def stop(self):
        self.running = False
