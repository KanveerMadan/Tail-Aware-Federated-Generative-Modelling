#!/usr/bin/env python3
"""
Export pipeline outputs as clean JSON for the presentation frontend (web/).

Reads only files the pipeline already wrote:
  data/raw/bank_*_raw.parquet, data/raw/SOURCE, data/processed/bank_*/*,
  outputs/{local,centralized,garch,federated}/..., outputs/evaluation/results.csv,
  configs/default.yaml
and writes web/public/data/*.json. It never trains or downloads anything.
The only computation is evaluation of saved predictions (same metric code as
scripts/evaluate.py), pooling of per-bank predictions, an "always predict 0"
baseline from the saved targets, and one masking example produced by
src/privacy/masking.py on real model weights.

Usage:  python scripts/export_web_data.py
"""

import argparse
import ast
import importlib.util
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.eval.metrics import comprehensive_evaluation  # noqa: E402

N_BANKS = 4
METRIC_KEYS = [
    "mse", "mae", "rmse", "var_95_error", "var_99_error", "kurtosis_error",
    "skewness_error", "acf_error", "ks_statistic", "wasserstein_distance",
]


# --------------------------------------------------------------------------- utils

def clean(obj):
    """Make an object JSON-safe (numpy -> python, NaN/inf -> None)."""
    if isinstance(obj, dict):
        return {str(k): clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return clean(obj.tolist())
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (pd.Timestamp, datetime)):
        return obj.strftime("%Y-%m-%d")
    return obj


def write_json(out_dir: Path, name: str, payload) -> None:
    path = out_dir / name
    with open(path, "w") as f:
        json.dump(clean(payload), f, separators=(",", ":"))
    print(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KB)")


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def load_npy(path: Path) -> Optional[np.ndarray]:
    return np.load(path).astype(np.float64).reshape(-1) if path.exists() else None


def direction_accuracy(pred: np.ndarray, actual: np.ndarray) -> Optional[float]:
    mask = actual != 0
    if not mask.any():
        return None
    return float(np.mean(np.sign(pred[mask]) == np.sign(actual[mask])))


def evaluate(pred: np.ndarray, actual: np.ndarray) -> Dict:
    """Same metric function as scripts/evaluate.py, plus direction accuracy."""
    with np.errstate(all="ignore"):
        try:
            m = comprehensive_evaluation(pred.reshape(-1, 1), actual.reshape(-1, 1), [0.95, 0.99])
        except Exception:
            # Degenerate predictions (e.g. constant zero) break some tail metrics.
            res = pred - actual
            q = lambda x, c: float(-np.quantile(x, 1 - c))  # noqa: E731
            m = {
                "mse": float(np.mean(res ** 2)),
                "mae": float(np.mean(np.abs(res))),
                "rmse": float(np.sqrt(np.mean(res ** 2))),
                "var_95_error": abs(q(pred, 0.95) - q(actual, 0.95)),
                "var_99_error": abs(q(pred, 0.99) - q(actual, 0.99)),
            }
    out = {k: m.get(k) for k in METRIC_KEYS}
    out["direction_accuracy"] = direction_accuracy(pred, actual)
    out["n"] = int(len(actual))
    return out


def extract_source(path: Path, names: List[str]) -> str:
    """Return the exact source of the named top-level functions/classes/methods."""
    text = path.read_text()
    tree = ast.parse(text)
    chunks = []
    wanted = set(names)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in wanted:
            seg = ast.get_source_segment(text, node)
            if seg:
                indent = node.col_offset
                lines = [ln[indent:] if ln[:indent].strip() == "" else ln for ln in seg.splitlines()]
                chunks.append("\n".join(lines))
                wanted.discard(node.name)
    return "\n\n\n".join(chunks)


# --------------------------------------------------------------------------- sections

def export_source(raw_dir: Path) -> Dict:
    path = raw_dir / "SOURCE"
    if not path.exists():
        return {"available": False}
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    kind = lines[0].lower() if lines else "unknown"
    return {
        "available": True,
        "kind": "real" if kind.startswith("real") else ("synthetic" if kind.startswith("synthetic") else kind),
        "lines": lines,
    }


def export_prices(raw_dir: Path, bank_configs: Dict) -> Dict:
    banks = []
    all_dates = set()
    all_tickers = set()
    for b in range(N_BANKS):
        path = raw_dir / f"bank_{b}_raw.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(path)
        df["date"] = pd.to_datetime(df["date"])
        series = []
        for ticker, g in df.sort_values("date").groupby("ticker", sort=False):
            series.append({
                "ticker": str(ticker),
                "dates": [d.strftime("%Y-%m-%d") for d in g["date"]],
                "close": [round(float(c), 4) for c in g["close"]],
            })
            all_tickers.add(str(ticker))
        all_dates.update(df["date"].dt.strftime("%Y-%m-%d").unique().tolist())
        cfg = bank_configs.get(b, {})
        order = cfg.get("tickers", [])
        series.sort(key=lambda s: order.index(s["ticker"]) if s["ticker"] in order else 99)
        banks.append({
            "bank_id": b,
            "name": cfg.get("name"),
            "sector": cfg.get("sector"),
            "start": df["date"].min(),
            "end": df["date"].max(),
            "n_rows": int(len(df)),
            "series": series,
        })
    if not banks:
        return {"available": False}
    dates = sorted(all_dates)
    return {
        "available": True,
        "n_tickers": len(all_tickers),
        "n_trading_days": len(dates),
        "start": dates[0],
        "end": dates[-1],
        "banks": banks,
    }


def export_banks(processed_dir: Path, bank_configs: Dict, cfg: Dict) -> Dict:
    banks = []
    for b in range(N_BANKS):
        meta_path = processed_dir / f"bank_{b}" / "metadata.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        bc = bank_configs.get(b, {})
        het = meta.get("heterogeneity_config", {})
        banks.append({
            "bank_id": b,
            "name": bc.get("name"),
            "sector": bc.get("sector"),
            "tickers": bc.get("tickers", []),
            "period": [bc.get("start_date"), bc.get("end_date")],
            "description": het.get("description"),
            "correlation_type": het.get("correlation_type"),
            "vol_scale": het.get("vol_scale"),
            "regime_switch": het.get("regime_switch"),
            "n_sequences": meta.get("n_sequences", {}),
            "statistics": meta.get("statistics", {}),
        })
    if not banks:
        return {"available": False}
    return {"available": True, "sequence_length": cfg["data"]["sequence_length"], "banks": banks}


def parse_history(hist: Dict, n_rounds_hint: int) -> List[Dict]:
    """Normalise a federated history.json into a per-round list."""
    if isinstance(hist.get("rounds"), list):
        rounds = []
        for r in hist["rounds"]:
            rounds.append({k: r.get(k) for k in r})
        return rounds

    def series(obj, key):
        vals = (obj or {}).get(key) or []
        return {int(r): float(v) for r, v in vals}

    fit = hist.get("metrics_distributed_fit") or {}
    ev = hist.get("metrics_distributed") or {}
    losses = {int(r): float(v) for r, v in (hist.get("losses_distributed") or [])}
    rounds_idx = sorted(set(losses) | set(series(fit, "train_loss")))
    out = []
    for r in rounds_idx:
        row = {"round": r, "val_loss": losses.get(r)}
        for key in set(fit) | set(ev):
            s = series(fit, key) if key in fit else series(ev, key)
            if r in s:
                row[key if key not in row or row[key] is None else key] = s[r]
        out.append(row)
    return out


def latest_run(fed_dir: Path, strategy: str) -> Optional[Path]:
    if not fed_dir.exists():
        return None
    runs = sorted(p for p in fed_dir.iterdir() if p.is_dir() and p.name.startswith(strategy + "_")
                  and (p / "history.json").exists())
    return runs[-1] if runs else None


def export_federated(fed_dir: Path, cfg: Dict) -> Dict:
    out = {"available": False, "strategies": {}}
    for strategy in ["fedavg", "fedprox"]:
        run = latest_run(fed_dir, strategy)
        if run is None:
            continue
        hist = json.loads((run / "history.json").read_text())
        info = json.loads((run / "run_info.json").read_text()) if (run / "run_info.json").exists() else {}
        run_cfg = yaml.safe_load((run / "config.yaml").read_text()) if (run / "config.yaml").exists() else cfg
        rounds = parse_history(hist, run_cfg["federated"]["n_rounds"])
        out["strategies"][strategy] = {
            "run_id": run.name,
            "mu": info.get("mu", run_cfg["federated"].get("mu")),
            "n_clients": info.get("n_clients", run_cfg["federated"].get("min_fit_clients")),
            "n_rounds": info.get("n_rounds", run_cfg["federated"]["n_rounds"]),
            "use_masking": info.get("use_masking"),
            "local_epochs": run_cfg["training"]["local_epochs"],
            "rounds": rounds,
        }
        out["available"] = True
    return out


def test_sizes(processed_dir: Path) -> List[int]:
    sizes = []
    for b in range(N_BANKS):
        meta = json.loads((processed_dir / f"bank_{b}" / "metadata.json").read_text())
        sizes.append(int(meta["n_sequences"]["test"]))
    return sizes


def reconstruct_test_labels(raw_dir: Path, processed_dir: Path, cfg: Dict, csb) -> Dict[int, Dict]:
    """
    Recover the date (and ticker) of every test target by replaying the exact
    row ordering of scripts/create_synthetic_banks.py. Used only if the replayed
    returns match the saved test targets; otherwise the frontend shows indices.
    """
    out = {}
    L = cfg["data"]["sequence_length"]
    for b in range(N_BANKS):
        try:
            df = pd.read_parquet(raw_dir / f"bank_{b}_raw.parquet")
            hc = csb.HETEROGENEITY_CONFIG[b]
            df = csb.apply_correlation_structure(df, hc)
            df = csb.apply_volatility_transformations(df, hc, cfg["random_seed"] + b)
            df = df.sort_values("date").reset_index(drop=True)
            y_all = df["log_return"].values[L:]
            test_y = pd.read_parquet(processed_dir / f"bank_{b}" / "test.parquet")["y"].values
            n = len(test_y)
            y_tail = y_all[-n:] if len(y_all) >= n else None
            # create_rolling_windows uses range(0, len - L): last target is at index len-1
            if y_tail is not None and np.allclose(y_tail, test_y, atol=1e-12):
                tail = df.iloc[len(df) - n:]
                out[b] = {
                    "dates": pd.to_datetime(tail["date"]).dt.strftime("%Y-%m-%d").tolist(),
                    "tickers": tail["ticker"].astype(str).tolist(),
                }
        except Exception as e:  # pragma: no cover - best effort only
            print(f"  note: could not recover test dates for bank {b}: {e}")
    return out


def export_predictions_and_results(out_root: Path, processed_dir: Path, raw_dir: Path,
                                   cfg: Dict, csb, bank_configs: Dict):
    sizes = test_sizes(processed_dir)
    offsets = np.concatenate([[0], np.cumsum(sizes)])
    fed_dir = out_root / "federated"

    # model key -> (label, group, per-bank arrays or pooled arrays)
    per_bank: Dict[str, Dict[int, np.ndarray]] = {}
    actual: Dict[int, np.ndarray] = {}

    def add_pooled(key: str, preds: Optional[np.ndarray], targets: Optional[np.ndarray]):
        if preds is None or targets is None or len(preds) != offsets[-1]:
            if preds is not None:
                print(f"  note: {key} has {len(preds)} predictions, expected {offsets[-1]}; skipped")
            return
        per_bank[key] = {b: preds[offsets[b]:offsets[b + 1]] for b in range(N_BANKS)}
        for b in range(N_BANKS):
            actual.setdefault(b, targets[offsets[b]:offsets[b + 1]])

    for kind in ["local", "garch"]:
        d = {}
        for b in range(N_BANKS):
            p = load_npy(out_root / kind / f"bank_{b}" / "test_predictions.npy")
            t = load_npy(out_root / kind / f"bank_{b}" / "test_targets.npy")
            if p is not None and t is not None:
                d[b] = p
                actual.setdefault(b, t)
        if d:
            per_bank[kind] = d

    add_pooled("centralized", load_npy(out_root / "centralized" / "test_predictions.npy"),
               load_npy(out_root / "centralized" / "test_targets.npy"))
    fed_runs = {}
    for strategy in ["fedavg", "fedprox"]:
        run = latest_run(fed_dir, strategy)
        if run is not None:
            fed_runs[strategy] = run.name
            add_pooled(strategy, load_npy(run / "test_predictions.npy"), load_npy(run / "test_targets.npy"))

    if not actual:
        return {"available": False}, {"available": False}

    banks_present = sorted(actual)
    per_bank["zero"] = {b: np.zeros_like(actual[b]) for b in banks_present}

    labels = {
        "local": "Local model", "garch": "GARCH(1,1)", "centralized": "Centralized",
        "fedavg": "FedAvg", "fedprox": "FedProx", "zero": "Always predict 0",
    }
    descriptions = {
        "local": "Each bank trains alone on its own data",
        "garch": "Classical GARCH(1,1) per bank",
        "centralized": "All data pooled in one place (privacy-violating upper bound)",
        "fedavg": "Federated averaging with masked updates",
        "fedprox": "Federated with proximal term (non-IID robust) and masked updates",
        "zero": "Trivial baseline computed from the saved targets",
    }

    # ---- metrics
    rows = []
    pooled_actual = np.concatenate([actual[b] for b in banks_present])
    for key, d in per_bank.items():
        if all(b in d for b in banks_present):
            pooled = np.concatenate([d[b] for b in banks_present])
            name = {"local": "Local ensemble", "garch": "GARCH (pooled)"}.get(key, labels[key])
            rows.append({"key": key, "name": name, "scope": "pooled", "bank_id": None,
                         **evaluate(pooled, pooled_actual)})
        for b in banks_present:
            if b in d:
                rows.append({"key": key, "name": labels[key], "scope": "bank", "bank_id": b,
                             **evaluate(d[b], actual[b])})

    evaluate_csv = None
    csv_path = out_root / "evaluation" / "results.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        keep = [c for c in ["model_name", "model_type", "bank_id"] + METRIC_KEYS if c in df.columns]
        evaluate_csv = df[keep].to_dict(orient="records")

    results = {
        "available": True,
        "metrics": METRIC_KEYS + ["direction_accuracy"],
        "rows": rows,
        "models": {k: {"label": labels[k], "description": descriptions[k]} for k in per_bank},
        "federated_runs": fed_runs,
        "evaluate_py": evaluate_csv,
        "n_test_pooled": int(len(pooled_actual)),
    }

    # ---- predictions per bank
    labels_t = reconstruct_test_labels(raw_dir, processed_dir, cfg, csb)
    pred_banks = []
    for b in banks_present:
        entry = {
            "bank_id": b,
            "name": bank_configs.get(b, {}).get("name"),
            "actual": [round(float(v), 7) for v in actual[b]],
            "dates": labels_t.get(b, {}).get("dates"),
            "tickers": labels_t.get(b, {}).get("tickers"),
            "models": {k: [round(float(v), 7) for v in d[b]] for k, d in per_bank.items() if b in d},
        }
        pred_banks.append(entry)
    predictions = {"available": True, "labels": labels, "banks": pred_banks}
    return results, predictions


def export_masking(out_root: Path, processed_dir: Path, cfg: Dict) -> Dict:
    """Mask real weights (output layer of each bank's local model) with the project's masker."""
    import torch
    from src.privacy import masking

    updates, num_examples, n_train = [], [], []
    for b in range(N_BANKS):
        ckpt = out_root / "local" / f"bank_{b}" / "best_model.pt"
        if not ckpt.exists():
            return {"available": False}
        sd = torch.load(ckpt, map_location="cpu")["model_state_dict"]
        w = sd["output_projection.weight"].numpy().astype(np.float64).reshape(-1)
        bias = sd["output_projection.bias"].numpy().astype(np.float64).reshape(-1)
        updates.append([np.concatenate([bias, w])])
        n = int(json.loads((processed_dir / f"bank_{b}" / "metadata.json").read_text())["n_sequences"]["train"])
        n_train.append(n)
        num_examples.append(n)  # FedAvg weight n_i = training examples (as in client.fit)

    server_round = int(cfg["federated"]["n_rounds"])
    ex = masking.masking_example(updates, num_examples, server_round=server_round)
    show = 6
    plain_avg, masked_avg = ex["plain_avg"][0], ex["masked_avg"][0]
    plain_sum, masked_sum = ex["plain_sum"][0], ex["masked_sum"][0]
    return {
        "available": True,
        "source": "output_projection (bias + weights) of each bank's trained local model "
                  "(outputs/local/bank_i/best_model.pt), masked by src/privacy/masking.py",
        "server_round": server_round,
        "mask_scale": masking.MASK_SCALE,
        "n_values_total": int(len(plain_avg)),
        "n_values_shown": show,
        "value_labels": ["bias"] + [f"w[{i}]" for i in range(show - 1)],
        "banks": [{
            "bank_id": b,
            "num_examples": num_examples[b],
            "n_train": n_train[b],
            "real": updates[b][0][:show],
            "weighted": ex["weighted"][b][0][:show],
            "masked": ex["masked"][b][0][:show],
            "masked_rel_distance": float(np.linalg.norm(ex["masked"][b][0] - ex["weighted"][b][0])
                                         / np.linalg.norm(ex["weighted"][b][0])),
        } for b in range(N_BANKS)],
        "total_examples": int(sum(num_examples)),
        "plain_avg": plain_avg[:show],
        "masked_avg": masked_avg[:show],
        "plain_sum": plain_sum[:show],
        "masked_sum": masked_sum[:show],
        "max_abs_diff_avg": float(np.max(np.abs(plain_avg - masked_avg))),
        "max_abs_diff_sum": float(np.max(np.abs(plain_sum - masked_sum))),
    }


def export_summary(results: Dict, federated: Dict) -> Dict:
    if not results.get("available"):
        return {"available": False}
    pooled = {r["key"]: r for r in results["rows"] if r["scope"] == "pooled"}

    def pct(a, b, metric):
        if a not in pooled or b not in pooled:
            return None
        va, vb = pooled[a].get(metric), pooled[b].get(metric)
        if va is None or vb in (None, 0):
            return None
        return (va - vb) / vb * 100.0

    feds = [k for k in ["fedavg", "fedprox"] if k in pooled]
    best_fed = min(feds, key=lambda k: pooled[k]["mse"]) if feds else None
    out = {"available": True, "best_federated": best_fed, "comparisons": {}}
    for metric in ["mse", "var_95_error", "mae"]:
        c = {}
        for f in feds:
            c[f] = {
                "vs_centralized_pct": pct(f, "centralized", metric),
                "vs_local_ensemble_pct": pct(f, "local", metric),
                "vs_zero_pct": pct(f, "zero", metric),
                "vs_garch_pct": pct(f, "garch", metric),
            }
        c["centralized_vs_zero_pct"] = pct("centralized", "zero", metric)
        c["local_vs_zero_pct"] = pct("local", "zero", metric)
        out["comparisons"][metric] = c
    rounds_ok = {}
    for s, d in federated.get("strategies", {}).items():
        rs = d["rounds"]
        rounds_ok[s] = {
            "n_rounds": len(rs),
            "all_results": all(r.get("n_results") == d["n_clients"] for r in rs) if rs and "n_results" in rs[0] else None,
            "total_failures": sum(int(r.get("n_failures") or 0) for r in rs) if rs and "n_failures" in rs[0] else None,
        }
    out["rounds"] = rounds_ok
    return out


def export_code() -> Dict:
    """Real source snippets + commands for the 'Under the hood' drawer."""
    steps = {
        "data": {
            "title": "Download prices",
            "command": "python scripts/fetch_yfinance.py   # falls back to generate_synthetic_data.py",
            "file": "scripts/fetch_yfinance.py", "names": ["download_ticker_data"],
        },
        "banks": {
            "title": "Split into four non-IID banks",
            "command": "python scripts/create_synthetic_banks.py",
            "file": "scripts/create_synthetic_banks.py",
            "names": ["apply_correlation_structure", "create_rolling_windows", "split_data"],
        },
        "problem": {
            "title": "Each bank loads only its own data",
            "command": "python scripts/train_local.py --all",
            "file": "src/data/dataset.py", "names": ["load_bank_datasets"],
        },
        "training": {
            "title": "Local training with the FedProx term",
            "command": "python scripts/run_federated.py --strategy fedprox --n_rounds 20 --mu 0.01",
            "file": "src/flwr/client.py", "names": ["fit", "_train_fedprox"],
        },
        "rounds": {
            "title": "Server: combine masked updates",
            "command": "python scripts/run_federated.py --strategy fedavg --n_rounds 20",
            "file": "src/flwr/server_strategy.py", "names": ["aggregate_fit"],
        },
        "masking": {
            "title": "Pairwise additive masking",
            "command": "python -B src/privacy/masking.py   # assert-based self-test",
            "file": "src/privacy/masking.py",
            "names": ["PairwiseMasker", "unmask_weighted_average"],
        },
        "results": {
            "title": "Evaluate every model",
            "command": "python scripts/evaluate.py --plots",
            "file": "src/eval/metrics.py", "names": ["compute_var", "compute_var_error"],
        },
        "predict": {
            "title": "Export predictions for this site",
            "command": "python scripts/export_web_data.py",
            "file": "scripts/export_web_data.py", "names": ["export_predictions_and_results"],
        },
        "takeaways": {
            "title": "Masking self-test",
            "command": "python -B src/privacy/masking.py",
            "file": "src/privacy/masking.py", "names": ["self_test"],
        },
    }
    out = {}
    for key, s in steps.items():
        path = ROOT / s["file"]
        code = extract_source(path, s["names"]) if path.exists() else ""
        out[key] = {"title": s["title"], "command": s["command"], "file": s["file"],
                    "symbols": s["names"], "code": code}
    return {"available": True, "steps": out}


def main():
    parser = argparse.ArgumentParser(description="Export pipeline outputs for the web frontend")
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--out", default="web/public/data")
    args = parser.parse_args()

    cfg = yaml.safe_load((ROOT / args.config).read_text())
    raw_dir = ROOT / cfg["paths"]["data_raw"]
    processed_dir = ROOT / cfg["paths"]["data_processed"]
    out_root = ROOT / cfg["paths"]["outputs"]
    out_dir = ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    bank_configs = load_module(ROOT / "scripts" / "generate_synthetic_data.py", "gsd").BANK_CONFIGS
    csb = load_module(ROOT / "scripts" / "create_synthetic_banks.py", "csb")

    print("Exporting web data ->", out_dir.relative_to(ROOT))
    files = {}

    def emit(name, payload):
        write_json(out_dir, name, payload)
        files[name] = bool(payload.get("available", True))

    emit("source.json", export_source(raw_dir))
    emit("prices.json", export_prices(raw_dir, bank_configs))
    emit("banks.json", export_banks(processed_dir, bank_configs, cfg))
    federated = export_federated(out_root / "federated", cfg)
    emit("federated.json", federated)
    if (processed_dir / "bank_0" / "metadata.json").exists():
        results, predictions = export_predictions_and_results(
            out_root, processed_dir, raw_dir, cfg, csb, bank_configs)
    else:
        results, predictions = {"available": False}, {"available": False}
    emit("results.json", results)
    emit("predictions.json", predictions)
    emit("masking.json", export_masking(out_root, processed_dir, cfg)
         if (processed_dir / "bank_0" / "metadata.json").exists() else {"available": False})
    emit("summary.json", export_summary(results, federated))
    emit("code.json", export_code())
    readme = (ROOT / "README.md").read_text() if (ROOT / "README.md").exists() else ""
    title = next((ln[2:].strip() for ln in readme.splitlines() if ln.startswith("# ")), ROOT.name)
    team_match = re.search(r"author\s*=\s*\{([^}]*)\}", readme)
    local_meta = out_root / "local" / "bank_0" / "metadata.json"
    emit("settings.json", {
        "available": True,
        "project": ROOT.name,
        "title": title,
        "team": team_match.group(1).strip() if team_match else None,
        "n_parameters": json.loads(local_meta.read_text()).get("n_parameters") if local_meta.exists() else None,
        "config": cfg,
    })
    emit("manifest.json", {
        "available": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "files": files,
    })
    print("[OK] web data export complete")


if __name__ == "__main__":
    main()
