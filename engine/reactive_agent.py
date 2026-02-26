from database.redis_client import get_redis_client
import time
import json

redis_client = get_redis_client()

def is_known_fraud(transaction_data):
    """
    First-pass filter. Zero-latency rule-based checks using Redis.
    Must be very fast.
    """
    if not redis_client:
        return False, "Redis connection down, skipping reactive checks", 0
        
    account_id = transaction_data.get('account_id')
    amount = transaction_data.get('amount', 0)
    tx_time_str = transaction_data.get('time', '00:00:00')

    # 1. Velocity Check (e.g., > 3 transactions in 10 seconds)
    key = f"velocity:{account_id}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 10) # Window is 10 seconds
    
    if count > 3:
        return True, "High Velocity - Possible Bot/Takeover", 95
        
    # 2. Static Threshold & Time Check (High amount at night)
    try:
        hour = int(tx_time_str.split(':')[0])
        is_night = (hour >= 23 or hour <= 4)
    except Exception:
        is_night = False

    if amount > 50000000 and is_night:
        return True, f"High Amount ({amount}) at Unusual Hour", 85
        
    # 3. Dynamic Watchlist Check (List of risky accounts)
    # Checks directly against a Redis set for zero-latency lookups
    if redis_client.sismember('watchlist', account_id):
        return True, "Account in Dynamic Watchlist", 99

    return False, "Clean", 0
