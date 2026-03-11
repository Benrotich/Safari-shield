# SAFARI-SHIELD Complete Demo Script (Windows PowerShell)

Write-Host "========================================="
Write-Host " SAFARI-SHIELD DEMONSTRATION"
Write-Host "========================================="
Write-Host ""

# Step 1: Show project structure

Write-Host " STEP 1: Project Structure"
Write-Host "-----------------------------------------"
Get-ChildItem
Start-Sleep -Seconds 2

# Step 2: Generate sample data

Write-Host ""
Write-Host " STEP 2: Generating Sample Data"
Write-Host "-----------------------------------------"
python run_data_generation.py --sample
Start-Sleep -Seconds 2

# Step 3: Show the generated data

Write-Host ""
Write-Host " STEP 3: Exploring Generated Data"
Write-Host "-----------------------------------------"
python -c "
import pandas as pd
df = pd.read_csv('data/synthetic/mpesa_transactions.csv')
print('Loaded', len(df), 'transactions')
print('Columns:', list(df.columns))
print('Fraud Rate:', round(df['is_fraud'].mean()*100,2),'%')
print('\nSample transactions:')
print(df[['transaction_id','amount','is_fraud']].head())
"
Start-Sleep -Seconds 3

# Step 4: Run preprocessing

Write-Host ""
Write-Host " STEP 4: Feature Engineering"
Write-Host "-----------------------------------------"
python run_preprocessing.py --input data/synthetic/mpesa_sample.csv
Start-Sleep -Seconds 2

# Step 5: Train a quick model

Write-Host ""
Write-Host " STEP 5: Training Model (Quick Mode)"
Write-Host "-----------------------------------------"
python run_models_training.py --models xgboost --no-tune
Start-Sleep -Seconds 2

# Step 6: Show model performance

Write-Host ""
Write-Host "STEP 6: Model Performance"
Write-Host "-----------------------------------------"

python show_model_performance.py

# Step 7: Generate explanation

Write-Host ""
Write-Host " STEP 7: Explainable AI Demo"
Write-Host "-----------------------------------------"
python run_xai.py --instance-idx 0 --method shap
Start-Sleep -Seconds 2

# Step 8: API info

Write-Host ""
Write-Host " STEP 8: Starting API (optional)"
Write-Host "-----------------------------------------"
Write-Host "To start the API run:"
Write-Host "uvicorn src.api.app:app --reload"
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "========================================="
Write-Host " DEMO COMPLETE!"
