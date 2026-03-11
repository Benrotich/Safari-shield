"""
Prometheus metrics for monitoring the fraud detection system.
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CollectorRegistry
import time
from functools import wraps
import psutil
import os

# Create custom registry
registry = CollectorRegistry()

# Prediction metrics
prediction_counter = Counter(
    'fraud_predictions_total',
    'Total number of fraud predictions',
    ['model_version', 'risk_level'],
    registry=registry
)

fraud_counter = Counter(
    'fraud_detections_total',
    'Total number of fraud detections',
    ['model_version'],
    registry=registry
)

prediction_latency = Histogram(
    'fraud_prediction_latency_seconds',
    'Prediction latency in seconds',
    ['model_version'],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=registry
)

# Cache metrics
cache_hits = Counter(
    'cache_hits_total',
    'Total number of cache hits',
    registry=registry
)

cache_misses = Counter(
    'cache_misses_total',
    'Total number of cache misses',
    registry=registry
)

# System metrics
active_requests = Gauge(
    'active_requests',
    'Number of active requests',
    registry=registry
)

memory_usage = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    registry=registry
)

cpu_usage = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage',
    registry=registry
)

# Business metrics
high_risk_transactions = Counter(
    'high_risk_transactions_total',
    'Total number of high-risk transactions',
    ['risk_level'],
    registry=registry
)

blocked_transactions = Counter(
    'blocked_transactions_total',
    'Total number of blocked transactions',
    registry=registry
)

# Model metrics
model_accuracy = Gauge(
    'model_accuracy',
    'Current model accuracy',
    registry=registry
)

model_precision = Gauge(
    'model_precision',
    'Current model precision',
    registry=registry
)

model_recall = Gauge(
    'model_recall',
    'Current model recall',
    registry=registry
)


def track_latency(model_version="v1"):
    """Decorator to track prediction latency."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                latency = time.time() - start_time
                prediction_latency.labels(model_version=model_version).observe(latency)
        return wrapper
    return decorator


def update_system_metrics():
    """Update system metrics."""
    memory_usage.set(psutil.Process(os.getpid()).memory_info().rss)
    cpu_usage.set(psutil.cpu_percent(interval=1))


class MetricsMiddleware:
    """ASGI middleware for tracking metrics."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # Increment active requests
        active_requests.inc()
        
        start_time = time.time()
        
        async def wrapped_send(message):
            if message["type"] == "http.response.start":
                # Track response time
                duration = time.time() - start_time
                prediction_latency.observe(duration)
            
            await send(message)
        
        try:
            await self.app(scope, receive, wrapped_send)
        finally:
            active_requests.dec()
            update_system_metrics()


def get_metrics():
    """Get all metrics in Prometheus format."""
    return generate_latest(registry)


# Export metrics endpoint for FastAPI
def setup_metrics(app):
    """Setup metrics endpoint for FastAPI."""
    from fastapi import Response
    
    @app.get("/metrics")
    async def metrics():
        return Response(
            content=get_metrics(),
            media_type="text/plain"
        )
    
    # Add middleware
    app.add_middleware(MetricsMiddleware)
    
    return app