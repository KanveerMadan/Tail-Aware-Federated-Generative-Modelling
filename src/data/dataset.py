"""
PyTorch Dataset for time series financial data.
"""

from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
from torch.utils.data import Dataset


class TimeSeriesDataset(Dataset):
    """Dataset for autoregressive time series prediction."""
    
    def __init__(
        self,
        data_path: Union[str, Path],
        normalize: bool = True,
        train_stats: Optional[dict] = None
    ):
        """
        Args:
            data_path: Path to parquet file with 'X' and 'y' columns
            normalize: Whether to normalize returns using z-score
            train_stats: Dict with 'mean' and 'std' from training set (for val/test)
        """
        self.data_path = Path(data_path)
        self.normalize = normalize
        self.train_stats = train_stats
        
        df = pd.read_parquet(data_path)
        
        self.X = np.array([np.array(x) for x in df['X'].values])
        self.y = np.asarray(df['y'].values).reshape(-1, 1)  # [N, 1]
        
        # Compute or use provided normalization statistics
        if self.normalize:
            if self.train_stats is None:
                self.mean = float(self.y.mean())
                self.std = float(self.y.std())
            else:
                # Type checker: train_stats is checked via self.train_stats above
                assert train_stats is not None
                self.mean = train_stats['mean']
                self.std = train_stats['std']
            
            self.X = (self.X - self.mean) / (self.std + 1e-8)
            self.y = (self.y - self.mean) / (self.std + 1e-8)
        else:
            self.mean = 0.0
            self.std = 1.0
    
    def __len__(self) -> int:
        return len(self.X)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns:
            x: Input sequence [seq_len]
            y: Target value [1]
        """
        x = torch.FloatTensor(self.X[idx])
        y = torch.FloatTensor(self.y[idx])
        
        return x, y
    
    def get_stats(self) -> dict:
        """Get normalization statistics."""
        return {'mean': self.mean, 'std': self.std}
    
    def denormalize(self, normalized_values: np.ndarray) -> np.ndarray:
        """Convert normalized values back to original scale."""
        if not self.normalize:
            return normalized_values
        return normalized_values * (self.std + 1e-8) + self.mean


def load_bank_datasets(
    bank_id: int,
    data_dir: str = "data/processed",
    normalize: bool = True
) -> Tuple[TimeSeriesDataset, TimeSeriesDataset, TimeSeriesDataset]:
    """
    Load train, validation, and test datasets for a bank.
    
    Args:
        bank_id: Bank identifier (0-3)
        data_dir: Root directory for processed data
        normalize: Whether to apply z-score normalization
    
    Returns:
        train_dataset, val_dataset, test_dataset
    """
    bank_dir = Path(data_dir) / f"bank_{bank_id}"
    
    train_dataset = TimeSeriesDataset(
        str(bank_dir / "train.parquet"),
        normalize=normalize,
        train_stats=None
    )
    
    train_stats = train_dataset.get_stats() if normalize else None
    
    val_dataset = TimeSeriesDataset(
        str(bank_dir / "val.parquet"),
        normalize=normalize,
        train_stats=train_stats
    )
    
    test_dataset = TimeSeriesDataset(
        str(bank_dir / "test.parquet"),
        normalize=normalize,
        train_stats=train_stats
    )
    
    return train_dataset, val_dataset, test_dataset


def load_centralized_dataset(
    bank_ids: list,
    data_dir: str = "data/processed",
    normalize: bool = True,
    split: str = "train"
) -> TimeSeriesDataset:
    """
    Load and concatenate datasets from multiple banks (for centralized training).
    
    CRITICAL: Preserves temporal ordering per bank. Does NOT shuffle across time.
    
    Args:
        bank_ids: List of bank IDs to pool
        data_dir: Root directory for processed data
        normalize: Whether to apply z-score normalization
        split: Which split to load ('train', 'val', or 'test')
    
    Returns:
        Combined dataset preserving temporal structure
    """
    all_X = []
    all_y = []
    
    for bank_id in bank_ids:
        bank_dir = Path(data_dir) / f"bank_{bank_id}"
        df = pd.read_parquet(bank_dir / f"{split}.parquet")
        
        X = np.array([np.array(x) for x in df['X'].values])
        y = np.asarray(df['y'].values).reshape(-1, 1)
        
        all_X.append(X)
        all_y.append(y)
    
    combined_X = np.concatenate(all_X, axis=0)
    combined_y = np.concatenate(all_y, axis=0)
    
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.parquet', delete=False) as f:
        temp_path = f.name
    
    combined_df = pd.DataFrame({
        'X': [combined_X[i].tolist() for i in range(len(combined_X))],
        'y': combined_y.flatten(),
    })
    combined_df.to_parquet(temp_path, index=False)
    
    dataset = TimeSeriesDataset(
        temp_path,
        normalize=normalize,
        train_stats=None if split == 'train' else None  # Compute from pooled data
    )
    
    return dataset


if __name__ == "__main__":
    # Test dataset loading
    import sys
    
    print("Testing TimeSeriesDataset...")
    
    # Try to load bank 0
    try:
        train_ds, val_ds, test_ds = load_bank_datasets(0)
        
        print(f"Train: {len(train_ds)} samples")
        print(f"Val: {len(val_ds)} samples")
        print(f"Test: {len(test_ds)} samples")
        
        # Sample a batch
        x, y = train_ds[0]
        print(f"\nSample shape:")
        print(f"  X: {x.shape}")
        print(f"  y: {y.shape}")
        
        print(f"\nNormalization stats: {train_ds.get_stats()}")
        
        print("\n[OK] Dataset loading successful!")
        
    except FileNotFoundError as e:
        print(f"\n[ERROR] Data not found: {e}")
        print("Run 'python scripts/create_synthetic_banks.py' first")
        sys.exit(1)
