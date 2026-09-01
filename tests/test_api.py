import os
import pytest
from fastapi.testclient import TestClient
from main import app
from database import init_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = os.path.join(tmp_path, "test_dukaan_api.db")
    monkeypatch.setattr("database.DB_PATH", test_db)
    init_db()
    yield test_db

def test_verify_pin_success():
    response = client.post("/api/verify-pin", json={"pin": "1234"})
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert "token" in data

def test_verify_pin_failure():
    response = client.post("/api/verify-pin", json={"pin": "9999"})
    assert response.status_code == 401

def test_get_inventory_endpoint():
    response = client.get("/api/inventory")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_ledger_endpoint():
    response = client.get("/api/ledger")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_daily_summary_endpoint():
    response = client.get("/api/daily-summary")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "estimated_profit" in data["data"]

def test_reminders_endpoint():
    response = client.get("/api/reminders")
    assert response.status_code == 200
    assert response.json()["status"] == "success"
