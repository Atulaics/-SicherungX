import sqlite3
import os

db_path = os.path.join('database', 'sicherungx.db')
conn = sqlite3.connect(db_path)
conn.execute('CREATE TABLE IF NOT EXISTS system_settings (key TEXT PRIMARY KEY, value TEXT)')
conn.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES ("org_name", "SicherungX Enterprise")')
conn.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES ("timezone", "UTC")')
conn.execute('INSERT OR IGNORE INTO system_settings (key, value) VALUES ("alert_sensitivity", "Medium")')
conn.commit()
conn.close()
print('Settings table created.')
