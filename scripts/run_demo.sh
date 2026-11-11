#!/bin/bash
# End-to-end demo pipeline for Federated Transformer MVP
#
# This script runs the complete workflow:
# 1. Fetch financial data
# 2. Create non-IID bank datasets
# 3. Train local models
# 4. Train centralized oracle
# 5. Run federated training (FedProx and FedAvg)
# 6. Evaluate all models
# 7. Generate analysis notebook

set -e  # Exit on error

echo "======================================================================"
echo "FEDERATED TRANSFORMER FOR SYSTEMIC RISK MODELING - MVP DEMO"
echo "======================================================================"
echo ""
echo "This will run the complete pipeline (~3-4 hours on standard laptop)"
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected"
    echo "   Recommended: activate venv before running"
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 1: Fetch financial data
echo ""
echo "======================================================================"
echo "STEP 1/7: Fetching Financial Data from Yahoo Finance"
echo "======================================================================"
python scripts/fetch_yfinance.py

# Step 2: Create synthetic non-IID banks
echo ""
echo "======================================================================"
echo "STEP 2/7: Creating Non-IID Bank Datasets"
echo "======================================================================"
python scripts/create_synthetic_banks.py

# Step 3: Train local models
echo ""
echo "======================================================================"
echo "STEP 3/7: Training Local Models (Per-Bank Baselines)"
echo "======================================================================"
python scripts/train_local.py --all

# Step 4: Train centralized oracle
echo ""
echo "======================================================================"
echo "STEP 4/7: Training Centralized Oracle (Upper Bound)"
echo "======================================================================"
python scripts/train_centralized.py

# Step 5: Run federated training (FedProx)
echo ""
echo "======================================================================"
echo "STEP 5/7: Running Federated Training (FedProx)"
echo "======================================================================"
python scripts/run_federated.py --strategy fedprox --n_rounds 20 --mu 0.01

# Step 6: Run federated training (FedAvg for comparison)
echo ""
echo "======================================================================"
echo "STEP 6/7: Running Federated Training (FedAvg)"
echo "======================================================================"
python scripts/run_federated.py --strategy fedavg --n_rounds 20

# Step 7: Evaluate all models
echo ""
echo "======================================================================"
echo "STEP 7/7: Evaluating All Models"
echo "======================================================================"
python scripts/evaluate.py --plots

# Summary
echo ""
echo "======================================================================"
echo "[OK] DEMO COMPLETE"
echo "======================================================================"
echo ""
echo "Results are available in:"
echo "  - outputs/local/           (per-bank models)"
echo "  - outputs/centralized/     (oracle model)"
echo "  - outputs/federated/       (federated models)"
echo "  - outputs/evaluation/      (comparative metrics & plots)"
echo ""
echo "Next steps:"
echo "  1. View results:  cat outputs/evaluation/results.csv"
echo "  2. Open notebook: jupyter notebook notebooks/analysis.ipynb"
echo "  3. Check plots:   open outputs/evaluation/plots/"
echo ""
echo "Expected key finding:"
echo "  FedProx should show 15-30% reduction in VaR(95) error vs local models"
echo ""
echo "======================================================================"
