"""
Pairwise additive masking for secure aggregation (Bonawitz-style, simplified).

Every client pair (i, j) shares one secret seed. In each round, client i adds
PRG(seed_ij, round) for every peer j > i and subtracts it for every peer j < i,
so the masks cancel exactly in the sum over all clients.

Weighting: client i masks n_i * w_i (its sample-weighted parameters). The server
sums the masked arrays and divides by sum(n_i). That is FedAvg's weighted mean,
and the masks still cancel because they are added after the weighting.

SIMULATION ONLY:
- seeds come from generate_pairwise_seeds() in the client launch code, not from
  a real key agreement (e.g. Diffie-Hellman);
- there is no dropout recovery: every client must report every round;
- masks are real-valued floats, not finite-field integers;
- it only protects against an honest-but-curious server.
See docs/threat_model.md.
"""

import secrets
from typing import Dict, List, Optional, Sequence

import numpy as np

# Large relative to n_i * w_i, so one masked update says little about its value.
MASK_SCALE = 1e4


def generate_pairwise_seeds(
    n_clients: int, rng_seed: Optional[int] = None
) -> Dict[int, Dict[int, int]]:
    """
    Create one secret seed per client pair, returned per client:
    {client_id: {peer_id: seed}}.

    Give client i only seeds[i]. None of it may be passed to the server/strategy.
    rng_seed is only for reproducible tests; leave it None for real runs.
    """
    draw = (
        np.random.default_rng(rng_seed).integers
        if rng_seed is not None
        else None
    )
    seeds: Dict[int, Dict[int, int]] = {i: {} for i in range(n_clients)}
    for i in range(n_clients):
        for j in range(i + 1, n_clients):
            s = int(draw(0, 2**62)) if draw is not None else secrets.randbits(62)
            seeds[i][j] = s
            seeds[j][i] = s
    return seeds


class PairwiseMasker:
    """Client-side masker. Holds only this client's pairwise seeds."""

    def __init__(self, client_id: int, peer_seeds: Dict[int, int], scale: float = MASK_SCALE):
        if client_id in peer_seeds:
            raise ValueError("A client cannot share a seed with itself")
        self.client_id = client_id
        self.peer_seeds = dict(peer_seeds)
        self.scale = scale

    def mask(self, arrays: Sequence[np.ndarray], server_round: int) -> List[np.ndarray]:
        """Return float64 arrays + sum of signed pairwise masks for this round."""
        out = [np.array(a, dtype=np.float64, copy=True) for a in arrays]
        for peer in sorted(self.peer_seeds):
            # Both clients of a pair build the same stream: same seed, same round,
            # same array shapes in the same order.
            rng = np.random.default_rng([self.peer_seeds[peer], int(server_round)])
            sign = 1.0 if self.client_id < peer else -1.0
            for a in out:
                a += sign * self.scale * rng.standard_normal(a.shape)
        return out


def unmask_weighted_average(
    masked_updates: Sequence[Sequence[np.ndarray]], num_examples: Sequence[int]
) -> List[np.ndarray]:
    """
    Server side: sum the masked n_i * w_i arrays (masks cancel) and divide by
    the total number of examples. Needs every client's update for the round.
    """
    total = float(sum(num_examples))
    if total <= 0:
        raise ValueError("Total number of examples must be positive")
    n_arrays = len(masked_updates[0])
    return [
        np.sum([np.asarray(u[k], dtype=np.float64) for u in masked_updates], axis=0) / total
        for k in range(n_arrays)
    ]


def masking_example(
    updates: Sequence[Sequence[np.ndarray]],
    num_examples: Sequence[int],
    server_round: int = 1,
    rng_seed: Optional[int] = None,
) -> Dict:
    """
    Mask the given per-client updates exactly as the federated clients do and
    return the plain values, masked values and both totals. Used by the self-test
    and by scripts/export_web_data.py.
    """
    n_clients = len(updates)
    seeds = generate_pairwise_seeds(n_clients, rng_seed=rng_seed)
    weighted = [[n * np.asarray(a, dtype=np.float64) for a in u] for u, n in zip(updates, num_examples)]
    masked = [PairwiseMasker(i, seeds[i]).mask(weighted[i], server_round) for i in range(n_clients)]
    plain_sum = [np.sum([w[k] for w in weighted], axis=0) for k in range(len(weighted[0]))]
    masked_sum = [np.sum([m[k] for m in masked], axis=0) for k in range(len(masked[0]))]
    return {
        "weighted": weighted,
        "masked": masked,
        "plain_sum": plain_sum,
        "masked_sum": masked_sum,
        "plain_avg": [s / float(sum(num_examples)) for s in plain_sum],
        "masked_avg": unmask_weighted_average(masked, num_examples),
    }


def self_test(n_clients: int = 4, seed: int = 0) -> None:
    """Assert that masks cancel in the sum and hide every single update."""
    rng = np.random.default_rng(seed)
    shapes = [(64, 1), (64,), (192, 64), (192,), (128, 64), (1,)]
    updates = [[rng.normal(0, 0.1, s) for s in shapes] for _ in range(n_clients)]
    num_examples = [int(n) for n in rng.integers(200, 4000, n_clients)]

    ex = masking_example(updates, num_examples, server_round=3, rng_seed=seed)

    for k, (p, m) in enumerate(zip(ex["plain_sum"], ex["masked_sum"])):
        assert np.allclose(p, m, rtol=1e-9, atol=1e-6), f"array {k}: sum of masked != sum of plain"
    for k, (p, m) in enumerate(zip(ex["plain_avg"], ex["masked_avg"])):
        assert np.allclose(p, m, rtol=1e-9, atol=1e-9), f"array {k}: weighted average differs"

    for i in range(n_clients):
        real = np.concatenate([a.ravel() for a in ex["weighted"][i]])
        masked = np.concatenate([a.ravel() for a in ex["masked"][i]])
        rel = np.linalg.norm(masked - real) / np.linalg.norm(real)
        assert rel > 10, f"client {i}: masked update too close to its real value ({rel:.2f})"

    # A different round must give different masks.
    seeds = generate_pairwise_seeds(n_clients, rng_seed=seed)
    a = PairwiseMasker(0, seeds[0]).mask([np.zeros(5)], 1)[0]
    b = PairwiseMasker(0, seeds[0]).mask([np.zeros(5)], 2)[0]
    assert not np.allclose(a, b), "masks repeat across rounds"

    max_diff = max(float(np.max(np.abs(p - m))) for p, m in zip(ex["plain_avg"], ex["masked_avg"]))
    print(f"[OK] masking self-test passed: {n_clients} clients, max |avg diff| = {max_diff:.2e}")


if __name__ == "__main__":
    self_test()
