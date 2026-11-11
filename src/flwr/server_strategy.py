"""
Custom Flower server strategy for FedProx and FedAvg.
"""

from typing import Dict, List, Optional, Tuple, Union
import numpy as np

import flwr as fl
from flwr.common import (
    EvaluateRes,
    FitRes,
    Parameters,
    Scalar,
    parameters_to_ndarrays,
    ndarrays_to_parameters,
)
from flwr.server.client_proxy import ClientProxy

from src.privacy.masking import unmask_weighted_average


class FedProxStrategy(fl.server.strategy.FedAvg):
    """
    Custom strategy for FedProx.
    
    Extends FedAvg to:
    1. Send global model weights to clients for proximal term computation
    2. Standard weighted averaging of client updates
    3. Optional model checkpointing per round
    """
    
    def __init__(
        self,
        *,
        fraction_fit: float = 1.0,
        fraction_evaluate: float = 1.0,
        min_fit_clients: int = 2,
        min_evaluate_clients: int = 2,
        min_available_clients: int = 2,
        evaluate_fn: Optional[callable] = None,
        on_fit_config_fn: Optional[callable] = None,
        on_evaluate_config_fn: Optional[callable] = None,
        accept_failures: bool = True,
        initial_parameters: Optional[Parameters] = None,
        fit_metrics_aggregation_fn: Optional[callable] = None,
        evaluate_metrics_aggregation_fn: Optional[callable] = None,
        strategy_name: str = "FedProx",
        masked: bool = False,
    ):
        """
        Args:
            fraction_fit: Fraction of clients to sample for training
            min_fit_clients: Minimum number of clients for training
            min_available_clients: Minimum total clients required
            strategy_name: Name of strategy ("FedProx" or "FedAvg")
            masked: Clients send pairwise-masked n_i * w_i (secure aggregation)
        """
        super().__init__(
            fraction_fit=fraction_fit,
            fraction_evaluate=fraction_evaluate,
            min_fit_clients=min_fit_clients,
            min_evaluate_clients=min_evaluate_clients,
            min_available_clients=min_available_clients,
            evaluate_fn=evaluate_fn,
            on_fit_config_fn=on_fit_config_fn,
            on_evaluate_config_fn=on_evaluate_config_fn,
            accept_failures=accept_failures,
            initial_parameters=initial_parameters,
            fit_metrics_aggregation_fn=fit_metrics_aggregation_fn,
            evaluate_metrics_aggregation_fn=evaluate_metrics_aggregation_fn,
        )
        
        self.strategy_name = strategy_name
        self.masked = masked
        self.current_round = 0
    
    def configure_fit(
        self,
        server_round: int,
        parameters: Parameters,
        client_manager: fl.server.client_manager.ClientManager
    ) -> List[Tuple[ClientProxy, fl.common.FitIns]]:
        """
        Configure the next round of training.
        
        Sends global model parameters to clients for FedProx proximal term.
        """
        self.current_round = server_round
        
        # Standard client sampling
        config = {}
        if self.on_fit_config_fn is not None:
            config = self.on_fit_config_fn(server_round)
        
        # Sample clients
        sample_size, min_num_clients = self.num_fit_clients(
            client_manager.num_available()
        )
        
        clients = client_manager.sample(
            num_clients=sample_size,
            min_num_clients=min_num_clients
        )
        
        # Create fit instructions with global parameters
        fit_ins = fl.common.FitIns(parameters, config)
        
        return [(client, fit_ins) for client in clients]
    
    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, FitRes]],
        failures: List[Union[Tuple[ClientProxy, FitRes], BaseException]],
    ) -> Tuple[Optional[Parameters], Dict[str, Scalar]]:
        """
        Aggregate model updates from clients.
        
        For secure aggregation:
        - Clients send masked updates
        - Aggregation cancels masks automatically
        - Server receives sum of updates without seeing individual updates
        """
        if not results:
            return None, {}
        
        # Log failures
        if failures:
            print(f"Round {server_round}: {len(failures)} client failures")
        
        if self.masked:
            # Each client sent n_i * w_i + mask_i. The masks cancel in the sum,
            # so sum / sum(n_i) is the FedAvg weighted mean. The server never
            # holds any pairwise seed, so it cannot unmask a single update.
            masked_updates = [parameters_to_ndarrays(r.parameters) for _, r in results]
            num_examples = [r.num_examples for _, r in results]
            averaged = unmask_weighted_average(masked_updates, num_examples)
            aggregated_parameters = ndarrays_to_parameters(
                [a.astype(np.float32) for a in averaged]
            )
            metrics = {}
            if self.fit_metrics_aggregation_fn is not None:
                metrics = self.fit_metrics_aggregation_fn(
                    [(r.num_examples, r.metrics) for _, r in results]
                )
        else:
            # Weighted averaging (standard FedAvg)
            aggregated_parameters, metrics = super().aggregate_fit(
                server_round, results, failures
            )
        
        # Extract training metrics
        train_losses = [r.metrics.get("train_loss", 0.0) for _, r in results]
        avg_train_loss = float(np.mean(train_losses))
        
        metrics["train_loss"] = avg_train_loss
        
        # Print progress
        print(f"Round {server_round} - Strategy: {self.strategy_name} - "
              f"Avg Train Loss: {avg_train_loss:.6f}")
        
        return aggregated_parameters, metrics
    
    def aggregate_evaluate(
        self,
        server_round: int,
        results: List[Tuple[ClientProxy, EvaluateRes]],
        failures: List[Union[Tuple[ClientProxy, EvaluateRes], BaseException]],
    ) -> Tuple[Optional[float], Dict[str, Scalar]]:
        """Aggregate evaluation results from clients."""
        if not results:
            return None, {}
        
        # Weighted averaging of losses
        losses = [r.loss * r.num_examples for _, r in results]
        examples = [r.num_examples for _, r in results]
        
        aggregated_loss = sum(losses) / sum(examples) if sum(examples) > 0 else 0.0
        
        # Aggregate metrics
        metrics = {}
        if results:
            # Get validation losses
            val_losses = [r.metrics.get("val_loss", 0.0) for _, r in results]
            metrics["val_loss"] = float(np.mean(val_losses))
        
        print(f"Round {server_round} - Avg Val Loss: {metrics.get('val_loss', 0.0):.6f}")
        
        return aggregated_loss, metrics


def create_strategy(
    strategy_name: str,
    initial_parameters: Parameters,
    config: Dict,
    evaluate_fn: Optional[callable] = None,
    masked: bool = False,
) -> FedProxStrategy:
    """
    Factory function to create strategy.
    
    Args:
        strategy_name: "fedprox" or "fedavg"
        initial_parameters: Initial model parameters
        config: Configuration dict
        evaluate_fn: Optional server-side evaluation function
    
    Returns:
        FedProx strategy instance
    """
    
    def fit_config(server_round: int):
        """Return training configuration for each round."""
        return {
            "local_epochs": config['training']['local_epochs'],
            "server_round": server_round,
        }
    
    def evaluate_config(server_round: int):
        """Return evaluation configuration for each round."""
        return {
            "server_round": server_round,
        }
    
    def fit_metrics_aggregation_fn(metrics: List[Tuple[int, Dict]]) -> Dict:
        """Aggregate training metrics from clients."""
        # Weighted average of metrics
        total_examples = sum([num_examples for num_examples, _ in metrics])
        
        aggregated = {}
        if metrics:
            # Average train loss
            train_losses = [m.get("train_loss", 0.0) * n for n, m in metrics]
            aggregated["train_loss"] = sum(train_losses) / total_examples
        
        return aggregated
    
    def evaluate_metrics_aggregation_fn(metrics: List[Tuple[int, Dict]]) -> Dict:
        """Aggregate evaluation metrics from clients."""
        total_examples = sum([num_examples for num_examples, _ in metrics])
        
        aggregated = {}
        if metrics:
            # Average validation loss
            val_losses = [m.get("val_loss", 0.0) * n for n, m in metrics]
            aggregated["val_loss"] = sum(val_losses) / total_examples
        
        return aggregated
    
    strategy = FedProxStrategy(
        fraction_fit=config['federated']['fraction_fit'],
        min_fit_clients=config['federated']['min_fit_clients'],
        min_available_clients=config['federated']['min_available_clients'],
        evaluate_fn=evaluate_fn,
        on_fit_config_fn=fit_config,
        on_evaluate_config_fn=evaluate_config,
        initial_parameters=initial_parameters,
        fit_metrics_aggregation_fn=fit_metrics_aggregation_fn,
        evaluate_metrics_aggregation_fn=evaluate_metrics_aggregation_fn,
        strategy_name=strategy_name.upper(),
        masked=masked,
    )
    
    return strategy
