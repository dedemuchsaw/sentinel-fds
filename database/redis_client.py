import redis
import os

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
