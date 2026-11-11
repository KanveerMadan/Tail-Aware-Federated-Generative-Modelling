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
from typing import Dict, Optional

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
from src.privacy.masking import PairwiseMasker, generate_pairwise_seeds, self_test as masking_self_test


def write_history(strategy, n_rounds: int, output_dir: Path) -> None:
    """Write history.json, or fail if any round is missing or incomplete."""
    rounds = strategy.round_log
    if len(rounds) != n_rounds or any(
        r["n_failures"] or r.get("eval_n_failures", 1) or "val_loss" not in r for r in rounds
    ):
        raise RuntimeError(
            f"Federated run incomplete: {len(rounds)}/{n_rounds} complete rounds; "
            "not writing history.json"
        )
    with open(output_dir / "history.json", "w") as f:
        json.dump({"strategy": strategy.strategy_name, "n_rounds": n_rounds,
                   "masked": strategy.masked, "rounds": rounds}, f, indent=2)
    print(f"[OK] History saved to: {output_dir / 'history.json'}")


def run_server(server_address: str, n_rounds: int, strategy, output_dir: Path):
    """Run the Flower server; exits non-zero (exception) if any round fails."""
    fl.server.start_server(
        server_address=server_address,
        config=fl.server.ServerConfig(num_rounds=n_rounds),
        strategy=strategy,
    )
    write_history(strategy, n_rounds, output_dir)


def run_client(
    client_id: int,
    config: Dict,
    server_address: str,
    peer_seeds: Optional[Dict[int, int]] = None
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
            masker=PairwiseMasker(client_id, peer_seeds) if peer_seeds is not None else None
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
        sys.exit(1)


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
    
    # Pairwise secrets for secure aggregation. Created here in the client launch
    # code; each client process gets only its own seeds, the server gets none.
    use_masking = not args.no_masking
    client_seeds = None
    
    if use_masking:
        print("\nInitializing secure aggregation (pairwise masking)...")
        masking_self_test(n_clients=args.n_clients)
        client_seeds = generate_pairwise_seeds(args.n_clients)
    
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
        evaluate_fn=None,
        masked=use_masking,
    )
    
    # Start server in background
    print(f"\nStarting Flower server on {args.server_address}...")
    
    server_process = mp.Process(
        target=run_server,
        args=(args.server_address, config['federated']['n_rounds'], strategy, output_dir)
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
            args=(client_id, config, args.server_address,
                  client_seeds[client_id] if use_masking else None)
        )
        p.start()
        client_processes.append(p)
        print(f"Started client {client_id}")
        time.sleep(1)  # Stagger client starts
    
    # Wait for all clients to finish
    print("\nWaiting for federated training to complete...")
    for p in client_processes:
        p.join()
    
    # Wait for server to finish (it writes history.json and the results)
    server_process.join(timeout=900)
    if server_process.is_alive():
        server_process.terminate()
        server_process.join()
    
    client_codes = [p.exitcode for p in client_processes]
    if server_process.exitcode != 0 or any(c != 0 for c in client_codes):
        print("\n" + "="*60)
        print("FEDERATED TRAINING FAILED")
        print("="*60)
        print(f"Server exit code: {server_process.exitcode}, client exit codes: {client_codes}")
        sys.exit(1)
    if not (output_dir / "history.json").exists():
        print(f"ERROR: {output_dir / 'history.json'} was not written")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("FEDERATED TRAINING COMPLETE")
    print("="*60)
    print(f"Results saved to: {output_dir}")
    print("\nNext step: python scripts/evaluate.py")


if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)  # Required for multiprocessing
    main()
