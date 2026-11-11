# Data Source Documentation

## Real Financial Data

This project uses **real financial market data** sourced from Yahoo Finance via the `yfinance` Python library.

### Source Information

- **Data Provider**: Yahoo Finance
- **Python Library**: `yfinance`
- **Library URL**: https://pypi.org/project/yfinance/
- **Data Source URL**: https://finance.yahoo.com/
- **Documentation**: https://github.com/ranaroussi/yfinance

### Data Description

The project fetches historical stock price data for multiple financial sectors:

**Bank 0 - Technology Portfolio**
- Period: 2018-01-01 to 2021-12-31
- Tickers: AAPL, MSFT, GOOGL, NVDA, AMD
- Sector: Technology stocks

**Bank 1 - Finance Portfolio**
- Period: 2015-01-01 to 2018-12-31
- Tickers: JPM, BAC, GS, WFC, C
- Sector: Financial services stocks

**Bank 2 - Energy Portfolio**
- Period: 2019-01-01 to 2022-12-31
- Tickers: XOM, CVX, COP, SLB, EOG
- Sector: Energy sector stocks

**Bank 3 - Healthcare Portfolio**
- Period: 2017-01-01 to 2020-12-31
- Tickers: JNJ, UNH, PFE, ABBV, TMO
- Sector: Healthcare and pharmaceutical stocks

### Data Features

For each stock:
- Adjusted Close Price (daily)
- Log Returns (computed from price changes)
- Business days only (excludes weekends and holidays)

### Fallback: Synthetic Data

If Yahoo Finance is unavailable or rate-limited, the project includes a synthetic data generator (`scripts/generate_synthetic_data.py`) that creates realistic stock price data using:
- Geometric Brownian motion
- Configurable volatility parameters
- Autocorrelated returns
- Sector-specific characteristics

### Data Fetching

To fetch real data:
```bash
python scripts/fetch_yfinance.py
```

To generate synthetic data (fallback):
```bash
python scripts/generate_synthetic_data.py
```

### Data Processing

Raw data is processed into time series sequences using:
```bash
python scripts/create_synthetic_banks.py
```

This creates:
- Rolling window sequences (default: 64 timesteps)
- Train/validation/test splits (70%/15%/15%)
- Non-IID heterogeneity across banks
- Normalized returns (z-score normalization)

### License and Terms of Use

**Important**: Yahoo Finance data is subject to their terms of service. This project is for educational and research purposes only. For commercial use, please review Yahoo Finance's terms and consider appropriate licensing.

### Citation

If using this project or data in academic work:
```
Data Source: Yahoo Finance (finance.yahoo.com)
Accessed via yfinance Python library (https://github.com/ranaroussi/yfinance)
```
