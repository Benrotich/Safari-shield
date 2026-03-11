#!/usr/bin/env python3
"""
Run script for Phase 3: Model Development & Training.
"""
import argparse
import sys
import pandas as pd  # noqa: F401
import numpy as np
import joblib
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / 'src'))

from src.models.train import ModelTrainer
from src.models.ensemble import FraudEnsemble
from src.models.evaluate import ModelEvaluator  # noqa: F401


def main():
    parser = argparse.ArgumentParser(
        description='Train and evaluate fraud detection models'
    )
    parser.add_argument(
        '--data-dir',
        type=str,
        default='data/processed',
        help='Directory containing processed data'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='models',
        help='Directory to save trained models'
    )
    parser.add_argument(
        '--models',
        nargs='+',
        default=['xgboost', 'lightgbm', 'random_forest', 'logistic_regression'],
        help='Models to train'
    )
    parser.add_argument(
        '--tune',
        action='store_true',
        default=True,
        help='Perform hyperparameter tuning'
    )
    parser.add_argument(
        '--ensemble',
        action='store_true',
        default=True,
        help='Create ensemble model'
    )

    args = parser.parse_args()

    # Create output directory
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("🤖 SAFARI-SHIELD: MODEL TRAINING PIPELINE")
    print("=" * 60)

    # 1. Load processed data
    print(f"\n📂 Loading data from: {args.data_dir}")
    data_dir = Path(args.data_dir)

    X_train = joblib.load(data_dir / 'X_train.pkl')
    X_val = joblib.load(data_dir / 'X_val.pkl')
    X_test = joblib.load(data_dir / 'X_test.pkl')
    y_train = joblib.load(data_dir / 'y_train.pkl')
    y_val = joblib.load(data_dir / 'y_val.pkl')
    y_test = joblib.load(data_dir / 'y_test.pkl')

    # Derive feature names safely
    if hasattr(X_train, "columns"):
        feature_names = X_train.columns.tolist()
    else:
        feature_names = [f"feature_{i}" for i in range(X_train.shape[1])]

    # Ensure numpy arrays
    y_train = np.asarray(y_train)
    y_val = np.asarray(y_val)
    y_test = np.asarray(y_test)

    print(" Data loaded:")
    print(f"   Train: {X_train.shape}, Fraud: {y_train.mean()*100:.2f}%")
    print(f"   Val: {X_val.shape}, Fraud: {y_val.mean()*100:.2f}%")
    print(f"   Test: {X_test.shape}, Fraud: {y_test.mean()*100:.2f}%")
    print(f"   Features: {len(feature_names) if feature_names is not None else 'Unknown'}")

    # 2. Initialize trainer
    print("\n Initializing model trainer...")
    trainer = ModelTrainer(random_state=42, n_jobs=-1)
    data = trainer.prepare_data(X_train, X_val, X_test, y_train, y_val, y_test)

    # 3. Train selected models
    model_map = {
        'logistic_regression': trainer.train_logistic_regression,
        'random_forest': trainer.train_random_forest,
        'xgboost': trainer.train_xgboost,
        'lightgbm': trainer.train_lightgbm
    }

    for model_name in args.models:
        if model_name in model_map:
            print(f"\n{'='*60}")
            print(f"Training {model_name}...")
            model_map[model_name](data, tune_hyperparameters=args.tune)

    # 4. Evaluate models
    print("\n Evaluating models...")
    trainer.evaluate_all_models(data)
    trainer.save_best_model("models")

    if hasattr(trainer, "print_results"):
        trainer.print_results()

    # 5. Create ensemble
    if args.ensemble and len(getattr(trainer, "models", {})) > 1:
        print("\n🤝 Creating ensemble model...")

        ensemble_models = {
            name: trainer.models[name]
            for name in ['xgboost', 'lightgbm', 'random_forest']
            if name in trainer.models
        }

        if ensemble_models:
            ensemble = FraudEnsemble(
                models=ensemble_models,
                method='weighted_average'
            )

            # Optimize weights safely
            if hasattr(ensemble, "optimize_weights"):
                ensemble.optimize_weights(X_val, y_val, metric='pr_auc')

            ensemble_proba = ensemble.predict_proba(X_test)
            ensemble_pred = ensemble.predict(X_test)  # noqa: F841

            from sklearn.metrics import average_precision_score
            ensemble_pr_auc = average_precision_score(y_test, ensemble_proba)
            print(f"✅ Ensemble PR-AUC: {ensemble_pr_auc:.4f}")

            trainer.models['ensemble'] = ensemble
            trainer.evaluate_model(ensemble, 'ensemble', data)

    # 6. Save models
    print("\n💾 Saving models...")
    trainer.save_models(args.output_dir)

    # 7. Save feature names
    if feature_names is not None:
        joblib.dump(feature_names, Path(args.output_dir) / 'feature_names.pkl')

    print(f"\n✅ Training complete! Models saved to: {args.output_dir}")

    # Safe best model print
    best = getattr(trainer, "best_model_name", None)
    if isinstance(best, str) and hasattr(trainer, "results"):

        pr_auc = 0.0
        if best in trainer.results:
            model_result = trainer.results[best]
            if isinstance(model_result, dict) and 'test' in model_result:
                test_result = model_result['test']
                if isinstance(test_result, dict) and 'pr_auc' in test_result:
                    pr_auc = float(test_result['pr_auc'])

        print(f"   Best model: {best}")
        print(f"   Test PR-AUC: {pr_auc:.4f}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
