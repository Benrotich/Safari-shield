"""
Visualization utilities for explainable AI.
Creates interactive and static visualizations of model explanations.
"""

import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import json
import os
import warnings

warnings.filterwarnings("ignore")


# =====================================================
# VISUALIZER
# =====================================================
class XAIVisualizer:
    """Create visualizations for model explanations."""

    # --------------------------------------------------
    # SHAP WATERFALL
    # --------------------------------------------------
    @staticmethod
    def plot_shap_waterfall(explanation: Dict) -> go.Figure:
        features = explanation.get("feature_importance", [])[:10]
        if not features:
            return go.Figure()

        names = [f["feature"] for f in features]
        values = [float(f["shap_value"]) for f in features]
        base = float(explanation.get("base_value", 0))

        cumulative = [base]
        for v in values:
            cumulative.append(cumulative[-1] + v)

        fig = go.Figure(go.Waterfall(
            orientation="h",
            measure=["relative"] * len(values) + ["total"],
            y=names + ["Final score"],
            x=values + [cumulative[-1]],
            text=[f"{v:.3f}" for v in values] + [f"{cumulative[-1]:.3f}"],
        ))

        fig.update_layout(title="SHAP Waterfall – Feature Contribution", height=500)
        return fig

    # --------------------------------------------------
    # SHAP SUMMARY
    # --------------------------------------------------
    @staticmethod
    def plot_shap_summary(
        shap_values: np.ndarray,
        features: pd.DataFrame,
        feature_names: List[str],
        max_display: int = 20,
    ) -> go.Figure:

        if shap_values is None or len(shap_values) == 0:
            return go.Figure()

        shap_values = np.array(shap_values)
        mean_shap = np.abs(shap_values).mean(axis=0)
        top_idx = np.argsort(mean_shap)[-max_display:]

        rows = []
        for idx in top_idx:
            fname = feature_names[idx]
            for s, f in zip(shap_values[:, idx], features.iloc[:, idx]):
                rows.append(
                    {
                        "feature": fname,
                        "shap_value": float(s),
                        "feature_value": float(f),
                    }
                )

        df = pd.DataFrame(rows)

        fig = px.scatter(
            df,
            x="shap_value",
            y="feature",
            color="feature_value",
            title="SHAP Summary Plot",
        )
        fig.update_layout(height=600)
        return fig

    # --------------------------------------------------
    # FEATURE IMPORTANCE BAR
    # --------------------------------------------------
    @staticmethod
    def plot_feature_importance_bar(
        importance_df: pd.DataFrame, title: str = "Feature Importance", top_n: int = 20
    ) -> go.Figure:

        if importance_df is None or importance_df.empty:
            return go.Figure()

        df = importance_df.head(top_n)

        fig = go.Figure(go.Bar(x=df["importance"], y=df["feature"], orientation="h"))
        fig.update_layout(
            title=title,
            height=max(400, top_n * 20),
            yaxis={"categoryorder": "total ascending"},
        )
        return fig

    # --------------------------------------------------
    # LIME PLOT
    # --------------------------------------------------
    @staticmethod
    def plot_lime_explanation(explanation: Dict) -> Optional[Figure]:

        if "lime_features" not in explanation:
            return None

        features = explanation["lime_features"]
        names = [f["feature"] for f in features]
        values = [float(f["importance"]) for f in features]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(names, values)
        ax.set_title("LIME Feature Importance")
        ax.set_xlabel("Importance")
        plt.tight_layout()
        return fig
    class ExplanationVisualizer:

       def plot(self):
        from plotly.subplots import make_subplots
        import plotly.graph_objects as go

        fig = make_subplots(rows=1, cols=2)

        fig.add_trace(go.Scatter(y=[1, 3, 2]), row=1, col=1)
        fig.add_trace(go.Bar(y=[2, 1, 3]), row=1, col=2)

        fig.show()



# =====================================================
# EXPORTER
# =====================================================
class ExplanationExporter:
    """Export explanations to files."""

    # --------------------------------------------------
    # HTML EXPORT
    # --------------------------------------------------
    @staticmethod
    def to_html(explanation: Dict, path: str):
        html_content = f"""
        <html>
        <head>
            <title>Fraud Explanation Report</title>
            <style>
                body {{ font-family: Arial; margin: 40px; }}
                .box {{ background:#f4f4f4; padding:15px; border-radius:8px; }}
            </style>
        </head>
        <body>
            <h2>Fraud Prediction Explanation</h2>
            <div class="box">
                <p><b>Transaction ID:</b> {explanation.get('instance_id','N/A')}</p>
                <p><b>Prediction:</b> {explanation.get('prediction_class','N/A')}</p>
                <p><b>Risk Score:</b> {float(explanation.get('prediction',0))*100:.2f}%</p>
                <p><b>Confidence:</b> {explanation.get('confidence',0):.2%}</p>
            </div>
            <h3>Top Factors</h3>
            <ul>
        """

        for f in explanation.get("feature_importance", [])[:10]:
            html_content += f"""
            <li><b>{f.get('feature')}</b> :
            value={f.get('feature_value','N/A')} ,
            impact={float(f.get('shap_value',0)):.4f}</li>
            """

        html_content += "</ul></body></html>"

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_content)

    # --------------------------------------------------
    # JSON EXPORT (FIXED — accepts dict OR list)
    # --------------------------------------------------
    @staticmethod
    def to_json(explanation, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        def convert(obj):
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, (np.ndarray,)):
                return obj.tolist()
            return str(obj)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(explanation, f, indent=2, default=convert)

    # --------------------------------------------------
    # CSV EXPORT
    # --------------------------------------------------
    @staticmethod
    def to_csv(explanations: List[Dict], path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)

        rows = []
        for e in explanations:
            rows.append(
                {
                    "transaction_id": e.get("instance_id"),
                    "prediction": e.get("prediction"),
                    "risk_score": float(e.get("prediction", 0)) * 100,
                }
            )

        pd.DataFrame(rows).to_csv(path, index=False)
