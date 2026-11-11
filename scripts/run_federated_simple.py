#!/usr/bin/env python3
"""
Simplified federated training using Flower's simulation.
Runs all clients in a single process for macOS compatibility.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import torch
import torch.utils.data
import yaml

import flwr as fl
from flwr.common import ndarrays_to_parameters, parameters_to_ndarrays

import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.data.dataset import load_bank_datasets
from src.models.transformer_ts import create_model
from src.flwr.client import create_client
from src.flwr.server_strategy import create_strategy
from src.privacy.masking import PairwiseMasker, generate_pairwise_seeds, self_test as masking_self_test


def client_fn(cid: str, config: dict, peer_seeds: Optional[Dict[int, int]] = None):
    """Create a Flower client for simulation."""
    client_id = int(cid)
    
    # Set random seed
    torch.manual_seed(config['random_seed'] + client_id)
    np.random.seed(config['random_seed'] + client_id)
    
    # Device
    device = torch.device("cpu")
    
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
    return create_client(
        client_id=client_id,
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        device=device,
        masker=PairwiseMasker(client_id, peer_seeds) if peer_seeds is not None else None
    )


def main():
    parser = argparse.ArgumentParser(description="Federated Training (Simplified)")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Path to configuration file"
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
        default=20,
        help="Number of federated rounds"
    )
    parser.add_argument(
        "--mu",
        type=float,
        default=0.01,
        help="FedProx proximal term (only for fedprox strategy)"
    )
    parser.add_argument(
        "--n_clients",
        type=int,
        default=4,
        help="Number of clients"
    )
    parser.add_argument(
        "--no_masking",
        action="store_true",
        help="Disable secure aggregation"
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="outputs/federated",
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override config with command line args
    config['federated']['strategy'] = args.strategy
    config['federated']['n_rounds'] = args.n_rounds
    if args.strategy == "fedprox":
        config['federated']['mu'] = args.mu
    
    # Set random seed
    torch.manual_seed(config['random_seed'])
    np.random.seed(config['random_seed'])
    
    # Create output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.strategy == "fedprox":
        output_dir = Path(args.output_dir) / f"fedprox_mu{args.mu:.3f}_{timestamp}"
    else:
        output_dir = Path(args.output_dir) / f"fedavg_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save config
    with open(output_dir / "config.yaml", 'w') as f:
        yaml.dump(config, f)
    
    print("="*60)
    print("FEDERATED TRAINING (SIMULATION MODE)")
    print("="*60)
    print(f"Strategy: {args.strategy.upper()}")
    print(f"Clients: {args.n_clients}")
    print(f"Rounds: {args.n_rounds}")
    if args.strategy == "fedprox":
        print(f"FedProx μ: {args.mu}")
    print(f"Secure aggregation: {not args.no_masking}")
    print(f"Output: {output_dir}")
    print("="*60)
    
    # Initialize secure aggregation
    use_masking = not args.no_masking
    client_seeds = None
    
    if use_masking:
        # Pairwise secrets live only in the client_fn closure, never in the strategy.
        print("\nInitializing secure aggregation (pairwise masking)...")
        masking_self_test(n_clients=args.n_clients)
        client_seeds = generate_pairwise_seeds(args.n_clients)
    
    # Initialize global model
    print("\nInitializing global model...")
    global_model = create_model(config['model'])
    initial_parameters = [v.cpu().numpy() for v in global_model.state_dict().values()]
    print(f"Model parameters: {sum(p.numel() for p in global_model.parameters()):,}")
    
    # Create strategy
    print("\nCreating server strategy...")
    strategy = create_strategy(
        strategy_name=args.strategy,
        initial_parameters=ndarrays_to_parameters(initial_parameters),
        config=config,
        evaluate_fn=None,
        masked=use_masking,
    )
    
    # Create client function for simulation
    def wrapped_client_fn(cid: str):
        return client_fn(cid, config, client_seeds[int(cid)] if use_masking else None)
    
    # Run simulation
    print(f"\nStarting federated training simulation...")
    print("-" * 60)
    
    history = fl.simulation.start_simulation(
        client_fn=wrapped_client_fn,
        num_clients=args.n_clients,
        config=fl.server.ServerConfig(num_rounds=config['federated']['n_rounds']),
        strategy=strategy,
        client_resources={"num_cpus": 1},
    )
    
    print("-" * 60)
    print("\n" + "="*60)
    print("FEDERATED TRAINING COMPLETE")
    print("="*60)
    
    # Stop loudly unless every round had all results and no failures
    rounds = strategy.round_log
    n_rounds = config['federated']['n_rounds']
    if len(rounds) != n_rounds or any(
        r["n_failures"] or r.get("eval_n_failures", 1) or "val_loss" not in r for r in rounds
    ):
        print(f"ERROR: federated run incomplete ({len(rounds)}/{n_rounds} complete rounds); "
              "not writing history.json")
        sys.exit(1)
    
    history_dict = {
        "strategy": strategy.strategy_name,
        "n_rounds": n_rounds,
        "masked": strategy.masked,
        "rounds": rounds,
        "losses_distributed": history.losses_distributed,
        "metrics_distributed": history.metrics_distributed,
    }
    
    with open(output_dir / "history.json", 'w') as f:
        json.dump(history_dict, f, indent=2, default=str)
    
    print(f"\n[OK] Training history saved to: {output_dir / 'history.json'}")
    print(f"[OK] Results saved to: {output_dir}")
    print(f"\n[OK] Completed {len(rounds)} federated rounds")
    print("\nNext step: python scripts/run_federated_simple.py --strategy fedavg --n_rounds 10")
    print("          or python scripts/evaluate.py")


if __name__ == "__main__":
    main()
