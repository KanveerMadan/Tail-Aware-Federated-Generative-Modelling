"""
Flower client implementation with FedProx and secure aggregation.
"""

from typing import Dict, List, Tuple, Optional
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

import flwr as fl

from src.models.transformer_ts import get_loss_function
from src.privacy.masking import MaskCoordinator


class FedProxClient(fl.client.NumPyClient):
    """
    Federated client implementing FedProx algorithm with secure aggregation.
    
    FedProx modification: Adds proximal term to local objective:
        L_local = L_task + (μ/2) * ||w - w_global||²
    
    where w_global is the global model received from server.
    """
    
    def __init__(
        self,
        client_id: int,
        model: nn.Module,
        train_loader: DataLoader,
        val_loader: DataLoader,
        config: Dict,
        device: torch.device,
        mask_coordinator: Optional[MaskCoordinator] = None
    ):
        """
        Args:
            client_id: Unique client identifier
            model: Local model instance
            train_loader: Training data loader
            val_loader: Validation data loader
            config: Configuration dictionary
            device: Torch device
            mask_coordinator: Optional masking coordinator for secure aggregation
        """
        self.client_id = client_id
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.config = config
        self.device = device
        self.mask_coordinator = mask_coordinator
        
        self.mu = config['federated'].get('mu', 0.01)
        
        self.global_params = None
    
    def get_parameters(self, config: Dict) -> List[np.ndarray]:
        """
        Return model parameters (with optional masking for secure aggregation).
        """
        # Extract parameters as NumPy arrays
        params = [p.cpu().detach().numpy() for p in self.model.parameters()]
        
        # Apply masking if coordinator is available
        if self.mask_coordinator is not None:
            params = self.mask_coordinator.apply_mask(params, self.client_id)
        
        return params
    
    def set_parameters(self, parameters: List[np.ndarray]) -> None:
        """
        Set model parameters from server.
        """
        # Store current global parameters for proximal term
        self.global_params = [p.copy() for p in parameters]
        
        # Update model
        params_dict = zip(self.model.parameters(), parameters)
        for param, new_param in params_dict:
            param.data = torch.from_numpy(new_param).to(self.device)
    
    def fit(
        self,
        parameters: List[np.ndarray],
        config: Dict
    ) -> Tuple[List[np.ndarray], int, Dict]:
        """
        Train model locally with FedProx objective.
        
        Returns:
            Updated parameters, number of samples, metrics
        """
        # Set global parameters
        self.set_parameters(parameters)
        
        # Get training configuration
        local_epochs = config.get("local_epochs", self.config['training']['local_epochs'])
        
        metrics, num_samples = self._train_fedprox(local_epochs)
        
        updated_params = self.get_parameters(config)
        
        return updated_params, num_samples, metrics
    
    def evaluate(
        self,
        parameters: List[np.ndarray],
        config: Dict
    ) -> Tuple[float, int, Dict]:
        """
        Evaluate model on local validation set.
        
        Returns:
            Loss, number of samples, metrics
        """
        # Set parameters
        self.set_parameters(parameters)
        
        # Evaluate
        loss, num_samples = self._evaluate()
        
        return float(loss), num_samples, {"val_loss": float(loss)}
    
    def _train_fedprox(self, local_epochs: int) -> Tuple[Dict, int]:
        """
        Train with FedProx proximal term.
        
        Returns:
            Metrics dict and total number of samples
        """
        self.model.train()
        
        criterion = get_loss_function(
            self.config['training']['loss_type'],
            self.config['training']['huber_delta']
        )
        
        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config['training']['lr'],
            weight_decay=self.config['training']['weight_decay']
        )
        
        total_loss = 0.0
        total_samples = 0
        
        for epoch in range(local_epochs):
            epoch_loss = 0.0
            
            for X, y in self.train_loader:
                X, y = X.to(self.device), y.to(self.device)
                
                y_pred = self.model(X)
                task_loss = criterion(y_pred, y)
                
                proximal_term = 0.0
                if self.global_params is not None and self.mu > 0:
                    for param, global_param in zip(
                        self.model.parameters(),
                        self.global_params
                    ):
                        global_param_tensor = torch.from_numpy(global_param).to(self.device)
                        proximal_term += torch.sum((param - global_param_tensor) ** 2)
                    
                    proximal_term = (self.mu / 2) * proximal_term
                
                loss = task_loss + proximal_term
                
                optimizer.zero_grad()
                loss.backward()
                
                torch.nn.utils.clip_grad_norm_(
                    self.model.parameters(),
                    self.config['training']['max_grad_norm']
                )
                
                optimizer.step()
                
                epoch_loss += loss.item() * len(X)
                total_samples += len(X)
            
            total_loss += epoch_loss
        
        avg_loss = total_loss / total_samples if total_samples > 0 else 0.0
        
        metrics = {
            "train_loss": float(avg_loss),
            "mu": float(self.mu),
            "local_epochs": local_epochs
        }
        
        return metrics, total_samples
    
    def _evaluate(self) -> Tuple[float, int]:
        """Evaluate on validation set.
        
        Returns:
            Average loss and number of samples
        """
        self.model.eval()
        
        criterion = get_loss_function(
            self.config['training']['loss_type'],
            self.config['training']['huber_delta']
        )
        
        total_loss = 0.0
        total_samples = 0
        
        with torch.no_grad():
            for X, y in self.val_loader:
                X, y = X.to(self.device), y.to(self.device)
                
                y_pred = self.model(X)
                loss = criterion(y_pred, y)
                
                batch_size = len(X)
                total_loss += loss.item() * batch_size
                total_samples += batch_size
        
        avg_loss = total_loss / total_samples if total_samples > 0 else 0.0
        
        return avg_loss, total_samples


def create_client(
    client_id: int,
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    config: Dict,
    device: torch.device,
    mask_coordinator: Optional[MaskCoordinator] = None
) -> FedProxClient:
    """Factory function to create Flower client."""
    return FedProxClient(
        client_id=client_id,
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        device=device,
        mask_coordinator=mask_coordinator
    )
