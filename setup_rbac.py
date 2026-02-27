# ~/sentinel-fds/setup_rbac.py
from arango import ArangoClient
from werkzeug.security import generate_password_hash

def init_db():
    # 1. Inisialisasi Client
    client = ArangoClient(hosts='http://localhost:8529')
    
    # 2. Login ke System DB untuk memastikan Database Aplikasi ada
    # Pakai password yang sudah lo tes sukses di arangosh tadi
    sys_db = client.db('_system', username='root', password='123123#')
    
    db_name = 'sentinel_fds'
    if not sys_db.has_database(db_name):
        sys_db.create_database(db_name)
        print(f">>> Database {db_name} created.")

    # 3. Login ULANG secara spesifik ke Database Aplikasi
    # Ini langkah krusial biar gak kena 401 lagi
    db = client.db(db_name, username='root', password='123123#')

    # 4. Buat Koleksi dengan Proteksi
    collections = {
        'document': ['users', 'roles'],
        'edge': ['has_role']
    }

    for col in collections['document']:
        if not db.has_collection(col):
            db.create_collection(col)
            print(f">>> Collection {col} created.")

    for col in collections['edge']:
        if not db.has_collection(col):
            db.create_collection(col, edge=True)
            print(f">>> Edge Collection {col} created.")

    # 5. Seed Roles (Maker-Checker-Validator-Auditor-Admin-Reviewer)
    # Sesuai rencana RBAC yang lo minta
    roles = ['super_admin', 'maker', 'checker', 'validator', 'auditor', 'reviewer']
    for r in roles:
        if not db.collection('roles').get(r):
            db.collection('roles').insert({'_key': r, 'role_name': r.upper()})

    # 6. Create Super Admin (dede)
    admin_data = {
        '_key': 'admin_dede',
        'username': 'dede',
        'password': generate_password_hash('Password123!'),
        'full_name': 'Super Admin Sentinel'
    }

    if not db.collection('users').get('admin_dede'):
        db.collection('users').insert(admin_data)
        db.collection('has_role').insert({
            '_from': 'users/admin_dede',
            '_to': 'roles/super_admin'
        })
        print(">>> Super Admin 'dede' is now active.")

    print("\n[SUCCESS] RBAC Framework Ready for FDS Engine.")

if __name__ == "__main__":
    init_db()
