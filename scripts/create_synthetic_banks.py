#!/usr/bin/env python3
"""
Create synthetic non-IID bank datasets from raw financial data.

Heterogeneity strategies:
1. Temporal: Different time periods per bank
2. Sector: Different asset classes (tech/finance/energy/healthcare)
3. Statistical: Volatility scaling and regime switches
4. Correlation: Single-ticker vs portfolio returns (NEW)
"""

import argparse
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import yaml
from tqdm import tqdm


# Heterogeneity configurations
HETEROGENEITY_CONFIG = {
    0: {
        "vol_scale": 1.2,  # Amplify volatility by 20%
        "regime_switch": False,
        "correlation_type": "single_ticker",  # Use individual ticker returns
        "description": "High-volatility, single-ticker",
    },
    1: {
        "vol_scale": 1.0,  # No scaling
        "regime_switch": False,
        "correlation_type": "single_ticker",
        "description": "Standard, single-ticker",
    },
    2: {
        "vol_scale": 1.0,
        "regime_switch": True,  # Add synthetic regime switch
        "regime_switch_prob": 0.2,  # 20% of days have 2x volatility
        "regime_switch_multiplier": 2.0,
        "correlation_type": "weighted_portfolio",  # Weighted average portfolio
        "portfolio_weights": [0.4, 0.3, 0.3],  # First 3 tickers
        "description": "Regime-switching, weighted portfolio",
    },
    3: {
        "vol_scale": 1.0,
        "regime_switch": False,
        "correlation_type": "equal_portfolio",  # Equal-weight portfolio
        "description": "Equal-weight portfolio",
    },
}


def load_raw_bank_data(bank_id: int, data_dir: str) -> pd.DataFrame:
    """Load raw bank data from parquet file."""
    file_path = Path(data_dir) / f"bank_{bank_id}_raw.parquet"
    if not file_path.exists():
        raise FileNotFoundError(f"Raw data not found: {file_path}")
    
    df = pd.read_parquet(file_path)
    print(f"Loaded Bank {bank_id}: {len(df)} records, "
          f"{df['ticker'].nunique()} tickers, "
          f"{df['date'].nunique()} unique dates")
    
    return df


def apply_correlation_structure(df: pd.DataFrame, config: Dict) -> pd.DataFrame:
    """
    Apply correlation structure transformation.
    
    - single_ticker: Keep individual ticker returns (no change)
    - weighted_portfolio: Weighted average of first N tickers
    - equal_portfolio: Equal-weight average of all tickers
    """
    corr_type = config.get("correlation_type", "single_ticker")
    
    if corr_type == "single_ticker":
        return df
    
    returns_pivot = df.pivot(index='date', columns='ticker', values='log_return')
    
    if corr_type == "weighted_portfolio":
        weights = config.get("portfolio_weights", [0.4, 0.3, 0.3])
        tickers = returns_pivot.columns[:len(weights)]
        
        portfolio_return = sum(
            w * returns_pivot[ticker]
            for w, ticker in zip(weights, tickers)
        )
        
        portfolio_df = pd.DataFrame({
            'date': portfolio_return.index,
            'ticker': 'PORTFOLIO_WEIGHTED',
            'log_return': portfolio_return.values,
        })
        
    elif corr_type == "equal_portfolio":
        portfolio_return = returns_pivot.mean(axis=1)
        
        portfolio_df = pd.DataFrame({
            'date': portfolio_return.index,
            'ticker': 'PORTFOLIO_EQUAL',
            'log_return': portfolio_return.values,
        })
    
    else:
        raise ValueError(f"Unknown correlation type: {corr_type}")
    
    return portfolio_df.dropna()


def apply_volatility_transformations(df: pd.DataFrame, config: Dict, seed: int) -> pd.DataFrame:
    """Apply volatility scaling and regime switches."""
    df = df.copy()
    
    vol_scale = config.get("vol_scale", 1.0)
    if vol_scale != 1.0:
        mean_return = df['log_return'].mean()
        df['log_return'] = mean_return + (df['log_return'] - mean_return) * vol_scale
    
    if config.get("regime_switch", False):
        np.random.seed(seed)
        n = len(df)
        prob = config.get("regime_switch_prob", 0.2)
        multiplier = config.get("regime_switch_multiplier", 2.0)
        
        regime_mask = np.random.rand(n) < prob
        
        mean_return = df['log_return'].mean()
        df.loc[regime_mask, 'log_return'] = (
            mean_return + (df.loc[regime_mask, 'log_return'] - mean_return) * multiplier
        )
    
    return df


def create_rolling_windows(
    df: pd.DataFrame,
    sequence_length: int,
    stride: int = 1
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create rolling windows for time series sequences.
    
    Returns:
        X: input sequences [N, sequence_length]
        y: target values [N, 1]
    """
    returns = df['log_return'].values
    
    X, y = [], []
    
    for i in range(0, len(returns) - sequence_length, stride):
        X.append(returns[i:i + sequence_length])
        y.append(returns[i + sequence_length])
    
    return np.array(X), np.array(y)


def split_data(
    X: np.ndarray,
    y: np.ndarray,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
    """
    Split data into train/val/test preserving temporal order.
    
    Returns:
        X_splits: {'train': X_train, 'val': X_val, 'test': X_test}
        y_splits: {'train': y_train, 'val': y_val, 'test': y_test}
    """
    assert abs(train_ratio + val_ratio + test_ratio - 1.0) < 1e-6
    
    n = len(X)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    X_splits = {
        'train': X[:train_end],
        'val': X[train_end:val_end],
        'test': X[val_end:],
    }
    
    y_splits = {
        'train': y[:train_end],
        'val': y[train_end:val_end],
        'test': y[val_end:],
    }
    
    return X_splits, y_splits


def compute_statistics(returns: np.ndarray) -> Dict:
    """Compute descriptive statistics for returns."""
    from scipy import stats
    
    return {
        'n_samples': len(returns),
        'mean': float(np.mean(returns)),
        'std': float(np.std(returns)),
        'skewness': float(stats.skew(returns)),
        'kurtosis': float(stats.kurtosis(returns)),
        'min': float(np.min(returns)),
        'max': float(np.max(returns)),
    }


def process_bank(
    bank_id: int,
    raw_data_dir: str,
    output_dir: str,
    sequence_length: int,
    train_ratio: float,
    val_ratio: float,
    test_ratio: float,
    seed: int
) -> None:
    """Process a single bank's data."""
    
    print(f"\n{'='*60}")
    print(f"Processing Bank {bank_id}")
    print(f"{'='*60}")
    
    df = load_raw_bank_data(bank_id, raw_data_dir)
    
    config = HETEROGENEITY_CONFIG[bank_id]
    print(f"Config: {config['description']}")
    
    print(f"Applying correlation structure: {config['correlation_type']}")
    df = apply_correlation_structure(df, config)
    
    print("Applying volatility transformations...")
    df = apply_volatility_transformations(df, config, seed + bank_id)
    
    df = df.sort_values('date').reset_index(drop=True)
    
    print(f"Creating rolling windows (length={sequence_length})...")
    X, y = create_rolling_windows(df, sequence_length, stride=1)
    
    print(f"Total sequences: {len(X)}")
    
    print(f"Splitting data (train={train_ratio}, val={val_ratio}, test={test_ratio})...")
    X_splits, y_splits = split_data(X, y, train_ratio, val_ratio, test_ratio)
    
    stats = {}
    for split_name in ['train', 'val', 'test']:
        split_stats = compute_statistics(y_splits[split_name])
        stats[split_name] = split_stats
        print(f"\n{split_name.upper()} statistics:")
        print(f"  N: {split_stats['n_samples']}")
        print(f"  Mean: {split_stats['mean']:.6f}")
        print(f"  Std: {split_stats['std']:.6f}")
        print(f"  Skewness: {split_stats['skewness']:.3f}")
        print(f"  Kurtosis: {split_stats['kurtosis']:.3f}")
    
    bank_dir = Path(output_dir) / f"bank_{bank_id}"
    bank_dir.mkdir(parents=True, exist_ok=True)
    
    for split_name in ['train', 'val', 'test']:
        split_df = pd.DataFrame({
            'X': [X_splits[split_name][i].tolist() for i in range(len(X_splits[split_name]))],
            'y': y_splits[split_name],
        })
        
        output_path = bank_dir / f"{split_name}.parquet"
        split_df.to_parquet(output_path, index=False)
        print(f"Saved {split_name}: {output_path}")
    
    metadata = {
        'bank_id': bank_id,
        'heterogeneity_config': config,
        'sequence_length': sequence_length,
        'statistics': stats,
        'n_sequences': {k: len(v) for k, v in X_splits.items()},
    }
    
    import json
    metadata_path = bank_dir / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved metadata: {metadata_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create synthetic non-IID bank datasets"
    )
    parser.add_argument(
        "--raw_data_dir",
        type=str,
        default="data/raw",
        help="Directory with raw yfinance data"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/processed",
        help="Output directory for processed data"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Configuration file"
    )
    parser.add_argument(
        "--bank_id",
        type=int,
        choices=[0, 1, 2, 3],
        default=None,
        help="Specific bank to process (default: all)"
    )
    
    args = parser.parse_args()
    
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    sequence_length = config['data']['sequence_length']
    train_ratio = config['data']['train_ratio']
    val_ratio = config['data']['val_ratio']
    test_ratio = config['data']['test_ratio']
    seed = config['random_seed']
    
    print("="*60)
    print("SYNTHETIC BANK DATASET CREATION")
    print("="*60)
    print(f"Raw data dir: {args.raw_data_dir}")
    print(f"Output dir: {args.output_dir}")
    print(f"Sequence length: {sequence_length}")
    print(f"Train/Val/Test: {train_ratio}/{val_ratio}/{test_ratio}")
    print(f"Random seed: {seed}")
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    if args.bank_id is not None:
        process_bank(
            args.bank_id,
            args.raw_data_dir,
            args.output_dir,
            sequence_length,
            train_ratio,
            val_ratio,
            test_ratio,
            seed
        )
    else:
        for bank_id in range(4):
            process_bank(
                bank_id,
                args.raw_data_dir,
                args.output_dir,
                sequence_length,
                train_ratio,
                val_ratio,
                test_ratio,
                seed
            )
    
    print("\n" + "="*60)
    print("DATASET CREATION COMPLETE")
    print("="*60)
    print(f"Processed data saved to: {args.output_dir}")
    print("\nNon-IID Heterogeneity Summary:")
    for bank_id, config in HETEROGENEITY_CONFIG.items():
        print(f"  Bank {bank_id}: {config['description']}")
    print(f"\nNext step: python scripts/train_local.py")


if __name__ == "__main__":
    main()
