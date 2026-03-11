"""
FastAPI application for real-time fraud detection.
Provides endpoints for predictions, explanations, and monitoring.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  # noqa: F401
from typing import List, Dict, Optional, Any
import pandas as pd
import numpy as np
import joblib
import redis
import json  # noqa: F401
import os
from datetime import datetime
import logging
import uvicorn
from contextlib import asynccontextmanager
import sys
from fastapi import Query

# Pydantic (Stable v1 style — works perfectly with FastAPI)
from pydantic import BaseModel, Field, validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Redis connection with error handling
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    logger.info("Redis connected successfully")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Running without Redis cache.")
    redis_client = None

# Global variables with proper typing
model: Optional[Any] = None
preprocessor: Optional[Any] = None
explainer: Optional[Any] = None
feature_names: Optional[List[str]] = None
threshold: float = 0.5


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting up Safari-Shield API...")
    try:
        load_models_sync()
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
    yield
    logger.info("🛑 Shutting down Safari-Shield API...")
    if redis_client:
        try:
            redis_client.close()
        except Exception:
            pass


app = FastAPI(
    title="Safari-Shield Fraud Detection API",
    description="Real-time fraud detection for M-Pesa transactions with explainable AI",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================
# Pydantic Models
# ===============================

class TransactionRequest(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction ID")
    customer_id: str = Field(..., description="Customer ID")
    amount: float = Field(..., gt=0, description="Transaction amount in KES")
    transaction_type: str = Field(..., description="Type of transaction")
    sender_msisdn: str = Field(..., description="Sender's phone number")
    receiver_msisdn: str = Field(..., description="Receiver's phone number")
    device_id: str = Field(..., description="Device ID")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    location: Optional[str] = Field(None, description="Transaction location")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    channel: str = Field("USSD", description="Transaction channel")

    @validator('sender_msisdn', 'receiver_msisdn')
    def validate_msisdn(cls, v: str) -> str:
        if not v.startswith('254'):
            raise ValueError('Phone number must start with 254')
        if len(v) != 12:
            raise ValueError('Phone number must be 12 digits')
        return v


class PredictionResponse(BaseModel):
    transaction_id: str
    risk_score: float = Field(..., ge=0, le=1)
    risk_level: str
    is_fraud: bool
    confidence: float
    processing_time_ms: int
    timestamp: datetime
    explanation_id: Optional[str] = None


class ExplanationResponse(BaseModel):
    transaction_id: str
    risk_score: float
    risk_level: str
    top_factors: List[Dict[str, Any]]
    narrative: str
    recommendations: List[str]
    visualization_data: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    redis_connected: bool
    uptime: str
    timestamp: datetime


class MetricsResponse(BaseModel):
    total_predictions: int
    fraud_count: int
    fraud_rate: float
    avg_response_time_ms: float
    p95_response_time_ms: float
    cache_hit_rate: float
    model_version: str
    start_time: datetime


# ===============================
# Model Loading
# ===============================

def load_models_sync():
    global model, preprocessor, explainer, feature_names, threshold

    model_path = os.getenv('MODEL_PATH', 'models/best_model.pkl')
    if os.path.exists(model_path):
        model = joblib.load(model_path)
        logger.info("Model loaded successfully")
    else:
        logger.warning(f"Model file not found: {model_path}")

    preprocessor_path = os.getenv('PREPROCESSOR_PATH', 'models/preprocessing_pipeline.pkl')
    if os.path.exists(preprocessor_path):
        preprocessor = joblib.load(preprocessor_path)
        logger.info("Preprocessor loaded successfully")

    features_path = os.getenv('FEATURES_PATH', 'models/feature_names.pkl')
    if os.path.exists(features_path):
        feature_names = joblib.load(features_path)
        logger.info("Feature names loaded successfully")

    threshold_path = os.getenv('THRESHOLD_PATH', 'models/threshold_info.pkl')
    if os.path.exists(threshold_path):
        threshold_info = joblib.load(threshold_path)
        threshold = threshold_info.get('optimal_threshold', 0.5)

    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.xai.explainer import FraudExplainer
        if model is not None and feature_names is not None:
            explainer = FraudExplainer(model, feature_names, "Production Model")
    except Exception:
        explainer = None


# ===============================
# Utility Functions
# ===============================

def get_model_data(obj):
    return obj.dict()


def preprocess_transaction(transaction: TransactionRequest) -> pd.DataFrame:
    df = pd.DataFrame([get_model_data(transaction)])

    if preprocessor:
        features = preprocessor.transform(df)
        if not isinstance(features, pd.DataFrame):
            if hasattr(features, "toarray"):
                features = pd.DataFrame(features.toarray())
            else:
                features = pd.DataFrame(features)
    else:
        features = df.select_dtypes(include=[np.number])

    return features


def get_risk_level(score: float) -> str:
    if score >= 0.7:
        return "HIGH"
    elif score >= 0.3:
        return "MEDIUM"
    return "LOW"


# ===============================
# Health Endpoint
# ===============================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    redis_connected = False
    if redis_client:
        try:
            redis_connected = bool(redis_client.ping())
        except Exception:
            redis_connected = False

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        model_loaded=model is not None,
        redis_connected=redis_connected,
        uptime="N/A",
        timestamp=datetime.now()
    )


# ===============================
# Metrics Endpoint (FIXED TYPES)
# ===============================

@app.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    if not redis_client:
        return MetricsResponse(
            total_predictions=0,
            fraud_count=0,
            fraud_rate=0.0,
            avg_response_time_ms=0.0,
            p95_response_time_ms=0.0,
            cache_hit_rate=0.0,
            model_version="1.0.0",
            start_time=datetime.now()
        )
    
    total_raw = redis_client.get("stats:total_predictions")
    fraud_raw = redis_client.get("stats:fraud_count")
    hits_raw = redis_client.get("stats:cache_hits")
    misses_raw = redis_client.get("stats:cache_misses")
    
    if isinstance(total_raw, (str, bytes)):
        total = int(total_raw)
    else:
        total = 0

    if isinstance(fraud_raw, (str, bytes)):
        fraud = int(fraud_raw)
    else:
        fraud = 0

    if isinstance(hits_raw, (str, bytes)):
        hits = int(hits_raw)
    else:
        hits = 0

    if isinstance(misses_raw, (str, bytes)):
        misses = int(misses_raw)
    else:
        misses = 0

    fraud_rate = fraud / total if total > 0 else 0.0
    hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0.0

    return MetricsResponse(
        total_predictions=total,
        fraud_count=fraud,
        fraud_rate=fraud_rate,
        avg_response_time_ms=0.0,
        p95_response_time_ms=0.0,
        cache_hit_rate=hit_rate,
        model_version="1.0.0",
        start_time=datetime.now()
    )


# ===============================
# Prediction Endpoint
# ===============================

@app.post("/predict", response_model=PredictionResponse)
async def predict_fraud(transaction: TransactionRequest):
    start_time = datetime.now()
    if model is None:
        risk_score = min(transaction.amount / 100000, 1.0)
    else:
        features = preprocess_transaction(transaction)
        if feature_names:
            feature_df = pd.DataFrame(0, index=[0], columns=feature_names)
            for col in features.columns:
                if col in feature_df.columns:
                    feature_df[col] = features[col].values[0]
            features = feature_df
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(features)
            risk_score = float(probabilities[0, 1])
        else:
            risk_score = float(model.predict(features)[0])
    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

    response_data = PredictionResponse(
        transaction_id=transaction.transaction_id,
        risk_score=risk_score,
        risk_level=get_risk_level(risk_score),
        is_fraud=risk_score >= threshold,
        confidence=abs(risk_score - 0.5) * 2,
        processing_time_ms=processing_time,
        timestamp=datetime.now()
    )

    # ✅ Append to recent transactions
    recent_transactions.append(response_data.dict())

    return response_data
    


@app.post("/explain", response_model=ExplanationResponse)
async def explain_transaction(transaction: TransactionRequest):

    prediction = await predict_fraud(transaction)

    return ExplanationResponse(
        transaction_id=transaction.transaction_id,
        risk_score=prediction.risk_score,
        risk_level=prediction.risk_level,
        top_factors=[
            {"factor": "amount", "impact": prediction.risk_score},
            {"factor": "transaction_type", "impact": 0.2},
        ],
        narrative="Transaction risk determined by transaction amount and behavioral patterns.",
        recommendations=[
            "Verify customer identity",
            "Request OTP confirmation",
            "Flag for manual review if suspicious"
        ]
    )
@app.post("/bulk_predict")
async def bulk_predict(transactions: List[TransactionRequest]):

    results = []

    for tx in transactions:
        prediction = await predict_fraud(tx)
        results.append(prediction)

    return {
        "total_processed": len(results),
        "results": results
    }

# Simple in-memory store for demonstration
recent_transactions = []

@app.get("/recent")
def get_recent(limit: int = Query(5)):
    """
    Return recent predictions as a list of dicts
    """
    # Return last `limit` transactions (demo)
    last_transactions = recent_transactions[-limit:]
    return last_transactions

if __name__ == "__main__":
    uvicorn.run(
        "src.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )