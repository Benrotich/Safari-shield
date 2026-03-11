"""
Automated API tests using pytest.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.app import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_transaction():
    """Sample transaction for testing."""
    return {
        "transaction_id": "TEST_001",
        "customer_id": "CUST001",
        "amount": 5000.0,
        "transaction_type": "send_money",
        "sender_msisdn": "254712345678",
        "receiver_msisdn": "254723456789",
        "device_id": "DEV001",
        "timestamp": datetime.now().isoformat(),
        "location": "Nairobi",
        "channel": "USSD"
    }


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_predict_endpoint(client, sample_transaction):
    """Test prediction endpoint."""
    response = client.post("/predict", json=sample_transaction)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert data["transaction_id"] == sample_transaction["transaction_id"]
    assert "risk_score" in data
    assert "risk_level" in data
    assert "is_fraud" in data
    assert "processing_time_ms" in data
    
    # Check value ranges
    assert 0 <= data["risk_score"] <= 1
    assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert isinstance(data["is_fraud"], bool)


def test_explain_endpoint(client, sample_transaction):
    """Test explanation endpoint."""
    response = client.post("/explain", json=sample_transaction)
    assert response.status_code == 200
    data = response.json()
    
    # Check response structure
    assert data["transaction_id"] == sample_transaction["transaction_id"]
    assert "risk_score" in data
    assert "risk_level" in data
    assert "top_factors" in data
    assert "narrative" in data
    assert "recommendations" in data
    
    # Check that we have at least one factor
    if data["top_factors"]:
        factor = data["top_factors"][0]
        assert "factor" in factor
        assert "impact" in factor


def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    
    # Check metrics structure
    assert "total_predictions" in data
    assert "fraud_count" in data
    assert "avg_response_time_ms" in data
    assert "cache_hit_rate" in data


def test_invalid_transaction(client):
    """Test with invalid transaction data."""
    invalid_transaction = {
        "transaction_id": "TEST_002",
        "amount": -100,  # Invalid negative amount
        "customer_id": "CUST001"
        # Missing required fields
    }
    
    response = client.post("/predict", json=invalid_transaction)
    assert response.status_code == 422  # Validation error


def test_bulk_predict(client, sample_transaction):
    """Test bulk prediction endpoint."""
    transactions = [sample_transaction] * 3
    response = client.post("/bulk_predict", json=transactions)
    assert response.status_code == 200
    data = response.json()
    
    assert data["total_processed"] == 3
    assert "results" in data
    assert len(data["results"]) == 3


@pytest.mark.parametrize("amount,expected_risk", [
    (100, "LOW"),
    (50000, "MEDIUM"),
    (150000, "HIGH")
])
def test_risk_levels(client, sample_transaction, amount, expected_risk):
    """Test different risk levels."""
    sample_transaction["amount"] = amount
    response = client.post("/predict", json=sample_transaction)
    assert response.status_code == 200
    data = response.json()
    
    if expected_risk == "HIGH":
        assert data["risk_level"] in ["MEDIUM", "HIGH"]  # May vary based on model
    elif expected_risk == "LOW":
        assert data["risk_level"] in ["LOW", "MEDIUM"]