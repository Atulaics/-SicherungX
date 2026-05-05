import os
import time
import threading
import sqlite3
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

logger = setup_logger('file_monitor', 'agent.log')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'sicherungx.db')

class SensitiveFileHandler(FileSystemEventHandler):
    def __init__(self, user_name):
        self.user_name = user_name
        self.files_accessed = 0
        self.lock = threading.Lock()
    
    def on_modified(self, event):
        if not event.is_directory:
            with self.lock:
                self.files_accessed += 1

    def on_created(self, event):
        if not event.is_directory:
            with self.lock:
                self.files_accessed += 1

    def reset_counter(self):
        with self.lock:
            count = self.files_accessed
            self.files_accessed = 0
            return count

class FileMonitor(threading.Thread):
    def __init__(self, user_name, device_id, paths_to_watch):
        super().__init__()
        self.user_name = user_name
        self.device_id = device_id
        self.paths_to_watch = paths_to_watch
        self.daemon = True
        self.running = True
        self.handler = SensitiveFileHandler(user_name)
        self.observer = Observer()
        
    def log_to_db(self, files_accessed):
        import requests
        try:
            payload = {
                'username': self.user_name,
                'device_id': self.device_id,
                'activity_type': 'FILE_ACTIVITY',
                'details': f"Accessed {files_accessed} files in the last minute",
                'files_accessed': files_accessed,
                'data_transfer_mb': 0.0
            }
            response = requests.post('http://127.0.0.1:5000/api/agent/submit', json=payload)
            if response.status_code != 201:
                logger.error(f"Failed to log File activity via API: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"API Error in File Monitor: {e}")

    def run(self):
        logger.info(f"Starting File Monitor on paths: {self.paths_to_watch}")
        for path in self.paths_to_watch:
            if os.path.exists(path):
                self.observer.schedule(self.handler, path, recursive=True)
            else:
                logger.warning(f"Path does not exist to monitor: {path}")
        
        self.observer.start()
        
        while self.running:
            time.sleep(60) # Log activity every 60 seconds
            count = self.handler.reset_counter()
            if count > 0:
                self.log_to_db(count)
                logger.info(f"Logged {count} file operations for {self.user_name}")
                
        self.observer.stop()
        self.observer.join()

    def stop(self):
        self.running = False
