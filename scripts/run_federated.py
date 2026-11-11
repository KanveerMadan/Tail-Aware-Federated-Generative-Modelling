#!/usr/bin/env python3
"""
Run federated training with Flower.

Launches server and multiple client processes on single machine.
Supports FedProx and FedAvg strategies with secure aggregation.
"""

import argparse
import json
import multiprocessing as mp
import os
from pathlib import Path
import time
from typing import Dict

# Fix for macOS multiprocessing
mp.set_start_method('fork', force=True)

import numpy as np
import torch
import yaml

import flwr as fl
from flwr.common import ndarrays_to_parameters

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.data.dataset import load_bank_datasets
from src.models.transformer_ts import create_model
from src.flwr.client import create_client
from src.flwr.server_strategy import create_strategy
from src.privacy.masking import MaskCoordinator


def run_server(server_address: str, n_rounds: int, strategy):
    """Run the Flower server."""
    fl.server.start_server(
        server_address=server_address,
        config=fl.server.ServerConfig(num_rounds=n_rounds),
        strategy=strategy,
    )


def run_client(
    client_id: int,
    config: Dict,
    server_address: str,
    use_masking: bool,
    mask_coordinator: MaskCoordinator = None
):
    """Run a single client process."""
    try:
        # Set random seed
        torch.manual_seed(config['random_seed'] + client_id)
        np.random.seed(config['random_seed'] + client_id)
        
        # Device
        device = torch.device("cpu")  # Use CPU for simulated clients
        
        # Load datasets
        train_dataset, val_dataset, _ = load_bank_datasets(
            client_id,
            data_dir=config['paths']['data_processed'],
            normalize=True
        )
        
        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=config['training']['batch_size'],
            shuffle=True
        )
        
        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=config['training']['batch_size'],
            shuffle=False
        )
        
        # Create model
        model = create_model(config['model']).to(device)
        
        # Create client
        client = create_client(
            client_id=client_id,
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            config=config,
            device=device,
            mask_coordinator=mask_coordinator if use_masking else None
        )
        
        # Connect to server
        print(f"Client {client_id} connecting to {server_address}...")
        fl.client.start_numpy_client(
            server_address=server_address,
            client=client
        )
        
        print(f"Client {client_id} finished")
        
    except Exception as e:
        print(f"Client {client_id} error: {e}")
        import traceback
        traceback.print_exc()


def save_global_model(
    parameters,
    server_round: int,
    output_dir: Path,
    config: Dict
):
    """Save global model checkpoint."""
    # Convert parameters to state dict
    model = create_model(config['model'])
    
    keys = list(model.state_dict().keys())
    model.load_state_dict(
        {k: torch.from_numpy(np.asarray(v, dtype=np.float32)) for k, v in zip(keys, parameters)},
        strict=True,
    )
    
    # Save checkpoint
    checkpoint_path = output_dir / f"round_{server_round:03d}.pt"
    torch.save({
        'round': server_round,
        'model_state_dict': model.state_dict(),
        'config': config,
    }, checkpoint_path)
    
    # Also save as latest
    latest_path = output_dir / "latest.pt"
    torch.save({
        'round': server_round,
        'model_state_dict': model.state_dict(),
        'config': config,
    }, latest_path)


def main():
    parser = argparse.ArgumentParser(description="Run federated training")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Configuration file"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="fedprox",
        choices=["fedprox", "fedavg"],
        help="Federated learning strategy"
    )
    parser.add_argument(
        "--n_rounds",
        type=int,
        default=None,
        help="Number of federated rounds (default: from config)"
    )
    parser.add_argument(
        "--mu",
        type=float,
        default=None,
        help="FedProx proximal term (default: from config)"
    )
    parser.add_argument(
        "--n_clients",
        type=int,
        default=4,
        help="Number of clients"
    )
    parser.add_argument(
        "--run_id",
        type=str,
        default=None,
        help="Run identifier"
    )
    parser.add_argument(
        "--no_masking",
        action="store_true",
        help="Disable secure aggregation masking"
    )
    parser.add_argument(
        "--server_address",
        type=str,
        default="127.0.0.1:8080",
        help="Server address"
    )
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override config with command line args
    if args.n_rounds is not None:
        config['federated']['n_rounds'] = args.n_rounds
    
    if args.mu is not None:
        config['federated']['mu'] = args.mu
    
    if args.strategy == "fedavg":
        config['federated']['mu'] = 0.0  # Disable proximal term for FedAvg
    
    # Generate run ID
    if args.run_id is None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        args.run_id = f"{args.strategy}_mu{config['federated']['mu']:.3f}_{timestamp}"
    
    # Create output directory
    output_dir = Path(config['paths']['outputs']) / "federated" / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set random seed
    torch.manual_seed(config['random_seed'])
    np.random.seed(config['random_seed'])
    
    print("="*60)
    print("FEDERATED TRAINING")
    print("="*60)
    print(f"Strategy: {args.strategy.upper()}")
    print(f"Clients: {args.n_clients}")
    print(f"Rounds: {config['federated']['n_rounds']}")
    print(f"FedProx μ: {config['federated']['mu']}")
    print(f"Secure aggregation: {not args.no_masking}")
    print(f"Output: {output_dir}")
    print(f"Server: {args.server_address}")
    print("="*60)
    
    # Create mask coordinator for secure aggregation
    use_masking = not args.no_masking
    mask_coordinator = None
    
    if use_masking:
        print("\nInitializing secure aggregation...")
        mask_coordinator = MaskCoordinator(
            n_clients=args.n_clients,
            seed=config['random_seed']
        )
        
        # Test masking
        model = create_model(config['model'])
        param_shapes = [p.shape for p in model.parameters()]
        mask_coordinator.test_cancellation(param_shapes)
    
    # Create initial model
    print("\nInitializing global model...")
    initial_model = create_model(config['model'])
    initial_parameters = [v.cpu().numpy() for v in initial_model.state_dict().values()]
    
    print(f"Model parameters: {initial_model.count_parameters():,}")
    
    # Save configuration
    with open(output_dir / "config.yaml", 'w') as f:
        yaml.dump(config, f)
    
    with open(output_dir / "run_info.json", 'w') as f:
        json.dump({
            'strategy': args.strategy,
            'n_clients': args.n_clients,
            'n_rounds': config['federated']['n_rounds'],
            'mu': config['federated']['mu'],
            'use_masking': use_masking,
            'run_id': args.run_id,
        }, f, indent=2)
    
    # Create strategy
    print("\nCreating server strategy...")
    strategy = create_strategy(
        strategy_name=args.strategy,
        initial_parameters=ndarrays_to_parameters(initial_parameters),
        config=config,
        evaluate_fn=None
    )
    
    # Start server in background
    print(f"\nStarting Flower server on {args.server_address}...")
    
    server_process = mp.Process(
        target=run_server,
        args=(args.server_address, config['federated']['n_rounds'], strategy)
    )
    server_process.start()
    
    # Wait for server to start
    time.sleep(5)
    
    # Start clients
    print(f"\nStarting {args.n_clients} clients...")
    client_processes = []
    
    for client_id in range(args.n_clients):
        p = mp.Process(
            target=run_client,
            args=(client_id, config, args.server_address, use_masking, mask_coordinator)
        )
        p.start()
        client_processes.append(p)
        print(f"Started client {client_id}")
        time.sleep(1)  # Stagger client starts
    
    # Wait for all clients to finish
    print("\nWaiting for federated training to complete...")
    for p in client_processes:
        p.join()
    
    # Wait for server to finish
    server_process.join(timeout=10)
    if server_process.is_alive():
        server_process.terminate()
    
    print("\n" + "="*60)
    print("FEDERATED TRAINING COMPLETE")
    print("="*60)
    print(f"Results saved to: {output_dir}")
    print("\nNext step: python scripts/evaluate.py")


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)  # Required for multiprocessing
    main()
