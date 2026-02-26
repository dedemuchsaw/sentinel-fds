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

def check_monetary_anomaly_fixed(transaction_data):
    """
    6. Monetary Anomaly - Fixed Amount
    Mengecek transaksi dengan jumlah kumulatif sangat besar.
    - obs_days: 30
    - amount_threshold: 100000000
    """
    if not arango_db:
        return False, "DB disconnected", 0
        
    account_id = transaction_data.get('account_id')
    amount = float(transaction_data.get('amount', 0))
    obs_days = 30
    amount_threshold = 100000000
    
    try:
        query = """
        LET threshold_date = DATE_SUBTRACT(DATE_NOW(), @obs_days, "days")
        FOR t IN transactions
            FILTER t._from == @account
            // FILTER t.timestamp >= threshold_date
        COLLECT AGGREGATE sum_amt = SUM(t.amount)
        RETURN sum_amt
        """
        cursor = arango_db.aql.execute(query, bind_vars={'account': f"accounts/{account_id}", 'obs_days': obs_days})
        results = [doc for doc in cursor]
        
        cumm_amount = float(results[0]) if results and results[0] else 0
        total_now = cumm_amount + amount
        
        if total_now > amount_threshold:
            return True, f"Monetary Anomaly (Fixed): Cumulative > {amount_threshold}", 95
    except Exception as e:
        print(f"[ENGINE ERROR] {e}")
        
    return False, "Clean", 0

def check_monetary_anomaly_behavioral(transaction_data, historical_profile):
    """
    7. Monetary Anomaly - Behavioral (Z-Score)
    - obs_days: 30
    - zscore_high: 5
    """
    amount = float(transaction_data.get('amount', 0))
    mean = historical_profile.get('mean_amount', 1000)
    std_dev = historical_profile.get('std_dev_amount', 500) # Assuming we also grab std_dev from DB
    
    if std_dev == 0: std_dev = 1 # Prevent div/0
    
    z_score = (amount - mean) / std_dev
    
    if z_score > 5:
        return True, f"Monetary Anomaly (Behavioral): Z-Score {z_score:.2f} > 5", 90
        
    return False, "Clean", 0


def detect_behavioral_shift(transaction_data):
    """
    Second-pass filter. 
    Queries ArangoDB for history and applies statistical/AI logic.
    """
    account_id = transaction_data.get('account_id')

    # Update memori jangka pendek (sliding window) di Redis
    recent_transactions = update_window(account_id, transaction_data, window_size=5)

    # 1. Cek Monetary Fixed
    is_fraud, desc, score = check_monetary_anomaly_fixed(transaction_data)
    if is_fraud: return True, desc, score

    # Retrieve the user's historical profile dynamically from ArangoDB
    historical_profile = {
        "mean_amount": 500000, # fallback baseline
        "std_dev_amount": 250000,
        "frequent_locations": ["Jakarta", "Bandung"]
    }
    
    if arango_db:
        try:
            # Query average and variance for Z-Score calculation
            query = """
            FOR t IN transactions
                FILTER t._from == @account
                COLLECT AGGREGATE 
                    mean_amt = AVERAGE(t.amount),
                    var_amt = VARIANCE_POPULATION(t.amount)
                RETURN { mean: mean_amt, variance: var_amt }
            """
            cursor = arango_db.aql.execute(query, bind_vars={'account': f"accounts/{account_id}"})
            results = [doc for doc in cursor]
            
            if results and results[0]:
                historical_profile["mean_amount"] = float(results[0].get('mean') or 500000)
                variance = float(results[0].get('variance') or 0)
                historical_profile["std_dev_amount"] = variance ** 0.5 if variance > 0 else 250000
        except Exception as e:
            print(f"[ENGINE ERROR] Failed fetching profile from DB: {e}")
    
    # 2. Cek Monetary Behavioral (Z-Score)
    is_fraud, desc, score = check_monetary_anomaly_behavioral(transaction_data, historical_profile)
    if is_fraud: return True, desc, score

    # Legacy dummy ML logic
    features = extract_features(transaction_data, historical_profile, recent_transactions)
    prediction = mock_predict(features)
    risk_score = calculate_risk_probability(features)
    
    if prediction == -1 and risk_score > 80:
         return True, f"AI Behavioral Deviation Detected ({risk_score}% Risk)", risk_score

    return False, "Normal Behavior", risk_score
