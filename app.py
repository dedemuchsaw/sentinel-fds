import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from arango import ArangoClient
from werkzeug.security import check_password_hash
from functools import wraps
from flask_socketio import SocketIO
from database.redis_client import get_redis_client
import json

app = Flask(__name__)
# Gunakan key statis dulu agar session gak reset tiap kali venv restart
app.secret_key = 'sentinel_dev_key_2026'

# --- SOCKET.IO INITIALIZATION ---
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins="*")

# --- REDIS LISTENER ---
redis_client = get_redis_client()

def background_redis_listener():
    """ Runs in background, listens for fraud alerts from Redis, pushes to WebSocket """
    print("[SYSTEM] Starting Redis Background Listener...")
    if not redis_client:
        print("[SYSTEM CRITICAL] Redis not available, listener disabled.")
        return

    pubsub = redis_client.pubsub()
    pubsub.subscribe('alerts_channel')

    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                alert_data = json.loads(message['data'])
                print(f"[WEBSOCKET] Emitting new alert: {alert_data['tx_id']}")
                # Push data ke semua klien yang connect ke dashboard
                socketio.emit('new_fraud_alert', alert_data)
            except Exception as e:
                print(f"[WEBSOCKET ERROR] Could not emit alert: {e}")

# --- DATABASE INITIALIZATION ---
client = ArangoClient(hosts='http://127.0.0.1:8529')

try:
    db = client.db('sentinel_fds', username='root', password='123123#')
except Exception as e:
    print(f"CRITICAL: Database Connection Error: {e}")
    db = None

# --- AUTH DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- ROUTES ---

@app.route('/')
def login():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/auth', methods=['POST'])
def auth():
    username = request.form.get('username')
    password = request.form.get('password')

    # Log untuk memantau trafik masuk di terminal
    print(f"\n[AUTH ATTEMPT] User: {username}")

    if not username or not password or not db:
        print("[AUTH ERROR] Missing input or DB connection down")
        flash("System error or invalid input.")
        return redirect(url_for('login'))

    try:
        # Mencari user dengan key admin_username sesuai setup_rbac.py
        user_key = f"admin_{username}"
        user = db.collection('users').get(user_key)

        if user:
            print(f"[AUTH INFO] User found in ArangoDB: {user_key}")
            
            # Verifikasi password
            if check_password_hash(user['password'], password):
                # AQL Query untuk ambil Role dari Graph
                query = "FOR r IN 1..1 OUTBOUND @user_id has_role RETURN r._key"
                cursor = db.aql.execute(query, bind_vars={'user_id': user['_id']})
                roles = [doc for doc in cursor]

                print(f"[AUTH SUCCESS] Verified Roles: {roles}")

                # Set session data
                session['user'] = username
                session['full_name'] = user.get('full_name', 'Security Officer')
                session['roles'] = roles
                return redirect(url_for('dashboard'))
            else:
                print("[AUTH FAIL] Password mismatch")
        else:
            print(f"[AUTH FAIL] User key {user_key} not found")

        flash("Invalid Access Key or Token.")
    except Exception as e:
        print(f"[AUTH CRITICAL] Exception: {e}")
        flash("Connectivity issue with the Auth Engine.")

    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Menyiapkan statistik simulasi untuk Fraud Detection Engine
    stats = {
        "total_scanned": 1250,
        "high_risk": 12,
        "pending_review": 5,
        "iso_messages": 842 
    }

    recent_alerts = [
        {"time": "15:20", "type": "High Risk", "desc": "Multiple rapid transactions - User ID: 9942"},
        {"time": "15:12", "type": "Anomaly", "desc": "Geo-fencing breach detected - IP: 103.x.x.x"},
        {"time": "14:55", "type": "Compliance", "desc": "ISO 20022 message structure warning"}
    ]

    return render_template('dashboard.html',
                           name=session['full_name'],
                           roles=session['roles'],
                           stats=stats,
                           alerts=recent_alerts)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Memulai background thread listener Redis
    socketio.start_background_task(background_redis_listener)
    
    # Menjalankan server melalui SocketIO (membungkus Flask)
    print("\n[SYSTEM] Sentinel FDS starting via SocketIO on port 5000...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=False)
