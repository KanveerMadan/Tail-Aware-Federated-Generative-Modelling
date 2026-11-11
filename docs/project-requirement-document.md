# Project Requirement Document (MVP)

## Federated Generative Transformer for Systemic Risk Modeling (Open-source, zero upfront cost)

---

## 1. Objective

Demonstrate that multiple simulated financial institutions (non-IID) can collaboratively train a small generative Transformer using federated optimization (FedProx) and a software-only secure aggregation technique, producing better tail / volatility modeling than local models while preserving raw-data privacy.

## 2. Scope & Deliverables

**Scope (MVP):**

* Single-machine simulation of 3–5 banks as independent clients (processes or threads).
* Small autoregressive Transformer trained federatedly with FedProx.
* Secure aggregation via masking (Bonawitz-style) implementation.
* Evaluation showing improvements in heavy tails, volatility clustering, and VaR estimates versus local baselines.
* Reproducible Jupyter notebook, scripts, and README suitable for reviewers.

**Deliverables:**

* GitHub repo with modular code, configs, and datasets (scripts to fetch).
* Jupyter notebook: experiments + plots.
* PDF: results, threat model, limitations, future work.
* Small demo script to run full pipeline end-to-end locally.

## 3. Success Criteria (measurable)

* Federated model yields statistically better tail modeling than any local model on held-out test sets (e.g., lower VaR estimation error at 95/99%).
* Federated training converges under non-IID simulation where FedAvg either diverges or underperforms; FedProx stabilizes.
* Secure aggregation prevents server access to plaintext local updates in normal operation (documented threat model).
* All code runs on a standard laptop (CPU only) within practical runtime (< several hours for full experiment) and is fully reproducible.

## 4. Constraints & Assumptions

* Zero upfront cost: use free/open-source software and public data; run on a local laptop (no paid cloud or hardware enclaves).
* Reproducible: no proprietary libraries or paid APIs.
* Limited scale: small model sizes to keep runtime reasonable.
* Security: prototype uses masking-based secure aggregation (software simulation), not production-grade cryptography. Document this clearly.
* Regulatory claims: do not claim legal compliance — present privacy as “research-grade” protections and outline next steps for production.

## 5. Tech Stack

* Language: Python 3.10+
* ML: PyTorch
* Federated framework: Flower (flwr)
* DP (optional): Opacus
* Secure aggregation primitives: custom masking implementation (Bonawitz pattern) or PySyft primitives for reference
* Data: yfinance, Pandas, NumPy
* Experiment orchestration: Hydra or simple config files (YAML)
* Visualization: Matplotlib, Seaborn
* Environment: virtualenv / pip / requirements.txt
* Version control: Git + GitHub
* Notebook: Jupyter

## 6. Databases & Data Storage

* Local file storage only (no DB server required)

  * CSV / Parquet files per simulated bank under `data/bank_{i}.parquet`
  * Experiment outputs under `outputs/{run_id}/` (models, plots, metrics, logs)
* Optional lightweight DB: SQLite for experiment metadata (if desired)

## 7. Models & Architecture (model details)

**Model family:** Autoregressive Transformer for time series (lightweight)
**Architecture (suggested default):**

* Input: sequence of log-returns (length = 64)
* Embedding size: 64
* Positional encoding: learned or sinusoidal
* Transformer blocks: 2–4 blocks, 4 attention heads
* Feedforward hidden size: 128
* Output head: linear projecting to next-step return (or distribution parameters)
* Parameters: aim for < 2M parameters

**Loss & training:** MSE for next-step regression OR negative log-likelihood if modeling distribution (e.g., Gaussian mixture head). Use Adam optimizer; learning rate schedule optional.

## 8. Privacy & Secure Aggregation

**MVP choice:** Masking-based secure aggregation (Bonawitz-style) implemented in software:

* Each client generates random masks and pairwise shares to cancel masks at aggregate.
* Server receives masked updates; after aggregation masks cancel, server obtains sum of updates but not individual updates.

**Optional:** add Opacus gradient clipping + Gaussian noise to produce (ε, δ)-DP guarantees for the aggregated model (report ε for experimental noise values).

**Threat model to document:** honest-but-curious server, no collusion between all clients and server, client dropouts managed by masking protocol (describe limitations).

## 9. Phases & Step-by-Step Build Plan

### Phase 0 — Repo & Environment (one commit)

* Create repo skeleton: `src/`, `data/`, `notebooks/`, `configs/`, `outputs/`, `README.md`.
* Add `requirements.txt`, minimal Dockerfile (optional), and run scripts.
* Provide a single reproducible conda/pip environment spec.

### Phase 1 — Data Simulation & Ingestion

Tasks:

1. Implement data fetch scripts: `scripts/fetch_yfinance.py` to download tickers for different bank archetypes.
2. Build `scripts/create_synthetic_banks.py` that:

   * Loads multiple tickers and creates per-bank datasets with different volatility regimes, return distributions, and time windows.
   * Produces `data/bank_{i}` folders with train/val/test splits and rolling windows.
3. Write data loader `src/data/dataset.py` exposing PyTorch Dataset for sequences.

Deliverables: reproducible per-bank parquet files; dataset loader.

### Phase 2 — Baseline Model & Local Training

Tasks:

1. Implement `src/models/transformer_ts.py` — small Transformer module.
2. Implement `scripts/train_local.py` to train model per bank (single process).
3. Produce baseline metrics and plots (return distribution reproduction, kurtosis, ACF).

Deliverables: local baselines and metrics.

### Phase 3 — Federated Layer with Flower + FedProx

Tasks:

1. Create Flower client wrapper `src/flwr/client.py` that trains local Transformer on local dataset and supports custom FedProx objective (add proximal term in local training loop).
2. Implement server strategy `src/flwr/server.py` with FedProx aggregation. (Flower allows custom strategies; implement FedProx parameter μ).
3. Provide run script `scripts/run_federated.sh` to instantiate N simulated clients (different processes) and a local Flower server.

Deliverables: working federated training runs; logs showing convergence behavior.

### Phase 4 — Secure Aggregation (masking)

Tasks:

1. Implement masking protocol in client code: generate random mask tensors, exchange mask seeds or shares with peers (simulate via local IPC or files).
2. Ensure aggregate of masked updates equals sum of updates and individual updates are unrecoverable by the server.
3. Handle client dropouts by precomputed mask shares or recovery logic (document simple assumptions in MVP).

Deliverables: masked aggregation working end-to-end; documented limitations.

### Phase 5 — Evaluation & Metrics

Tasks:

1. Implement evaluation scripts:

   * Compute kurtosis, skew, VaR (95/99) on generated sequences vs ground truth.
   * ACF of squared returns to measure volatility clustering.
   * KS test or distributional similarity metrics.
2. Compare: Local models, Federated (FedAvg), Federated (FedProx), Centralized (oracle) if feasible.
3. Produce visualizations (histograms, QQ plots, ACF, VaR backtest tables).

Deliverables: `notebooks/analysis.ipynb` with results and figures.

### Phase 6 — Optional DP & Ablation

Tasks:

1. Integrate Opacus to produce DP-SGD local updates or add noise at server after aggregation.
2. Report ε for multiple noise scales; plot utility vs privacy curve.
3. Ablation: FedAvg vs FedProx, with and without masking/DP.

Deliverables: DP results and ablation section.

### Phase 7 — Documentation & Paper Artifacts

Tasks:

1. Produce PDF with problem, method, threat model, experiments, results, limitations, and future work.
2. Create README with step-by-step reproducible instructions and expected outputs.
3. Add `run_demo.sh` that executes a full pipeline (data creation → FL training → evaluation) with one command.

Deliverables: paper draft PDF, reproducible scripts.

## 10. Architecture (textual diagram)

```
+----------------------+       +----------------------+       +----------------------+
| Bank Client 1        |       | Flower Server        |       | Bank Client 2        |
| (process)            | <---> | (local process)      | <-->  | (process)            |
| - local dataset      |       | - orchestrates FL    |       | - local dataset      |
| - local Transformer  |       | - aggregates updates |       | - local Transformer  |
| - masking module     |       | - no plaintext reqd. |       | - masking module     |
+----------------------+       +----------------------+       +----------------------+
        \                         /          |            \         /
         \-- Bank Client 3 -----/           |             \-- Client N/
                                             |
                                   Secure Aggregation (masked sum)
                                             |
                                   FedProx global update broadcast
```

Notes:

* All components run on a single machine but as independent processes to simulate network behavior.
* Mask exchange simulated via secure channels (local sockets / temp files).
* Optional: centralized notebook reads `outputs/` to produce plots.

## 11. User Flow (for reviewer / demo)

1. Clone repo and create virtual environment (`pip install -r requirements.txt`).
2. Run `python scripts/create_synthetic_banks.py` to generate per-bank datasets.
3. Run `bash scripts/run_federated.sh --clients 4 --rounds 20 --strategy fedprox` which:

   * Starts Flower server locally.
   * Starts N client processes; clients train locally and send masked updates.
4. Wait for federated rounds to finish.
5. Run `python scripts/evaluate.py --run outputs/latest` to compute metrics and save plots.
6. Open `notebooks/analysis.ipynb` to inspect results and figures.
7. Export figures and attach to the paper draft in `docs/`.

## 12. Evaluation Metrics (explicit)

* Convergence: training loss and validation loss per round.
* Distributional: kurtosis, skewness of generated returns vs real.
* Volatility clustering: ACF of squared returns (plot and ACF decay).
* Tail risk: VaR(95), VaR(99) estimation error and backtesting p-values.
* Statistical tests: KS test / Wasserstein distance between return distributions.
* Privacy: if DP used, report ε, δ for each experiment; otherwise document masking threat model.

## 13. Risks, Limitations & Mitigations

* **Compute limits:** mitigate with very small model sizes and fewer rounds.
* **Masking limitations:** does not provide formal DP; document and add DP later.
* **Non-IID pathology:** FedProx hyperparameter tuning required. Provide default μ and ablation.
* **Reproducibility:** freeze random seeds and provide deterministic configs.
* **Regulatory claims:** do not claim compliance; state prototype research intent.

## 14. Project Timeline (high-level phases for planning only)

* Repo & data scripts → model & local runs → federated integration (FedProx) → secure aggregation → evaluation & notebook → documentation & paper. (Execute sequentially; parallelize where possible.)

## 15. Files & Directory Layout (recommended)

```
/README.md
/requirements.txt
/scripts/
  fetch_yfinance.py
  create_synthetic_banks.py
  run_federated.sh
  train_local.py
/src/
  data/
    dataset.py
  models/
    transformer_ts.py
  flwr/
    client.py
    server_strategy.py
  privacy/
    masking.py
  eval/
    metrics.py
/notebooks/
  analysis.ipynb
/outputs/
/docs/
  paper_draft.pdf
```

## 16. Minimal run commands (examples)

```bash
python scripts/create_synthetic_banks.py
bash scripts/run_federated.sh --clients 4 --rounds 20 --strategy fedprox --mu 0.01
python scripts/evaluate.py --run outputs/latest
jupyter notebook notebooks/analysis.ipynb
```

## 17. Next Steps (post-MVP)

* Replace masking with secure multiparty primitives or PySyft for stronger guarantees.
* Add Opacus DP and publish ε,δ results.
* Evaluate with larger transformer variants and more realistic datasets.
* Consider homomorphic encryption or TEE as production options (move to future work).

---

End of document.
