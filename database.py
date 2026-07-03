import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "dukaan.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create inventory table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT UNIQUE NOT NULL,
        quantity INTEGER DEFAULT 0,
        cost_price REAL NOT NULL DEFAULT 0.0,
        selling_price REAL NOT NULL DEFAULT 0.0,
        low_stock_threshold INTEGER DEFAULT 3,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create ledger table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        phone_number TEXT,
        amount REAL NOT NULL,
        reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

# --- Inventory Operations ---

def get_inventory():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventory")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

def update_inventory_stock(item_name: str, quantity_change: int, cost_price: float = None, selling_price: float = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if item exists
    cursor.execute("SELECT * FROM inventory WHERE item_name = ?", (item_name,))
    row = cursor.fetchone()
    
    now = datetime.now().isoformat()
    if row:
        new_quantity = max(0, row["quantity"] + quantity_change)
        
        # Determine values to update
        c_price = cost_price if cost_price is not None else row["cost_price"]
        s_price = selling_price if selling_price is not None else row["selling_price"]
        
        cursor.execute("""
            UPDATE inventory 
            SET quantity = ?, cost_price = ?, selling_price = ?, updated_at = ? 
            WHERE item_name = ?
        """, (new_quantity, c_price, s_price, now, item_name))
    else:
        # Create new item
        c_price = cost_price if cost_price is not None else 0.0
        s_price = selling_price if selling_price is not None else 0.0
        new_quantity = max(0, quantity_change)
        cursor.execute("""
            INSERT INTO inventory (item_name, quantity, cost_price, selling_price, updated_at) 
            VALUES (?, ?, ?, ?, ?)
        """, (item_name, new_quantity, c_price, s_price, now))
        
    conn.commit()
    
    # Fetch updated record
    cursor.execute("SELECT * FROM inventory WHERE item_name = ?", (item_name,))
    updated_row = dict(cursor.fetchone())
    conn.close()
    return updated_row

# --- Ledger Operations ---

def get_ledger():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ledger ORDER BY created_at DESC")
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries

def add_ledger_entry(customer_name: str, amount: float, reason: str = None, phone_number: str = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Try to find existing customer phone number if not supplied
    if not phone_number:
        cursor.execute("SELECT phone_number FROM ledger WHERE customer_name = ? AND phone_number IS NOT NULL LIMIT 1", (customer_name,))
        row = cursor.fetchone()
        if row:
            phone_number = row["phone_number"]
            
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO ledger (customer_name, phone_number, amount, reason, created_at) 
        VALUES (?, ?, ?, ?, ?)
    """, (customer_name, phone_number, amount, reason, now))
    
    conn.commit()
    conn.close()
    return {
        "customer_name": customer_name,
        "phone_number": phone_number,
        "amount": amount,
        "reason": reason,
        "created_at": now
    }

# --- Analytical Operations ---

def get_daily_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Total credit given today (amount > 0)
    cursor.execute("SELECT SUM(amount) FROM ledger WHERE amount > 0 AND created_at LIKE ?", (f"{today}%",))
    total_credit = cursor.fetchone()[0] or 0.0
    
    # Total payments received today (amount < 0)
    cursor.execute("SELECT SUM(amount) FROM ledger WHERE amount < 0 AND created_at LIKE ?", (f"{today}%",))
    total_payments = abs(cursor.fetchone()[0] or 0.0)
    
    # Find top 3 items sold today (from ledger reason field parses or general updates)
    # Since reasons might contain item mentions, we extract from ledger items where amount > 0
    cursor.execute("""
        SELECT reason, COUNT(*) as cnt 
        FROM ledger 
        WHERE amount > 0 AND created_at LIKE ? AND reason IS NOT NULL AND reason != ''
        GROUP BY reason 
        ORDER BY cnt DESC 
        LIMIT 3
    """, (f"{today}%",))
    
    top_items = [{"item_name": row["reason"], "quantity_sold": row["cnt"]} for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        "total_sales": total_payments, # Cash/payments received
        "total_credit_given": total_credit,
        "top_items": top_items
    }

def get_outstanding_reminders():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Group by customer and find aggregate balances > 0 (debtors)
    cursor.execute("""
        SELECT customer_name, phone_number, SUM(amount) as balance, 
               MIN(created_at) as oldest_debt_date
        FROM ledger
        GROUP BY customer_name
        HAVING balance > 0
    """)
    
    reminders = []
    now = datetime.now()
    for row in cursor.fetchall():
        oldest_date_str = row["oldest_debt_date"].split("T")[0]
        try:
            oldest_date = datetime.strptime(oldest_date_str, "%Y-%m-%d")
            days_pending = (now - oldest_date).days
        except Exception:
            days_pending = 0
            
        reminders.append({
            "customer_name": row["customer_name"],
            "phone_number": row["phone_number"] or "",
            "amount_owed": row["balance"],
            "days_pending": days_pending
        })
        
    conn.close()
    return reminders
