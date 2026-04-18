from flask import Flask, request, jsonify
from models import init_db, get_db_connection
import os

app = Flask(__name__, static_folder='../frontend', static_url_path='/')

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

# ================================
# REST API ENDPOINTS
# ================================

@app.route('/api/materials', methods=['GET'])
def get_materials():
    conn = get_db_connection()
    materials = conn.execute('SELECT * FROM materials').fetchall()
    conn.close()
    return jsonify([dict(m) for m in materials])

@app.route('/api/materials', methods=['POST'])
def add_material():
    data = request.json
    name = data.get('name')
    m_type = data.get('type')  # 'RAW' or 'FINISHED'
    cost = data.get('cost', 0.0)
    stock = data.get('stock', 0)
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO materials (name, type, cost, stock) VALUES (?, ?, ?, ?)',
              (name, m_type, cost, stock))
    conn.commit()
    conn.close()
    return jsonify({"message": "Material added successfully"}), 201

@app.route('/api/bom/<int:product_id>', methods=['GET'])
def get_bom(product_id):
    conn = get_db_connection()
    bom = conn.execute('''
        SELECT b.id, b.component_id, m.name, b.quantity, m.cost 
        FROM bom b
        JOIN materials m ON b.component_id = m.id
        WHERE b.product_id = ?
    ''', (product_id,)).fetchall()
    conn.close()
    return jsonify([dict(b) for b in bom])

@app.route('/api/bom', methods=['POST'])
def add_bom():
    data = request.json
    product_id = data.get('product_id')
    component_id = data.get('component_id')
    quantity = data.get('quantity')
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('INSERT INTO bom (product_id, component_id, quantity) VALUES (?, ?, ?)',
              (product_id, component_id, quantity))
    conn.commit()
    conn.close()
    return jsonify({"message": "BOM entry added successfully"}), 201

@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    orders = conn.execute('''
        SELECT o.id, o.product_id, m.name, o.quantity, o.status, o.total_cost 
        FROM orders o
        JOIN materials m ON o.product_id = m.id
    ''').fetchall()
    conn.close()
    return jsonify([dict(o) for o in orders])

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity')
    
    conn = get_db_connection()
    
    # MRP Simulation: Check if enough raw materials available
    bom_items = conn.execute('SELECT component_id, quantity FROM bom WHERE product_id = ?', (product_id,)).fetchall()
    total_cost = 0.0
    
    for item in bom_items:
        required_qty = item['quantity'] * quantity
        comp_id = item['component_id']
        
        material = conn.execute('SELECT name, stock, cost FROM materials WHERE id = ?', (comp_id,)).fetchone()
        if material['stock'] < required_qty:
            conn.close()
            return jsonify({
                "error": "Shortage message generated: Not enough stock",
                "details": f"Missing {required_qty - material['stock']} of {material['name']}"
            }), 400
        
        total_cost += material['cost'] * required_qty

    # All checks passed, create order
    c = conn.cursor()
    c.execute('INSERT INTO orders (product_id, quantity, status, total_cost) VALUES (?, ?, ?, ?)',
              (product_id, quantity, 'CREATED', total_cost))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Production order created successfully.", "cost": total_cost}), 201

@app.route('/api/production/start', methods=['POST'])
def start_production():
    order_id = request.json.get('order_id')
    
    conn = get_db_connection()
    order = conn.execute('SELECT product_id, quantity, status FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order or order['status'] != 'CREATED':
        conn.close()
        return jsonify({"error": "Invalid order or order already started."}), 400
    
    # Deduct raw materials
    bom_items = conn.execute('SELECT component_id, quantity FROM bom WHERE product_id = ?', (order['product_id'],)).fetchall()
    c = conn.cursor()
    for item in bom_items:
        required_qty = item['quantity'] * order['quantity']
        c.execute('UPDATE materials SET stock = stock - ? WHERE id = ?', (required_qty, item['component_id']))
        
    c.execute('UPDATE orders SET status = ? WHERE id = ?', ('IN_PROGRESS', order_id))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Production started. Raw materials deducted."})

@app.route('/api/production/complete', methods=['POST'])
def complete_production():
    order_id = request.json.get('order_id')
    
    conn = get_db_connection()
    order = conn.execute('SELECT product_id, quantity, status FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if not order or order['status'] != 'IN_PROGRESS':
        conn.close()
        return jsonify({"error": "Invalid order or order not in progress."}), 400
        
    c = conn.cursor()
    # Increase finished goods inventory
    c.execute('UPDATE materials SET stock = stock + ? WHERE id = ?', (order['quantity'], order['product_id']))
    c.execute('UPDATE orders SET status = ? WHERE id = ?', ('COMPLETED', order_id))
    conn.commit()
    conn.close()
    
    return jsonify({"message": "Production completed. Finished goods added to inventory."})

if __name__ == '__main__':
    # Initialize DB (creates file and sample data if needed)
    init_db()
    app.run(debug=True, port=5000)
