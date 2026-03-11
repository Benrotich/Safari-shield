"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import re  # noqa: F401


class TransactionBase(BaseModel):
    """Base transaction schema."""
    transaction_id: str
    customer_id: str
    amount: float = Field(..., gt=0, le=200000)
    transaction_type: str
    sender_msisdn: str
    receiver_msisdn: str
    timestamp: datetime
    device_id: str
    location: Optional[str] = None
    agent_id: Optional[str] = None
    channel: str = "USSD"


class TransactionCreate(TransactionBase):
    """Schema for creating a transaction."""
    pass


class TransactionResponse(TransactionBase):
    """Schema for transaction response with prediction."""
    risk_score: float
    risk_level: str
    is_fraud: bool
    processing_time_ms: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PredictionRequest(BaseModel):
    """Request schema for single prediction."""
    transaction: TransactionCreate


class BatchPredictionRequest(BaseModel):
    """Request schema for batch predictions."""
    transactions: List[TransactionCreate]
    max_concurrent: Optional[int] = 10


class PredictionResult(BaseModel):
    """Individual prediction result."""
    transaction_id: str
    risk_score: float
    risk_level: str
    is_fraud: bool
    confidence: float
    error: Optional[str] = None


class BatchPredictionResponse(BaseModel):
    """Response schema for batch predictions."""
    results: List[PredictionResult]
    total_processed: int
    successful: int
    failed: int
    processing_time_ms: int


class ExplanationFactor(BaseModel):
    """Single factor in explanation."""
    feature: str
    importance: float
    value: float
    impact: str  # 'increases' or 'decreases'


class ExplanationResponse(BaseModel):
    """Explanation response schema."""
    transaction_id: str
    risk_score: float
    risk_level: str
    top_factors: List[ExplanationFactor]
    narrative: str
    recommendations: List[str]
    shap_plot_url: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information."""
    name: str
    version: str
    type: str
    features: List[str]
    feature_count: int
    threshold: float
    metrics: Dict[str, float]
    last_trained: datetime


class SystemHealth(BaseModel):
    """System health status."""
    status: str
    components: Dict[str, bool]
    version: str
    uptime_seconds: float
    active_requests: int
    memory_usage_mb: float
    cpu_percent: float


class AlertConfig(BaseModel):
    """Alert configuration."""
    enabled: bool = True
    webhook_url: Optional[str] = None
    email: Optional[str] = None
    slack_channel: Optional[str] = None
    min_risk_score: float = 0.7
    min_transaction_amount: float = 10000
    cooldown_minutes: int = 5


class Alert(BaseModel):
    """Alert message."""
    alert_id: str
    timestamp: datetime
    severity: str  # 'info', 'warning', 'critical'
    type: str  # 'fraud_detected', 'high_risk', 'system_issue'
    transaction_id: Optional[str] = None
    risk_score: Optional[float] = None
    message: str
    details: Dict[str, Any]