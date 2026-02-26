import json
from database.redis_client import get_redis_client
from engine.reactive_agent import is_known_fraud
from engine.learning_agent import detect_behavioral_shift
from engine.chargeback_agent import check_account_chargeback
from engine.identity_agent import check_stolen_identity, check_fraud_identity
from engine.merchant_agent import check_merchant_cashback, check_merchant_behavior_change
from engine.activity_agent import check_dormant_account

from database.arango_client import get_db

redis_client = get_redis_client()
arango_db = get_db()

def store_transaction(tx_data):
    if not arango_db: return
    try:
        # Menyesuaikan dengan format skema graph (contoh sederhana)
        tx_doc = tx_data.copy()
        tx_doc['_key'] = tx_data['id']
        arango_db.collection('transactions').insert(tx_doc, overwrite=True)
        print(f"[GRAPH DB] Stored transaction: {tx_data['id']}")
    except Exception as e:
        print(f"[GRAPH DB ERROR] {e}")

def store_account(acc_data):
    if not arango_db: return
    try:
        acc_doc = acc_data.copy()
        acc_doc['_key'] = acc_data.get('account_id')
        arango_db.collection('accounts').insert(acc_doc, overwrite=True)
        print(f"[GRAPH DB] Stored account: {acc_data.get('account_id')}")
    except Exception as e:
        print(f"[GRAPH DB ERROR] {e}")

def store_alert(alert_data, related_node_id):
    if not arango_db: return
    try:
        alert_doc = alert_data.copy()
        alert_doc['related_node'] = related_node_id
        # Misal collection 'alerts'
        if not arango_db.has_collection('alerts'):
            arango_db.create_collection('alerts')
        arango_db.collection('alerts').insert(alert_doc)
        print(f"[GRAPH DB] Stored alert for: {related_node_id}")
    except Exception as e:
        print(f"[GRAPH DB ERROR] {e}")

def publish_alert(alert_data):
    """
    Publish security alert to the Redis channel 'alerts_channel'
    for the Dashboard to pick up in real-time.
    """
    if redis_client:
        try:
            redis_client.publish('alerts_channel', json.dumps(alert_data))
            print(f"[ENGINE] Published Alert to Redis: {alert_data['tx_id']}")
        except Exception as e:
            print(f"[ENGINE ERROR] Failed to publish alert: {e}")

def process_transaction(incoming_tx):
    """
    Graph-First Architecture: Store -> Execute Rules -> Store Alert -> Respond
    """
    print(f"\n[ENGINE INFO] Processing Transaction: {incoming_tx['id']}")
    
    # 1. STORE DATA: Simpan ke Graph DB sebelum eksekusi rule
    store_transaction(incoming_tx)
    
    frauds = []

    # 2. EKSEKUSI LOGIC PARALEL/SEKUENSIAL
    # LAYER 1: REACTIVE AGENT
    is_f_reactive, reason_r, score_r = is_known_fraud(incoming_tx)
    if is_f_reactive:
        frauds.append({"tx_id": incoming_tx['id'], "type": "Expert Rule", "desc": reason_r, "score": score_r, "status": "BLOCKED"})

    # LAYER 1.5: SPECIALIZED AGENTS
    rule_signals = {}
    is_dormant, reason_d, score_d = check_dormant_account(incoming_tx)
    if is_dormant: rule_signals['is_dormant'] = True
    
    is_m_cb, reason_m1, score_m1 = check_merchant_cashback(incoming_tx)
    is_m_bh, reason_m2, score_m2 = check_merchant_behavior_change(incoming_tx)
    if is_m_cb or is_m_bh: rule_signals['is_merchant_anomaly'] = True
    
    is_abuse, reason_a, score_a = check_account_chargeback(incoming_tx)
    if is_abuse:
        frauds.append({"tx_id": incoming_tx['id'], "type": "Chargeback Abuse", "desc": reason_a, "score": score_a, "status": "FLAGGED_FOR_REVIEW"})

    # LAYER 2: LEARNING AGENT (Hybrid ML)
    is_anomaly, reason_l, score_l = detect_behavioral_shift(incoming_tx, rule_signals=rule_signals)
    if is_anomaly:
        frauds.append({"tx_id": incoming_tx['id'], "type": "Hybrid ML Anomaly", "desc": reason_l, "score": score_l, "status": "FLAGGED_FOR_REVIEW"})

    # 3. STORE ALERT & PUSH TO DASHBOARD
    for alert in frauds:
        store_alert(alert, incoming_tx['id'])
        publish_alert(alert)

    # 4. RESPOND
    if frauds:
        return {"status": "FRAUD_DETECTED", "frauds": frauds}
        
    return {"status": "APPROVED", "desc": "Passed all checks", "score": 0}

def process_account_event(account_data):
    """
    Workflow for Identity Events (Account Registration or Update)
    Store -> Execute -> Store Alert -> Respond
    """
    account_id = account_data.get('account_id', 'Unknown')
    print(f"\n[ENGINE INFO] Processing Account Event: {account_id}")
    tx_id_pseudo = f"ACC-EVT-{account_id}"

    # 1. STORE DATA
    store_account(account_data)

    frauds = []

    # 2. EXECUTE LOGIC
    is_stolen, desc_stolen, score_stolen = check_stolen_identity(account_data)
    if is_stolen:
        frauds.append({"tx_id": tx_id_pseudo, "type": "Stolen Identity", "desc": desc_stolen, "score": score_stolen, "status": "BLOCKED"})

    is_fraud, desc_fraud, score_fraud = check_fraud_identity(account_data)
    if is_fraud:
        frauds.append({"tx_id": tx_id_pseudo, "type": "Fraud Identity Match", "desc": desc_fraud, "score": score_fraud, "status": "BLOCKED"})

    # 3. STORE ALERT & PUSH TO DASHBOARD
    for alert in frauds:
        store_alert(alert, account_id)
        publish_alert(alert)
        
    # 4. RESPOND
    if frauds:
        return {"status": "FRAUD_DETECTED", "frauds": frauds}
        
    return {"status": "APPROVED", "desc": "Identity clear", "score": 0}
