import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "dukaan.db")

def seed():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Clear existing data to start fresh
    cursor.execute("DELETE FROM inventory")
    cursor.execute("DELETE FROM ledger")
    
    # 2. Insert mock inventory
    # Columns: item_name, quantity, cost_price, selling_price, low_stock_threshold, updated_at
    now = datetime.now().isoformat()
    mock_inventory = [
        ("Maggi Noodles", 2, 10.0, 14.0, 5, now), # Low stock (Qty 2 < Threshold 5)
        ("Britannia Marie Gold", 18, 20.0, 25.0, 5, now),
        ("Tata Salt", 12, 18.0, 22.0, 3, now),
        ("Amul Butter", 1, 46.0, 55.0, 4, now), # Low stock (Qty 1 < Threshold 4)
        ("Coca Cola 500ml", 24, 30.0, 40.0, 6, now),
        ("Surf Excel 1kg", 0, 110.0, 130.0, 2, now), # Out of stock
    ]
    cursor.executemany("""
        INSERT INTO inventory (item_name, quantity, cost_price, selling_price, low_stock_threshold, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, mock_inventory)
    
    # 3. Insert mock ledger entries
    # Columns: customer_name, phone_number, amount, reason, created_at
    today = datetime.now()
    
    # Old debt (18 days ago)
    date_18_days_ago = (today - timedelta(days=18)).isoformat()
    # Old debt (16 days ago)
    date_16_days_ago = (today - timedelta(days=16)).isoformat()
    # Recent debt (3 days ago)
    date_3_days_ago = (today - timedelta(days=3)).isoformat()
    # Today's date
    date_today = today.isoformat()
    
    mock_ledger = [
        ("Ramesh Kumar", "9876543210", 350.0, "Udaari (Groceries)", date_18_days_ago),
        ("Ramesh Kumar", "9876543210", 120.0, "Britannia & Maggi", date_16_days_ago),
        
        ("Amit Verma", "9988776655", 850.0, "Surf Excel & Butter", date_16_days_ago),
        
        ("Suresh Singh", "8877665544", 450.0, "Salt & Coca Cola", date_3_days_ago),
        ("Suresh Singh", "8877665544", -200.0, "Jama (Cash payment)", date_today), # Payment today
        
        # Today's direct cash transactions (recorded as ledger payment entries)
        ("Cash Customer", None, 45.0, "Tata Salt", date_today),
        ("Cash Customer", None, -45.0, "Cash Received", date_today),
    ]
    
    cursor.executemany("""
        INSERT INTO ledger (customer_name, phone_number, amount, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, mock_ledger)
    
    conn.commit()
    conn.close()
    print("Database successfully seeded with mock Kirana data!")

if __name__ == "__main__":
    seed()
