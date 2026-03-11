#!/usr/bin/env python3
"""
Quick test script for Safari-Shield API endpoints.
Run this after starting the API server.
"""
import requests
import json
from datetime import datetime
import time
import sys


# Configuration
BASE_URL = "http://localhost:8000"  # Change if API is on different host/port


def print_separator():
    """Print a separator line."""
    print("\n" + "="*60)


def test_health():
    """Test health endpoint."""
    print_separator()
    print("🔍 Testing Health Endpoint: GET /health")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Health Check Passed!")
            print(f"   Status: {data.get('status')}")
            print(f"   Model Loaded: {data.get('model_loaded')}")
            print(f"   Redis Connected: {data.get('redis_connected')}")
            print(f"   Version: {data.get('version')}")
            return True
        else:
            print(f"❌ Health Check Failed: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {BASE_URL}")
        print("   Make sure the API server is running:")
        print("   • Local: uvicorn src.api.app:app --reload")
        print("   • Docker: docker-compose up -d")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_prediction():
    """Test prediction endpoint."""
    print_separator()
    print("🎯 Testing Prediction Endpoint: POST /predict")
    
    # Sample transaction (legitimate - small amount, normal pattern)
    transaction = {
        "transaction_id": f"TEST_{int(time.time())}",
        "customer_id": "CUST12345",
        "amount": 500.00,  # Small amount
        "transaction_type": "send_money",
        "sender_msisdn": "254712345678",
        "receiver_msisdn": "254723456789",
        "device_id": "DEV_ABC123",
        "timestamp": datetime.now().isoformat(),
        "location": "Nairobi",
        "channel": "USSD"
    }
    
    print(f"📤 Sending transaction: {json.dumps(transaction, indent=2)}")
    
    try:
        start_time = time.time()
        response = requests.post(
            f"{BASE_URL}/predict",
            json=transaction,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        elapsed = (time.time() - start_time) * 1000
        
        print(f"\n📥 Response (took {elapsed:.1f}ms):")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Prediction Successful!")
            print(f"   Transaction ID: {data.get('transaction_id')}")
            print(f"   Risk Score: {data.get('risk_score'):.3f}")
            print(f"   Risk Level: {data.get('risk_level')}")
            print(f"   Is Fraud: {data.get('is_fraud')}")
            print(f"   Confidence: {data.get('confidence'):.3f}")
            print(f"   Processing Time: {data.get('processing_time_ms')}ms")
            return data
        else:
            print(f"❌ Prediction Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_fraud_prediction():
    """Test prediction with fraudulent pattern."""
    print_separator()
    print("🚨 Testing Fraudulent Transaction Detection")
    
    # Sample transaction (fraudulent - large amount, unusual pattern)
    transaction = {
        "transaction_id": f"FRAUD_TEST_{int(time.time())}",
        "customer_id": "CUST99999",
        "amount": 95000.00,  # Large amount
        "transaction_type": "send_money",
        "sender_msisdn": "254712345678",
        "receiver_msisdn": "254798765432",  # New recipient
        "device_id": "NEW_DEVICE_XYZ789",  # New device
        "timestamp": datetime.now().isoformat(),
        "location": "Unknown Location",
        "channel": "USSD"
    }
    
    print("📤 Sending suspicious transaction...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/predict",
            json=transaction,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n📊 Result:")
            print(f"   Risk Score: {data.get('risk_score'):.3f}")
            print(f"   Risk Level: {data.get('risk_level')}")
            print(f"   Is Fraud: {data.get('is_fraud')}")
            
            if data.get('is_fraud'):
                print("✅ Correctly identified as fraud!")
            else:
                print("⚠️ Transaction not flagged as fraud")
            return data
        else:
            print(f"❌ Test Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_explanation():
    """Test explanation endpoint."""
    print_separator()
    print("🔍 Testing Explanation Endpoint: POST /explain")
    
    transaction = {
        "transaction_id": f"EXP_TEST_{int(time.time())}",
        "customer_id": "CUST12345",
        "amount": 25000.00,
        "transaction_type": "send_money",
        "sender_msisdn": "254712345678",
        "receiver_msisdn": "254723456789",
        "device_id": "DEV_ABC123",
        "timestamp": datetime.now().isoformat(),
        "location": "Nairobi",
        "channel": "USSD"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/explain",
            json=transaction,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Explanation Generated!")
            print("\n📋 Risk Assessment:")
            print(f"   Risk Score: {data.get('risk_score'):.3f}")
            print(f"   Risk Level: {data.get('risk_level')}")
            
            print("\n📊 Top Factors:")
            for i, factor in enumerate(data.get('top_factors', [])[:3], 1):
                print(f"   {i}. {factor.get('factor')}: {factor.get('impact')} risk")
            
            print("\n📝 Narrative:")
            print(f"   {data.get('narrative')}")
            
            print("\n💡 Recommendations:")
            for rec in data.get('recommendations', [])[:3]:
                print(f"   • {rec}")
            
            return data
        else:
            print(f"❌ Explanation Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_bulk_prediction():
    """Test bulk prediction endpoint."""
    print_separator()
    print("📦 Testing Bulk Prediction Endpoint: POST /bulk_predict")
    
    transactions = []
    for i in range(3):
        transactions.append({
            "transaction_id": f"BULK_{i}_{int(time.time())}",
            "customer_id": f"CUST{i}",
            "amount": 1000 * (i + 1),
            "transaction_type": "send_money",
            "sender_msisdn": "254712345678",
            "receiver_msisdn": f"25472345{i:04d}",
            "device_id": f"DEV_{i}",
            "timestamp": datetime.now().isoformat(),
            "location": "Nairobi",
            "channel": "USSD"
        })
    
    print(f"📤 Sending {len(transactions)} transactions...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/bulk_predict",
            json=transactions,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Bulk Prediction Successful!")
            print(f"   Total Processed: {data.get('total_processed')}")
            print(f"   Successful: {data.get('successful')}")
            print(f"   Failed: {data.get('failed')}")
            
            print("\n📊 Results:")
            for result in data.get('results', []):
                status = "✅" if not result.get('error') else "❌"
                risk = result.get('risk_score', 'N/A')
                print(f"   {status} {result.get('transaction_id')}: risk={risk}")
            
            return data
        else:
            print(f"❌ Bulk Prediction Failed: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_metrics():
    """Test metrics endpoint."""
    print_separator()
    print("📊 Testing Metrics Endpoint: GET /metrics")
    
    try:
        response = requests.get(f"{BASE_URL}/metrics", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Metrics Retrieved!")
            print(f"   Total Predictions: {data.get('total_predictions')}")
            print(f"   Fraud Count: {data.get('fraud_count')}")
            print(f"   Fraud Rate: {data.get('fraud_rate'):.2%}")
            print(f"   Avg Response Time: {data.get('avg_response_time_ms'):.1f}ms")
            print(f"   P95 Response Time: {data.get('p95_response_time_ms'):.1f}ms")
            print(f"   Cache Hit Rate: {data.get('cache_hit_rate'):.2%}")
            return True
        else:
            print(f"❌ Metrics Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_recent():
    """Test recent predictions endpoint."""
    print_separator()
    print("🔄 Testing Recent Predictions Endpoint: GET /recent")
    
    try:
        response = requests.get(f"{BASE_URL}/recent?limit=5", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Recent Predictions Retrieved!")
            print(f"   Found {len(data)} recent predictions")
            
            for pred in data[:3]:
                print(f"   • {pred.get('timestamp')}: {pred.get('transaction_id')} - risk {pred.get('risk_score'):.3f}")
            
            return True
        else:
            print(f"❌ Recent Predictions Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def run_all_tests():
    """Run all API tests."""
    print("\n" + "="*60)
    print("🚀 SAFARI-SHIELD API TEST SUITE")
    print("="*60)
    
    # First check if API is reachable
    if not test_health():
        print("\n❌ API is not reachable. Please start the server first.")
        print("\nTo start the API:")
        print("  • Local: uvicorn src.api.app:app --reload")
        print("  • Docker: docker-compose up -d")
        return False
    
    # Run all tests
    test_prediction()
    test_fraud_prediction()
    test_explanation()
    test_bulk_prediction()
    test_metrics()
    test_recent()
    
    print_separator()
    print("✅ All tests completed!")
    print_separator()
    
    return True


if __name__ == "__main__":
    # Parse command line arguments
    if len(sys.argv) > 1:
        test_name = sys.argv[1].lower()
        
        if test_name == "health":
            test_health()
        elif test_name == "predict":
            test_prediction()
        elif test_name == "fraud":
            test_fraud_prediction()
        elif test_name == "explain":
            test_explanation()
        elif test_name == "bulk":
            test_bulk_prediction()
        elif test_name == "metrics":
            test_metrics()
        elif test_name == "recent":
            test_recent()
        elif test_name == "all":
            run_all_tests()
        else:
            print(f"Unknown test: {test_name}")
            print("Available tests: health, predict, fraud, explain, bulk, metrics, recent, all")
    else:
        # Run all tests by default
        run_all_tests()