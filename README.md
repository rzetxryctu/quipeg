# QuIPEG v3 — Quantum Internet Protocol & Entanglement Gateway

A Python toolkit for simulating quantum key distribution (QKD) networks,
quantum repeaters, entanglement swapping, and BB84 secret-key-rate estimation.
No third-party dependencies. Python 3.9+.

[Install](#install) · [Quickstart](#quickstart) · [Docs](#physics-model) · [Contributing](#contributing)

---

## Overview

QuIPEG models a global quantum communication network: nodes (cities, ground
stations, data centres) connected by optical-fibre links. Entangled photon
pairs are distributed across those links, and the toolkit tracks how
fidelity degrades with distance, decoherence, and swapping operations.

It is useful for teaching quantum networking concepts, prototyping network
topologies for research papers, and evaluating real-world fibre routes for
quantum communication deployments.

## Install

```bash
pip install quipeg
```

From source:

```bash
git clone https://github.com/rzetxryctu/quipeg.git
cd quipeg && pip install -e .
```

Requires Python 3.9 or later. No other dependencies.

## Quickstart

```python
from quipeg import QuantumNetwork

# Build the built-in 8-city demo network
net = QuantumNetwork.demo()

# Simulate end-to-end entanglement distribution
result = net.end_to_end("London", "Tokyo")
print(f"Fidelity:  {result['fidelity']:.4f}")
print(f"QBER:      {result['qber']:.5f}")
print(f"Key rate:  {result['key_rate']:.1f} bit/s")
```

Generate an interactive map and export data:

```bash
quipeg render      --output network.html
quipeg export      --format geojson --output network.geojson
quipeg simulate    --from London --to Tokyo
```

Open `network.html` in a browser: hover over links to inspect fidelity,
QBER, and secret-key rate. The file is fully self-contained (no CDN, no
external resources).

### Build a custom network

```python
from quipeg import QuantumNetwork, NodeRole

net = QuantumNetwork("European Backbone")

net.add_node("London",    51.5074, -0.1278,  role=NodeRole.BACKBONE)
net.add_node("Frankfurt", 50.1109,  8.6821,  role=NodeRole.BACKBONE)
net.add_node("Milan",     45.4642,  9.1900)

net.add_link("London",    "Frankfurt", fidelity=0.97)
net.add_link("Frankfurt", "Milan",     fidelity=0.96)

result = net.end_to_end("London", "Milan")
print(f"Path: {' → '.join(result['path'])}")
print(f"End-to-end fidelity: {result['fidelity']:.4f}")
```

### Direct physics functions

```python
from quipeg.physics import (
    decohere_t1_t2,
    swap_fidelity_bell,
    dejmps_purify,
    secret_key_rate,
    haversine,
)

# Fibre decoherence over 100 km
time_s = 100 / 2e5          # 100 km at 200 000 km/s in fibre
f = decohere_t1_t2(0.99, time_s, T1=1e-3, T2=1e-3)
print(f"Fidelity after 100 km: {f:.4f}")

# Entanglement swapping
f_swap = swap_fidelity_bell(0.95, 0.93)
print(f"Swapped fidelity: {f_swap:.4f}")

# BB84 secret key rate
skr, info = secret_key_rate(0.97, 50.0)
print(f"Key rate at 50 km: {skr:.1f} bit/s")
```

---

## Physics Model

### Fibre Loss

Standard single-mode fibre at 1550 nm: 0.2 dB/km (ITU-T G.652).

```
loss(dB) = 0.2 × distance_km
η = 10^(-loss_dB / 10)
```

### Decoherence

Two independent channels model realistic quantum-memory noise:

| Channel | Constant | Effect |
|---------|----------|--------|
| Energy relaxation (T1) | 1 ms (default) | Decays population toward 0.5 |
| Phase dephasing (T2) | 1 ms (default) | Decays coherence toward 0.25 |

```
F(t) = ¼ + ¼·exp(-t/T1) + ½·exp(-t/T2)
```

### Entanglement Swapping (Bell-Corrected)

When two Bell pairs (F1, F2) are fused via Bell-state measurement:

```
F_swap = F1 · F2 + (1 - F1)(1 - F2) / 3
```

This is the standard result from the quantum repeater literature (Pan et al.,
Rev. Mod. Phys. 84, 777). It reduces to 1.0 for perfect inputs and 0.25 for
maximally mixed inputs.

### DEJMPS Purification

The Deutsch–Jozsa–Maslennikov–Pedersen protocol takes two imperfect pairs
and probabilistically produces one pair of higher fidelity:

```
F_pur = (F1·F2 + (1-F1)(1-F2)/3) / (F1·F2 + (1-F1)(1-F2))
P_succ = (F1·F2 + (1-F1)(1-F2))²
```

Purification fails (returns `ok=False`) when either input pair is already
maximally mixed (F = 0.25), since no entanglement remains to distil.

### BB84 Secret Key Rate

```
QBER = (1 - F) / 2
H₂(x) = -x·log₂(x) - (1-x)·log₂(1-x)
SKR = ½ · η · μ · p_swap · (1 - 2·QBER - H₂(QBER)) · f_EC · clock_rate
```

---

## Features

| Feature | Description |
|---------|-------------|
| Zero dependencies | Pure Python 3.9+ |
| T1/T2 decoherence | Independent energy-relaxation and dephasing channels |
| Bell-corrected swap | Physically accurate entanglement-swapping formula |
| DEJMPS purification | Probabilistic entanglement distillation |
| HTML/SVG renderer | Self-contained interactive map, works offline |
| GeoJSON export | Import into GIS tools |
| JSON save/load | Full network serialisation |
| CLI | `quipeg simulate`, `render`, `export`, `info` |
| 50+ unit-tested physics functions | Verified edge cases and invariants |

---

## Project Structure

```
src/quipeg/           Core package
  __init__.py         Public API exports
  physics.py          Physics functions (decoherence, swap, QBER, SKR)
  network.py          QuantumNetwork, QuantumNode, QuantumLink
  render.py           HTML/SVG visualisation
  cli.py              Command-line interface
tests/                Test suite (~150 tests, CI on Python 3.9–3.12)
```

---

## Contributing

Bug reports, feature requests, and pull requests are welcome.

```bash
pip install -e ".[dev]"
pytest tests/ -v           # run the full suite
ruff check src/ tests/     # style check
```

See the [issues](https://github.com/rzetxryctu/quipeg/issues) page for open
topics.

## License

Apache License 2.0. See [LICENSE].
