"""Data schemas for M-Pesa transactions"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
import re


class TransactionType(str, Enum):
    """M-Pesa transaction types"""
    SEND_MONEY = "send_money"
    WITHDRAW_CASH = "withdraw_cash"
    BUY_GOODS = "buy_goods"
    PAY_BILL = "pay_bill"
    DEPOSIT = "deposit"
    REVERSAL = "reversal"
    AIRTIME = "airtime"
    LOAN_DISBURSEMENT = "loan_disbursement"


class FraudType(str, Enum):
    """Types of fraud"""
    SIM_SWAP = "sim_swap"
    SOCIAL_ENGINEERING = "social_engineering"
    AGENT_FRAUD = "agent_fraud"
    ACCOUNT_TAKEOVER = "account_takeover"
    FAKE_REVERSAL = "fake_reversal"
    IDENTITY_THEFT = "identity_theft"
    PHISHING = "phishing"
    NONE = "none"


class Channel(str, Enum):
    """Transaction channels"""
    USSD = "USSD"
    MOBILE_APP = "Mobile_App"
    AGENT = "Agent"
    WEB = "Web"


class MPesaTransaction(BaseModel):
    """M-Pesa transaction schema"""
    transaction_id: str = Field(..., description="Unique transaction ID")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    customer_id: str = Field(..., description="Customer ID")
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    
    amount: float = Field(..., gt=0, description="Transaction amount in KES")
    sender_msisdn: str = Field(..., description="Sender's phone number")
    receiver_msisdn: str = Field(..., description="Receiver's phone number")
    
    sender_balance_before: float = Field(..., ge=0, description="Sender balance before transaction")
    
    time_since_last_tx_seconds: float = Field(0.0, description="Seconds since customer's last transaction")
    is_high_velocity: bool = Field(False, description="Flag for rapid-fire transactions")
    sender_balance_after: float = Field(..., ge=0, description="Sender balance after transaction")
    
    agent_id: Optional[str] = Field(None, description="Agent ID if applicable")
    location: Optional[str] = Field(None, description="Transaction location")
    device_id: str = Field(..., description="Device ID used for transaction")
    sim_serial: str = Field(..., description="SIM card serial number")
    channel: Channel = Field(..., description="Transaction channel")
    
    is_fraud: bool = Field(False, description="Whether transaction is fraudulent")
    fraud_type: Optional[FraudType] = Field(None, description="Type of fraud if applicable")
    fraud_description: Optional[str] = Field(None, description="Description of fraud")
    
    # Metadata
    processing_time_ms: Optional[int] = Field(None, description="Transaction processing time")
    network_type: Optional[str] = Field(None, description="Network type (2G, 3G, 4G, WiFi)")
    ip_address: Optional[str] = Field(None, description="IP address if available")
    
    @validator('sender_msisdn', 'receiver_msisdn')
    def validate_msisdn(cls, v):
        """Validate MSISDN format (Kenyan numbers)"""
        pattern = r'^254[17][0-9]{8}$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid MSISDN format: {v}")
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        """Validate transaction amount"""
        if v > 250000:  # Maximum transaction limit
            raise ValueError(f"Amount exceeds maximum limit: {v}")
        return v
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "transaction_id": "TX123456789",
                "timestamp": "2024-01-15T10:30:00",
                "customer_id": "CUST001",
                "transaction_type": "send_money",
                "amount": 5000.0,
                "sender_msisdn": "254712345678",
                "receiver_msisdn": "254723456789",
                "sender_balance_before": 15000.0,
                "sender_balance_after": 10000.0,
                "agent_id": "AGENT123",
                "location": "Nairobi CBD",
                "device_id": "DEV001",
                "sim_serial": "SIM123456",
                "channel": "USSD",
                "is_fraud": False,
                "fraud_type": None
            }
        }


class CustomerProfile(BaseModel):
    """Customer behavior profile"""
    customer_id: str
    registration_date: datetime
    total_transactions: int = 0
    total_amount: float = 0.0
    avg_transaction_amount: float = 0.0
    typical_transaction_times: List[int] = []  # List of hours (0-23)
    frequent_counterparties: List[str] = []
    usual_locations: List[str] = []
    device_fingerprint: str = ""
    transaction_frequency_daily: float = 0.0
    risk_score: float = 0.0
    
    # Behavior patterns
    preferred_transaction_types: Dict[str, float] = {}  # type -> frequency
    weekly_pattern: Dict[str, float] = {}  # day_of_week -> activity_level
    hourly_pattern: Dict[int, float] = {}  # hour -> activity_level


class FraudPattern(BaseModel):
    """Patterns for generating fraudulent transactions"""
    pattern_type: FraudType
    characteristics: Dict[str, Any]
    probability: float = 0.01  # Base probability
    severity: str = "high"  # high, medium, low
    
    class Config:
        schema_extra = {
            "example": {
                "pattern_type": "sim_swap",
                "characteristics": {
                    "device_change": True,
                    "unusual_time": True,
                    "large_amount": True,
                    "new_recipient": True
                },
                "probability": 0.005,
                "severity": "high"
            }
        }