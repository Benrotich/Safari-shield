#!/usr/bin/env python3
"""
Run script for Phase 4: Explainable AI Integration.
"""
import argparse
import sys
import pandas as pd  # noqa: F401
import numpy as np  # noqa: F401
import joblib
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.xai.explainer import FraudExplainer, BatchExplainer
from src.xai.visualizations import ExplanationExporter

import src.xai.explainer
print(src.xai.explainer.__file__)


def main():
    parser = argparse.ArgumentParser(
        description='Generate explanations for fraud predictions'
    )
    parser.add_argument(
        '--model-path',
        type=str,
        default='models/best_model.pkl',
        help='Path to trained model'
    )
    parser.add_argument(
        '--features-path',
        type=str,
        default='models/feature_names.pkl',
        help='Path to feature names'
    )
    parser.add_argument(
        '--data-path',
        type=str,
        default='data/processed/X_test.pkl',
        help='Path to test data'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='reports',
        help='Output directory for explanations'
    )
    parser.add_argument(
        '--method',
        type=str,
        default='shap',
        choices=['shap', 'lime', 'both'],
        help='Explanation method'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=100,
        help='Number of samples to explain'
    )
    parser.add_argument(
        '--instance-idx',
        type=int,
        default=None,
        help='Index of single instance to explain'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🔍 SAFARI-SHIELD: EXPLAINABLE AI PIPELINE")
    print("=" * 60)
    
    # 1. Load model and data
    print(f"\n📂 Loading model from: {args.model_path}")
    model = joblib.load(args.model_path)
    feature_names = joblib.load(args.features_path)
    
    print(f"✅ Model loaded: {type(model).__name__}")
    print(f"✅ Features: {len(feature_names)}")
    
    print(f"\n📂 Loading data from: {args.data_path}")
    X = joblib.load(args.data_path)
    if args.sample_size and len(X) > args.sample_size:
        X = X.sample(n=args.sample_size, random_state=42)
    print(f"✅ Data loaded: {X.shape}")
    if args.instance_idx is not None and args.instance_idx >= len(X):
        print("❌ Instance index out of range")
        return 1
    
    # 2. Initialize explainer
    print("\n🔧 Initializing explainer...")
    explainer = FraudExplainer(
        model=model,
        feature_names=feature_names,
        model_name=type(model).__name__
    )
    
    # 3. Generate explanations
    if args.instance_idx is not None:
        # Single instance explanation
        print(f"\n🎯 Explaining instance {args.instance_idx}")
        instance = X.iloc[[args.instance_idx]]
        
        if args.method in ['shap', 'both']:
            print("   Using SHAP...")
            explainer.fit_shap(X, sample_size=min(100, len(X)))
            explanation = explainer.explain_with_shap(
                instance,
                instance_id=f"instance_{args.instance_idx}"
            )
            
            # Save explanation
            ExplanationExporter.to_json(
                explanation,
                f"{args.output_dir}/explanation_shap_{args.instance_idx}.json"
            )
            
            # Generate report
            report = explainer.generate_explanation_report(explanation)
            print(f"\n📋 Report for instance {args.instance_idx}:")
            print(f"   Risk Score: {report['summary']['risk_score']:.1f}%")
            print(f"   Risk Level: {report['summary']['risk_level']}")
            print(f"   Top Factor: {report['top_factors'][0]['factor'] if report['top_factors'] else 'None'}")
        
        if args.method in ['lime', 'both']:
            print("   Using LIME...")
            explainer.fit_lime(X)
            explanation = explainer.explain_with_lime(
                instance,
                instance_id=f"instance_{args.instance_idx}"
            )
            
            # Save explanation
            ExplanationExporter.to_json(
                explanation,
                f"{args.output_dir}/explanation_lime_{args.instance_idx}.json"
            )
    
    else:
        # Batch explanation
        print(f"\n📦 Generating {args.method.upper()} explanations for {len(X)} instances...")
        
        if args.method in ['shap', 'both']:
            explainer.fit_shap(X, sample_size=min(100, len(X)))
        
        if args.method in ['lime', 'both']:
            explainer.fit_lime(X)
        
        batch_explainer = BatchExplainer(explainer)
        batch_explainer.explain_batch(
            X,
            method=args.method if args.method != 'both' else 'shap',
            save_path=f"{args.output_dir}/batch_explanations.json"
        )
        
        # Create summary
        summary_df = batch_explainer.get_explanation_summary()
        summary_df.to_csv(f"{args.output_dir}/explanations_summary.csv", index=False)
        print(f"\n📊 Summary saved to: {args.output_dir}/explanations_summary.csv")
        
        # Print summary statistics
        print("\n   Summary Statistics:")
        print(f"   High Risk: {(summary_df['risk_level'] == 'HIGH').sum()}")
        print(f"   Medium Risk: {(summary_df['risk_level'] == 'MEDIUM').sum()}")
        print(f"   Low Risk: {(summary_df['risk_level'] == 'LOW').sum()}")
    
    print(f"\n✅ Explanations saved to: {args.output_dir}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())