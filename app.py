import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from arango import ArangoClient
from werkzeug.security import check_password_hash
from functools import wraps
from flask_socketio import SocketIO
from database.redis_client import get_redis_client
import json
import uuid
import datetime
import random
from engine.pipeline import process_transaction, process_account_event

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

@app.route('/api/simulate', methods=['POST'])
@login_required
def api_simulate():
    """Manual trigger for testing Transaction Anomalies & Chargebacks."""
    accounts = ['ACC-101', 'ACC-202', 'ACC-303', 'ACC-999']
    now = datetime.datetime.now()
    
    # 20% chance to simulate a Chargeback event
    is_chargeback = random.random() < 0.2
    
    tx_data = {
        "id": f"TX-{str(uuid.uuid4())[:8].upper()}",
        "account_id": random.choice(accounts),
        "merchant_id": f"MERCH-{random.randint(100,500)}",
        "amount": random.randint(1000, 60000000),  # Random amount
        "time": now.strftime("%H:%M:%S"),
        "type": "CHARGEBACK" if is_chargeback else "SALE",
        "ip_address": f"192.168.1.{random.randint(1,255)}",
        "description": random.choice(["Normal Purchase", "Gift", "OTP verification", "Payment", "PIN code test"])
    }
    
    # Process it directly in the pipeline
    result = process_transaction(tx_data)
    
    return {"status": "success", "tx_id": tx_data['id'], "result": result}

@app.route('/api/simulate_account', methods=['POST'])
@login_required
def api_simulate_account():
    """Manual trigger for testing Identity Events (Registration/Update)."""
    # Dummy data that attempts to reuse identities or is in watchlist
    payloads = [
        # Simulating Stolen Identity (matching KTP, Address, Phone of someone else)
        {"account_id": f"NEW-{random.randint(1000,9999)}", "ktp": "317000000", "address": "Jl. Mawar Merah No 5 Jakarta", "phone": "08123456789"},
        # Simulating Fraud Identity (In blocklist)
        {"account_id": f"NEW-{random.randint(1000,9999)}", "ktp": "DTTOT-ID-001", "name": "Budi Koruptor", "phone": "0899BlockList"},
        # Normal
        {"account_id": f"NEW-{random.randint(1000,9999)}", "ktp": str(random.randint(10**9, 10**10)), "name": "Regular User"}
    ]
    
    account_data = random.choice(payloads)
    result = process_account_event(account_data)
    return {"status": "success", "event": "ACCOUNT_REGISTRATION", "result": result}

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

@app.route('/investigation')
@login_required
def investigation():
    return render_template('investigation.html',
                           name=session.get('full_name', 'Security Officer'),
                           roles=session.get('roles', []))

@app.route('/compliance')
@login_required
def compliance():
    roles = session.get('roles', [])
    if 'auditor' not in roles and 'super_admin' not in roles:
        flash("You do not have the required clearance to access Compliance Audit.")
        return redirect(url_for('dashboard'))
        
    return render_template('compliance.html',
                           name=session.get('full_name', 'Security Officer'),
                           roles=roles)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/engine_config')
@login_required
def engine_config():
    # Provide dummy parameters to the template for viewing
    config = {
        "hybrid_ml": {"enabled": True, "zscore_threshold": 5, "base_penalty": 20},
        "merchants": {"obs_days": 7, "cashback_rate": 0.3, "cb_trx": 3},
        "anomalies": {"time_start": "22:00", "time_end": "05:00", "small_trx_limit": 5}
    }
    return render_template('engine_config.html', name=session.get('full_name', 'Security Officer'), roles=session.get('roles', []), config=config)

if __name__ == '__main__':
    # Memulai background thread listener Redis
    socketio.start_background_task(background_redis_listener)
    
    # Menjalankan server melalui SocketIO (membungkus Flask)
    print("\n[SYSTEM] Sentinel FDS starting via SocketIO on port 5000...")
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=False)
