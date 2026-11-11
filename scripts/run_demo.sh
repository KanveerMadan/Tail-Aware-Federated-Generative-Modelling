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

# Non-interactive: warn only
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: No virtual environment detected (continuing)"
    echo ""
fi

# Run from the repo root so the relative paths in configs/default.yaml resolve
cd "$(dirname "$0")/.."
export FLWR_TELEMETRY_ENABLED=0
export RAY_USAGE_STATS_ENABLED=0

# Step 1: Fetch financial data
echo ""
echo "======================================================================"
echo "STEP 1/7: Fetching Financial Data from Yahoo Finance"
echo "======================================================================"
if ! python scripts/fetch_yfinance.py; then
    echo ""
    echo "Yahoo Finance fetch failed -> falling back to synthetic data"
    python scripts/generate_synthetic_data.py
fi
echo "Data source: $(head -n 1 data/raw/SOURCE)"

# Step 2: Create synthetic non-IID banks
echo ""
echo "======================================================================"
echo "STEP 2/7: Creating Non-IID Bank Datasets"
echo "======================================================================"
python scripts/create_synthetic_banks.py

# GARCH(1,1) baseline for every bank
echo ""
echo "======================================================================"
echo "GARCH(1,1) Baselines (all banks)"
echo "======================================================================"
python -c "import sys; sys.path.insert(0, '.'); from src.models.garch_baseline import train_garch_baseline; [train_garch_baseline(b) for b in range(4)]"

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
echo "======================================================================"
