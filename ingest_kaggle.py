import kagglehub
import pandas as pd
from database.arango_client import get_db

print("Initializing ArangoDB connection...")
db = get_db()
if not db:
    print("Failed to connect to ArangoDB. Exiting.")
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

    # Pass 2: Insert transaction edges
    print("Inserting transaction edges...")
    edge_docs = []
    for index, row in df.iterrows():
        edge_docs.append({
            '_from': f"{ACCOUNTS_COLLECTION}/{row['nameOrig']}",
            '_to': f"{ACCOUNTS_COLLECTION}/{row['nameDest']}",
            'step': row['step'],
            'type': row['type'],
            'amount': row['amount'],
            'oldbalanceOrg': row['oldbalanceOrg'],
            'newbalanceOrig': row['newbalanceOrig'],
            'oldbalanceDest': row['oldbalanceDest'],
            'newbalanceDest': row['newbalanceDest'],
            'isFraud': row['isFraud'],
            'isFlaggedFraud': row['isFlaggedFraud']
        })
        
    try:
        # We can batch these if it's too large, but 10k is small enough
        transactions.insert_many(edge_docs)
        print(f"Successfully ingested {len(edge_docs)} transactions into ArangoDB!")
    except Exception as e:
        print(f"Error inserting transactions: {e}")

if __name__ == "__main__":
    start_ingestion()
