#!/usr/bin/env python3
import argparse
import sys
import pandas as pd
from pathlib import Path
from src.data.preprocessing import DataPreprocessor
from src.data.balancing import DataBalancer
from src.data.validation import DataValidator
from sklearn.model_selection import train_test_split
import joblib

def main():
    parser = argparse.ArgumentParser(
        description='Preprocess M-Pesa transaction data and engineer features'
    )
    parser.add_argument('--input', type=str,
                        default='data/synthetic/mpesa_sample.csv',
                        help='Input CSV file path')
    parser.add_argument('--output-dir', type=str,
                        default='data/processed',
                        help='Output directory for processed data')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate data, do not preprocess')
    parser.add_argument('--balance', action='store_true',
                        help='Apply class balancing')
    parser.add_argument('--strategy', type=str,
                        default='smotetomek',
                        choices=['smote', 'adasyn', 'smoteenn', 'smotetomek'],
                        help='Resampling strategy for class imbalance')

    args = parser.parse_args()
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    print("="*60)
    print("🛡️ SAFARI-SHIELD: DATA PREPROCESSING PIPELINE")
    print("="*60)

    # Load data
    print(f"\n📂 Loading data from: {args.input}")
    df = pd.read_csv(args.input)
    print(f"   Shape: {df.shape}")

    # Validate
    print("\n🔍 Validating data...")
    validator = DataValidator()
    validation_results = validator.validate(df)
    is_valid = validation_results.get("is_valid", True) if isinstance(validation_results, dict) else True
    if not is_valid:
        print("❌ Data validation failed!")
        return 1
    else:
        print("✅ Data validation passed")
    if args.validate_only:
        print("\n✅ Validation complete. Exiting.")
        return 0

    # Preprocess
    print("\n🔄 Starting preprocessing pipeline...")
    preprocessor = DataPreprocessor()
    X, y = preprocessor.preprocess(df, fit=True)

    # Save preprocessor
    preprocessor.save_pipeline(f'{args.output_dir}/preprocessing_pipeline.pkl')

    # Handle class imbalance
    if args.balance:
        print(f"\n⚖️ Applying {args.strategy} resampling...")
        balancer = DataBalancer(strategy=args.strategy)
        X, y = balancer.fit_resample(X, y)

    # Save processed data for training
    print(f"\n💾 Saving processed data to: {args.output_dir}")

    # Save full features & target (optional)
    X.to_parquet(f'{args.output_dir}/features.parquet', index=False)
    pd.Series(y, name='is_fraud').to_csv(f'{args.output_dir}/target.csv', index=False)
    feature_names = X.columns.tolist()
    pd.Series(feature_names).to_csv(f'{args.output_dir}/feature_names.csv', index=False)

    # --- Split into Train / Validation / Test ---
    X_train_full, X_test, y_train_full, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_full, y_train_full, test_size=0.25, random_state=42, stratify=y_train_full
    )
    # 0.25 x 0.8 = 0.2 of total dataset as validation

    # Save all splits
    joblib.dump(X_train, f'{args.output_dir}/X_train.pkl')
    joblib.dump(X_val, f'{args.output_dir}/X_val.pkl')
    joblib.dump(X_test, f'{args.output_dir}/X_test.pkl')
    joblib.dump(y_train, f'{args.output_dir}/y_train.pkl')
    joblib.dump(y_val, f'{args.output_dir}/y_val.pkl')
    joblib.dump(y_test, f'{args.output_dir}/y_test.pkl')

    print("\n🎉 Preprocessing complete!")
    print(f"   Features shape: {X.shape}")
    print(f"   Feature count: {len(feature_names)}")
    print(f"   Fraud rate: {y.mean():.2%}")
    print(f"   Train/Val/Test split done: {len(X_train)}/{len(X_val)}/{len(X_test)} samples")

    return 0

if __name__ == '__main__':
    sys.exit(main())
