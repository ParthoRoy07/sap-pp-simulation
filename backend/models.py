import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'sap_pp.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create Materials Table (Raw Materials & Finished Goods)
    c.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- 'RAW' or 'FINISHED'
            cost REAL NOT NULL,
            stock INTEGER DEFAULT 0
        )
    ''')
    
    # Create BOM Table (Bill of Materials)
    c.execute('''
        CREATE TABLE IF NOT EXISTS bom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            component_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            FOREIGN KEY (product_id) REFERENCES materials (id),
            FOREIGN KEY (component_id) REFERENCES materials (id)
        )
    ''')
    
    # Create Production Orders Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL, -- 'CREATED', 'IN_PROGRESS', 'COMPLETED'
            total_cost REAL NOT NULL,
            FOREIGN KEY (product_id) REFERENCES materials (id)
        )
    ''')

    # Insert sample data if the materials table is empty
    c.execute('SELECT COUNT(*) FROM materials')
    if c.fetchone()[0] == 0:
        # Insert Materials
        c.execute("INSERT INTO materials (name, type, cost, stock) VALUES ('Bicycle', 'FINISHED', 0.0, 0)") # ID: 1
        c.execute("INSERT INTO materials (name, type, cost, stock) VALUES ('Frame', 'RAW', 50.0, 10)")    # ID: 2
        c.execute("INSERT INTO materials (name, type, cost, stock) VALUES ('Wheel', 'RAW', 25.0, 20)")    # ID: 3
        c.execute("INSERT INTO materials (name, type, cost, stock) VALUES ('Seat', 'RAW', 15.0, 10)")     # ID: 4
        
        # Insert BOM for Bicycle
        c.execute("INSERT INTO bom (product_id, component_id, quantity) VALUES (1, 2, 1)") # 1 Frame
        c.execute("INSERT INTO bom (product_id, component_id, quantity) VALUES (1, 3, 2)") # 2 Wheels
        c.execute("INSERT INTO bom (product_id, component_id, quantity) VALUES (1, 4, 1)") # 1 Seat

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
