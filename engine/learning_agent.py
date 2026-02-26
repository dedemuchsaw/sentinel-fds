from database.arango_client import get_db
from database.redis_client import update_window
import random

arango_db = get_db()

# Dummy implementation of ML components.
def extract_features(transaction_data, historical_profile, recent_transactions):
    """
    Simulates feature extraction from raw data, user history, AND short-term memory.
    """
    # Menghitung rata-rata dari sliding window (5 transaksi terakhir)
    window_amounts = [float(tx.get('amount', 0)) for tx in recent_transactions]
    window_avg = sum(window_amounts) / len(window_amounts) if window_amounts else 0

    return {
        "amount": float(transaction_data.get('amount', 0)), 
        "historical_mean": float(historical_profile.get('mean_amount', 0)),
        "recent_window_avg": window_avg
    }

def mock_predict(features):
    """
    Simulates model prediction.
    Randomly flags 10% of transactions as behavioral anomalies.
    Returns: -1 for anomaly, 1 for normal.
    """
    return -1 if random.random() < 0.1 else 1
    
def calculate_risk_probability(features):
    """
    Simulates generating a risk score from model outputs.
    Returns score 0-100.
    """
    # Jika transaksi ini jauh lebih besar dari rata-rata sliding window (Cheng Wang logic)
    if features['amount'] > (features['recent_window_avg'] * 3):
        return random.randint(85, 99)
    return random.randint(60, 80)

def detect_behavioral_shift(transaction_data):
    """
    Second-pass filter. 
    Queries ArangoDB for history and applies "AI" logic.
    """
    account_id = transaction_data.get('account_id')

    # Update memori jangka pendek (sliding window) di Redis
    recent_transactions = update_window(account_id, transaction_data, window_size=5)

    # Retrieve the user's historical profile dynamically from ArangoDB
    historical_profile = {
        "mean_amount": 500000, # fallback baseline
        "frequent_locations": ["Jakarta", "Bandung"]
    }
    
    if arango_db:
        try:
            # Query average transaction amount for this account
            query = """
            FOR t IN transactions
                FILTER t._from == @account
                COLLECT AGGREGATE mean_amt = AVERAGE(t.amount)
                RETURN mean_amt
            """
            cursor = arango_db.aql.execute(query, bind_vars={'account': f"accounts/{account_id}"})
            results = [doc for doc in cursor]
            
            if results and results[0] is not None:
                historical_profile["mean_amount"] = float(results[0])
        except Exception as e:
            print(f"[ENGINE ERROR] Failed fetching profile from DB: {e}")
    
    features = extract_features(transaction_data, historical_profile, recent_transactions)
    prediction = mock_predict(features)
    risk_score = calculate_risk_probability(features)
    
    # If our mock ML flagged it and gave a high score
    if prediction == -1 and risk_score > 75:
        # Check against past behavioral threshold
        if features['amount'] > historical_profile['mean_amount'] * 10:
             return True, f"Behavioral Anomaly: 10x Usual Transfer ({risk_score}% Risk)", risk_score
        else:
             return True, f"Slight Deviation from Profile ({risk_score}% Risk)", risk_score

    return False, "Normal Behavior", risk_score
