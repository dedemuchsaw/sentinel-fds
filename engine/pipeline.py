import json
from database.redis_client import get_redis_client
from engine.reactive_agent import is_known_fraud
from engine.learning_agent import detect_behavioral_shift

redis_client = get_redis_client()

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
    Main Workflow Orchestrator for Sentinel FDS.
    Routes transactions through the dual-layer architecture.
    """
    print(f"\n[ENGINE INFO] Processing Transaction: {incoming_tx['id']}")

    # ==========================================
    # LAYER 1: REACTIVE AGENT (Zero Latency)
    # ==========================================
    is_fraud_reactive, reason_reactive, score_reactive = is_known_fraud(incoming_tx)
    if is_fraud_reactive:
        # We block immediately based on simple hard rule matching
        alert = {
            "tx_id": incoming_tx['id'], 
            "type": "Reactive Rule", 
            "desc": reason_reactive,
            "score": score_reactive,
            "status": "BLOCKED"
        }
        publish_alert(alert)
        return alert

    # ==========================================
    # LAYER 2: LEARNING AGENT (Behavioral AI)
    # ==========================================
    # If the transaction passed Layer 1, analyze deeper.
    is_anomaly, reason_learning, score_learning = detect_behavioral_shift(incoming_tx)
    if is_anomaly:
        alert = {
            "tx_id": incoming_tx['id'], 
            "type": "AI Anomaly", 
            "desc": reason_learning,
            "score": score_learning,
            "status": "FLAGGED_FOR_REVIEW"
        }
        publish_alert(alert)
        return alert

    # If it passes both layers, approve
    return {
        "tx_id": incoming_tx['id'], 
        "status": "APPROVED",
        "desc": "Passed all checks",
        "score": 0
    }
