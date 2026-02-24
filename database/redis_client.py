import redis
import os
import json

# Initialize Redis client
# Hardcoded for the local lab environment, but can be configured via Env Vars
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
    # Ping to check connection on startup
    redis_client.ping()
    print(f"[REDIS INFO] Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
except Exception as e:
    print(f"CRITICAL: Redis Connection Error: {e}")
    redis_client = None

def get_redis_client():
    return redis_client

def update_window(account_id, transaction_data, window_size=5):
    """
    Menyimpan riwayat (sliding window) 'w' transaksi terakhir untuk account_id.
    Menggunakan Redis List: RPUSH untuk menambah, LTRIM untuk memotong.
    """
    if not redis_client:
        print("[REDIS WARNING] Redis is down, update_window bypassed.")
        # If no redis, just return a window of size 1 for the current transaction
        return [transaction_data]

    key = f"window:{account_id}"
    
    try:
        # Masukkan transaksi baru di akhir list (kanan)
        redis_client.rpush(key, json.dumps(transaction_data))
        
        # Potong list agar selalu maksimal berisi `window_size` elemen terakhir
        # -window_size sampai -1 (mengambil N elemen paling belakang)
        redis_client.ltrim(key, -window_size, -1)
        
        # Ambil kembali isi list yang terbaru
        raw_list = redis_client.lrange(key, 0, -1)
        
        # Kembalikan list of dict
        return [json.loads(item) for item in raw_list]
    except Exception as e:
        print(f"[REDIS ERROR] Failed to update window for {account_id}: {e}")
        return [transaction_data]
