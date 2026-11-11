#!/usr/bin/env python3
"""
Train centralized Transformer model on pooled data from all banks.

CRITICAL: Preserves temporal ordering per bank. Does NOT shuffle across time.
This represents the "perfect data pooling without privacy" upper bound.
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
import yaml

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.data.dataset import TimeSeriesDataset
from src.models.transformer_ts import create_model, get_loss_function


class PooledDataset(Dataset):
    """Dataset that pools data from multiple banks preserving temporal order."""
    
    def __init__(self, bank_ids: list, data_dir: str, split: str, normalize: bool = True):
        """
        Args:
            bank_ids: List of bank IDs to pool
            data_dir: Data directory
            split: 'train', 'val', or 'test'
            normalize: Whether to normalize
        """
        self.bank_ids = bank_ids
        self.split = split
        
        # Load all bank datasets
        all_X = []
        all_y = []
        
        for bank_id in bank_ids:
            bank_dir = Path(data_dir) / f"bank_{bank_id}"
            df = pd.read_parquet(bank_dir / f"{split}.parquet")
            
            X = np.array([np.array(x) for x in df['X'].values])
            y = df['y'].values.reshape(-1, 1)
            
            all_X.append(X)
            all_y.append(y)
        
        # Concatenate preserving order within each bank
        # This creates heterogeneous pooled data
        self.X = np.concatenate(all_X, axis=0)
        self.y = np.concatenate(all_y, axis=0)
        
        # Normalize using pooled statistics
        if normalize:
            if split == 'train':
                self.mean = float(self.y.mean())
                self.std = float(self.y.std())
            else:
                # For val/test, use train statistics
                # This is handled by passing train_stats
                self.mean = 0.0  # Will be set externally
                self.std = 1.0
            
            if split == 'train':
                self.X = (self.X - self.mean) / (self.std + 1e-8)
                self.y = (self.y - self.mean) / (self.std + 1e-8)
        else:
            self.mean = 0.0
            self.std = 1.0
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        x = torch.FloatTensor(self.X[idx])
        y = torch.FloatTensor(self.y[idx])
        return x, y
    
    def get_stats(self):
        return {'mean': self.mean, 'std': self.std}
    
    def denormalize(self, normalized_values):
        return normalized_values * (self.std + 1e-8) + self.mean


import pandas as pd

def load_pooled_datasets(
    bank_ids: list,
    data_dir: str,
    normalize: bool = True
):
    """Load pooled datasets from multiple banks."""
    
    train_dataset = PooledDataset(bank_ids, data_dir, 'train', normalize)
    
    # Get train stats for val/test normalization
    train_stats = train_dataset.get_stats()
    
    val_dataset = PooledDataset(bank_ids, data_dir, 'val', normalize)
    val_dataset.mean = train_stats['mean']
    val_dataset.std = train_stats['std']
    if normalize:
        val_dataset.X = (val_dataset.X - val_dataset.mean) / (val_dataset.std + 1e-8)
        val_dataset.y = (val_dataset.y - val_dataset.mean) / (val_dataset.std + 1e-8)
    
    test_dataset = PooledDataset(bank_ids, data_dir, 'test', normalize)
    test_dataset.mean = train_stats['mean']
    test_dataset.std = train_stats['std']
    if normalize:
        test_dataset.X = (test_dataset.X - test_dataset.mean) / (test_dataset.std + 1e-8)
        test_dataset.y = (test_dataset.y - test_dataset.mean) / (test_dataset.std + 1e-8)
    
    return train_dataset, val_dataset, test_dataset


def train_epoch(model, dataloader, criterion, optimizer, device, max_grad_norm=1.0):
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    
    for X, y in dataloader:
        X, y = X.to(device), y.to(device)
        
        y_pred = model(X)
        loss = criterion(y_pred, y)
        
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
        optimizer.step()
        
        total_loss += loss.item() * len(X)
    
    return total_loss / len(dataloader.dataset)


def evaluate(model, dataloader, criterion, device):
    """Evaluate model."""
    model.eval()
    total_loss = 0.0
    all_preds = []
    all_targets = []
    
    with torch.no_grad():
        for X, y in dataloader:
            X, y = X.to(device), y.to(device)
            
            y_pred = model(X)
            loss = criterion(y_pred, y)
            
            total_loss += loss.item() * len(X)
            all_preds.append(y_pred.cpu().numpy())
            all_targets.append(y.cpu().numpy())
    
    avg_loss = total_loss / len(dataloader.dataset)
    predictions = np.concatenate(all_preds, axis=0)
    targets = np.concatenate(all_targets, axis=0)
    
    return avg_loss, predictions, targets


def main():
    parser = argparse.ArgumentParser(description="Train centralized oracle model")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Configuration file"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="outputs/centralized",
        help="Output directory"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        choices=["cpu", "cuda", "mps"],
        help="Device to use"
    )
    parser.add_argument(
        "--bank_ids",
        type=int,
        nargs='+',
        default=[0, 1, 2, 3],
        help="Banks to pool"
    )
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Set random seed
    torch.manual_seed(config['random_seed'])
    np.random.seed(config['random_seed'])
    
    # Device
    if args.device == "mps" and torch.backends.mps.is_available():
        device = torch.device("mps")
    elif args.device == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    
    print("="*60)
    print("CENTRALIZED ORACLE TRAINING")
    print("="*60)
    print(f"Pooling banks: {args.bank_ids}")
    print(f"Device: {device}")
    print("IMPORTANT: Preserving temporal ordering per bank")
    print("="*60)
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load pooled datasets
    print("\nLoading pooled datasets...")
    train_dataset, val_dataset, test_dataset = load_pooled_datasets(
        args.bank_ids,
        data_dir=config['paths']['data_processed'],
        normalize=True
    )
    
    print(f"Train: {len(train_dataset)} samples")
    print(f"Val: {len(val_dataset)} samples")
    print(f"Test: {len(test_dataset)} samples")
    
    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=True,  # Shuffle batches but temporal order preserved within banks
        num_workers=0
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=False,
        num_workers=0
    )
    
    test_loader = DataLoader(
        test_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=False,
        num_workers=0
    )
    
    # Create model
    print("\nCreating model...")
    model = create_model(config['model']).to(device)
    print(f"Parameters: {model.count_parameters():,}")
    
    # Loss and optimizer
    criterion = get_loss_function(
        config['training']['loss_type'],
        config['training']['huber_delta']
    )
    
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config['training']['lr'],
        weight_decay=config['training']['weight_decay']
    )
    
    # Training loop
    print("\nTraining...")
    best_val_loss = float('inf')
    best_epoch = 0
    history = {'train_loss': [], 'val_loss': []}
    
    n_epochs = 50
    patience = 10
    patience_counter = 0
    
    for epoch in range(n_epochs):
        train_loss = train_epoch(
            model, train_loader, criterion, optimizer, device,
            max_grad_norm=config['training']['max_grad_norm']
        )
        
        val_loss, _, _ = evaluate(model, val_loader, criterion, device)
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1}/{n_epochs}: "
                  f"Train Loss = {train_loss:.6f}, "
                  f"Val Loss = {val_loss:.6f}")
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'config': config,
            }, Path(args.output_dir) / "best_model.pt")
        else:
            patience_counter += 1
        
        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch+1}")
            break
    
    print(f"\nBest model: Epoch {best_epoch+1}, Val Loss = {best_val_loss:.6f}")
    
    # Load best model
    checkpoint = torch.load(Path(args.output_dir) / "best_model.pt")
    model.load_state_dict(checkpoint['model_state_dict'])
    
    # Evaluate on test set
    print("\nEvaluating on test set...")
    test_loss, test_predictions, test_targets = evaluate(
        model, test_loader, criterion, device
    )
    
    print(f"Test Loss: {test_loss:.6f}")
    
    # Denormalize
    test_predictions_denorm = test_dataset.denormalize(test_predictions)
    test_targets_denorm = test_dataset.denormalize(test_targets)
    residuals = test_predictions_denorm - test_targets_denorm
    
    # Save results
    np.save(Path(args.output_dir) / "test_predictions.npy", test_predictions_denorm)
    np.save(Path(args.output_dir) / "test_targets.npy", test_targets_denorm)
    np.save(Path(args.output_dir) / "test_residuals.npy", residuals)
    
    with open(Path(args.output_dir) / "training_history.json", 'w') as f:
        json.dump(history, f, indent=2)
    
    metadata = {
        'model_type': 'centralized_oracle',
        'bank_ids': args.bank_ids,
        'best_epoch': best_epoch,
        'best_val_loss': float(best_val_loss),
        'test_loss': float(test_loss),
        'n_parameters': model.count_parameters(),
        'train_stats': train_dataset.get_stats(),
    }
    
    with open(Path(args.output_dir) / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nSaved outputs to: {args.output_dir}")
    print("\n" + "="*60)
    print("CENTRALIZED TRAINING COMPLETE")
    print("="*60)
    print("Next step: python scripts/run_federated.py")


if __name__ == "__main__":
    main()