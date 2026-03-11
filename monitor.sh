#!/bin/bash

# Safari-Shield Monitoring Script

while true; do
    clear
    echo "📊 Safari-Shield Monitoring Dashboard"
    echo "======================================"
    echo ""
    
    # Check service status
    echo "🔍 Service Status:"
    docker-compose ps --services --filter "status=running" | while read service; do
        if docker-compose ps | grep -q "$service.*Up"; then
            echo "   ✅ $service"
        else
            echo "   ❌ $service"
        fi
    done
    
    echo ""
    
    # Get API metrics
    echo "📈 API Metrics:"
    curl -s http://localhost:8000/metrics | grep -E "fraud_predictions_total|fraud_detections_total|prediction_latency" | head -10
    
    echo ""
    
    # Get recent predictions
    echo "🔄 Recent Predictions:"
    curl -s http://localhost:8000/recent | jq -r '.[] | "\(.timestamp): \(.transaction_id) - risk: \(.risk_score)"' | head -5
    
    echo ""
    
    # Check resource usage
    echo "💻 Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -6
    
    sleep 5
done