-- Create tables for audit logging
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) UNIQUE NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    risk_score DECIMAL(5,4) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    is_fraud BOOLEAN NOT NULL,
    processing_time_ms INTEGER NOT NULL,
    model_version VARCHAR(20),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_predictions_customer ON predictions(customer_id);
CREATE INDEX idx_predictions_timestamp ON predictions(timestamp);
CREATE INDEX idx_predictions_risk ON predictions(risk_level);

CREATE TABLE IF NOT EXISTS explanations (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) REFERENCES predictions(transaction_id),
    explanation_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(50) REFERENCES predictions(transaction_id),
    actual_fraud BOOLEAN NOT NULL,
    feedback_type VARCHAR(20),
    comments TEXT,
    reviewed_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) UNIQUE NOT NULL,
    severity VARCHAR(20) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(50),
    message TEXT NOT NULL,
    details JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS model_metrics (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR(20),
    accuracy DECIMAL(5,4),
    precision DECIMAL(5,4),
    recall DECIMAL(5,4),
    f1_score DECIMAL(5,4),
    roc_auc DECIMAL(5,4),
    pr_auc DECIMAL(5,4),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create views for reporting
CREATE VIEW daily_stats AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_predictions,
    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
    AVG(risk_score) as avg_risk_score,
    AVG(processing_time_ms) as avg_processing_time
FROM predictions
GROUP BY DATE(timestamp)
ORDER BY date DESC;

CREATE VIEW customer_risk AS
SELECT 
    customer_id,
    COUNT(*) as total_transactions,
    SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count,
    AVG(risk_score) as avg_risk_score,
    MAX(risk_score) as max_risk_score,
    MAX(timestamp) as last_transaction
FROM predictions
GROUP BY customer_id
HAVING COUNT(*) > 10;