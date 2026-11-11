#!/usr/bin/env python3
"""
Fetch financial data from Yahoo Finance for different bank archetypes.
Creates sector-specific datasets with different time periods.
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from tqdm import tqdm


# Bank configurations: sector, tickers, and time periods
BANK_CONFIGS = {
    0: {
        "name": "Tech-Heavy Portfolio",
        "sector": "Technology",
        "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD"],
        "start_date": "2018-01-01",
        "end_date": "2021-12-31",
    },
    1: {
        "name": "Finance Portfolio",
        "sector": "Finance",
        "tickers": ["JPM", "BAC", "GS", "WFC", "C"],
        "start_date": "2015-01-01",
        "end_date": "2018-12-31",
    },
    2: {
        "name": "Energy Portfolio",
        "sector": "Energy",
        "tickers": ["XOM", "CVX", "COP", "SLB", "EOG"],
        "start_date": "2019-01-01",
        "end_date": "2022-12-31",
    },
    3: {
        "name": "Healthcare Portfolio",
        "sector": "Healthcare",
        "tickers": ["JNJ", "UNH", "PFE", "ABBV", "TMO"],
        "start_date": "2017-01-01",
        "end_date": "2020-12-31",
    },
}


def download_ticker_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Download historical price data for a single ticker."""
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            print(f"Warning: No data retrieved for {ticker}")
            return pd.DataFrame()
        
        df = pd.DataFrame({
            'date': data.index,
            'ticker': ticker,
            'close': data['Adj Close'].values,
        })
        
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        df = df.dropna()
        
        return df
    except Exception as e:
        print(f"Error downloading {ticker}: {e}")
        return pd.DataFrame()


def fetch_bank_data(bank_id: int, output_dir: str) -> None:
    """Fetch and save data for a specific bank."""
    config = BANK_CONFIGS[bank_id]
    
    print(f"\n{'='*60}")
    print(f"Bank {bank_id}: {config['name']}")
    print(f"Sector: {config['sector']}")
    print(f"Period: {config['start_date']} to {config['end_date']}")
    print(f"Tickers: {', '.join(config['tickers'])}")
    print(f"{'='*60}\n")
    
    all_data = []
    
    for ticker in tqdm(config['tickers'], desc=f"Downloading Bank {bank_id}"):
        df = download_ticker_data(ticker, config['start_date'], config['end_date'])
        if not df.empty:
            all_data.append(df)
    
    if not all_data:
        print(f"ERROR: No data downloaded for Bank {bank_id}")
        return
    
    combined = pd.concat(all_data, ignore_index=True)
    combined = combined.sort_values(['ticker', 'date']).reset_index(drop=True)
    
    output_path = Path(output_dir) / f"bank_{bank_id}_raw.parquet"
    combined.to_parquet(output_path, index=False)
    
    print(f"\nBank {bank_id} Statistics:")
    print(f"  Total records: {len(combined)}")
    print(f"  Date range: {combined['date'].min()} to {combined['date'].max()}")
    print(f"  Tickers: {combined['ticker'].nunique()}")
    
    for ticker in config['tickers']:
        ticker_data = combined[combined['ticker'] == ticker]
        if not ticker_data.empty:
            returns = ticker_data['log_return'].dropna()
            print(f"  {ticker:6s}: {len(ticker_data):4d} days, "
                  f"mean={returns.mean():.6f}, std={returns.std():.6f}, "
                  f"kurt={returns.kurtosis():.3f}")
    
    print(f"\nSaved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Fetch financial data from Yahoo Finance")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="data/raw",
        help="Output directory for raw data"
    )
    parser.add_argument(
        "--bank_id",
        type=int,
        choices=[0, 1, 2, 3],
        default=None,
        help="Specific bank to download (default: all)"
    )
    
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    print("="*60)
    print("FEDERATED TRANSFORMER - DATA FETCHING")
    print("="*60)
    print(f"Output directory: {args.output_dir}")
    print(f"Total banks: {len(BANK_CONFIGS)}")
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.bank_id is not None:
        fetch_bank_data(args.bank_id, args.output_dir)
    else:
        for bank_id in BANK_CONFIGS.keys():
            fetch_bank_data(bank_id, args.output_dir)
    
    print("\n" + "="*60)
    print("DATA FETCHING COMPLETE")
    print("="*60)
    print(f"Next step: python scripts/create_synthetic_banks.py")


if __name__ == "__main__":
    main()
