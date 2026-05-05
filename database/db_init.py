import sqlite3
import os
import logging
from werkzeug.security import generate_password_hash

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), 'sicherungx.db')

def init_db():
    """Initializes the SQLite database with required tables."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create activity_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now')),
                username TEXT,
                device_id TEXT,
                activity_type TEXT,
                details TEXT,
                files_accessed INTEGER DEFAULT 0,
                data_transfer_mb REAL DEFAULT 0.0,
                risk_score REAL DEFAULT 0.0,
                is_anomaly INTEGER DEFAULT 0
            )
        ''')

        # Create alerts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now')),
                username TEXT,
                device_id TEXT,
                activity_type TEXT,
                risk_score REAL,
                alert_status TEXT
            )
        ''')

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'employee',
                full_name TEXT,
                profile_picture TEXT,
                created_at DATETIME DEFAULT (datetime('now'))
            )
        ''')

        # Create devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                device_id TEXT UNIQUE,
                device_name TEXT,
                ip_address TEXT,
                os_info TEXT,
                system_username TEXT,
                last_seen DATETIME DEFAULT (datetime('now')),
                status TEXT DEFAULT 'active',
                is_blocked INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Create audit_logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now')),
                action TEXT,
                performed_by TEXT,
                target_user TEXT,
                details TEXT
            )
        ''')

        # Create system_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT UNIQUE PRIMARY KEY,
                value TEXT
            )
        ''')

        # Insert default admin user ('admin', 'password')
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='admin'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin', 'admin@sicherungx.com', generate_password_hash('password'), 'admin', 'System Administrator'))

        # Insert a sample employee user ('employee', 'password')
        cursor.execute("SELECT COUNT(*) FROM users WHERE username='employee'")
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, role, full_name)
                VALUES (?, ?, ?, ?, ?)
            ''', ('employee', 'employee@sicherungx.com', generate_password_hash('password'), 'employee', 'Test Employee'))

        # Ensure is_blocked exists for legacy databases
        try:
            cursor.execute("ALTER TABLE devices ADD COLUMN is_blocked INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # Column already exists


        conn.commit()
        logger.info(f"Database initialized successfully at {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    init_db()
