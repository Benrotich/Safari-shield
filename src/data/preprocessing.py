import pandas as pd
import numpy as np
from datetime import datetime  # noqa: F401
from typing import List, Dict, Tuple, Optional, Any  # noqa: F401
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import RobustScaler
from sklearn.pipeline import Pipeline
import warnings
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
import joblib
from scipy import sparse  # noqa: F401

warnings.filterwarnings('ignore')

class TransactionCleaner(BaseEstimator, TransformerMixin):
    def __init__(self, 
                datetime_col: str = 'timestamp',
                amount_col: str = 'amount',
                customer_id_col: str = 'customer_id',
                transaction_id_col: str = 'transaction_id'):
        self.datetime_col = datetime_col
        self.amount_col = amount_col
        self.customer_id_col = customer_id_col
        self.transaction_id_col = transaction_id_col
        
    def fit(self, X: pd.DataFrame, y=None):
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        X[self.datetime_col] = pd.to_datetime(X[self.datetime_col], errors='coerce')
        X = X.dropna(subset=[self.datetime_col])
        X = X[(X[self.amount_col] > 0) & (X[self.amount_col] <= 250000)]
        X = X.drop_duplicates(subset=[self.transaction_id_col], keep='first')
        X = X.sort_values([self.customer_id_col, self.datetime_col])
        return X

class TemporalFeatureEngineer(BaseEstimator, TransformerMixin):
    def __init__(self, datetime_col: str = 'timestamp', customer_id_col: str = 'customer_id'):
        self.datetime_col = datetime_col
        self.customer_id_col = customer_id_col
        self.typical_hours_map: Dict[Any, List[int]] = {}
        
    def fit(self, X: pd.DataFrame, y=None):
        X = X.copy()
        times = pd.to_datetime(X[self.datetime_col])
        temp_df = pd.DataFrame({
            self.customer_id_col: X[self.customer_id_col], 
            'hour': times.dt.hour
        })
        for cust_id, group in temp_df.groupby(self.customer_id_col):
            self.typical_hours_map[cust_id] = group['hour'].value_counts().nlargest(3).index.tolist()
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        t_series = pd.to_datetime(X[self.datetime_col])
        X['hour'] = t_series.dt.hour
        X['day_of_week'] = t_series.dt.day_of_week
        X['is_weekend'] = X['day_of_week'].isin([5, 6]).astype(int)
        
        X['hour_sin'] = np.sin(2 * np.pi * X['hour'] / 24)
        X['hour_cos'] = np.cos(2 * np.pi * X['hour'] / 24)
        
        X = X.sort_values([self.customer_id_col, self.datetime_col])
        
        # FIXED: Explicit cast to Timedelta to avoid "Properties" error on total_seconds
        diff_series = X.groupby(self.customer_id_col)[self.datetime_col].diff()
        X['time_since_last_tx'] = pd.to_timedelta(diff_series).dt.total_seconds() / 3600
        # Fill NaNs with 24 hours (first transaction for each customer)
        X['time_since_last_tx'] = X['time_since_last_tx'].fillna(24)

        
        X['unusual_time'] = [
            0 if h in self.typical_hours_map.get(c, []) else 1 
            for c, h in zip(X[self.customer_id_col], X['hour'])
        ]
        return X

class BehavioralFeatureEngineer(BaseEstimator, TransformerMixin):
    def __init__(self, customer_id_col: str = 'customer_id', 
                timestamp_col: str = 'timestamp', 
                amount_col: str = 'amount', 
                windows_hours: List[int] = [1, 24]):
        self.customer_id_col = customer_id_col
        self.timestamp_col = timestamp_col
        self.amount_col = amount_col
        self.windows_hours = windows_hours
        
    def fit(self, X: pd.DataFrame, y=None):
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        X = X.sort_values([self.customer_id_col, self.timestamp_col])
        
        X_temp = X[[self.customer_id_col, self.amount_col, self.timestamp_col]].copy()
        X_temp = X_temp.set_index(self.timestamp_col)
        
        for window in self.windows_hours:
            w_str = f'{window}h'
            # groupby rolling
            rolled = X_temp.groupby(self.customer_id_col)[self.amount_col].rolling(window=f'{window}h')
            
            # Compute count and sum, fill NaNs with 0
            rolled_count = rolled.count().fillna(0)
            rolled_sum = rolled.sum().fillna(0)
            
            # Assign back to main DataFrame
            X[f'tx_count_{w_str}'] = rolled_count.values
            X[f'tx_sum_{w_str}'] = rolled_sum.values

            
        return X

class FeatureSelector(BaseEstimator, TransformerMixin):
    def __init__(self, target_col: str = 'is_fraud', exclude_cols: Optional[List[str]] = None):
        self.target_col = target_col
        if exclude_cols is None:
            self.exclude_cols = []
        else:
            self.exclude_cols = exclude_cols
            
        self.scaler = RobustScaler()
        self.final_columns: List[str] = []
        
    def fit(self, X: pd.DataFrame, y=None):
        drop_cols = [c for c in self.exclude_cols if c in X.columns]
        if self.target_col in X.columns:
            drop_cols.append(self.target_col)
            
        X_feats = X.drop(columns=drop_cols)
        X_dummies = pd.get_dummies(X_feats)
        self.final_columns = X_dummies.columns.tolist()
        
        num_cols = X_feats.select_dtypes(include=[np.number]).columns
        if not num_cols.empty:
            self.scaler.fit(X_feats[num_cols].fillna(0))
        return self
    
    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X_out = X.copy()
        y = X_out[self.target_col] if self.target_col in X_out.columns else None
        
        drop_cols = [c for c in self.exclude_cols if c in X_out.columns]
        if self.target_col in X_out.columns:
            drop_cols.append(self.target_col)
            
        X_out = X_out.drop(columns=drop_cols)
        num_cols = X_out.select_dtypes(include=[np.number]).columns
        if not num_cols.empty:
            X_out[num_cols] = self.scaler.transform(X_out[num_cols].fillna(0))
            
        X_out = pd.get_dummies(X_out)
        X_out = X_out.reindex(columns=self.final_columns, fill_value=0)
        
        if y is not None:
            X_out[self.target_col] = y.values
        return X_out

def create_mpesa_pipeline():
    return Pipeline([
        ('cleaner', TransactionCleaner()),
        ('temporal', TemporalFeatureEngineer()),
        ('behavioral', BehavioralFeatureEngineer()),
        ('selector', FeatureSelector())
    ])
class DataPreprocessor:
    """
    Full preprocessing pipeline:
    - Cleaning
    - Feature Engineering
    - Encoding
    - Scaling
    """

    def __init__(self):
        self.pipeline = None
        self.numeric_cols = []
        self.categorical_cols = []

    def preprocess(self, df: pd.DataFrame, fit: bool = False):
        """Run full preprocessing"""

        df = df.copy()

        # Target
        y = df["is_fraud"].astype(int)

        # Drop non-feature columns
        drop_cols = [
            "is_fraud",
            "fraud_type",
            "fraud_description",
            "transaction_id",
        ]
        X = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")

        # Detect column types
        self.numeric_cols = X.select_dtypes(include=["int64", "float64"]).columns.tolist()
        self.categorical_cols = X.select_dtypes(include=["object", "category"]).columns.tolist()
        # Split categorical columns by cardinality
        high_card_cols = [c for c in self.categorical_cols if X[c].nunique() > 100]  # adjust threshold
        low_card_cols = [c for c in self.categorical_cols if c not in high_card_cols]
        transformers = []

        if self.numeric_cols:
            transformers.append(("num", StandardScaler(), self.numeric_cols))

        if low_card_cols:
            transformers.append((
                "cat_low",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                low_card_cols
            ))

        if high_card_cols:
            from sklearn.preprocessing import OrdinalEncoder
            transformers.append((
                "cat_high",
                OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1),
                high_card_cols
            ))

        preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder="drop",
        )

        # Fit if needed
        if fit or self.pipeline is None:
            self.pipeline = preprocessor.fit(X)

        X_processed = self.pipeline.transform(X)

        # 🔧 FORCE ndarray (removes spmatrix typing issue completely)
        if not isinstance(X_processed, np.ndarray):
            X_processed = np.asarray(X_processed)

        # Feature names
        # -----------------------------
        feature_names = self.numeric_cols.copy()
        feature_names = self.numeric_cols.copy()

        if low_card_cols:
            feature_names += list(
                self.pipeline.named_transformers_["cat_low"].get_feature_names_out(low_card_cols)
            )

        if high_card_cols:
            # OrdinalEncoder → just use original column names
            feature_names += high_card_cols

        # Convert to DataFrame safely
        X_processed = pd.DataFrame(X_processed, columns=feature_names, index=X.index)
        X_processed.fillna(0, inplace=True)

        return X_processed, y
    def save_pipeline(self, path: str):
        joblib.dump(self.pipeline, path)
        print(f"Pipeline saved to: {path}")

    def load_pipeline(self, path: str):
        self.pipeline = joblib.load(path)
        print(f"Pipeline loaded from: {path}")