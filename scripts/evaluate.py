#!/usr/bin/env python3
"""
Comprehensive evaluation of all models.

Compares:
- Local models (per-bank)
- Centralized oracle
- Federated models (FedProx, FedAvg)
- GARCH baseline
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import yaml

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.eval.metrics import comprehensive_evaluation


def load_model_predictions(
    model_type: str,
    bank_id: int = None,
    base_dir: str = "outputs"
) -> Dict:
    """
    Load predictions for a model.
    
    Args:
        model_type: "local", "centralized", "federated", or "garch"
        bank_id: Bank ID (for local/garch models)
        base_dir: Base output directory
    
    Returns:
        Dictionary with predictions, targets, residuals
    """
    base_path = Path(base_dir)
    
    if model_type == "local":
        model_dir = base_path / "local" / f"bank_{bank_id}"
    elif model_type == "centralized":
        model_dir = base_path / "centralized"
    elif model_type == "garch":
        model_dir = base_path / "garch" / f"bank_{bank_id}"
    elif model_type.startswith("federated"):
        # Find latest federated run
        fed_dir = base_path / "federated"
        if not fed_dir.exists():
            return None
        
        # Latest finished run of this strategy (run ids start with the strategy)
        strategy = model_type.split("_", 1)[1] if "_" in model_type else ""
        runs = [
            d for d in fed_dir.iterdir()
            if d.is_dir() and d.name.startswith(strategy)
            and (d / "test_predictions.npy").exists()
        ]
        if not runs:
            print(f"Warning: no finished {model_type} run in {fed_dir}")
            return None
        
        model_dir = max(runs, key=lambda d: (d / "test_predictions.npy").stat().st_mtime)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    if not model_dir.exists():
        print(f"Warning: {model_dir} does not exist")
        return None
    
    # Load predictions
    try:
        predictions = np.load(model_dir / "test_predictions.npy")
        targets = np.load(model_dir / "test_targets.npy")
        residuals = np.load(model_dir / "test_residuals.npy")
        
        return{
            'predictions': predictions,
            'targets': targets,
            'residuals': residuals,
            'path': str(model_dir)
        }
    except FileNotFoundError as e:
        print(f"Warning: Could not load predictions from {model_dir}: {e}")
        return None


def evaluate_all_models(
    bank_ids: List[int],
    output_dir: str = "outputs/evaluation",
    var_levels: List[float] = [0.95, 0.99]
) -> pd.DataFrame:
    """Evaluate all available models."""
    
    results = []
    
    print("="*60)
    print("COMPREHENSIVE MODEL EVALUATION")
    print("="*60)
    
    # Evaluate local models
    print("\nEvaluating local models...")
    for bank_id in bank_ids:
        data = load_model_predictions("local", bank_id)
        if data is not None:
            metrics = comprehensive_evaluation(
                data['predictions'],
                data['targets'],
                var_levels=var_levels
            )
            
            metrics['model_type'] = 'local'
            metrics['bank_id'] = bank_id
            metrics['model_name'] = f'Local Bank {bank_id}'
            
            results.append(metrics)
            print(f"  Bank {bank_id}: VaR(95) error = {metrics['var_95_error']:.6f}")
    
    # Evaluate centralized oracle
    print("\nEvaluating centralized oracle...")
    data = load_model_predictions("centralized")
    if data is not None:
        # For centralized, we need to evaluate on each bank's test set
        # For now, use overall metrics
        metrics = comprehensive_evaluation(
            data['predictions'],
            data['targets'],
            var_levels=var_levels
        )
        
        metrics['model_type'] = 'centralized'
        metrics['bank_id'] = -1  # All banks
        metrics['model_name'] = 'Centralized Oracle'
        
        results.append(metrics)
        print(f"  Overall: VaR(95) error = {metrics['var_95_error']:.6f}")
    
    # Evaluate GARCH baselines
    print("\nEvaluating GARCH baselines...")
    for bank_id in bank_ids:
        data = load_model_predictions("garch", bank_id)
        if data is not None:
            metrics = comprehensive_evaluation(
                data['predictions'],
                data['targets'],
                var_levels=var_levels
            )
            
            metrics['model_type'] = 'garch'
            metrics['bank_id'] = bank_id
            metrics['model_name'] = f'GARCH Bank {bank_id}'
            
            results.append(metrics)
            print(f"  Bank {bank_id}: VaR(95) error = {metrics['var_95_error']:.6f}")
    
    # Evaluate federated models
    print("\nEvaluating federated models...")
    for model_type in ["federated_fedprox", "federated_fedavg"]:
        data = load_model_predictions(model_type)
        if data is not None:
            metrics = comprehensive_evaluation(
                data['predictions'],
                data['targets'],
                var_levels=var_levels
            )
            
            strategy = "FedProx" if "fedprox" in model_type else "FedAvg"
            metrics['model_type'] = model_type
            metrics['bank_id'] = -1
            metrics['model_name'] = f'Federated {strategy}'
            
            results.append(metrics)
            print(f"  {strategy}: VaR(95) error = {metrics['var_95_error']:.6f}")
    
    # Convert to DataFrame
    if not results:
        print("\nNo results found! Please train models first.")
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    csv_path = output_path / "results.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nResults saved to: {csv_path}")
    
    # Generate summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    summary_metrics = ['mse', 'var_95_error', 'var_99_error', 'kurtosis_error', 'acf_error']
    
    summary = df.groupby('model_type')[summary_metrics].mean()
    print("\nAverage metrics by model type:")
    print(summary)
    
    return df


def create_plots(df: pd.DataFrame, output_dir: str = "outputs/evaluation/plots"):
    """Create comparison plots."""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    sns.set_style("whitegrid")
    
    # VaR error comparison
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    
    # VaR 95
    var95_data = df[['model_name', 'var_95_error']].sort_values('var_95_error')
    axes[0].barh(var95_data['model_name'], var95_data['var_95_error'])
    axes[0].set_xlabel('VaR(95) Error')
    axes[0].set_title('VaR 95% Estimation Error')
    
    # VaR 99
    var99_data = df[['model_name', 'var_99_error']].sort_values('var_99_error')
    axes[1].barh(var99_data['model_name'], var99_data['var_99_error'])
    axes[1].set_xlabel('VaR(99) Error')
    axes[1].set_title('VaR 99% Estimation Error')
    
    plt.tight_layout()
    plt.savefig(output_path / "var_comparison.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path / 'var_comparison.png'}")
    
    # Distributional metrics heatmap
    fig, ax = plt.subplots(figsize=(10, 6))
    
    metrics_for_heatmap = ['mse', 'kurtosis_error', 'var_95_error', 'var_99_error', 'acf_error']
    heatmap_data = df[['model_name'] + metrics_for_heatmap].set_index('model_name')
    
    sns.heatmap(heatmap_data, annot=True, fmt='.4f', cmap='YlOrRd', ax=ax)
    ax.set_title('Model Performance Metrics Heatmap')
    
    plt.tight_layout()
    plt.savefig(output_path / "metrics_heatmap.png", dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path / 'metrics_heatmap.png'}")
    
    plt.close('all')


def main():
    parser = argparse.ArgumentParser(description="Evaluate all models")
    parser.add_argument(
        "--output_dir",
        type=str,
        default="outputs/evaluation",
        help="Output directory"
    )
    parser.add_argument(
        "--output_csv",
        type=str,
        default=None,
        help="Output CSV path (default: output_dir/results.csv)"
    )
    parser.add_argument(
        "--bank_ids",
        type=int,
        nargs='+',
        default=[0, 1, 2, 3],
        help="Bank IDs to evaluate"
    )
    parser.add_argument(
        "--plots",
        action="store_true",
        help="Generate plots"
    )
    
    args = parser.parse_args()
    
    # Run evaluation
    df = evaluate_all_models(
        bank_ids=args.bank_ids,
        output_dir=args.output_dir,
        var_levels=[0.95, 0.99]
    )
    
    if not df.empty:
        # Create plots if requested
        if args.plots:
            print("\nGenerating plots...")
            create_plots(df, output_dir=args.output_dir + "/plots")
        
        print("\n" + "="*60)
        print("EVALUATION COMPLETE")
        print("="*60)
        print(f"Results: {args.output_dir}/results.csv")
        if args.plots:
            print(f"Plots: {args.output_dir}/plots/")


if __name__ == "__main__":
    main()
