from flask import Blueprint, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import os
import sys
import datetime
import csv
import io
from flask import Response

# Append parent dir
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger
from ai_model.detector import BehaviorDetector
from alerts.notifier import AlertNotifier

def verify_agent_key():
    expected_key = os.getenv('AGENT_API_KEY', 'default-agent-key')
    provided_key = request.headers.get('X-Agent-Key')
    return provided_key == expected_key

logger = setup_logger('backend_routes', 'backend.log')
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'sicherungx.db')
DIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dist')
STATIC_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'dashboard', 'static')

main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)

login_manager = LoginManager()

class User(UserMixin):
    def __init__(self, id, username, email, role, full_name, profile_picture):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.full_name = full_name
        self.profile_picture = profile_picture

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if user_row:
        return User(id=user_row['id'], username=user_row['username'], email=user_row['email'], role=user_row['role'], full_name=user_row['full_name'], profile_picture=user_row['profile_picture'])
    return None

try:
    detector = BehaviorDetector()
except Exception as e:
    logger.error(f"Failed to load AI detector: {e}")
    detector = None

try:
    notifier = AlertNotifier()
except Exception as e:
    logger.error(f"Failed to load Alert Notifier: {e}")
    notifier = None

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def log_audit(action, performed_by, target_user, details):
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO audit_logs (action, performed_by, target_user, details)
            VALUES (?, ?, ?, ?)
        ''', (action, performed_by, target_user, details))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
    finally:
        conn.close()

# --- Public Website Routes ---
@main_bp.route('/landing')
def landing():
    return render_template('public/home.html')

@main_bp.route('/agent')
def public_agent():
    return render_template('public/agent.html')

@main_bp.route('/about')
def about():
    return render_template('public/about.html')

@main_bp.route('/features')
def features():
    return render_template('public/features.html')

@main_bp.route('/support')
def support():
    return render_template('public/support.html')

@main_bp.route('/contact')
def contact():
    return render_template('public/contact.html')

@main_bp.route('/download/agent')
def download_agent():
    return send_from_directory(DIST_PATH, 'SicherungAgent.exe', as_attachment=True)

@main_bp.route('/robots.txt')
@main_bp.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(STATIC_PATH, request.path[1:])

# --- Authentication Routes ---
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user_row = conn.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username)).fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row['password_hash'], password):
            user = User(id=user_row['id'], username=user_row['username'], email=user_row['email'], role=user_row['role'], full_name=user_row['full_name'], profile_picture=user_row['profile_picture'])
            login_user(user)
            log_audit("LOGIN", user.username, user.username, "User logged into dashboard")
            if user.role == 'admin':
                return redirect(url_for('main.index'))
            else:
                return redirect(url_for('main.employee_dashboard'))
            
        return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    log_audit("LOGOUT", current_user.username, current_user.username, "User logged out")
    logout_user()
    return redirect(url_for('main.login'))

# --- Web Interface Routes ---
@main_bp.route('/')
@login_required
def index():
    if current_user.role != 'admin': return redirect(url_for('main.employee_dashboard'))
    return render_template('index.html')

@main_bp.route('/users')
@login_required
def users_page():
    if current_user.role != 'admin': return redirect('/')
    return render_template('users.html')

@main_bp.route('/alerts')
@login_required
def alerts_page():
    if current_user.role != 'admin': return redirect('/')
    return render_template('alerts.html')

@main_bp.route('/audit')
@login_required
def audit_page():
    if current_user.role != 'admin': return redirect('/')
    return render_template('audit_logs.html')

@main_bp.route('/user/<identifier>')
@login_required
def user_detail_page(identifier):
    if current_user.role != 'admin': return redirect('/')
    return render_template('user_detail.html', username=identifier)

@main_bp.route('/admin/settings')
@login_required
def admin_settings_page():
    if current_user.role != 'admin': return redirect('/')
    conn = get_db_connection()
    settings_rows = conn.execute("SELECT key, value FROM system_settings").fetchall()
    conn.close()
    settings = {row['key']: row['value'] for row in settings_rows}
    return render_template('admin_settings.html', settings=settings)

@main_bp.route('/admin/manage-users')
@login_required
def manage_users_page():
    if current_user.role != 'admin': return redirect('/')
    return render_template('manage_users.html')

@main_bp.route('/employee_dashboard')
@login_required
def employee_dashboard():
    return render_template('employee_index.html')

# --- API Routes for Dashboard Data ---
@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    conn = get_db_connection()
    users_count = conn.execute("SELECT COUNT(DISTINCT username) FROM activity_logs").fetchone()[0]
    alerts_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    alerts_today = conn.execute("SELECT COUNT(*) FROM alerts WHERE date(timestamp) = date('now')").fetchone()[0]
    
    # Risk distribution
    low_risk = conn.execute("SELECT COUNT(*) FROM activity_logs WHERE risk_score < 30").fetchone()[0]
    med_risk = conn.execute("SELECT COUNT(*) FROM activity_logs WHERE risk_score >= 30 AND risk_score < 70").fetchone()[0]
    high_risk = conn.execute("SELECT COUNT(*) FROM activity_logs WHERE risk_score >= 70").fetchone()[0]
    
    # Active devices (seen in last 30 seconds)
    active_devices = conn.execute("SELECT COUNT(*) FROM devices WHERE (julianday('now') - julianday(last_seen)) * 86400 < 30").fetchone()[0]
    
    # Most active users
    most_active = conn.execute("SELECT username, COUNT(*) as count FROM activity_logs GROUP BY username ORDER BY count DESC LIMIT 5").fetchall()
    
    # High risk users
    high_risk_users = conn.execute("SELECT username, MAX(risk_score) as max_risk FROM activity_logs GROUP BY username HAVING max_risk >= 70 ORDER BY max_risk DESC LIMIT 5").fetchall()

    conn.close()
    return jsonify({
        'total_users': users_count,
        'total_alerts': alerts_count,
        'alerts_today': alerts_today,
        'active_devices': active_devices,
        'risk_distribution': [low_risk, med_risk, high_risk],
        'most_active_users': [dict(m) for m in most_active],
        'high_risk_users': [dict(h) for h in high_risk_users]
    })

@api_bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    conn = get_db_connection()
    logs = conn.execute("SELECT id, timestamp || 'Z' as timestamp, username, device_id, activity_type, details, risk_score, is_anomaly FROM activity_logs ORDER BY timestamp DESC LIMIT 200").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in logs])

@api_bp.route('/logs/export', methods=['GET'])
@login_required
def export_logs():
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    logs = conn.execute("SELECT id, timestamp || 'Z' as timestamp, username, device_id, activity_type, details, risk_score, is_anomaly FROM activity_logs ORDER BY timestamp DESC LIMIT 1000").fetchall()
    conn.close()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Timestamp', 'Username', 'Device ID', 'Activity Type', 'Details', 'Risk Score', 'Is Anomaly'])
    for log in logs:
        cw.writerow([log['id'], log['timestamp'], log['username'], log['device_id'], log['activity_type'], log['details'], log['risk_score'], log['is_anomaly']])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=sicherungx_logs.csv"}
    )

@api_bp.route('/alerts/data', methods=['GET'])
@login_required
def get_alerts_data():
    conn = get_db_connection()
    alerts = conn.execute("SELECT id, timestamp || 'Z' as timestamp, username, device_id, activity_type, risk_score, alert_status FROM alerts ORDER BY timestamp DESC LIMIT 100").fetchall()
    conn.close()
    
    # Mark as read (simple approach: update all to 'Viewed' upon fetching)
    if current_user.role == 'admin':
        conn = get_db_connection()
        conn.execute("UPDATE alerts SET alert_status = 'Viewed' WHERE alert_status = 'Triggered'")
        conn.commit()
        conn.close()
        
    return jsonify([dict(ix) for ix in alerts])

@api_bp.route('/alerts/unread-count', methods=['GET'])
@login_required
def get_unread_alerts():
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) FROM alerts WHERE alert_status = 'Triggered'").fetchone()[0]
    conn.close()
    return jsonify({'count': count})

@api_bp.route('/audit-logs', methods=['GET'])
@login_required
def get_audit_logs():
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    logs = conn.execute("SELECT id, timestamp || 'Z' as timestamp, action, performed_by, target_user, details FROM audit_logs ORDER BY timestamp DESC LIMIT 200").fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in logs])

# --- Admin APIs ---
@api_bp.route('/users', methods=['GET'])
@login_required
def get_users():
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    
    query = """
    SELECT u.id, u.username, u.email, u.role, u.full_name, u.profile_picture, u.created_at || 'Z' as created_at,
           d.last_seen || 'Z' as last_seen
    FROM users u
    LEFT JOIN devices d ON u.id = d.user_id AND d.id = (SELECT MAX(id) FROM devices WHERE user_id = u.id)
    """
    users = conn.execute(query).fetchall()
    
    now = datetime.datetime.utcnow()
    res = []
    for u in users:
        udict = dict(u)
        status = 'offline'
        if u['last_seen']:
            try:
                last_seen_dt = datetime.datetime.strptime(u['last_seen'].replace('Z', ''), '%Y-%m-%d %H:%M:%S')
                if (now - last_seen_dt).total_seconds() < 30: # 30 seconds threshold
                    status = 'active'
            except:
                pass
        udict['status'] = status
        res.append(udict)

    conn.close()
    return jsonify(res)

@api_bp.route('/create-user', methods=['POST'])
@login_required
def create_user():
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    username = data.get('username')
    email = data.get('email')
    full_name = data.get('full_name')
    password = data.get('password')
    role = data.get('role', 'employee')
    
    if not all([username, password]):
        return jsonify({'error': 'Username and password are required'}), 400
        
    try:
        conn = get_db_connection()
        hashed_pw = generate_password_hash(password)
        conn.execute('''
            INSERT INTO users (username, email, password_hash, role, full_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, hashed_pw, role, full_name))
        conn.commit()
        conn.close()
        
        log_audit("CREATE_USER", current_user.username, username, f"Created {role} account")
        return jsonify({'status': 'success'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/make-admin', methods=['POST'])
@login_required
def make_admin():
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    user_id = data.get('id')
    
    conn = get_db_connection()
    target_user = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    if target_user:
        log_audit("PROMOTE_ADMIN", current_user.username, target_user['username'], "Promoted to admin")
        
    return jsonify({'status': 'success'})

@api_bp.route('/remove-admin', methods=['POST'])
@login_required
def remove_admin():
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    user_id = data.get('id')
    if user_id == current_user.id:
        return jsonify({'error': 'Cannot remove yourself'}), 400
        
    conn = get_db_connection()
    target_user = conn.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.execute("UPDATE users SET role = 'employee' WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    
    if target_user:
        log_audit("REMOVE_ADMIN", current_user.username, target_user['username'], "Removed admin privileges")
        
    return jsonify({'status': 'success'})

@api_bp.route('/user/<identifier>', methods=['GET'])
@login_required
def get_user_profile(identifier):
    conn = get_db_connection()
    if identifier.isdigit():
        user = conn.execute("SELECT id, username, email, role, full_name, profile_picture, created_at || 'Z' as created_at FROM users WHERE id = ?", (int(identifier),)).fetchone()
    else:
        user = conn.execute("SELECT id, username, email, role, full_name, profile_picture, created_at || 'Z' as created_at FROM users WHERE username = ?", (identifier,)).fetchone()
        
    if not user:
        conn.close()
        return jsonify({'error': 'Not found'}), 404
        
    user_id = user['id']
    if current_user.role != 'admin' and current_user.id != user_id:
        conn.close()
        return jsonify({'error': 'Unauthorized'}), 403
    
    devices = conn.execute("SELECT device_id, device_name, ip_address, os_info, system_username, is_blocked, last_seen || 'Z' as last_seen FROM devices WHERE user_id = ?", (user_id,)).fetchall()
    logs = conn.execute("SELECT id, timestamp || 'Z' as timestamp, activity_type, details, risk_score, is_anomaly FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 50", (user['username'],)).fetchall()
    recent_risk = conn.execute("SELECT AVG(risk_score) FROM (SELECT risk_score FROM activity_logs WHERE username = ? ORDER BY timestamp DESC LIMIT 20)", (user['username'],)).fetchone()[0]
    
    conn.close()
    
    now = datetime.datetime.utcnow()
    status = 'offline'
    last_active = None
    for d in devices:
        if d['last_seen']:
            if not last_active or d['last_seen'] > last_active:
                last_active = d['last_seen']
            try:
                last_seen_dt = datetime.datetime.strptime(d['last_seen'].replace('Z', ''), '%Y-%m-%d %H:%M:%S')
                if (now - last_seen_dt).total_seconds() < 30: # 30 seconds threshold
                    status = 'active'
            except:
                pass
    
    return jsonify({
        'profile': dict(user),
        'devices': [dict(d) for d in devices],
        'logs': [dict(l) for l in logs],
        'overall_risk_score': round(recent_risk, 2) if recent_risk else 0.0,
        'last_active': last_active,
        'status': status
    })

@api_bp.route('/device/<device_id>/block', methods=['POST'])
@login_required
def block_device(device_id):
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    conn.execute("UPDATE devices SET is_blocked = 1 WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()
    log_audit("ISOLATE_DEVICE", current_user.username, device_id, f"Administratively blocked device")
    return jsonify({'status': 'success'})

@api_bp.route('/device/<device_id>/unblock', methods=['POST'])
@login_required
def unblock_device(device_id):
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    conn = get_db_connection()
    conn.execute("UPDATE devices SET is_blocked = 0 WHERE device_id = ?", (device_id,))
    conn.commit()
    conn.close()
    log_audit("UNBLOCK_DEVICE", current_user.username, device_id, f"Administratively unblocked device")
    return jsonify({'status': 'success'})

@api_bp.route('/update-profile', methods=['PUT'])
@login_required
def update_profile():
    data = request.json
    full_name = data.get('full_name')
    password = data.get('password')
    
    conn = get_db_connection()
    try:
        if full_name:
            conn.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, current_user.id))
        if password:
            hashed = generate_password_hash(password)
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed, current_user.id))
        conn.commit()
        log_audit("PROFILE_UPDATE", current_user.username, current_user.username, "User updated their profile")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/settings', methods=['PUT'])
@login_required
def update_settings():
    if current_user.role != 'admin': return jsonify({'error': 'Unauthorized'}), 403
    data = request.json
    conn = get_db_connection()
    try:
        for key, value in data.items():
            conn.execute("UPDATE system_settings SET value = ? WHERE key = ?", (value, key))
        conn.commit()
        log_audit("SETTINGS_UPDATE", current_user.username, "SYSTEM", f"Updated system settings: {list(data.keys())}")
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# --- Agent APIs ---
@api_bp.route('/agent/login', methods=['POST'])
def agent_login():
    """Agent authentication and device binding"""
    if not verify_agent_key():
        return jsonify({'error': 'Unauthorized Agent Key'}), 401
        
    data = request.json
    username = data.get('username')
    password = data.get('password')
    device_id = data.get('device_id')
    device_name = data.get('device_name')
    ip_address = data.get('ip_address')
    os_info = data.get('os_info')
    system_username = data.get('system_username')
    
    if not all([username, password, device_id]):
        return jsonify({'error': 'Missing credentials or device info'}), 400

    conn = get_db_connection()
    user_row = conn.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username)).fetchone()
    
    if user_row and check_password_hash(user_row['password_hash'], password):
        user_id = user_row['id']
        actual_username = user_row['username']
        
        existing_device = conn.execute("SELECT id, is_blocked FROM devices WHERE device_id = ?", (device_id,)).fetchone()
        if existing_device:
            if existing_device['is_blocked'] == 1:
                conn.close()
                return jsonify({'error': 'Device is blocked by administrator.'}), 403

            conn.execute('''
                UPDATE devices 
                SET user_id = ?, device_name = ?, ip_address = ?, os_info = ?, system_username = ?, last_seen = datetime('now')
                WHERE device_id = ?
            ''', (user_id, device_name, ip_address, os_info, system_username, device_id))
        else:
            conn.execute('''
                INSERT INTO devices (user_id, device_id, device_name, ip_address, os_info, system_username)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, device_id, device_name, ip_address, os_info, system_username))
            
        conn.commit()
        conn.close()
        
        log_audit("DEVICE_BIND", actual_username, actual_username, f"Bound device {device_name} ({ip_address})")
        
        return jsonify({
            'status': 'success',
            'token': 'mock-agent-jwt',
            'username': actual_username
        })
        
    conn.close()
    return jsonify({'error': 'Invalid credentials'}), 401

@api_bp.route('/agent/submit', methods=['POST'])
def receive_agent_data():
    """Endpoint for remote agents to submit logs and get analyzed in real-time."""
    if not verify_agent_key():
        return jsonify({'error': 'Unauthorized Agent Key'}), 401

    # Data is queued by agent if offline, so this can receive an array or a single object.
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    if not isinstance(data, list):
        data = [data] # Make single log into list
        
    try:
        conn = get_db_connection()
        command = 'none'
        
        for item in data:
            username = item.get('username')
            device_id = item.get('device_id')
            activity_type = item.get('activity_type')
            details = item.get('details')
            files_accessed = item.get('files_accessed', 0)
            data_transfer_mb = item.get('data_transfer_mb', 0.0)
            
            agent_ts = item.get('timestamp') 
            
            if not username or not device_id:
                continue

            # Update device last_seen and check block status
            dev = conn.execute("SELECT is_blocked FROM devices WHERE device_id = ?", (device_id,)).fetchone()
            if dev:
                if dev['is_blocked'] == 1:
                    command = 'isolate'
                conn.execute("UPDATE devices SET last_seen = datetime('now') WHERE device_id = ?", (device_id,))
            
            if activity_type == 'HEARTBEAT':
                continue # Just needed to update last_seen

            is_anomaly = 0
            risk_score = 0.0
            
            # Calculate features
            one_hour_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
            one_hour_ago_str = one_hour_ago.strftime('%Y-%m-%d %H:%M:%S')
            
            f_row = conn.execute("SELECT SUM(files_accessed) FROM activity_logs WHERE username=? AND timestamp >= ?", (username, one_hour_ago_str)).fetchone()[0]
            total_files = (f_row if f_row else 0) + files_accessed
            
            d_row = conn.execute("SELECT SUM(data_transfer_mb) FROM activity_logs WHERE username=? AND timestamp >= ?", (username, one_hour_ago_str)).fetchone()[0]
            total_data = (d_row if d_row else 0.0) + data_transfer_mb
            
            u_row = conn.execute("SELECT COUNT(*) FROM activity_logs WHERE username=? AND activity_type LIKE 'USB%' AND timestamp >= ?", (username, one_hour_ago_str)).fetchone()[0]
            total_usb = (u_row if u_row else 0)
            if activity_type and activity_type.startswith('USB'):
                total_usb += 1
            
            if detector:
                hour_of_day = datetime.datetime.now().hour
                is_anomaly, risk_score = detector.analyze(total_files, total_data, total_usb, hour_of_day)

            # Insert into logs
            if agent_ts:
                conn.execute('''
                    INSERT INTO activity_logs (timestamp, username, device_id, activity_type, details, files_accessed, data_transfer_mb, risk_score, is_anomaly)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (agent_ts, username, device_id, activity_type, details, files_accessed, data_transfer_mb, risk_score, is_anomaly))
            else:
                conn.execute('''
                    INSERT INTO activity_logs (username, device_id, activity_type, details, files_accessed, data_transfer_mb, risk_score, is_anomaly)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (username, device_id, activity_type, details, files_accessed, data_transfer_mb, risk_score, is_anomaly))
            
            # Generate Alert
            if risk_score > 70.0:
                conn.execute('''
                    INSERT INTO alerts (username, device_id, activity_type, risk_score, alert_status)
                    VALUES (?, ?, ?, ?, ?)
                ''', (username, device_id, activity_type, risk_score, 'Triggered'))
                
                if notifier:
                    try:
                        notifier.send_alert(username, activity_type, risk_score)
                    except Exception as e:
                        logger.error(f"Notifier failed: {e}")

        conn.commit()
        conn.close()
        return jsonify({'status': 'success', 'command': command}), 201
    except Exception as e:
        logger.error(f"Error processing agent data: {e}")
        return jsonify({'error': 'Database error'}), 500
