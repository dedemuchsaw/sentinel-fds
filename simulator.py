import time
import random
import uuid
import datetime
from engine.pipeline import process_transaction

print("Starting Sentinel FDS Transaction Simulator...")
print("Press Ctrl+C to stop.\n")

accounts = ['ACC-101', 'ACC-202', 'ACC-303', 'ACC-999', 'ACC-404', 'ACC-505']

try:
    while True:
        # Generate random dummy transaction
        tx_id = f"TX-{str(uuid.uuid4())[:8].upper()}"
        
        # Sometime we burst transaction to simulate velocity
        is_burst = random.random() < 0.2
        num_tx = random.randint(3, 5) if is_burst else 1

        for _ in range(num_tx):
            now = datetime.datetime.now()
            tx_data = {
                "id": tx_id if num_tx == 1 else f"TX-{str(uuid.uuid4())[:8].upper()}",
                "account_id": random.choice(accounts),
                "amount": random.randint(10000, 1000000) * (100 if random.random() < 0.05 else 1), # chance of huge amount
                "time": now.strftime("%H:%M:%S")
            }
            
            # Send to engine pipeline
            result = process_transaction(tx_data)
            print(f"Result: {result['status']}")
            
            # Small delay between burst transactions
            if num_tx > 1:
                time.sleep(0.5)
                
        # Wait before next batch
        time.sleep(random.uniform(2.0, 5.0))

except KeyboardInterrupt:
    print("\nSimulator stopped.")
