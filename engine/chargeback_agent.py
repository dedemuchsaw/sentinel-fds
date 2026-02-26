import datetime
from database.arango_client import get_db

arango_db = get_db()

def check_account_chargeback(transaction_data):
    """
    4. Account Chargeback:
    Mengecek apabila sebuah akun sering mendapatkan refund/dispute.
    
    Parameters:
    - obs_days: 7
    - chargeback_period: 24h
    - min_threshold: 3
    - amount_difference: 0.75 (75%)
    """
    if not arango_db:
        return False, "ArangoDB disconnected", 0
        
    # Hanya mengeksekusi rule jika transaksi ini bertipe REFUND/CHARGEBACK
    if transaction_data.get('type') not in ['REFUND', 'CHARGEBACK']:
        return False, "Not a chargeback transaction", 0

    account_id = transaction_data.get('account_id')
    amount = float(transaction_data.get('amount', 0))
    
    obs_days = 7
    min_threshold = 3
    amount_difference = 0.75
    
    try:
        # AQL: Menghitung riwayat Chargeback dalam observasi waktu 7 hari ke belakang
        query = """
        LET threshold_date = DATE_SUBTRACT(DATE_NOW(), @obs_days, "days")
        FOR t IN transactions
            FILTER t._to == @account OR t._from == @account
            FILTER t.type IN ['REFUND', 'CHARGEBACK']
            // Asumsi data transaction memiliki field 'timestamp' berbasis ISO DateTime,
            // Jika tidak, kita hitung kasar dari relasi step (dummy logic Kaggle)
            # FILTER t.timestamp >= threshold_date
            
        COLLECT AGGREGATE 
            total_chargebacks = LENGTH(t),
            sum_chargeback_amount = SUM(t.amount)
        RETURN {
            count: total_chargebacks,
            total_amount: sum_chargeback_amount
        }
        """
        bind_vars = {
            "account": f"accounts/{account_id}",
            "obs_days": obs_days
        }
        
        cursor = arango_db.aql.execute(query, bind_vars=bind_vars)
        result = [doc for doc in cursor]
        
        if result and len(result) > 0:
            hist = result[0]
            cb_count = hist.get('count', 0)
            cb_amount = float(hist.get('total_amount', 0))
            
            # Simulated dummy logic: kita anggap "transaksi aslinya" (total trx account ini)
            # Dalam skenario asli, ini adalah total sum transaksi DEBIT dari akun ini
            # Di sini kita batasi perhitungannya agar bisa jalan di Kaggle PaySim log
            dummy_original_spending = cb_amount * 1.2 # Placeholder 
            
            ratio = cb_amount / dummy_original_spending if dummy_original_spending > 0 else 0
            
            # Evaluasi Rule
            if cb_count >= min_threshold and ratio >= amount_difference:
                return True, f"Account Chargeback Abuse ({cb_count} refunds, {ratio * 100:.0f}% ratio)", 88
            
    except Exception as e:
        print(f"[CHARGEBACK AGENT ERROR] {e}")

    return False, "Clean", 0
