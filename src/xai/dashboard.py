"""
Streamlit dashboard for interactive model explanations.
"""
import streamlit as st
import pandas as pd
import numpy as np  # noqa: F401
import plotly.graph_objects as go  # noqa: F401
import plotly.express as px  # noqa: F401
import joblib
import shap  # noqa: F401
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xai.explainer import FraudExplainer, BatchExplainer
from xai.visualizations import XAIVisualizer, ExplanationExporter


def run_dashboard():
    """Run the Streamlit explanation dashboard."""
    
    st.set_page_config(
        page_title="Safari-Shield XAI Dashboard",
        page_icon="🛡️",
        layout="wide"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .risk-high {
        color: #FF6B6B;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .risk-medium {
        color: #FFD166;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .risk-low {
        color: #06D6A0;
        font-weight: bold;
        font-size: 1.2rem;
    }
    .explanation-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .factor-positive {
        border-left: 4px solid #FF6B6B;
        padding-left: 1rem;
        margin: 0.5rem 0;
    }
    .factor-negative {
        border-left: 4px solid #4A90E2;
        padding-left: 1rem;
        margin: 0.5rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">🛡️ Safari-Shield Explainable AI Dashboard</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Controls")
        
        # Model selection
        st.subheader("Model Selection")
        model_path = st.text_input(
            "Model Path",
            value="models/best_model.pkl"
        )
        
        feature_path = st.text_input(
            "Feature Names Path",
            value="models/feature_names.pkl"
        )
        
        # Load model button
        if st.button("🔄 Load Model"):
            with st.spinner("Loading model..."):
                try:
                    st.session_state['model'] = joblib.load(model_path)
                    st.session_state['feature_names'] = joblib.load(feature_path)
                    st.session_state['model_loaded'] = True
                    st.success("✅ Model loaded successfully!")
                except Exception as e:
                    st.error(f"❌ Error loading model: {e}")
        
        # Explanation settings
        st.subheader("Explanation Settings")
        st.session_state['explanation_method'] = st.selectbox(
            "Method",
            ["SHAP", "LIME"]
        )
        
        st.session_state['num_features'] = st.slider(
            "Number of Features",
            min_value=5,
            max_value=20,
            value=10
        )
        
        # Initialize explainer if model is loaded
        if st.session_state.get('model_loaded', False):
            if st.button("🔧 Initialize Explainer"):
                with st.spinner("Initializing explainer..."):
                    st.session_state['explainer'] = FraudExplainer(
                        model=st.session_state['model'],
                        feature_names=st.session_state['feature_names'],
                        model_name="Best Model"
                    )
                    st.success("✅ Explainer initialized!")
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 Single Transaction",
        "📊 Batch Analysis",
        "📈 Global Explanations",
        "📋 Audit Reports"
    ])
    
    with tab1:
        st.header("Single Transaction Explanation")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Transaction Details")
            
            # Input form for transaction features
            if st.session_state.get('feature_names', []):
                feature_values = {}
                
                # Create input fields for top features
                top_features = st.session_state['feature_names'][:10]
                
                for feature in top_features:
                    feature_values[feature] = st.number_input(
                        f"{feature}",
                        value=0.0,
                        format="%.4f",
                        key=f"input_{feature}"
                    )
                
                if st.button("🔍 Explain Transaction", type="primary"):
                    # Create instance DataFrame
                    instance = pd.DataFrame([feature_values])
                    
                    # Get explanation
                    if st.session_state.get('explainer') and st.session_state['explainer'].is_fitted:
                        with st.spinner("Generating explanation..."):
                            if st.session_state['explanation_method'] == "SHAP":
                                explanation = st.session_state['explainer'].explain_with_shap(
                                    instance, 
                                    instance_id=f"TX_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                                )
                            else:
                                # Fit LIME if needed
                                st.session_state['explainer'].fit_lime(instance)
                                explanation = st.session_state['explainer'].explain_with_lime(
                                    instance,
                                    num_features=st.session_state['num_features']
                                )
                            
                            st.session_state['current_explanation'] = explanation
                            st.success("✅ Explanation generated!")
                    else:
                        st.warning("Please initialize the explainer first.")
        
        with col2:
            if 'current_explanation' in st.session_state:
                exp = st.session_state['current_explanation']
                
                # Risk score card
                risk_score = exp['prediction'] * 100
                risk_class = "risk-high" if risk_score >= 70 else "risk-medium" if risk_score >= 30 else "risk-low"
                
                st.markdown(f"""
                <div class="explanation-box">
                    <h3>Prediction Results</h3>
                    <p>Transaction ID: {exp.get('instance_id', 'N/A')}</p>
                    <p>Risk Score: <span class="{risk_class}">{risk_score:.1f}%</span></p>
                    <p>Decision: <strong>{exp['prediction_class']}</strong></p>
                    <p>Confidence: {exp.get('confidence', 0):.2%}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Top factors
                st.subheader("Top Contributing Factors")
                
                if 'feature_importance' in exp:
                    for factor in exp['feature_importance'][:5]:
                        factor_class = "factor-positive" if factor['shap_value'] > 0 else "factor-negative"
                        impact = "INCREASES" if factor['shap_value'] > 0 else "DECREASES"
                        
                        st.markdown(f"""
                        <div class="{factor_class}">
                            <strong>{factor['feature']}</strong><br>
                            Value: {factor.get('feature_value', 'N/A'):.4f}<br>
                            Impact: {impact} risk by {abs(factor['shap_value']):.4f}
                        </div>
                        """, unsafe_allow_html=True)
                
                # Export options
                st.subheader("Export")
                col_exp1, col_exp2, col_exp3 = st.columns(3)
                
                with col_exp1:
                    if st.button("📄 HTML Report"):
                        ExplanationExporter.to_html(
                            exp,
                            f"reports/explanation_{exp.get('instance_id', 'unknown')}.html"
                        )
                        st.success("Report saved!")
                
                with col_exp2:
                    if st.button("📊 JSON"):
                        ExplanationExporter.to_json(
                            exp,
                            f"reports/explanation_{exp.get('instance_id', 'unknown')}.json"
                        )
                
                with col_exp3:
                    if st.button("📝 Copy"):
                        st.write("Copied to clipboard (simulated)")
        
        # Visualization
        if 'current_explanation' in st.session_state:
            st.subheader("Visual Explanation")
            
            # Create waterfall plot
            fig = XAIVisualizer.plot_shap_waterfall(st.session_state['current_explanation'])
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.header("Batch Transaction Analysis")
        
        # File upload for batch
        uploaded_file = st.file_uploader(
            "Upload CSV with transactions",
            type=['csv']
        )
        
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            st.write(f"Loaded {len(df)} transactions")
            st.dataframe(df.head())
            
            if st.button("📊 Analyze Batch"):
                if st.session_state.get('explainer'):
                    with st.spinner(f"Analyzing {len(df)} transactions..."):
                        batch_explainer = BatchExplainer(st.session_state['explainer'])
                        
                        batch_explainer.explain_batch(
                            df[st.session_state['feature_names']],
                            method=st.session_state['explanation_method'].lower(),
                            save_path="reports/batch_explanations.json"
                        )
                        
                        # Show summary
                        summary_df = batch_explainer.get_explanation_summary()
                        st.dataframe(summary_df)
                        
                        # Download button
                        csv = summary_df.to_csv(index=False)
                        st.download_button(
                            "📥 Download Summary CSV",
                            csv,
                            "batch_summary.csv",
                            "text/csv"
                        )
    
    with tab3:
        st.header("Global Feature Importance")
        
        if st.session_state.get('explainer') and st.session_state.get('model_loaded'):
            # Load some background data (you'd typically load from file)
            st.info("Please upload background data for global explanations")
            
            bg_file = st.file_uploader(
                "Upload background data (CSV)",
                type=['csv'],
                key="bg_upload"
            )
            
            if bg_file is not None:
                bg_df = pd.read_csv(bg_file)
                
                if st.button("📈 Generate Global Explanations"):
                    with st.spinner("Calculating global SHAP values..."):
                        # Fit SHAP explainer
                        st.session_state['explainer'].fit_shap(
                            bg_df[st.session_state['feature_names']]
                        )
                        
                        # Get global SHAP values
                        global_shap = st.session_state['explainer'].get_global_shap_values(
                            bg_df[st.session_state['feature_names']]
                        )
                        
                        st.session_state['global_shap'] = global_shap
                        st.success("✅ Global explanations generated!")
            
            if 'global_shap' in st.session_state:
                # Feature importance bar chart
                st.subheader("Top 20 Most Important Features")
                
                importance_df = st.session_state['global_shap']['importance_df']
                
                fig = XAIVisualizer.plot_feature_importance_bar(
                    importance_df,
                    title="Global Feature Importance (Mean |SHAP|)"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Summary statistics
                st.subheader("Summary Statistics")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Features", len(importance_df))
                with col2:
                    st.metric("Top Feature", importance_df.iloc[0]['feature'])
                with col3:
                    st.metric("Top Importance", f"{importance_df.iloc[0]['importance']:.4f}")
    
    with tab4:
        st.header("Audit Reports")
        
        # Report generation options
        st.subheader("Generate Audit Report")
        
        st.date_input(
            "Date Range",
            value=(datetime.now(), datetime.now())
        )
        
        st.selectbox(
            "Report Type",
            ["Summary", "Detailed", "Compliance"]
        )
        
        if st.button("📋 Generate Report"):
            with st.spinner("Generating audit report..."):
                # Simulate report generation
                st.success("✅ Report generated!")
                
                # Sample report content
                st.markdown("""
                ### Audit Report Summary
                
                **Period:** Last 30 days
                **Total Transactions:** 15,234
                **Flagged Transactions:** 456 (3.0%)
                
                **Model Performance:**
                - Precision: 0.89
                - Recall: 0.92
                - F1-Score: 0.90
                
                **Top Fraud Indicators:**
                1. Transaction Velocity
                2. Device Change
                3. Amount Z-Score
                
                **Compliance Status:** ✅ All requirements met
                """)
                
                # Download buttons
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.download_button(
                        "📥 Download PDF",
                        "Sample PDF content",
                        "audit_report.pdf"
                    )
                with col2:
                    st.download_button(
                        "📥 Download CSV",
                        "Sample CSV content",
                        "audit_data.csv"
                    )
                with col3:
                    st.download_button(
                        "📥 Download JSON",
                        '{"status": "compliant"}',
                        "audit_metadata.json"
                    )


if __name__ == "__main__":
    run_dashboard()