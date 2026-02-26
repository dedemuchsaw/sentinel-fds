from database.redis_client import get_redis_client
import time
import json

redis_client = get_redis_client()

def check_recency_anomaly(transaction_data):
    """
    5. Recency Anomaly (Velocity Check)
    Mengecek jika terdapat banyak transaksi dari 1 pengguna dalam durasi waktu singkat.
    - obs_second: 3600
    - max_trx_count: 10
    """
    if not redis_client:
        return False, "Redis connection down", 0
        
    account_id = transaction_data.get('account_id')
    obs_second = 3600
    max_trx_count = 10
    
    key = f"recency:{account_id}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, obs_second)
        
    if count > max_trx_count:
        return True, f"Recency Anomaly (Velocity): >{max_trx_count} trx in {obs_second}s", 95
        
    return False, "Clean", 0

def check_time_anomaly_fixed(transaction_data):
    """
    8. Time Anomaly - Fixed Time Range
    Mengecek transaksi di luar jam normal.
    - start_offhour: 23:00:00
    - end_offhour: 04:00:00
    """
    tx_time_str = transaction_data.get('time', '00:00:00')
    start_offhour = 23
    end_offhour = 4
    
    try:
        hour = int(tx_time_str.split(':')[0])
        # between 23 and 04
        is_night = (hour >= start_offhour or hour <= end_offhour)
    except Exception:
        is_night = False
        
    if is_night:
        return True, f"Time Anomaly: Transaction at {tx_time_str} (Off-hours)", 85
        
    return False, "Clean", 0

def check_time_value_anomaly(transaction_data):
    """
    13. Time & Value Anomaly:
    Transaksi jam malam (22:00 - 05:00) dengan akumulasi > 50jt.
    """
    if not redis_client: return False, "Redis down", 0
    
    tx_time_str = transaction_data.get('time', '00:00:00')
    amount = float(transaction_data.get('amount', 0))
    account_id = transaction_data.get('account_id')
    
    try:
        hour = int(tx_time_str.split(':')[0])
        if hour >= 22 or hour <= 5:
            key = f"night_cum:{account_id}"
            cum_amt = redis_client.incrbyfloat(key, amount)
            if cum_amt == amount:
                redis_client.expire(key, 3600 * 8) # Reset after night shift
            
            if cum_amt > 50000000:
                return True, f"Time & Value Anomaly: Night accumulation {cum_amt:,.0f} > 50jt", 92
    except: pass
    return False, "Clean", 0

def check_repeated_small_transaction(transaction_data):
    """
    14. Repeated Small Transaction:
    Transaksi 10rb - 50rb berulang > 5x dlm 1 jam.
    """
    if not redis_client: return False, "Redis down", 0
    
    amount = float(transaction_data.get('amount', 0))
    account_id = transaction_data.get('account_id')
    
    if 10000 <= amount <= 50000:
        key = f"small_trx:{account_id}"
        count = redis_client.incr(key)
        if count == 1: redis_client.expire(key, 3600)
        
        if count > 5:
            return True, f"Repeated Small Transaction: {count}x in 1h", 85
    return False, "Clean", 0

def check_ip_blacklist(transaction_data):
    """
    16. IP Blacklist
    """
    if not redis_client: return False, "Redis down", 0
    ip = transaction_data.get('ip_address')
    if ip and redis_client.sismember('ip_blacklist', ip):
        return True, f"IP Blacklist Match: {ip}", 95
    return False, "Clean", 0

def check_sensitive_keyword(transaction_data):
    """
    17. Sensitive Keyword Check
    """
    desc = transaction_data.get('description', '').upper()
    keywords = ["PIN", "OTP", "CVV", "CREDIT CARD", "PASSWORD"]
    for word in keywords:
        if word in desc:
            return True, f"Sensitive Keyword Detected: {word}", 88
    return False, "Clean", 0

def check_watchlist(transaction_data):
    """
    Traditional Watchlist Check
    """
    if not redis_client:
        return False, "Redis down", 0
        
    account_id = transaction_data.get('account_id')
    if redis_client.sismember('watchlist', account_id):
        return True, "Account in Dynamic Watchlist", 99
        
    return False, "Clean", 0

def is_known_fraud(transaction_data):
    """
    Orchestrator for all zero-latency reactive rules.
    """
    # 1. Watchlist
    is_f, d, s = check_watchlist(transaction_data)
    if is_f: return True, d, s
    
    # 2. IP Blacklist
    is_f, d, s = check_ip_blacklist(transaction_data)
    if is_f: return True, d, s
    
    # 3. Sensitive Keyword
    is_f, d, s = check_sensitive_keyword(transaction_data)
    if is_f: return True, d, s
    
    # 4. Repeated Small Transaction
    is_f, d, s = check_repeated_small_transaction(transaction_data)
    if is_f: return True, d, s
    
    # 5. Time & Value Anomaly
    is_f, d, s = check_time_value_anomaly(transaction_data)
    if is_f: return True, d, s
    
    # 6. Recency Anomaly (Velocity)
    is_f, d, s = check_recency_anomaly(transaction_data)
    if is_f: return True, d, s
    
    # 7. Time Anomaly Fixed
    is_f, d, s = check_time_anomaly_fixed(transaction_data)
    if is_f: return True, d, s
    
    return False, "Clean", 0
