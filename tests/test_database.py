import os
import pytest
import sqlite3
from database import (
    init_db, get_inventory, update_inventory_stock,
    get_ledger, add_ledger_entry, get_daily_summary,
    get_stock_level, get_customer_balance,
    get_item_by_name_fuzzy, get_customer_by_name_fuzzy
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = os.path.join(tmp_path, "test_dukaan.db")
    monkeypatch.setattr("database.DB_PATH", test_db)
    init_db()
    yield test_db

def test_inventory_crud_and_profit():
    # Insert initial stock
    updated = update_inventory_stock("Maggi Noodles", 10, cost_price=10.0, selling_price=14.0)
    assert updated["item_name"] == "Maggi Noodles"
    assert updated["quantity"] == 10
    
    # Check inventory listing
    items = get_inventory()
    assert len(items) == 1
    assert items[0]["profit_margin"] == 4.0

    # Query stock level
    stock = get_stock_level("Maggi")
    assert stock["quantity"] == 10

def test_ledger_and_customer_balance():
    entry = add_ledger_entry("Ramesh Kumar", 250.0, reason="Biscuits & Tea")
    assert entry["customer_name"] == "Ramesh Kumar"
    assert entry["amount"] == 250.0

    bal = get_customer_balance("Ramesh")
    assert bal["balance"] == 250.0

    # Log payment
    add_ledger_entry("Ramesh Kumar", -100.0, reason="Payment Received")
    bal_updated = get_customer_balance("Ramesh Kumar")
    assert bal_updated["balance"] == 150.0

def test_fuzzy_matching():
    update_inventory_stock("Britannia Marie Gold", 20, cost_price=20.0, selling_price=25.0)
    matched = get_item_by_name_fuzzy("Britania Marie")
    assert matched == "Britannia Marie Gold"

def test_daily_summary():
    add_ledger_entry("Amit Verma", 300.0, reason="Maggi Noodles")
    add_ledger_entry("Amit Verma", -150.0, reason="Cash Payment")
    
    summary = get_daily_summary()
    assert summary["total_sales"] == 150.0
    assert summary["total_credit_given"] == 300.0
    assert "estimated_profit" in summary
