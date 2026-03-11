#!/bin/bash

# Smoke tests for Safari-Shield deployment

ENVIRONMENT=$1
BASE_URL=""

if [ "$ENVIRONMENT" = "staging" ]; then
    BASE_URL="https://staging-api.safari-shield.com"
elif [ "$ENVIRONMENT" = "production" ]; then
    BASE_URL="https://api.safari-shield.com"
else
    echo "Unknown environment: $ENVIRONMENT"
    exit 1
fi

echo "🚀 Running smoke tests for $ENVIRONMENT"

# Test 1: Health check
echo "Test 1: Health check"
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/health)
if [ "$HEALTH" -ne 200 ]; then
    echo "❌ Health check failed: $HEALTH"
    exit 1
fi
echo "✅ Health check passed"

# Test 2: Prediction endpoint
echo "Test 2: Prediction endpoint"
PREDICTION=$(curl -s -X POST $BASE_URL/predict \
    -H "Content-Type: application/json" \
    -d '{
        "transaction_id": "SMOKE_TEST_001",
        "customer_id": "SMOKE_CUST",
        "amount": 1000,
        "transaction_type": "send_money",
        "sender_msisdn": "254712345678",
        "receiver_msisdn": "254723456789",
        "device_id": "SMOKE_DEV",
        "timestamp": "'$(date -Iseconds)'",
        "channel": "USSD"
    }')

if [ $? -ne 0 ]; then
    echo "❌ Prediction failed"
    exit 1
fi
echo "✅ Prediction passed"

# Test 3: Metrics endpoint
echo "Test 3: Metrics endpoint"
METRICS=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/metrics)
if [ "$METRICS" -ne 200 ]; then
    echo "❌ Metrics check failed"
    exit 1
fi
echo "✅ Metrics check passed"

# Test 4: Database connection
echo "Test 4: Database connection"
DB_CHECK=$(kubectl exec -n safari-shield-$ENVIRONMENT deployment/postgres -- pg_isready -U safari)
if [ $? -ne 0 ]; then
    echo "❌ Database check failed"
    exit 1
fi
echo "✅ Database check passed"

# Test 5: Redis connection
echo "Test 5: Redis connection"
REDIS_CHECK=$(kubectl exec -n safari-shield-$ENVIRONMENT deployment/redis-master -- redis-cli ping)
if [ "$REDIS_CHECK" != "PONG" ]; then
    echo "❌ Redis check failed"
    exit 1
fi
echo "✅ Redis check passed"

echo "🎉 All smoke tests passed for $ENVIRONMENT!"