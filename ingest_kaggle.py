import kagglehub
import pandas as pd
import json
import time
import uuid
from database.arango_client import get_db
from database.redis_client import get_redis_client

print("Initializing ArangoDB & Redis connections...")
db = get_db()
redis_client = get_redis_client()

if not db or not redis_client:
    print("Failed to connect to required databases. Exiting.")
    exit(1)

# Ensure Collections and Graph exist
GRAPH_NAME = 'sentinel_graph'
ACCOUNTS_COLLECTION = 'accounts'
TRANSACTIONS_COLLECTION = 'transactions'

# Create graph
if not db.has_graph(GRAPH_NAME):
    graph = db.create_graph(GRAPH_NAME)
    print(f"Created Graph: {GRAPH_NAME}")
else:
    graph = db.graph(GRAPH_NAME)
    print(f"Graph '{GRAPH_NAME}' exists.")

# Create vertex collection (accounts)
if not db.has_collection(ACCOUNTS_COLLECTION):
    accounts = db.create_collection(ACCOUNTS_COLLECTION)
    print(f"Created Vertex Collection: {ACCOUNTS_COLLECTION}")
else:
    accounts = db.collection(ACCOUNTS_COLLECTION)

# Create edge collection (transactions) and bind to graph
if not db.has_collection(TRANSACTIONS_COLLECTION):
    transactions = db.create_collection(TRANSACTIONS_COLLECTION, edge=True)
    graph.create_edge_definition(
        edge_collection=TRANSACTIONS_COLLECTION,
        from_vertex_collections=[ACCOUNTS_COLLECTION],
        to_vertex_collections=[ACCOUNTS_COLLECTION]
    )
    print(f"Created Edge Collection: {TRANSACTIONS_COLLECTION} and bound to graph.")
else:
    transactions = db.collection(TRANSACTIONS_COLLECTION)

print("\nDownloading Dataset from Kaggle...")
path = kagglehub.dataset_download("ealaxi/paysim1")
csv_path = f"{path}/PS_20174392719_1491204439457_log.csv"
print("Dataset ready at:", csv_path)

print("\nLoading dataset (10,000 rows)...")
df = pd.read_csv(csv_path, nrows=10000)

def start_ingestion():
    print("Starting Data Ingestion to ArangoDB...")
    
    # We will accumulate accounts to avoid duplicate inserts and reduce DB calls
    unique_accounts = set()
    
    # Pass 1: Gather unique accounts
    for index, row in df.iterrows():
        unique_accounts.add(row['nameOrig'])
        unique_accounts.add(row['nameDest'])
        
    print(f"Identified {len(unique_accounts)} unique accounts. Inserting vertices...")
    
    account_docs = []
    for acc in unique_accounts:
        account_docs.append({'_key': acc, 'type': 'customer_or_merchant'})
        
    # Bulk insert accounts
    try:
        accounts.insert_many(account_docs, overwrite_mode='ignore')
        print("Accounts inserted.")
    except Exception as e:
         print(f"Error inserting accounts: {e}")

    # Pass 2: Insert transaction edges and Stream to Redis
    print("Inserting transaction edges and streaming to Redis...")
    
    success_count = 0
    for index, row in df.iterrows():
        # 1. Prepare Data
        tx_id = f"TX-{str(uuid.uuid4())[:8].upper()}"
        tx_data_graph = {
            '_from': f"{ACCOUNTS_COLLECTION}/{row['nameOrig']}",
            '_to': f"{ACCOUNTS_COLLECTION}/{row['nameDest']}",
            'tx_id': tx_id,
            'step': row['step'],
            'type': row['type'],
            'amount': row['amount'],
            'oldbalanceOrg': row['oldbalanceOrg'],
            'newbalanceOrig': row['newbalanceOrig'],
            'oldbalanceDest': row['oldbalanceDest'],
            'newbalanceDest': row['newbalanceDest'],
            'isFraud': row['isFraud'],
            'isFlaggedFraud': row['isFlaggedFraud']
        }
        
        # 2. Insert Edge to ArangoDB
        try:
            transactions.insert(tx_data_graph)
            success_count += 1
        except Exception as e:
            print(f"Error inserting transaction {tx_id}: {e}")
            continue

        # 3. Stream to Redis for Real-time Engine & Dashboard
        # Format payload specifically for the Pipeline you built
        tx_data_stream = {
            "id": tx_id,
            "account_id": row['nameOrig'], # We use origin account for velocity check
            "amount": row['amount'],
            "time": "12:00:00" # Dummy time since PaySim only has 'step' not actual time
        }
        
        try:
            # Publish to the pipeline stream (or directly to alerts if skipping engine)
            # In a real architecture, you'd publish to an 'incoming_tx' queue and the engine picks it up.
            # But here we will call process_transaction directly to reuse our engine.
            from engine.pipeline import process_transaction
            
            # This simulates the "Engine waking up"
            process_transaction(tx_data_stream)
            
        except Exception as e:
            print(f"Error streaming transaction {tx_id}: {e}")
            
        # Optional: Slow down ingestion slightly so the dashboard is readable (throttle)
        time.sleep(0.05) 

    print(f"Successfully ingested and streamed {success_count} transactions!")

if __name__ == "__main__":
    start_ingestion()
