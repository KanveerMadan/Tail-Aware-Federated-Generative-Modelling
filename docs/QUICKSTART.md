# Quick Start Guide

## Federated Transformer for Systemic Risk Modeling

**Time:** ~3-4 hours for complete pipeline  
**Hardware:** Standard laptop (CPU-only, 8GB+ RAM recommended)

---

## Option 1: One-Command Demo

```bash
# Run entire pipeline end-to-end
bash scripts/run_demo.sh
```

This will automatically:
1. Fetch financial data from Yahoo Finance
2. Create 4 non-IID bank datasets
3. Train local models (per-bank)
4. Train centralized oracle (upper bound)
5. Run federated training (FedProx & FedAvg)
6. Evaluate all models and generate plots

---

## Option 2: Step-by-Step Execution

### Step 0: Environment Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 1: Fetch Data (~5 minutes)

```bash
python scripts/fetch_yfinance.py
```

Creates `data/raw/bank_{0-3}_raw.parquet` with historical stock prices.

### Step 2: Create Non-IID Banks (~2 minutes)

```bash
python scripts/create_synthetic_banks.py
```

Generates `data/processed/bank_{0-3}/` with heterogeneous datasets:
- **Bank 0:** Tech stocks, 2018-2021, high volatility, single-ticker
- **Bank 1:** Finance stocks, 2015-2018, standard, single-ticker
- **Bank 2:** Energy stocks, 2019-2022, regime-switching, weighted portfolio
- **Bank 3:** Healthcare stocks, 2017-2020, equal-weight portfolio

### Step 3: Train Local Models (~30-60 minutes)

```bash
# Train all banks
python scripts/train_local.py --all

# Or train individually
python scripts/train_local.py --bank_id 0
```

Saves models to `outputs/local/bank_{i}/best_model.pt`.

### Step 4: Train Centralized Oracle (~15-30 minutes)

```bash
python scripts/train_centralized.py
```

Trains on pooled data (preserving temporal order). Upper-bound baseline.

### Step 5: Federated Training (~30-60 minutes)

```bash
# FedProx (recommended for non-IID)
python scripts/run_federated.py --strategy fedprox --n_rounds 20 --mu 0.01

# FedAvg (comparison baseline)
python scripts/run_federated.py --strategy fedavg --n_rounds 20
```

Launches Flower server + 4 client processes. Uses secure aggregation masking.

### Step 6: Evaluate (~5 minutes)

```bash
python scripts/evaluate.py --plots
```

Generates:
- `outputs/evaluation/results.csv` - Comprehensive metrics
- `outputs/evaluation/plots/` - Comparison visualizations

### Step 7: Analyze Results

```bash
jupyter notebook notebooks/analysis.ipynb
```

Interactive analysis with visualizations.

---

## Key Files

### Configuration
- `configs/default.yaml` - Hyperparameters (model, training, federated)

### Data
- `data/raw/` - Downloaded stock prices
- `data/processed/bank_{i}/` - Train/val/test splits per bank

### Models
- `outputs/local/bank_{i}/` - Per-bank trained models
- `outputs/centralized/` - Oracle model
- `outputs/federated/` - FL trained models

### Results
- `outputs/evaluation/results.csv` - Metrics comparison
- `notebooks/analysis.ipynb` - Interactive analysis

---

## Expected Results

**Success Criteria:**
- FedProx achieves **15-30% reduction** in VaR(95) error vs local models
- FedProx converges faster than FedAvg under non-IID data
- Secure aggregation masks cancel (verified in logs)
- Total runtime < 4 hours on laptop

**Sample Output:**
```
Model Rankings (VaR 95% Error):
1. centralized_oracle:  0.0045  # Upper bound
2. federated_fedprox:   0.0062  # 23% better than local
3. federated_fedavg:    0.0071
4. local:               0.0080  # Average across banks
5. garch:               0.0095
```

---

## Troubleshooting

### Data Download Issues
```bash
# If yfinance times out, retry:
python scripts/fetch_yfinance.py --bank_id 0  # Download one bank at a time
```

### Memory Errors
```python
# In configs/default.yaml, reduce:
training:
  batch_size: 16  # Default is 32
```

### Flower Connection Issues
```bash
# Check if port 8080 is available:
lsof -i :8080

# Use different port:
python scripts/run_federated.py --server_address 127.0.0.1:8081
```

### Missing Dependencies
```bash
# Install missing packages individually:
pip install torch flwr yfinance pandas numpy matplotlib seaborn
```

---

## Next Steps After Running

1. **Review Results**
   ```bash
   cat outputs/evaluation/results.csv
   ```

2. **Explore Notebook**
   - Open `notebooks/analysis.ipynb`
   - Run all cells for interactive plots

3. **Check Threat Model**
   - Read `docs/threat_model.md`
   - Understand security limitations

4. **Experiment**
   - Modify `configs/default.yaml`
   - Try different FedProx `mu` values
   - Add more federated rounds

---

## Citation

If you use this code:

```bibtex
@software{tgfl2026,
  title = {Federated Generative Transformer for Systemic Risk Modeling},
  author = {MVP Team},
  year = {2026},
  url = {https://github.com/your-repo/tgfl}
}
```

---

## Support

**Issues:** Open GitHub issue  
**Documentation:** See `README.md` and `docs/`  
**Threat Model:** `docs/threat_model.md`

---
