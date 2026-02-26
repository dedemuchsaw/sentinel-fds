import json
from database.arango_client import get_db
from database.redis_client import get_redis_client

arango_db = get_db()
redis_client = get_redis_client()

def check_stolen_identity(account_data):
    """
    1. Stolen Identity:
    Mencari kesamaan identitas (KTP, Address, Phone) dari data pendaftaran baru
    dengan customer lain yang sudah ada di sistem ArangoDB.
    
    Parameters:
    - similarity_threshold: 0.5 (Not explicitly used in exact match, but configurable for fuzzy)
    - attr_check: ["ktp", "address", "phone"]
    - min_attr: 2
    """
    if not arango_db:
        return False, "ArangoDB disconnected", 0
    
    attr_check = ["ktp", "address", "phone"]
    min_attr = 2
    
    # In real world, we might use AQL fuzzy matching or exact match per attribute.
    # For this example, we'll do an exact match check on existing accounts.
    try:
        # AQL: Find accounts where at least `min_attr` of the specified fields match exactly
        query = """
        FOR acc IN accounts
            FILTER acc._key != @new_account_id
            LET match_ktp = (acc.ktp == @ktp ? 1 : 0)
            LET match_address = (acc.address == @address ? 1 : 0)
            LET match_phone = (acc.phone == @phone ? 1 : 0)
            LET total_matches = match_ktp + match_address + match_phone
            FILTER total_matches >= @min_attr
            RETURN { matched_account: acc._key, total_matches: total_matches }
        """
        
        bind_vars = {
            "new_account_id": account_data.get('account_id', ''),
            "ktp": account_data.get('ktp', ''),
            "address": account_data.get('address', ''),
            "phone": account_data.get('phone', ''),
            "min_attr": min_attr
        }
        
        cursor = arango_db.aql.execute(query, bind_vars=bind_vars)
        matches = [doc for doc in cursor]
        
        if len(matches) > 0:
            matched_accounts = ", ".join([m['matched_account'] for m in matches])
            return True, f"Stolen Identity Detected: Matches found with {matched_accounts}", 95
            
    except Exception as e:
        print(f"[IDENTITY AGENT ERROR] {e}")

    return False, "Clean", 0

def check_fraud_identity(account_data):
    """
    2. Fraud Identity:
    Mencari kesamaan identitas dengan watchlist (DTTOT, SIPENDAR) di Redis.
    
    Parameters:
    - attr_check: ["ktp", "address", "phone", "name"]
    - min_attr: 2
    """
    if not redis_client:
        return False, "Redis disconnected", 0
        
    attr_check = ["ktp", "address", "phone", "name"]
    min_attr = 2
    
    matches = 0
    matched_fields = []
    
    for attr in attr_check:
        val = account_data.get(attr)
        if val:
            # We assume a Redis Set exists for each blocked attribute type:
            # e.g., 'watchlist_ktp', 'watchlist_phone'
            if redis_client.sismember(f"watchlist_{attr}", val):
                matches += 1
                matched_fields.append(attr)
                
    if matches >= min_attr:
        return True, f"Fraud Identity Watchlist Match: {', '.join(matched_fields)}", 99
        
    return False, "Clean", 0
