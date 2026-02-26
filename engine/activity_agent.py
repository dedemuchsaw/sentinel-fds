from database.arango_client import get_db

arango_db = get_db()

def check_dormant_account(transaction_data):
    """
    15. Dormant Account Transaction:
    Mendeteksi transaksi dari rekening yang tidak aktif > 80 hari.
    - days_threshold: 80
    """
    if not arango_db:
        return False, "DB disconnected", 0
        
    account_id = transaction_data.get('account_id')
    days_threshold = 80
    
    try:
        # Mencari transaksi terakhir dari akun ini
        query = """
        FOR t IN transactions
            FILTER t._from == @account OR t._to == @account
            SORT t.timestamp DESC
            LIMIT 1
            RETURN t.timestamp
        """
        cursor = arango_db.aql.execute(query, bind_vars={'account': f"accounts/{account_id}"})
        res = [doc for doc in cursor]
        
        if res:
            last_ts = res[0]
            # Sederhananya kita bandingkan selisih hari di AQL
            diff_query = "RETURN DATE_DIFF(@last_ts, DATE_NOW(), 'days')"
            diff_cursor = arango_db.aql.execute(diff_query, bind_vars={'last_ts': last_ts})
            days_diff = [doc for doc in diff_cursor][0]
            
            if days_diff > days_threshold:
                return True, f"Dormant Account Transaction: Last active {days_diff} days ago", 80
                
    except Exception as e:
        print(f"[ACTIVITY AGENT ERROR] {e}")
        
    return False, "Clean", 0
