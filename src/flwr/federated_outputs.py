"""
Save the final federated global model and its test predictions.

Same pattern as scripts/train_local.py and scripts/train_centralized.py:
test_predictions.npy / test_targets.npy / test_residuals.npy in raw return
units, so scripts/evaluate.py can score federated runs like the others.
"""

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch
from torch.utils.data import DataLoader

from src.data.dataset import load_bank_datasets
from src.models.transformer_ts import create_model


def save_federated_outputs(
    parameters: List[np.ndarray],
    config: Dict,
    output_dir: Path,
    n_clients: int,
    strategy_name: str,
) -> None:
    """
    Load the global parameters (state_dict order), save global_model.pt and
    predict every bank's test set with that bank's own normalisation stats.

    Writes per-bank bank_<i>_test_{predictions,targets}.npy and pooled
    test_{predictions,targets,residuals}.npy (banks concatenated in order,
    like the centralized oracle).
    """
    output_dir = Path(output_dir)
    model = create_model(config['model'])
    keys = list(model.state_dict().keys())
    if len(keys) != len(parameters):
        raise ValueError(f"Expected {len(keys)} arrays, got {len(parameters)}")
    model.load_state_dict(
        {k: torch.from_numpy(np.asarray(v, dtype=np.float32)) for k, v in zip(keys, parameters)},
        strict=True,
    )
    model.eval()

    torch.save({
        'round': config['federated']['n_rounds'],
        'strategy': strategy_name,
        'model_state_dict': model.state_dict(),
        'config': config,
    }, output_dir / "global_model.pt")

    all_pred, all_true, per_bank = [], [], {}
    for bank_id in range(n_clients):
        train_ds, _, test_ds = load_bank_datasets(
            bank_id, data_dir=config['paths']['data_processed'], normalize=True
        )
        loader = DataLoader(test_ds, batch_size=config['training']['batch_size'], shuffle=False)
        preds, targets = [], []
        with torch.no_grad():
            for X, y in loader:
                preds.append(model(X).numpy())
                targets.append(y.numpy())
        pred = train_ds.denormalize(np.concatenate(preds))
        true = train_ds.denormalize(np.concatenate(targets))

        np.save(output_dir / f"bank_{bank_id}_test_predictions.npy", pred)
        np.save(output_dir / f"bank_{bank_id}_test_targets.npy", true)
        per_bank[bank_id] = {'n_test': int(len(pred)), 'mse': float(np.mean((pred - true) ** 2))}
        all_pred.append(pred)
        all_true.append(true)

    pred = np.concatenate(all_pred)
    true = np.concatenate(all_true)
    np.save(output_dir / "test_predictions.npy", pred)
    np.save(output_dir / "test_targets.npy", true)
    np.save(output_dir / "test_residuals.npy", pred - true)

    with open(output_dir / "metadata.json", "w") as f:
        json.dump({
            'model_type': f"federated_{strategy_name.lower()}",
            'n_clients': n_clients,
            'n_rounds': config['federated']['n_rounds'],
            'mu': config['federated']['mu'],
            'test_mse_pooled': float(np.mean((pred - true) ** 2)),
            'per_bank': per_bank,
        }, f, indent=2)

    print(f"[OK] Global model and test predictions saved to: {output_dir}")
