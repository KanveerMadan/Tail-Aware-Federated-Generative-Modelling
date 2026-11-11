#!/usr/bin/env python3
"""
Generate synthetic financial data as a fallback when Yahoo Finance is unavailable.
Creates realistic stock price data with log returns for testing the pipeline.
"""

import argparse
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd
from datetime import datetime, timedelta


# Bank configurations matching the original fetch_yfinance.py
BANK_CONFIGS = {
    0: {
        "name": "Tech-Heavy Portfolio",
        "sector": "Technology",
        "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD"],
        "start_date": "2018-01-01",
        "end_date": "2021-12-31",
        "volatility": 0.025,  # Higher volatility for tech
    },
    1: {
        "name": "Finance Portfolio",
        "sector": "Finance",
        "tickers": ["JPM", "BAC", "GS", "WFC", "C"],
        "start_date": "2015-01-01",
        "end_date": "2018-12-31",
        "volatility": 0.018,  # Standard volatility
    },
    2: {
        "name": "Energy Portfolio",
        "sector": "Energy",
        "tickers": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "start_date": "2019-01-01",
        "end_date": "2022-12-31",
        "volatility": 0.030,  # High volatility with regime switches
    },
    3: {
        "name": "Healthcare Portfolio",
        "sector": "Healthcare",
        "tickers": ["JNJ", "UNH", "PFE", "ABBV", "TMO"],
        "start_date": "2017-01-01",
        "end_date": "2020-12-31",
        "volatility": 0.015,  # Lower volatility
    },
}


def generate_synthetic_prices(
    ticker: str, 
    start_date: str, 
    end_date: str, 
    initial_price: float = 100.0,
    drift: float = 0.0002,
    volatility: float = 0.02,
    seed: Optional[int] = None
) -> pd.DataFrame:
    """
    Generate synthetic stock prices using geometric Brownian motion.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date string
        end_date: End date string
        initial_price: Starting price
        drift: Daily drift rate
        volatility: Daily volatility
        seed: Random seed for reproducibility
    
    Returns:
        DataFrame with columns: date, ticker, close, log_return
    """
    if seed is not None:
        np.random.seed(seed)
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.bdate_range(start=start, end=end)
    n_days = len(dates)
    
    returns = np.random.normal(drift, volatility, n_days)
    
    for i in range(1, n_days):
        returns[i] += 0.1 * returns[i-1]
    
    log_returns = returns
    prices = initial_price * np.exp(np.cumsum(log_returns))
    
    df = pd.DataFrame({
        'date': dates,
        'ticker': ticker,
        'close': prices,
        'log_return': log_returns
    })
    
    return df


def generate_bank_data(bank_id: int, output_dir: str, seed: int = 42) -> None:
    """Generate and save synthetic data for a specific bank."""
    config = BANK_CONFIGS[bank_id]
    
    print(f"\n{'='*60}")
    print(f"Bank {bank_id}: {config['name']}")
    print(f"Sector: {config['sector']}")
    print(f"Period: {config['start_date']} to {config['end_date']}")
    print(f"Tickers: {', '.join(config['tickers'])}")
    print(f"{'='*60}\n")
    
    all_data = []
    
    for idx, ticker in enumerate(config['tickers']):
        ticker_seed = seed + bank_id * 100 + idx
        
        initial_price = 100.0 + np.random.RandomState(ticker_seed).uniform(-20, 50)
        
        df = generate_synthetic_prices(
            ticker=ticker,
            start_date=config['start_date'],
            end_date=config['end_date'],
            initial_price=initial_price,
            drift=0.0002,  # Small positive drift
            volatility=config['volatility'],
            seed=ticker_seed
        )
        
        all_data.append(df)
        print(f"  [OK] Generated {len(df)} days for {ticker}")
    
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.sort_values(['date', 'ticker']).reset_index(drop=True)
    
    output_path = Path(output_dir) / f"bank_{bank_id}_raw.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_parquet(output_path, index=False)
    
    print(f"\n[OK] Saved {len(combined_df)} rows to {output_path}")
    print(f"  Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
    print(f"  Tickers: {combined_df['ticker'].nunique()}")


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic financial data")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/raw",
        help="Output directory for raw data files"
    )
    parser.add_argument(
        "--bank_id",
        type=int,
        choices=[0, 1, 2, 3],
        help="Generate data for specific bank (default: all banks)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("SYNTHETIC FINANCIAL DATA GENERATION")
    print("="*60)
    print(f"Output directory: {args.output_dir}")
    print(f"Random seed: {args.seed}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.bank_id is not None:
        # Generate single bank
        generate_bank_data(args.bank_id, args.output_dir, args.seed)
    else:
        # Generate all banks
        for bank_id in range(4):
            generate_bank_data(bank_id, args.output_dir, args.seed)
    
    print("\n" + "="*60)
    print("SYNTHETIC DATA GENERATION COMPLETE")
    print("="*60)
    print(f"Next step: python scripts/create_synthetic_banks.py")


if __name__ == "__main__":
    main()
