import psutil
import time
import threading
import sqlite3
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

logger = setup_logger('system_monitor', 'agent.log')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'sicherungx.db')

class NetworkMonitor(threading.Thread):
    def __init__(self, user_name, device_id):
        super().__init__()
        self.user_name = user_name
        self.device_id = device_id
        self.daemon = True
        self.running = True
        
    def log_to_db(self, data_transfer_mb):
        import requests
        try:
            payload = {
                'username': self.user_name,
                'device_id': self.device_id,
                'activity_type': 'NETWORK_ACTIVITY',
                'details': f"Transferred {data_transfer_mb:.2f} MB in the last minute",
                'files_accessed': 0,
                'data_transfer_mb': data_transfer_mb
            }
            response = requests.post('http://127.0.0.1:5000/api/agent/submit', json=payload)
            if response.status_code != 201:
                logger.error(f"Failed to log Network activity via API: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"API Error in Network Monitor: {e}")

    def run(self):
        logger.info("Starting Network Monitor...")
        # Get initial network IO counters
        io_start = psutil.net_io_counters()
        
        while self.running:
            time.sleep(60) # Check every 60 seconds
            io_end = psutil.net_io_counters()
            
            bytes_sent = io_end.bytes_sent - io_start.bytes_sent
            bytes_recv = io_end.bytes_recv - io_start.bytes_recv
            
            total_mb = (bytes_sent + bytes_recv) / (1024 * 1024)
            
            if total_mb > 1.0: # Log only if transfer is greater than 1 MB
                self.log_to_db(total_mb)
                logger.info(f"Logged {total_mb:.2f} MB network transfer for {self.user_name}")
                
            io_start = io_end

    def stop(self):
        self.running = False
