import sqlite3

conn = sqlite3.connect('database/sicherungx.db')
conn.row_factory = sqlite3.Row

try:
    user = conn.execute("SELECT id, username, email, role, full_name, profile_picture, created_at || 'Z' as created_at FROM users WHERE id = 3").fetchone()
    print('User:', dict(user))
    
    devices = conn.execute("SELECT device_id, device_name, ip_address, os_info, system_username, is_blocked, last_seen || 'Z' as last_seen FROM devices WHERE user_id = 3").fetchall()
    print('Devices:', [dict(d) for d in devices])
    
    logs = conn.execute("SELECT id, timestamp || 'Z' as timestamp, activity_type, details, risk_score, is_anomaly FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 50", (user['username'],)).fetchall()
    print('Logs:', len(logs))
    
    recent_risk = conn.execute("SELECT AVG(risk_score) FROM (SELECT risk_score FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 20)", (user['username'],)).fetchone()[0]
    print('Risk:', recent_risk)
except Exception as e:
    import traceback
    traceback.print_exc()
