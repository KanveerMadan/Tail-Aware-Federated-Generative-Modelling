#!/usr/bin/env python3
"""
Train Transformer model locally on individual bank data.
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from tqdm import tqdm
import yaml

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.data.dataset import load_bank_datasets
from src.models.transformer_ts import create_model, get_loss_function


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    max_grad_norm: float = 1.0
) -> float:
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


def evaluate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device
) -> tuple:
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


def train_local_model(
    bank_id: int,
    config: dict,
    output_dir: str,
    device: torch.device
) -> dict:
    """Train model for a single bank."""
    
    print(f"\n{'='*60}")
    print(f"Training Bank {bank_id}")
    print(f"{'='*60}\n")
    
    # Load datasets
    print("Loading datasets...")
    train_dataset, val_dataset, test_dataset = load_bank_datasets(
        bank_id,
        data_dir=config['paths']['data_processed'],
        normalize=True
    )
    
    print(f"Train: {len(train_dataset)} samples")
    print(f"Val: {len(val_dataset)} samples")
    print(f"Test: {len(test_dataset)} samples")
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['training']['batch_size'],
        shuffle=True,
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
    
    print("\nCreating model...")
    model = create_model(config['model']).to(device)
    print(f"Parameters: {model.count_parameters():,}")
    
    criterion = get_loss_function(
        config['training']['loss_type'],
        config['training']['huber_delta']
    )
    
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config['training']['lr'],
        weight_decay=config['training']['weight_decay']
    )
    
    print("\nTraining...")
    best_val_loss = float('inf')
    best_epoch = 0
    history = {'train_loss': [], 'val_loss': []}
    
    n_epochs = config['training']['local_epochs'] * 10  # Train for more epochs locally
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
            
            bank_output_dir = Path(output_dir) / f"bank_{bank_id}"
            bank_output_dir.mkdir(parents=True, exist_ok=True)
            
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'config': config,
            }, bank_output_dir / "best_model.pt")
        else:
            patience_counter += 1
        
        if patience_counter >= patience:
            print(f"\nEarly stopping at epoch {epoch+1}")
            break
    
    print(f"\nBest model: Epoch {best_epoch+1}, Val Loss = {best_val_loss:.6f}")
    
    checkpoint = torch.load(bank_output_dir / "best_model.pt")
    model.load_state_dict(checkpoint['model_state_dict'])
    
    print("\nEvaluating on test set...")
    test_loss, test_predictions, test_targets = evaluate(
        model, test_loader, criterion, device
    )
    
    print(f"Test Loss: {test_loss:.6f}")
    
    test_predictions_denorm = train_dataset.denormalize(test_predictions)
    test_targets_denorm = train_dataset.denormalize(test_targets)
    
    residuals = test_predictions_denorm - test_targets_denorm
    
    np.save(bank_output_dir / "test_predictions.npy", test_predictions_denorm)
    np.save(bank_output_dir / "test_targets.npy", test_targets_denorm)
    np.save(bank_output_dir / "test_residuals.npy", residuals)
    
    with open(bank_output_dir / "training_history.json", 'w') as f:
        json.dump(history, f, indent=2)
    
    metadata = {
        'bank_id': bank_id,
        'best_epoch': best_epoch,
        'best_val_loss': float(best_val_loss),
        'test_loss': float(test_loss),
        'n_parameters': model.count_parameters(),
        'train_stats': train_dataset.get_stats(),
    }
    
    with open(bank_output_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"\nSaved outputs to: {bank_output_dir}")
    
    return metadata


def main():
    parser = argparse.ArgumentParser(description="Train local Transformer models")
    parser.add_argument(
        "--bank_id",
        type=int,
        choices=[0, 1, 2, 3],
        default=None,
        help="Specific bank to train (default: all)"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Configuration file"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="outputs/local",
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
        "--all",
        action="store_true",
        help="Train all banks"
    )
    
    args = parser.parse_args()
    
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    torch.manual_seed(config['random_seed'])
    np.random.seed(config['random_seed'])
    
    if args.device == "mps" and torch.backends.mps.is_available():
        device = torch.device("mps")
    elif args.device == "cuda" and torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")
    
    print("="*60)
    print("LOCAL MODEL TRAINING")
    print("="*60)
    print(f"Device: {device}")
    print(f"Output directory: {args.output_dir}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Train banks
    results = {}
    
    if args.all or args.bank_id is None:
        bank_ids = [0, 1, 2, 3]
    else:
        bank_ids = [args.bank_id]
    
    for bank_id in bank_ids:
        metadata = train_local_model(bank_id, config, args.output_dir, device)
        results[f"bank_{bank_id}"] = metadata
    
    # Save summary
    summary_path = Path(args.output_dir) / "training_summary.json"
    with open(summary_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "="*60)
    print("LOCAL TRAINING COMPLETE")
    print("="*60)
    print(f"Summary saved to: {summary_path}")
    print("\nNext step: python scripts/train_centralized.py")


if __name__ == "__main__":
    main()
