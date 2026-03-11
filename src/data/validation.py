"""
Data validation and quality checks for M-Pesa transactions.
Ensures data quality before feature engineering and model training.
"""

from __future__ import annotations
import pandas as pd
import numpy as np  # noqa: F401
from typing import Dict, List  # noqa: F401
from datetime import datetime  # noqa: F401


class DataValidator:
    """
    Validate transaction data quality and integrity.
    Performs checks to ensure data is suitable for modeling.
    """

    def __init__(self):
        self.validation_results: Dict = {}
        self.quality_score: float = 0.0

    # =========================================================
    # MAIN VALIDATION ENTRY
    # =========================================================
    def validate(self, df: pd.DataFrame) -> Dict:
        """Run all validation checks"""

        print("\n🔍 Running Data Validation...")
        print("=" * 60)

        df = df.copy()

        self._check_missing_values(df)
        self._check_duplicates(df)
        self._check_data_types(df)
        self._check_value_ranges(df)
        self._check_temporal_consistency(df)
        self._check_customer_consistency(df)
        self._check_fraud_distribution(df)

        self._calculate_quality_score()
        self._print_validation_summary()

        return self.validation_results

    # =========================================================
    # CHECKS
    # =========================================================

    def _check_missing_values(self, df: pd.DataFrame):
        missing_counts = df.isnull().sum()
        missing_pct = (missing_counts.astype(float) / len(df)) * 100  # FIXED

        critical_cols = ["transaction_id", "timestamp", "customer_id", "amount"]

        issues = []
        for col in critical_cols:
            if col in df.columns and missing_pct[col] > 0:
                issues.append(f"{col}: {missing_pct[col]:.2f}% missing")

        self.validation_results["missing_values"] = {
            "total_missing": int(missing_counts.sum()),
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
    }


    def _check_duplicates(self, df: pd.DataFrame):
        if "transaction_id" in df.columns:
            dup_ids = int(df["transaction_id"].duplicated().sum())
            dup_rows = int(df.duplicated().sum())

            self.validation_results["duplicates"] = {
                "duplicate_ids": dup_ids,
                "duplicate_rows": dup_rows,
                "status": "PASS" if dup_ids == 0 and dup_rows == 0 else "WARN",
            }
        else:
            self.validation_results["duplicates"] = {
                "status": "SKIPPED",
                "reason": "transaction_id missing",
            }

    def _check_data_types(self, df: pd.DataFrame):
        issues = []

        if "timestamp" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                issues.append("timestamp is not datetime")

        if "amount" in df.columns:
            if not pd.api.types.is_numeric_dtype(df["amount"]):
                issues.append("amount is not numeric")

        self.validation_results["data_types"] = {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
        }

    def _check_value_ranges(self, df: pd.DataFrame):
        issues = []

        if "amount" in df.columns:
            negative = int((df["amount"] < 0).sum())
            zero = int((df["amount"] == 0).sum())
            extreme = int((df["amount"] > 1_000_000).sum())

            if negative > 0:
                issues.append(f"{negative} negative amounts")
            if zero > 0:
                issues.append(f"{zero} zero-value transactions")
            if extreme > 0:
                issues.append(f"{extreme} extremely large amounts")

        self.validation_results["value_ranges"] = {
            "status": "PASS" if not issues else "WARN",
            "issues": issues,
        }

    def _check_temporal_consistency(self, df: pd.DataFrame):
        issues = []

        if "timestamp" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

            invalid_time = int(df["timestamp"].isna().sum())
            if invalid_time > 0:
                issues.append(f"{invalid_time} invalid timestamps")

        self.validation_results["temporal_consistency"] = {
            "status": "PASS" if not issues else "WARN",
            "issues": issues,
        }

    def _check_customer_consistency(self, df: pd.DataFrame):
        issues = []

        if "customer_id" in df.columns:
            unique_customers = df["customer_id"].nunique()
            if unique_customers == 0:
                issues.append("No customers found")

        self.validation_results["customer_consistency"] = {
            "status": "PASS" if not issues else "WARN",
            "issues": issues,
        }

    def _check_fraud_distribution(self, df: pd.DataFrame):
        if "is_fraud" not in df.columns:
            self.validation_results["fraud_distribution"] = {
                "status": "SKIPPED",
                "reason": "is_fraud column missing",
            }
            return

        fraud_rate = float(df["is_fraud"].mean())
        imbalance_ratio = float(
            df["is_fraud"].value_counts(normalize=True).min()
        )

        self.validation_results["fraud_distribution"] = {
            "fraud_rate": fraud_rate,
            "imbalance_ratio": imbalance_ratio,
            "status": "INFO",
        }

    # =========================================================
    # QUALITY SCORE
    # =========================================================

    def _calculate_quality_score(self):
        score = 100

        for check in self.validation_results.values():
            if check.get("status") == "FAIL":
                score -= 30
            elif check.get("status") == "WARN":
                score -= 10

        self.quality_score = max(score, 0)

        self.validation_results["quality_score"] = self.quality_score

    # =========================================================
    # PRINT SUMMARY
    # =========================================================

    def _print_validation_summary(self):
        print("\n📊 VALIDATION SUMMARY")
        print("=" * 60)

        for name, result in self.validation_results.items():
            if name == "quality_score":
                continue

            status = result.get("status", "UNKNOWN")
            print(f"{name.upper():30} : {status}")

        print("=" * 60)
        print(f"Overall Data Quality Score: {self.quality_score}/100")
        print("=" * 60)
