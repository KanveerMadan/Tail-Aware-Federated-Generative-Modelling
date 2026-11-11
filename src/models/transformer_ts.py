"""
Autoregressive Transformer for time series prediction.
"""

import math
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for time series."""
    
    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor [seq_len, batch, embed_dim]
        """
        x = x + self.pe[:x.size(0)]
        return self.dropout(x)


class TimeSeriesTransformer(nn.Module):
    """
    Autoregressive Transformer for financial time series prediction.
    
    Architecture:
    - Input projection: returns → embedding
    - Positional encoding
    - Transformer encoder with causal masking
    - Output projection: embedding → next-step prediction
    """
    
    def __init__(
        self,
        embed_dim: int = 64,
        n_heads: int = 4,
        n_layers: int = 3,
        ff_dim: int = 128,
        dropout: float = 0.1,
        max_seq_len: int = 128,
    ):
        super().__init__()
        
        self.embed_dim = embed_dim
        
        self.input_projection = nn.Linear(1, embed_dim)
        
        self.pos_encoder = PositionalEncoding(embed_dim, max_seq_len, dropout)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=n_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            activation='relu',
            batch_first=False,
        )
        
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=n_layers,
        )
        
        self.output_projection = nn.Linear(embed_dim, 1)
        
        self._init_weights()
    
    def _init_weights(self):
        """Initialize weights with Xavier initialization."""
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)
    
    def _generate_square_subsequent_mask(self, sz: int) -> torch.Tensor:
        """
        Generate causal mask for autoregressive modeling.
        Prevents attention to future positions.
        """
        mask = torch.triu(torch.ones(sz, sz), diagonal=1).bool()
        return mask
    
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            x: Input sequence [batch, seq_len]
            mask: Optional attention mask [seq_len, seq_len]
        
        Returns:
            predictions: [batch, 1] next-step predictions
        """
        batch_size, seq_len = x.shape
        
        x = x.unsqueeze(-1)
        x = self.input_projection(x)
        
        x = x.transpose(0, 1)
        
        x = self.pos_encoder(x)
        
        if mask is None:
            mask = self._generate_square_subsequent_mask(seq_len).to(x.device)
        
        x = self.transformer_encoder(x, mask=mask)
        
        x = x[-1, :, :]
        
        out = self.output_projection(x)
        
        return out
    
    def count_parameters(self) -> int:
        """Count total trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


def create_model(config: dict) -> TimeSeriesTransformer:
    """Create model from configuration dictionary."""
    model = TimeSeriesTransformer(
        embed_dim=config.get('embed_dim', 64),
        n_heads=config.get('n_heads', 4),
        n_layers=config.get('n_layers', 3),
        ff_dim=config.get('ff_dim', 128),
        dropout=config.get('dropout', 0.1),
        max_seq_len=config.get('max_seq_len', 128),
    )
    
    return model


def get_loss_function(loss_type: str = 'huber', huber_delta: float = 1.0) -> nn.Module:
    """
    Get loss function for training.
    
    Args:
        loss_type: 'mse' or 'huber'
        huber_delta: Delta parameter for Huber loss
    
    Returns:
        Loss function
    """
    if loss_type == 'mse':
        return nn.MSELoss()
    elif loss_type == 'huber':
        return nn.HuberLoss(delta=huber_delta)
    else:
        raise ValueError(f"Unknown loss type: {loss_type}")


if __name__ == "__main__":
    # Test model
    print("Testing TimeSeriesTransformer...")
    
    config = {
        'embed_dim': 64,
        'n_heads': 4,
        'n_layers': 3,
        'ff_dim': 128,
        'dropout': 0.1,
        'max_seq_len': 128,
    }
    
    model = create_model(config)
    
    print(f"\nModel architecture:")
    print(f"  Parameters: {model.count_parameters():,}")
    
    # Test forward pass
    batch_size = 8
    seq_len = 64
    
    x = torch.randn(batch_size, seq_len)
    y_pred = model(x)
    
    print(f"\nForward pass test:")
    print(f"  Input shape: {x.shape}")
    print(f"  Output shape: {y_pred.shape}")
    
    # Test loss functions
    y_true = torch.randn(batch_size, 1)
    
    mse_loss = get_loss_function('mse')
    huber_loss = get_loss_function('huber', huber_delta=1.0)
    
    print(f"\nLoss functions:")
    print(f"  MSE loss: {mse_loss(y_pred, y_true).item():.6f}")
    print(f"  Huber loss: {huber_loss(y_pred, y_true).item():.6f}")
    
    print("\n[OK] Model test successful!")
