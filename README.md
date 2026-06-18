# Quipeg v3 — Planetary Quantum Communication Backbone Simulator

<!-- Replace the placeholders below with real shields from https://shields.io -->
[![PyPI version](https://img.shields.io/pypi/v/quipeg)](https://pypi.org/project/quipeg/)
[![Python](https://img.shields.io/pypi/pyversions/quipeg)](https://pypi.org/project/quipeg/)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue)](LICENSE)
[![Downloads](https://static.pepy.tech/badge/quipeg)](https://pepy.tech/project/quipeg)

**Quipeg** is a lightweight, dependency-free Python engine for modelling
quantum key distribution (QKD) networks, quantum repeaters, entanglement
swapping, fidelity-aware routing, and secret-key-rate estimation.

---

## What's New in v3.0

| Feature | Description |
|---------|-------------|
| **Bell-corrected swap model** | Swap fidelity uses the full product formula `F₁·F₂ + (1-F₁)(1-F₂)/3` instead of arithmetic mean — accounts for Werner-state structure of Bell-state noise. |
| **DEJMPS purification** | `dejmps_purify()` function implements the Deutsch–Jozsa–Maslennikov–Pedersen protocol (simplified), improving fidelity at the cost of success probability. |
| **T1/T2 separate decoherence** | `decohere_t1_t2()` separates energy relaxation (T1) from phase dephasing (T2), giving more realistic memory decoherence for different qubit technologies. |
| **HTML network map** | `render.to_html()` exports a fully standalone, offline-capable interactive SVG map with hover tooltips showing link metrics — zero external dependencies. |
| **GeoJSON export** | `to_geojson()` now includes per-link fidelity, QBER, and key rate fields. |
| **JSON save/load** | `save()` / `load()` methods on `QuantumNetwork` persist and restore the full network state to JSON. |
| **CLI `render` & `export`** | New subcommands: `quipeg render` (HTML map) and `quipeg export` (GeoJSON/JSON). |
| **Dijkstra in-network** | `shortest_path` is implemented directly in `QuantumNetwork` — no external routing module needed. |
| **~140 tests** | Comprehensive test suite covering physics, network, render, and CLI. |

---

## Installation

```bash
# From PyPI (once published)
pip install quipeg

# Development install from source
pip install -e .
```

Requirements: Python 3.9+ — **no third-party dependencies**.

---

## Quickstart

```python
from quipeg import QuantumNetwork, __version__
from quipeg.physics import skr_bb84, swap_fidelity, decohere_t1_t2

print(f"Quipeg {__version__}")

# Build a simple network
net = QuantumNetwork(name="Europe QKD Backbone")
net.add_node("London",    51.5074,  -0.1278, population=9_000_000, is_repeater=True)
net.add_node("Paris",     48.8566,   2.3522, population=2_100_000, is_repeater=True)
net.add_node("Frankfurt", 50.1109,   8.6821, population=700_000)
net.add_node("Amsterdam", 52.3676,   4.9041, population=850_000)

net.add_link("London",    "Paris")
net.add_link("Paris",     "Frankfurt")
net.add_link("Frankfurt", "Amsterdam")

print(net.summary())

# Shortest path by distance
path = net.shortest_path("London", "Amsterdam")
print("Shortest path:", " → ".join(path))

# End-to-end fidelity via entanglement swapping
f_e2e, skr = net.end_to_end("London", "Amsterdam")
print(f"End-to-end fidelity: {f_e2e:.4f}")
print(f"Estimated SKR: {skr/1e6:.2f} Mbit/s")

# HTML map export
from quipeg.render import to_html
html = to_html(net)
with open("network_map.html", "w") as f:
    f.write(html)
print("Saved network_map.html")
```

---

## CLI Usage

```bash
# Show version and info
quipeg info

# Run the interactive demo
quipeg demo

# Simulate path fidelity between two nodes
quipeg simulate --from London --to Tokyo --network cities.csv

# Export network as interactive HTML map
quipeg render --output map.html

# Export network as GeoJSON or JSON
quipeg export --format geojson --output network.geojson
quipeg export --format json --output network.json
```

### Module-level invocation (without installing)

```bash
python -m quipeg.cli info
python -m quipeg.cli demo
python -m quipeg.cli render --output map.html
```

---

## Physics Model

### Entanglement Distribution & Decoherence

Photon pairs are distributed over optical fibre. The Bell-state fidelity
`F` evolves under two independent decoherence channels:

| Channel | Time constant | Effect |
|---------|--------------|--------|
| Energy relaxation (T1) | µs–ms | Decays toward 0.5 |
| Phase dephasing (T2) | µs–ms | Decays toward 0.25 (maximally mixed) |

```python
F_t = 0.25 + 0.25 * exp(-t/T1) + 0.50 * exp(-t/T2)
```

### Entanglement Swapping (Bell-corrected model)

When two Bell pairs `(F₁, F₂)` are swapped via a Bell measurement, the
output fidelity is:

```
F_swap = F₁ · F₂ + (1-F₁)(1-F₂) / 3
```

This formula correctly reduces to:
- `F_swap = 1.0` when both pairs are perfect (F₁=F₂=1)
- `F_swap = 0.25` when both pairs are maximally mixed (F₁=F₂=0.25)
- The arithmetic mean `(F₁+F₂)/2` is recovered in the high-fidelity limit

### DEJMPS Purification

The Deutsch–Jozsa–Maslennikov–Pedersen protocol takes two pairs of
fidelity `F₁, F₂` and post-selects on matching Bell-measurement outcomes.
After successful purification:

```
F_pur = (F₁·F₂ + (1-F₁)(1-F₂)/3) / (F₁·F₂ + (1-F₁)(1-F₂))
P_succ = (F₁·F₂ + (1-F₁)(1-F₂))²
```

### QBER & Secret Key Rate (BB84)

```
QBER = (1 - F) / 2
H₂(x) = -x·log₂(x) - (1-x)·log₂(1-x)
SKR  = ½ · η · μ · p_repeat · (1 - 2·QBER - H₂(QBER)) · f_EC · R
```

Where η is total transmittance (fibre × detector), μ is mean photon number,
and f_EC is error-correction efficiency.

---

## Roadmap

- [ ] Multi-path routing for parallel entanglement distribution
- [ ] BSM (Bell-State Measurement) success probability modelling
- [ ] Memory multiplexing (multiple memory modes per node)
- [ ] GMCS / E91 protocol variants
- [ ] Network resilience and attack surface analysis
- [ ] Jupyter notebook examples gallery
- [ ] Web-based interactive topology editor

---

## License

Apache License 2.0 — see [LICENSE](LICENSE)
