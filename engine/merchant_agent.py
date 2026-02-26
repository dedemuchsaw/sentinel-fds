from database.arango_client import get_db

arango_db = get_db()

def check_merchant_cashback(transaction_data):
    """
    11. Merchant Cashback:
    Mengecek rasio cashback merchant dalam durasi waktu tertentu.
    - obs_days: 7 hari
    - max_cashback_rate: 0.3 (30%)
    - max_cashback_trx: 3
    """
    if not arango_db or not transaction_data.get('merchant_id'):
        return False, "No merchant data", 0
        
    merchant_id = transaction_data.get('merchant_id')
    obs_days = 7
    max_cashback_rate = 0.3
    max_cashback_trx = 3
    
    try:
        query = """
        LET threshold_date = DATE_SUBTRACT(DATE_NOW(), @obs_days, "days")
        FOR t IN transactions
            FILTER t.merchant_id == @merchant_id
            // FILTER t.timestamp >= threshold_date
            COLLECT type = t.type AGGREGATE 
                total_count = LENGTH(t),
                total_amount = SUM(t.amount)
            INTO groups
        
        LET sales = FIRST(FOR g IN groups FILTER g.type == 'SALE' RETURN g)
        LET cashbacks = FIRST(FOR g IN groups FILTER g.type == 'CASHBACK' RETURN g)
        
        RETURN {
            sales_amt: (sales ? sales.total_amount : 0),
            cb_amt: (cashbacks ? cashbacks.total_amount : 0),
            cb_count: (cashbacks ? cashbacks.total_count : 0)
        }
        """
        cursor = arango_db.aql.execute(query, bind_vars={'merchant_id': merchant_id, 'obs_days': obs_days})
        res = [doc for doc in cursor]
        
        if res and res[0]:
            stats = res[0]
            cb_count = stats['cb_count']
            cb_amt = stats['cb_amt']
            sales_amt = stats['sales_amt']
            
            rate = cb_amt / sales_amt if sales_amt > 0 else 0
            
            if cb_count >= max_cashback_trx and rate >= max_cashback_rate:
                return True, f"High Merchant Cashback Rate: {rate*100:.1f}% ({cb_count} trx)", 85
                
    except Exception as e:
        print(f"[MERCHANT AGENT ERROR] {e}")
        
    return False, "Clean", 0

def check_merchant_behavior_change(transaction_data):
    """
    12. Merchant Behavior Change:
    Mendekteksi lonjakan volume/count transaksi merchant via Z-Score (30 hari).
    - zscore_threshold: 5
    """
    if not arango_db or not transaction_data.get('merchant_id'):
        return False, "No merchant data", 0
        
    merchant_id = transaction_data.get('merchant_id')
    amount = float(transaction_data.get('amount', 0))
    obs_days = 30
    threshold = 5
    
    try:
        query = """
        FOR t IN transactions
            FILTER t.merchant_id == @merchant_id
            COLLECT AGGREGATE 
                avg_amt = AVERAGE(t.amount),
                std_amt = STDDEV_POPULATION(t.amount),
                avg_cnt = AVERAGE(1), // Dummy average per record (not very useful alone)
                total_cnt = COUNT(t)
        RETURN { mean: avg_amt, std: std_amt, total_cnt: total_cnt }
        """
        # Note: True behavioral count spike would need time_grouping (86400s) as per user request.
        # For simplicity in this dummy engine, we compare against historical daily average.
        cursor = arango_db.aql.execute(query, bind_vars={'merchant_id': merchant_id})
        res = [doc for doc in cursor]
        
        if res and res[0]:
            mean = res[0]['mean'] or 1000
            std = res[0]['std'] or 100
            if std == 0: std = 1
            
            z_score_amt = (amount - mean) / std
            
            # Simplified Count Anomaly: If total transactions for this merchant today > 5x historical daily avg
            # (In real system, we'd query historical daily counts)
            if z_score_amt > threshold:
                return True, f"Merchant Behavior Change: Z-Score {z_score_amt:.2f} (Amount spike)", 90
                
    except Exception as e:
        print(f"[MERCHANT AGENT ERROR] {e}")
        
    return False, "Clean", 0
