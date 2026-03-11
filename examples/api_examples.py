"""
Example usage of Safari-Shield API.
Shows how to integrate with the API from other applications.
"""
import requests
import json  # noqa: F401
import time
from datetime import datetime
from typing import Dict, List


class SafariShieldClient:
    """Client for interacting with Safari-Shield API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def health_check(self) -> Dict:
        """Check API health."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def predict(self, transaction: Dict) -> Dict:
        """Get fraud prediction for a single transaction."""
        response = self.session.post(
            f"{self.base_url}/predict",
            json=transaction,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def explain(self, transaction: Dict) -> Dict:
        """Get prediction with explanation."""
        response = self.session.post(
            f"{self.base_url}/explain",
            json=transaction,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def bulk_predict(self, transactions: List[Dict]) -> Dict:
        """Get predictions for multiple transactions."""
        response = self.session.post(
            f"{self.base_url}/bulk_predict",
            json=transactions,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def get_metrics(self) -> Dict:
        """Get system metrics."""
        response = self.session.get(f"{self.base_url}/metrics")
        response.raise_for_status()
        return response.json()
    
    def get_recent(self, limit: int = 10) -> List[Dict]:
        """Get recent predictions."""
        response = self.session.get(f"{self.base_url}/recent?limit={limit}")
        response.raise_for_status()
        return response.json()


def create_sample_transaction(
    transaction_id: str,
    amount: float,
    is_suspicious: bool = False
) -> Dict:
    """Create a sample transaction."""
    if is_suspicious:
        # Suspicious transaction pattern
        return {
            "transaction_id": transaction_id,
            "customer_id": "CUST_SUSPICIOUS",
            "amount": amount,
            "transaction_type": "send_money",
            "sender_msisdn": "254712345678",
            "receiver_msisdn": "254799999999",  # Unknown recipient
            "device_id": "NEW_DEVICE_123",  # New device
            "timestamp": datetime.now().isoformat(),
            "location": "UNKNOWN",
            "channel": "USSD"
        }
    else:
        # Normal transaction pattern
        return {
            "transaction_id": transaction_id,
            "customer_id": "CUST_NORMAL",
            "amount": amount,
            "transaction_type": "send_money",
            "sender_msisdn": "254712345678",
            "receiver_msisdn": "254723456789",  # Frequent recipient
            "device_id": "DEVICE_ABC123",  # Known device
            "timestamp": datetime.now().isoformat(),
            "location": "Nairobi",
            "channel": "Mobile_App"
        }


def example_1_basic_prediction():
    """Example 1: Basic fraud prediction."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Fraud Prediction")
    print("="*60)
    
    client = SafariShieldClient()
    
    # Check health first
    health = client.health_check()
    print(f"✅ API Health: {health['status']}")
    
    # Normal transaction
    normal_tx = create_sample_transaction("TX_NORMAL_001", 500.00, False)
    result = client.predict(normal_tx)
    
    print("\n📊 Normal Transaction:")
    print(f"   Transaction ID: {result['transaction_id']}")
    print(f"   Amount: KES {normal_tx['amount']:,.2f}")
    print(f"   Risk Score: {result['risk_score']:.3f}")
    print(f"   Risk Level: {result['risk_level']}")
    print(f"   Fraud Detected: {result['is_fraud']}")
    
    # Suspicious transaction
    suspicious_tx = create_sample_transaction("TX_SUSPICIOUS_001", 95000.00, True)
    result = client.predict(suspicious_tx)
    
    print("\n🚨 Suspicious Transaction:")
    print(f"   Transaction ID: {result['transaction_id']}")
    print(f"   Amount: KES {suspicious_tx['amount']:,.2f}")
    print(f"   Risk Score: {result['risk_score']:.3f}")
    print(f"   Risk Level: {result['risk_level']}")
    print(f"   Fraud Detected: {result['is_fraud']}")


def example_2_with_explanation():
    """Example 2: Get explanation for predictions."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Fraud Prediction with Explanation")
    print("="*60)
    
    client = SafariShieldClient()
    
    # Transaction that might be flagged
    transaction = create_sample_transaction("TX_EXPLAIN_001", 75000.00, True)
    
    # Get prediction with explanation
    result = client.explain(transaction)
    
    print("\n📋 Transaction Analysis:")
    print(f"   Transaction ID: {result['transaction_id']}")
    print(f"   Risk Score: {result['risk_score']:.3f}")
    print(f"   Risk Level: {result['risk_level']}")
    
    print("\n🔍 Top Factors:")
    for i, factor in enumerate(result['top_factors'][:5], 1):
        print(f"   {i}. {factor['factor']} - {factor['impact']} risk")
    
    print("\n📝 Explanation:")
    print(f"   {result['narrative']}")
    
    print("\n💡 Recommendations:")
    for rec in result['recommendations']:
        print(f"   • {rec}")


def example_3_batch_processing():
    """Example 3: Batch processing multiple transactions."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Batch Transaction Processing")
    print("="*60)
    
    client = SafariShieldClient()
    
    # Create a batch of transactions
    transactions = []
    for i in range(5):
        is_suspicious = i % 2 == 0  # Every other transaction is suspicious
        amount = 1000 * (i + 1)
        tx = create_sample_transaction(
            f"TX_BATCH_{i:03d}",
            amount,
            is_suspicious
        )
        transactions.append(tx)
    
    print(f"📤 Processing {len(transactions)} transactions...")
    start_time = time.time()
    
    # Send batch request
    result = client.bulk_predict(transactions)
    
    elapsed = (time.time() - start_time) * 1000
    
    print(f"\n📥 Batch Results (took {elapsed:.1f}ms):")
    print(f"   Total: {result['total_processed']}")
    print(f"   Total Processed: {result['total_processed']}")
    print("   Failed: 0") 
    
    print("\n📊 Individual Results:")
    for res in result['results']:
        status = "✅" if not res.get('error') else "❌"
        risk = res.get('risk_score', 'N/A')
        fraud = "FRAUD" if res.get('is_fraud') else "OK"
        print(f"   {status} {res['transaction_id']}: risk={risk:.3f} [{fraud}]")


def example_4_monitoring():
    """Example 4: Monitoring and metrics."""
    print("\n" + "="*60)
    print("EXAMPLE 4: System Monitoring")
    print("="*60)
    
    client = SafariShieldClient()
    
    # Get system metrics
    metrics = client.get_metrics()
    
    print("\n📊 System Metrics:")
    print(f"   Total Predictions: {metrics['total_predictions']:,}")
    print(f"   Fraud Detected: {metrics['fraud_count']:,}")
    print(f"   Fraud Rate: {metrics['fraud_rate']:.2%}")
    print(f"   Avg Response Time: {metrics['avg_response_time_ms']:.1f}ms")
    print(f"   P95 Response Time: {metrics['p95_response_time_ms']:.1f}ms")
    print(f"   Cache Hit Rate: {metrics['cache_hit_rate']:.2%}")
    
    # Get recent predictions
    recent = client.get_recent(5)
    
    print("\n🔄 Recent Predictions:")
    for pred in recent:
        print(f"   • {pred['timestamp']}: {pred['transaction_id']} - risk {pred['risk_score']:.3f}")


def example_5_error_handling():
    """Example 5: Error handling and retries."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Error Handling")
    print("="*60)
    
    client = SafariShieldClient()
    
    # Try with invalid data
    invalid_tx = {
        "transaction_id": "TX_ERROR_001",
        "amount": -100,  # Invalid
        # Missing required fields
    }
    
    try:
        client.predict(invalid_tx)
    except requests.exceptions.HTTPError as e:
        print("\n❌ Expected error caught:")
        print(f"   {e}")
        
        if hasattr(e.response, 'json'):
            error_detail = e.response.json()
            print(f"   Detail: {error_detail.get('detail', 'Unknown error')}")
    
    # Implement retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"\n🔄 Attempt {attempt + 1}/{max_retries}")
            client.health_check()
            print(f"✅ Success on attempt {attempt + 1}")
            break
        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # Exponential backoff
                print(f"   Failed, retrying in {wait}s...")
                time.sleep(wait)
            else:
                print("❌ All retries failed")


def example_6_integration_pattern():
    """Example 6: Integration pattern for payment processing."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Payment Processing Integration")
    print("="*60)
    
    class PaymentProcessor:
        """Simulated payment processor with fraud detection."""
        
        def __init__(self, api_client: SafariShieldClient):
            self.client = api_client
            self.fraud_threshold = 0.7
            
        def process_payment(self, payment_data: Dict) -> Dict:
            """Process a payment with fraud check."""
            # Step 1: Check fraud
            fraud_result = self.client.predict(payment_data)
            
            # Step 2: Make decision
            if fraud_result['risk_score'] >= self.fraud_threshold:
                # High risk - block
                return {
                    'status': 'BLOCKED',
                    'transaction_id': payment_data['transaction_id'],
                    'risk_score': fraud_result['risk_score'],
                    'reason': 'High fraud risk detected',
                    'action': 'Contact customer support'
                }
            elif fraud_result['risk_score'] >= 0.3:
                # Medium risk - verify
                return {
                    'status': 'PENDING',
                    'transaction_id': payment_data['transaction_id'],
                    'risk_score': fraud_result['risk_score'],
                    'reason': 'Additional verification required',
                    'action': 'Send OTP verification'
                }
            else:
                # Low risk - approve
                return {
                    'status': 'APPROVED',
                    'transaction_id': payment_data['transaction_id'],
                    'risk_score': fraud_result['risk_score'],
                    'reason': 'Transaction approved',
                    'action': 'Process payment'
                }
    
    # Use the integration
    client = SafariShieldClient()
    processor = PaymentProcessor(client)
    
    # Test different risk levels
    test_cases = [
        ("TX_PAY_001", 500, False),    # Low risk
        ("TX_PAY_002", 25000, False),  # Medium risk
        ("TX_PAY_003", 95000, True),   # High risk
    ]
    
    for tx_id, amount, suspicious in test_cases:
        transaction = create_sample_transaction(tx_id, amount, suspicious)
        result = processor.process_payment(transaction)
        
        print(f"\n💰 Payment {tx_id}:")
        print(f"   Amount: KES {amount:,.2f}")
        print(f"   Status: {result['status']}")
        print(f"   Risk Score: {result['risk_score']:.3f}")
        print(f"   Action: {result['action']}")


if __name__ == "__main__":
    print("\n🚀 SAFARI-SHIELD API EXAMPLES")
    print("="*60)
    print("Make sure the API is running before executing these examples.")
    print("Run: uvicorn src.api.app:app --reload")
    
    # Run examples
    example_1_basic_prediction()
    example_2_with_explanation()
    example_3_batch_processing()
    example_4_monitoring()
    example_5_error_handling()
    example_6_integration_pattern()
    
    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("="*60)