"""
Explainable AI module for fraud detection models.
FULL VERSION — SHAP + LIME + Global importance + Reports
Pylance safe | SHAP v0.44+ compatible | No runtime crashes
"""

from __future__ import annotations

import json  # noqa: F401
import warnings
from datetime import datetime
from typing import Any, List, Optional

import lime.lime_tabular
import numpy as np
import pandas as pd
import shap

warnings.filterwarnings("ignore")


# ============================================================
# MAIN EXPLAINER
# ============================================================

class FraudExplainer:

    def __init__(self, model, feature_names: List[str], model_name: str = "Model"):
        self.model = model
        self.feature_names = feature_names
        self.model_name = model_name

        self.shap_explainer: Any = None
        self.lime_explainer: Any = None
        self.background_data: Any = None
        self.is_fitted = False

    def generate_explanation_report(self, explanation):
        """
        Generate structured explanation report from SHAP/LIME output.
        """
        # Example structure – adapt to your explanation format

        risk_score = explanation.get("prediction_proba", 0) * 100

        if risk_score >= 80:
            risk_level = "HIGH"
        elif risk_score >= 50:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        top_factors = explanation.get("top_features", [])

        return {
            "summary": {
                "risk_score": risk_score,
                "risk_level": risk_level
            },
            "top_factors": top_factors
        }      

    # ========================================================
    # SAFE probability extractor (ANY MODEL)
    # ========================================================
    def _get_proba(self, X) -> float:
        if hasattr(self.model, "predict_proba"):
            p = np.asarray(self.model.predict_proba(X))
            return float(p[0, 1] if p.ndim == 2 else p[0])
        return float(np.asarray(self.model.predict(X))[0])

    # ========================================================
    # SHAP FIT
    # ========================================================
    def fit_shap(self, X_background: pd.DataFrame, sample_size: int = 100):

        print("\n🔧 Initializing SHAP...")

        X_sample = (
            X_background.sample(sample_size, random_state=42)
            if len(X_background) > sample_size else X_background
        )

        self.background_data = X_sample

        try:
            if hasattr(self.model, "feature_importances_"):
                self.shap_explainer = shap.TreeExplainer(self.model)
            else:
                self.shap_explainer = shap.Explainer(self.model, X_sample)
        except Exception:
            self.shap_explainer = shap.Explainer(self.model, X_sample)

        if self.shap_explainer is None:
            raise RuntimeError("SHAP initialization failed")

        self.is_fitted = True
        print("✅ SHAP ready")

    # ========================================================
    # LIME FIT
    # ========================================================
    def fit_lime(self, X_train: pd.DataFrame):

        print("\n🔧 Initializing LIME...")

        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            training_data=np.asarray(X_train),
            feature_names=self.feature_names,
            class_names=["Legitimate", "Fraud"],
            mode="classification",
            discretize_continuous=True,
            random_state=42,
        )

        print("✅ LIME ready")

    # ========================================================
    # SHAP EXPLAIN
    # ========================================================
    def explain_with_shap(self, X_instance: pd.DataFrame, instance_id: Optional[str] = None):
        if not self.is_fitted or self.shap_explainer is None:
            raise ValueError("Run fit_shap() first")

        # Get prediction probability
        prediction = self._get_proba(X_instance)

        # Compute SHAP values
        shap_out = self.shap_explainer(X_instance)

        # Extract SHAP values and base values safely
        if hasattr(shap_out, "values"):
            shap_values_array = np.asarray(shap_out.values)
            base_values_array = np.asarray(shap_out.base_values)
        else:
            shap_values_array = np.asarray(shap_out)
            base_values_array = np.asarray(getattr(self.shap_explainer, "expected_value", 0))

        # Handle multi-class output
        if shap_values_array.ndim == 3:
            shap_values_array = shap_values_array[:, :, 1]

        # Flatten base values and get a scalar
        base_values_array = np.asarray(base_values_array).flatten()
        base_value = float(base_values_array[0])

        # Get first instance's SHAP row
        shap_row = shap_values_array[0]

        return {
            "instance_id": instance_id or "unknown",
            "model_name": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "prediction": prediction,
            "prediction_class": "Fraud" if prediction >= 0.5 else "Legitimate",
            "confidence": prediction if prediction >= 0.5 else 1 - prediction,
            "shap_values": shap_row.tolist(),
            "feature_names": self.feature_names,
            "base_value": base_value,
            "feature_importance": self._feature_importance(shap_row, X_instance),
        }

    # ========================================================
    # LIME EXPLAIN
    # ========================================================
    def explain_with_lime(self, X_instance: pd.DataFrame, instance_id=None, num_features=10):

        if self.lime_explainer is None:
            raise ValueError("Run fit_lime() first")

        prediction = self._get_proba(X_instance)

        exp = self.lime_explainer.explain_instance(
            data_row=np.asarray(X_instance)[0],
            predict_fn=self.model.predict_proba,
            num_features=num_features,
            top_labels=1,
        )

        # Get predicted class dynamically
        predicted_class = int(self.model.predict(np.asarray(X_instance))[0])

        # Ensure label exists in LIME explanation
        available_labels = list(exp.local_exp.keys())

        if predicted_class not in available_labels:
            predicted_class = available_labels[0]

        lime_features = [
            {"feature": f, "importance": float(v)}
            for f, v in exp.as_list(label=predicted_class)
]

        return {
            "instance_id": instance_id or "unknown",
            "model_name": self.model_name,
            "timestamp": datetime.now().isoformat(),
            "prediction": prediction,
            "prediction_class": "Fraud" if prediction >= 0.5 else "Legitimate",
            "confidence": prediction if prediction >= 0.5 else 1 - prediction,
            "lime_features": lime_features,
        }

    # ========================================================
    # GLOBAL SHAP
    # ========================================================
    def get_global_shap_values(self, X: pd.DataFrame, sample_size=1000):

        if not self.is_fitted:
            raise ValueError("Run fit_shap() first")

        X_sample = X.sample(sample_size, random_state=42) if len(X) > sample_size else X

        shap_out = self.shap_explainer(X_sample)

        values = np.asarray(shap_out.values if hasattr(shap_out, "values") else shap_out)

        if values.ndim == 3:
            values = values[:, :, 1]

        mean_shap = np.abs(values).mean(axis=0)

        importance_df = (
            pd.DataFrame({"feature": self.feature_names, "importance": mean_shap})
            .sort_values("importance", ascending=False)
        )

        return {
            "mean_shap_values": mean_shap.tolist(),
            "importance_df": importance_df,
            "top_features": importance_df.head(20).to_dict("records"),
        }

    # ========================================================
    # FEATURE IMPORTANCE
    # ========================================================
    def _feature_importance(self, shap_row, X_instance):

        vals = np.asarray(X_instance)[0]
        out = []

        for i, f in enumerate(self.feature_names):
            out.append({
                "feature": f,
                "shap_value": float(shap_row[i]),
                "feature_value": float(vals[i]) if i < len(vals) else None,
                "impact": "increases" if shap_row[i] > 0 else "decreases",
                "magnitude": abs(float(shap_row[i])),
            })

        out.sort(key=lambda x: x["magnitude"], reverse=True)
        return out


# ============================================================
# BATCH EXPLAINER
# ====================================================
class BatchExplainer:

    def __init__(self, explainer):
        self.explainer = explainer
        self.explanations = []

    def explain_batch(self, X, method="shap", save_path=None):
        """Explain a batch of transactions."""
        self.explanations = []

        for i in range(len(X)):
            instance = X.iloc[[i]]

            if method == "shap":
                exp = self.explainer.explain_with_shap(
                    instance,
                    instance_id=f"BATCH_{i}"
                )
            else:
                exp = self.explainer.explain_with_lime(instance)

            self.explanations.append(exp)

            # OPTIONAL save
            if save_path:
                from xai.visualizations import ExplanationExporter
                ExplanationExporter.to_json(self.explanations, save_path)

            return self.explanations

    

        

    # --------------------------------------------------
    # SUMMARY (FIXED)
    # --------------------------------------------------
    def get_explanation_summary(self):
        """Return summary dataframe of batch explanations."""
        if not self.explanations:
            import pandas as pd
            return pd.DataFrame()

        rows = []
        for e in self.explanations:

            risk_score = float(e.get("prediction", 0)) * 100
            if risk_score >= 80:
                risk_level = "HIGH"
            elif risk_score >= 50:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"
            rows.append({
                "transaction_id": e.get("instance_id"),
                "prediction": e.get("prediction"),
                "risk_score": float(e.get("prediction", 0)) * 100,
                "risk_level": risk_level, 
                "decision": e.get("prediction_class"),
                "confidence": e.get("confidence", 0)
            })

        import pandas as pd
        return pd.DataFrame(rows)

