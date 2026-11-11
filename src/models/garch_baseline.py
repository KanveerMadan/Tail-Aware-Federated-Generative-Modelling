"""
GARCH(1,1) baseline model for comparison.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from arch import arch_model
from pathlib import Path
from typing import Dict, Tuple


class GARCHBaseline:
    """GARCH(1,1) model for volatility forecasting."""
    
    def __init__(self, p: int = 1, q: int = 1):
        """
        Args:
            p: GARCH lag order
            q: ARCH lag order
        """
        self.p = p
        self.q = q
        self.model = None
        self.result = None
    
    def fit(self, returns: np.ndarray) -> None:
        """
        Fit GARCH model to return series.
        
        Args:
            returns: Array of log returns
        """
        # Convert to percentage returns for better numerical stability
        returns_pct = returns * 100
        
        # Fit GARCH(1,1)
        self.model = arch_model(
            returns_pct,
            vol='GARCH',
            p=self.p,
            q=self.q,
            rescale=False
        )
        
        self.result = self.model.fit(disp='off', show_warning=False)
    
    def forecast(self, horizon: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        """
        Forecast volatility.
        
        Args:
            horizon: Forecast horizon
        
        Returns:
            mean_forecast: Mean return forecast
            volatility_forecast: Conditional volatility forecast
        """
        if self.result is None:
            raise ValueError("Model not fitted yet")
        
        forecast = self.result.forecast(horizon=horizon)
        
        # Extract forecasts (convert back from percentage)
        mean_forecast = np.asarray(forecast.mean.iloc[-1].values) / 100
        vol_forecast = np.sqrt(np.asarray(forecast.variance.iloc[-1].values)) / 100
        
        return mean_forecast, vol_forecast
    
    def simulate(self, n_samples: int = 1000, horizon: int = 1) -> np.ndarray:
        """
        Simulate future returns using fitted model.
        
        Args:
            n_samples: Number of samples to simulate
            horizon: Forecast horizon
        
        Returns:
            Simulated returns
        """
        if self.result is None:
            raise ValueError("Model not fitted yet")
        
        simulations = self.result.forecast(
            horizon=horizon,
            method='simulation',
            simulations=n_samples
        )
        
        # Extract simulated values (convert back from percentage)
        sim_values = simulations.simulations
        if sim_values is not None:
            simulated_returns = np.asarray(sim_values.values[-1, :, 0]) / 100  # type: ignore
        else:
            raise ValueError("Simulation failed")
        
        return simulated_returns


def train_garch_baseline(
    bank_id: int,
    data_dir: str = "data/processed",
    output_dir: str = "outputs/garch"
) -> Dict:
    """
    Train GARCH model for a bank and generate forecasts.
    
    Args:
        bank_id: Bank identifier
        data_dir: Data directory
        output_dir: Output directory
    
    Returns:
        Metadata dictionary
    """
    print(f"\nTraining GARCH(1,1) for Bank {bank_id}...")
    
    # Load training data
    bank_dir = Path(data_dir) / f"bank_{bank_id}"
    train_df = pd.read_parquet(bank_dir / "train.parquet")
    test_df = pd.read_parquet(bank_dir / "test.parquet")
    
    # Extract returns
    train_returns = np.asarray(train_df['y'].values)
    test_returns = np.asarray(test_df['y'].values)
    
    print(f"Train samples: {len(train_returns)}")
    print(f"Test samples: {len(test_returns)}")
    
    # Fit GARCH
    garch = GARCHBaseline(p=1, q=1)
    garch.fit(train_returns)
    
    if garch.result is not None:
        print("GARCH parameters:")
        print(garch.result.summary().tables[1])
    else:
        print("Warning: GARCH fit failed")
    
    # Generate forecasts for test period
    # For each test point, we would need to refit in practice
    # For simplicity, we'll use one-step-ahead forecast
    test_predictions = []
    
    print("Generating test forecasts...")
    for i in range(len(test_returns)):
        # Use all data up to current point
        if i == 0:
            # Use training data only
            current_returns = train_returns
        else:
            # Include previous test points
            current_returns = np.concatenate([train_returns, test_returns[:i]])
        
        # Fit model (in practice, could use rolling window)
        if i % 50 == 0:  # Refit every 50 steps for efficiency
            temp_garch = GARCHBaseline(p=1, q=1)
            temp_garch.fit(current_returns)
            mean_fc, vol_fc = temp_garch.forecast(horizon=1)
        else:
            # Use previous fit
            mean_fc, vol_fc = temp_garch.forecast(horizon=1)
        
        test_predictions.append(mean_fc[0])
    
    test_predictions = np.array(test_predictions).reshape(-1, 1)
    test_targets = np.asarray(test_returns).reshape(-1, 1)
    
    # Compute residuals
    residuals = test_predictions - test_targets
    
    # Save results
    output_path = Path(output_dir) / f"bank_{bank_id}"
    output_path.mkdir(parents=True, exist_ok=True)
    
    np.save(output_path / "test_predictions.npy", test_predictions)
    np.save(output_path / "test_targets.npy", test_targets)
    np.save(output_path / "test_residuals.npy", residuals)
    
    # Compute metrics
    mse = np.mean(residuals ** 2)
    mae = np.mean(np.abs(residuals))
    
    print(f"Test MSE: {mse:.6f}")
    print(f"Test MAE: {mae:.6f}")
    
    metadata = {
        'bank_id': bank_id,
        'model_type': 'GARCH(1,1)',
        'test_mse': float(mse),
        'test_mae': float(mae),
        'n_train': len(train_returns),
        'n_test': len(test_returns),
    }
    
    import json
    with open(output_path / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved to: {output_path}")
    
    return metadata


if __name__ == "__main__":
    import sys
    
    # Test GARCH baseline
    print("Testing GARCH baseline...")
    
    try:
        metadata = train_garch_baseline(bank_id=0)
        print("\n[OK] GARCH baseline successful!")
        print(metadata)
    except FileNotFoundError as e:
        print(f"\n[ERROR] Data not found: {e}")
        print("Run 'python scripts/create_synthetic_banks.py' first")
        sys.exit(1)
