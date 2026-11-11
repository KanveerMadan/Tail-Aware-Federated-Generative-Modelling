# Threat Model & Security Analysis

## Federated Transformer for Systemic Risk Modeling - MVP

**Version:** 1.0  
**Status:** Research Prototype  
**Date:** February 2026

---

## 1. Overview

This document describes the threat model, security assumptions, and limitations of the secure aggregation implementation in this MVP. This is a **research-grade prototype** designed to demonstrate feasibility, not a production-ready system.

---

## 2. System Architecture

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Bank Client 1 │      │   Bank Client 2 │      │   Bank Client 3 │
│                 │      │                 │      │                 │
│ - Local Data    │      │ - Local Data    │      │ - Local Data    │
│ - Local Model   │      │ - Local Model   │      │ - Local Model   │
│ - Mask Gen.     │      │ - Mask Gen.     │      │ - Mask Gen.     │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                        │
         │    Masked Updates      │    Masked Updates      │
         │    (n·w + mask)        │    (n·w + mask)        │
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │  Flower Server  │
                         │                 │
                         │ - Aggregates    │
                         │   masked updates│
                         │ - Masks cancel  │
                         │ - No plaintext  │
                         └─────────────────┘
```

---

## 3. Security Properties

### 3.1 What IS Protected

**Raw Data Privacy**
- Raw training data never leaves client institutions
- Only model updates are transmitted (not data)

**Update-Level Privacy (simulated)**
- Each client masks its sample-weighted parameters before sending them
- Server receives `n_i·w_i + mask_i`; the pairwise masks cancel in the sum:
  `Σ(n_i·w_i + mask_i) = Σ n_i·w_i`, and `Σ n_i·w_i / Σ n_i` is the FedAvg mean
- The server never holds any pairwise seed, so it cannot remove the mask from a
  single update (as long as no client colludes with it)
- This is a single-machine **simulation** of the idea, not a deployable protocol
  (see 6.2 and 7.1)

**Non-IID Handling**
- FedProx algorithm stabilizes training under heterogeneous data distributions
- Each bank's unique data characteristics (sector, time period, volatility) are preserved locally

**Honest-But-Curious Server**
- The protocol protects against a server that follows the protocol but tries to learn extra information
- Server cannot reconstruct individual client models from masked aggregates

---

## 4. Threat Model Assumptions

### 4.1 Adversary Model

**Adversary Type:** Honest-but-curious server

**Capabilities:**
- Observes all network traffic
- Receives masked model updates from clients
- Performs aggregation operations
- May attempt to infer information from aggregated results

**DOES NOT:**
- Collude with clients to break masking
- Deviate from protocol (no Byzantine behavior)
- Perform gradient inversion attacks (assumed out of scope for MVP)
- Access client local data or intermediate computations

### 4.2 Trust Assumptions

1. **Clients do not collude with server**
   - If all clients collude with server, masking is broken
   - Assumption: banks are competitors with aligned privacy interests

2. **All clients participate in all rounds**
   - MVP simplification: no client dropout handling
   - In production, would need robust dropout recovery protocol

3. **Seed handling (simulation)**
   - Pairwise seeds are drawn with Python's `secrets` module in the client
     launch code and handed to each client directly; there is **no real key
     exchange** (a real system would derive them with Diffie-Hellman)
   - The mask stream itself is NumPy's PCG64 generator, which is fast but not a
     cryptographic PRG

4. **Semi-honest participants**
   - All parties follow the protocol
   - No malicious clients sending garbage updates

---

## 5. What is NOT Protected

### 5.1 Known Vulnerabilities

**Gradient Inversion Attacks**
- Sophisticated attacks can reconstruct training data from model updates
- Mitigation: Would require differential privacy (DP) noise
- Status: Not implemented in MVP

**Model Memorization**
- Trained models may memorize sensitive patterns from training data
- Mitigation: DP, model audit, membership inference defenses
- Status: Not addressed in MVP

**Inference Attacks**
- Observing model predictions may leak information about training data
- Examples: Membership inference, attribute inference
- Status: Not protected

**Collusion Attacks**
- If N-1 clients collude with server, they can recover the Nth client's update
- Mitigation: Threshold cryptography, secure multiparty computation
- Status: Simplified masking protocol vulnerable to this

**Byzantine Faults**
- Malicious clients can send adversarial updates
- Mitigation: Byzantine-robust aggregation (e.g., Krum, Median)
- Status: Not implemented

**Network-Level Attacks**
- Single-machine simulation does not model network adversaries
- Real deployment needs TLS, authentication, etc.
- Status: Out of scope for MVP

---

## 6. Secure Aggregation Protocol

### 6.1 Bonawitz-Style Masking (Simplified)

**Protocol Steps:**

1. **Mask Generation**
   - For N clients, generate pairwise masks using shared seeds
   - Client i's mask: `mask_i = Σ(mask_{i,j})` for all j ≠ i
   - Property: `Σ mask_i = 0` (masks cancel globally)

2. **Update Masking**
   - Client computes local update: `w_i = model_local - model_global`
   - Applies mask: `w_i_masked = w_i + mask_i`
   - Sends `w_i_masked` to server

3. **Server Aggregation**
   - Receives: `{w_1_masked, w_2_masked, ..., w_N_masked}`
   - Aggregates: `w_agg = Σ w_i_masked = Σ(w_i + mask_i) = Σw_i`
   - Masks cancel automatically

4. **Global Update**
   - Server broadcasts: `model_global_new = model_global + w_agg`

**Key Property:** Server never sees individual `w_i`, only the aggregate.

### 6.2 Implementation Details (what the code actually does)

Code: `src/privacy/masking.py`, `src/flwr/client.py`, `src/flwr/server_strategy.py`.

- **Seeds:** `generate_pairwise_seeds(n)` runs in the client launch code
  (`scripts/run_federated.py`, `scripts/run_federated_simple.py`). Client *i*
  gets only `seeds[i]` = `{peer: seed}`. Nothing seed-related is passed to the
  strategy/server.
- **Masking:** `PairwiseMasker.mask()` adds `+PRG(seed_ij, round)` for each peer
  `j > i` and `-PRG(seed_ij, round)` for each `j < i`, scaled by `MASK_SCALE`
  (1e4), on every `state_dict` array of `n_i·w_i`. Masks change every round.
- **Aggregation:** `FedProxStrategy.aggregate_fit` (with `masked=True`) sums the
  masked arrays and divides by `Σ n_i` (`unmask_weighted_average`), then casts
  to float32.
- **Fail-stop:** any failure or a missing client stops the run with an error,
  because masks only cancel when every client reports.
- **Verification:** `python src/privacy/masking.py` asserts that the sum of masked
  updates equals the sum of unmasked ones and that each masked update is far
  from its real value.

**Honest limits of this simulation:**
- No real key exchange: seeds are generated in one process and handed out
- No dropout recovery: one missing client means the round cannot be unmasked
- Real-valued (float64) masks, not finite-field arithmetic, so a masked update
  still leaks a little statistical information and sums carry ~1e-12 rounding error
- Honest-but-curious server only; no protection if clients collude with the server
- `n_i` (sample counts) and training metrics are sent in the clear

**Production Requirements:**
- Pairwise key agreement over authenticated channels
- Dropout recovery (secret-shared seeds, as in Bonawitz et al. 2017)
- Finite-field masking with a cryptographic PRG
- Authentication and integrity checks

---

## 7. Limitations & Caveats

### 7.1 MVP Simplifications

1. **Single-Machine Simulation**
   - All processes run on one machine
   - Does not model network delays, partitions, or adversaries
   - Real deployment requires distributed infrastructure

2. **No Differential Privacy**
   - Masking protects aggregates but not individual contributions at the model level
   - Would need Opacus + gradient clipping + noise injection for DP
   - Trade-off: DP adds noise that degrades model utility

3. **No Client Dropout Handling**
   - Assumes all clients participate in every round; the run stops otherwise
   - Real-world: clients may disconnect, fail, or be slow
   - Robust protocols use secret sharing or Lagrange interpolation

4. **No Byzantine Robustness**
   - Assumes all clients are semi-honest
   - Malicious client could poison model with adversarial updates
   - Defense: Median, trimmed mean, Krum, or other robust aggregation

5. **Small Model Size**
   - ~1.8M parameters for computational efficiency
   - Larger models increase attack surface for inference attacks

### 7.2 Regulatory Compliance

**This MVP does NOT claim compliance with:**
- GDPR (EU General Data Protection Regulation)
- GLBA (Gramm-Leach-Bliley Act)
- CCPA (California Consumer Privacy Act)
- Any other regulatory framework

**Reason:** Research prototype lacks production-grade controls:
- No formal privacy audit
- No access control infrastructure
- No data governance policies
- No compliance documentation

**Path to Production:**
- Engage legal/compliance teams
- Conduct privacy impact assessment (PIA)
- Implement DP with documented (ε, δ) guarantees
- Add audit logging and monitoring
- Establish data use agreements between institutions

---

## 8. Comparison with Production Systems

| Feature | MVP Implementation | Production Requirement |
|---------|-------------------|----------------------|
| **Secure Aggregation** | Bonawitz masking (simplified) | Threshold cryptography or SMC |
| **Differential Privacy** | None | (ε, δ)-DP with Opacus |
| **Byzantine Robustness** | None | Robust aggregation (Krum, etc.) |
| **Client Dropout** | Assumes full participation | Erasure coding / secret sharing |
| **Gradient Inversion Defense** | Vulnerable | DP noise + gradient clipping |
| **Communication Security** | Local simulation | TLS 1.3 + mutual auth |
| **Model Audit** | None | Membership inference defense |
| **Regulatory Compliance** | Not assessed | GDPR/GLBA audit + PIA |

---

## 9. Future Work & Recommendations

### 9.1 Immediate Next Steps (Post-MVP)

1. **Add Differential Privacy**
   - Integrate Opacus for gradient clipping + noise
   - Tune (ε, δ) for acceptable utility-privacy trade-off
   - Report privacy budget per experiment

2. **Implement Robust Aggregation**
   - Add Krum or median aggregation as alternative to FedAvg
   - Test against poisoning attacks

3. **Real-World Multi-Node Deployment**
   - Deploy on separate machines with network communication
   - Use Docker/Kubernetes for orchestration
   - Measure communication overhead

### 9.2 Production Roadmap

1. **Cryptographic Upgrades**
   - Replace masking with threshold Paillier or secure multiparty computation
   - Consider Intel SGX / AMD SEV for trusted execution environments

2. **Formal Verification**
   - Prove security properties using formal methods
   - Conduct third-party security audit

3. **Regulatory Compliance**
   - Work with legal team on GDPR Article 25 (data protection by design)
   - Document privacy-preserving measures
   - Establish data processing agreements

4. **Operational Security**
   - Add authentication (OAuth, mTLS)
   - Implement audit logging
   - Create incident response plan

---

## 10. Responsible Disclosure

**Current Status:** This is an open-source research prototype. All limitations are documented transparently.

**Not for Production Use:** Do not deploy this system in a production financial environment without addressing the limitations outlined in this document.

**Contact:** For security concerns or questions, please open a GitHub issue or contact the project maintainers.

---

## 11. Conclusion

This MVP demonstrates the **feasibility** of privacy-preserving federated learning for financial risk modeling. The secure aggregation protocol successfully prevents the server from accessing individual client updates while enabling collaborative model training.

However, this is a **research prototype** with known limitations. Production deployment requires:
- Differential privacy guarantees
- Byzantine-robust aggregation
- Formal security audit
- Regulatory compliance review

The trade-off between **privacy**, **utility**, and **computational efficiency** is inherent to federated learning. This MVP prioritizes demonstrating the core concept at research-grade quality, leaving production hardening for future work.

---

**Document Version:** 1.0  
**Last Updated:** February 10, 2026  
**Review Cycle:** Quarterly or after major security updates
