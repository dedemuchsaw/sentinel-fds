from arango import ArangoClient
import os

# Initialize ArangoDB connection
ARANGO_HOST = os.getenv('ARANGO_HOST', 'http://127.0.0.1:8529')
ARANGO_USER = os.getenv('ARANGO_USER', 'root')
ARANGO_PASS = os.getenv('ARANGO_PASS', '123123#')
ARANGO_DB   = os.getenv('ARANGO_DB', 'sentinel_fds')

try:
    client = ArangoClient(hosts=ARANGO_HOST)
    db = client.db(ARANGO_DB, username=ARANGO_USER, password=ARANGO_PASS)
    print(f"[ARANGO INFO] Connected to ArangoDB Database '{ARANGO_DB}'")
except Exception as e:
    print(f"CRITICAL: ArangoDB Connection Error: {e}")
    db = None

def get_db():
    return db
