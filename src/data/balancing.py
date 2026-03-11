# src/data/balancing.py

import numpy as np
from imblearn.over_sampling import SMOTE, ADASYN
from imblearn.under_sampling import RandomUnderSampler
from imblearn.combine import SMOTEENN, SMOTETomek
from imblearn.pipeline import Pipeline as ImbPipeline
from typing import Tuple, Any


class DataBalancer:
    """Handle imbalanced fraud dataset"""

    def __init__(self, strategy: str = "smote"):
        self.strategy = strategy.lower()
        self.balancer = None

    def fit_resample(self, X, y):
        """Resample data based on strategy"""

        # -----------------------------
        # Choose balancing strategy
        # -----------------------------
        if self.strategy == "smote":

            balancer = SMOTE(
                sampling_strategy=0.3,  # type: ignore[arg-type]
                random_state=42,
                k_neighbors=5,
            )

        elif self.strategy == "adasyn":

            balancer = ADASYN(
                sampling_strategy=0.3,  # type: ignore[arg-type]
                random_state=42,
                n_neighbors=5,
            )

        elif self.strategy == "combined":

            over = SMOTE(
                sampling_strategy=0.1,  # type: ignore[arg-type]
                random_state=42,
            )
            under = RandomUnderSampler(
                sampling_strategy=0.5,  # type: ignore[arg-type]
                random_state=42,
            )

            balancer = ImbPipeline([("over", over), ("under", under)])

        elif self.strategy == "smoteenn":

            balancer = SMOTEENN(random_state=42)

        elif self.strategy == "smotetomek":  # <-- NEW SUPPORT

            balancer = SMOTETomek(random_state=42)

        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        # Store balancer
        self.balancer = balancer

        # -----------------------------
        # Ensure y is integer numpy array
        # -----------------------------
        y_int = np.asarray(y).astype(int)

        # -----------------------------
        # Fit & resample safely
        # -----------------------------
        
        result: Tuple[Any, Any] = balancer.fit_resample(X, y_int)  # type: ignore
        X_resampled, y_resampled = result

        # -----------------------------
        # Safe counting
        # -----------------------------
        y_resampled_np = np.asarray(y_resampled).astype(int)

        orig_counts = np.bincount(y_int)
        resampled_counts = np.bincount(y_resampled_np)

        print(f"Original distribution: {orig_counts}")
        print(f"Resampled distribution: {resampled_counts}")

        return X_resampled, y_resampled
