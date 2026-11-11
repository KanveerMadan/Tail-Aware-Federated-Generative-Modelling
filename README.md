# Federated Generative Transformer for Systemic Risk Modeling

> **Demonstrating privacy-preserving collaborative training for financial risk prediction under non-IID data**

## Problem Statement

Modern financial institutions face "informational myopia"—the data essential for robust risk management is fragmented across competing entities and legally siloed by privacy regulations (GDPR, GLBA). This prevents institutions from accessing a holistic market view, causing conventional predictive frameworks like Value-at-Risk (VaR) to fail during unprecedented disruptions (e.g., COVID-19). Banks rely on limited local datasets that fail to capture complex market dynamics like volatility clustering, leaving the financial ecosystem exposed to unquantified systemic risks.

## Solution

This project demonstrates that multiple financial institutions can collaboratively train a generative Transformer using federated optimization (FedProx) with secure aggregation, producing better tail/volatility modeling than local models while preserving raw-data privacy.

## Key Components

- **Federated Learning**: FedProx algorithm handles non-IID data distribution across banks
- **Secure Aggregation**: Bonawitz-style masking prevents server from accessing plaintext updates
- **Autoregressive Transformer**: Small model (~1.8M params) for next-step return prediction
- **Tail Risk Focus**: Huber loss + VaR evaluation for heavy-tail distributions
- **Non-IID Simulation**: Realistic heterogeneity via temporal, sector, volatility, and correlation shifts

## Architecture

```
+----------------------+       +----------------------+       +----------------------+
| Bank Client 1        |       | Flower Server        |       | Bank Client 2        |
| (process)            | <---> | (local process)      | <-->  | (process)            |
| - local dataset      |       | - orchestrates FL    |       | - local dataset      |
| - local Transformer  |       | - aggregates updates |       | - local Transformer  |
| - masking module     |       | - no plaintext reqd. |       | - masking module     |
+----------------------+       +----------------------+       +----------------------+
        \                         /          |            \         /
         \-- Bank Client 3 -----/           |             \-- Client 4/
                                             |
                                   Secure Aggregation (masked sum)
                                             |
                                   FedProx global update broadcast
```

## Quick Start

### 1. Setup Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Complete Pipeline

```bash
# Run end-to-end demo (creates data, trains all models, evaluates)
bash scripts/run_demo.sh
```

Expected runtime: **3-4 hours** on standard laptop (CPU-only)

### 3. View Results

```bash
# Open analysis notebook
jupyter notebook notebooks/analysis.ipynb

# Check evaluation results
cat outputs/evaluation/results.csv
```

## Manual Execution

### Step 1: Generate Synthetic Bank Data

```bash
python scripts/create_synthetic_banks.py
```

Creates 4 non-IID bank datasets with:
- Different time periods (2015-2022, partitioned)
- Different sectors (tech, finance, energy, healthcare)
- Different volatility regimes
- Different correlation structures (single-ticker vs. portfolio returns)

### Step 2: Train Local Baselines

```bash
# Train per-bank models
python scripts/train_local.py --bank_id 0
python scripts/train_local.py --bank_id 1
python scripts/train_local.py --bank_id 2
python scripts/train_local.py --bank_id 3

# Or train all at once
python scripts/train_local.py --all
```

### Step 3: Train Centralized Oracle (Upper Bound)

```bash
python scripts/train_centralized.py
```

Trains on pooled data (privacy-violating baseline for comparison).

### Step 4: Run Federated Training

```bash
# FedProx (recommended for non-IID)
python scripts/run_federated.py --strategy fedprox --n_rounds 20 --mu 0.01

# FedAvg (comparison baseline)
python scripts/run_federated.py --strategy fedavg --n_rounds 20
```

### Step 5: Evaluate All Models

```bash
python scripts/evaluate.py --output_csv outputs/evaluation/results.csv
```

Computes metrics:
- **VaR estimation error** (95%, 99%)
- **Distributional metrics** (kurtosis, skewness, KS test)
- **Volatility clustering** (ACF of squared residuals)
- **Tail calibration** (Kupiec backtest)

## Frontend

A presentation web app in `web/` walks through the project step by step: data, the four banks, the privacy problem, how training works, an animated replay of the federated rounds, a bank's-view vs server's-view of the masking, results, per-bank predictions and honest takeaways. It reads only JSON exported from the pipeline outputs, never trains or fetches anything, and works fully offline (fonts, icons and libraries are bundled).

Stack: React 18, Vite, TypeScript, Tailwind CSS, Radix UI (shadcn-style components), Framer Motion, Apache ECharts, React Flow, zustand, react-router and react-hotkeys-hook.

```bash
# 1. Run the pipeline (once), then export its results for the site
bash scripts/run_demo.sh
python scripts/export_web_data.py        # writes web/public/data/*.json

# 2. Install and run (Node 18+)
cd web
npm install
npm run dev                              # dev server: http://127.0.0.1:5173

# or the production build
npm run build
npm run preview                          # built site: http://127.0.0.1:4173
```

Keys: ← / → move between steps, the top-right button enters presenter mode (fullscreen, larger type; Space also advances, Esc exits), and the `</>` button opens the command and source code behind each step. If a JSON file is missing, that screen shows a "not available" card instead of numbers.

## Project Structure

```
tgfl/
├── configs/
│   └── default.yaml          # Hyperparameters & settings
├── data/
│   ├── raw/                  # Downloaded yfinance data
│   └── processed/            # Per-bank train/val/test splits
├── docs/
│   ├── figures/              # Publication-ready plots
│   ├── paper_draft.pdf       # Results & methodology
│   └── threat_model.md       # Security analysis
├── notebooks/
│   └── analysis.ipynb        # Interactive results viewer
├── outputs/
│   ├── local/                # Per-bank trained models
│   ├── centralized/          # Oracle model
│   ├── federated/            # FL trained models
│   ├── garch/                # Classical baseline forecasts
│   └── evaluation/           # Metrics & plots
├── scripts/
│   ├── fetch_yfinance.py     # Download financial data
│   ├── create_synthetic_banks.py  # Generate non-IID datasets
│   ├── train_local.py        # Per-bank training
│   ├── train_centralized.py  # Pooled training
│   ├── run_federated.py      # Federated training orchestration
│   ├── evaluate.py           # Compute all metrics
│   └── run_demo.sh           # End-to-end pipeline
├── src/
│   ├── data/
│   │   └── dataset.py        # PyTorch Dataset for time series
│   ├── eval/
│   │   └── metrics.py        # VaR, ACF, tail metrics
│   ├── flwr/
│   │   ├── client.py         # FedProx client implementation
│   │   └── server_strategy.py  # Custom FL strategy
│   ├── models/
│   │   ├── transformer_ts.py  # Autoregressive Transformer
│   │   └── garch_baseline.py  # Classical GARCH model
│   └── privacy/
│       └── masking.py        # Bonawitz-style secure aggregation
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

## Success Criteria

- Federated model yields statistically better tail modeling than local models (lower VaR estimation error at 95%/99%)

- FedProx converges under non-IID simulation where FedAvg underperforms

- Secure aggregation prevents server access to plaintext updates (verified mask cancellation)

- Runs on standard laptop (CPU only) within 4 hours

## Threat Model & Limitations

### Protected
- Raw data never leaves client institutions
- Server cannot recover individual updates from masked aggregates
- Non-IID heterogeneity handled via FedProx

### NOT Protected (MVP Limitations)
- Gradient inversion attacks (would need differential privacy)
- Model memorization of sensitive patterns
- Byzantine faults / malicious clients
- Network-level adversaries (single-machine simulation)

**Status:** Research-grade privacy prototype. Production deployment requires:
- Differential privacy (Opacus integration)
- Secure multiparty computation or trusted execution environments
- Byzantine-robust aggregation
- Regulatory compliance audit

## Key Technologies

- **Language**: Python 3.10+
- **ML Framework**: PyTorch 2.1
- **Federated Learning**: Flower 1.6
- **Data**: yfinance, Pandas, NumPy
- **Classical Models**: arch (GARCH)
- **Config**: Hydra
- **Viz**: Matplotlib, Seaborn

## Results Preview

Expected improvements with FedProx over local models:
- **VaR(95) error**: 15-30% reduction
- **VaR(99) error**: 20-40% reduction
- **Kurtosis capture**: Better heavy-tail modeling
- **Volatility clustering**: Improved ACF structure

*(Full results in `outputs/evaluation/` after running experiments)*

## Citation

If you use this code for research, please cite:

```
@misc{tgfl2026,
  title={Federated Generative Transformer for Systemic Risk Modeling},
  author={MVP Research Team},
  year={2026},
  note={Open-source implementation}
}
```

## License

MIT License - See LICENSE file for details