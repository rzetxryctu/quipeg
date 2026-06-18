<div align="center">

# 🌐 QuIPEG v3 — Quantum Internet Simulator

**Simulate a global quantum internet. No PhD required.**

[![PyPI version](https://img.shields.io/pypi/v/quipeg?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/quipeg/)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-151%20passed-brightgreen?logo=pytest)](https://github.com/rzetxryctu/quipeg/actions)
[![Lines](https://img.shields.io/badge/lines-4000%2B-orange)](src/quipeg/)
[![Stars](https://img.shields.io/github/stars/rzetxryctu/quipeg?style=social)](https://github.com/rzetxryctu/quipeg/stargazers)

*Quantum Key Distribution • Entanglement Swapping • Quantum Repeaters • BB84*

[Demo](#-5-second-demo) • [Install](#-install) • [Docs](#-quickstart) • [Contribute](#-contributing)

</div>

---

## What is this? (ELI5)

Imagine an **unhackable internet** powered by quantum physics. Instead of sending classical bits through cables, you share **entangled particles** between cities. Anyone trying to eavesdrop physically destroys the signal — guaranteed by the laws of nature, not by math.

**QuIPEG** lets you **design, simulate, and visualize** such a network on your laptop:

- 🏙️ **Place nodes** anywhere on Earth (cities, satellites, data centers)
- 🔗 **Connect them** with realistic fiber optic links
- 📉 **Watch fidelity decay** as signals travel through fiber
- 🔄 **Add quantum repeaters** to extend range
- 🗺️ **Generate interactive maps** with full link metrics
- 📊 **Export data** for papers, presentations, or decision-making

> **No external dependencies. No quantum computer needed. Just Python 3.9+.**

---

## ⚡ 5-Second Demo

```bash
pip install quipeg
python -c "
from quipeg import QuantumNetwork
net = QuantumNetwork.demo()          # Global 8-city demo network
r = net.end_to_end('London', 'Tokyo')
print(f'Fidelity: {r[\"fidelity\"]:.3f} | Key rate: {r[\"key_rate\"]:.1f} bit/s')
" 
```

Then generate an **interactive HTML map** of the entire network:

```bash
quipeg render --output network.html
quipeg export --format geojson --output network.geojson
```

Open `network.html` in your browser — hover over any link to see fidelity, QBER, and secret key rate. **Zero external dependencies. Works offline.**

---

## 🚀 Why QuIPEG?

| Feature | QuIPEG | Alternatives |
|---------|--------|--------------|
| **Dependencies** | ✅ Zero | ❌ NumPy, SciPy, NetworkX... |
| **Python lines** | ~4,000 | Often 20,000+ |
| **Installation** | `pip install quipeg` | Complex setup |
| **Interactive maps** | ✅ Built-in HTML/SVG | ❌ Not included |
| **Realistic physics** | ✅ T1/T2 decoherence, Bell-corrected swap | ❌ Often simplified |
| **CLI tools** | ✅ `render`, `export`, `simulate` | ❌ API only |
| **Tests** | ✅ 151 tests, CI on 4 Python versions | ❌ Varies |
| **Quantum purification** | ✅ DEJMPS protocol | ❌ Rare |
| **GeoJSON export** | ✅ | ❌ |
| **Cost** | Free & open source (Apache 2.0) | Varies |

---

## 📦 Install

```bash
pip install quipeg
```

Or from source:

```bash
git clone https://github.com/rzetxryctu/quipeg.git
cd quipeg && pip install -e .
```

**Requirements:** Python 3.9+ — that's it. No NumPy, no SciPy, no Rust, no CUDA.

---

## 🎮 Quickstart

### Build a network from scratch

```python
from quipeg import QuantumNetwork, NodeRole

net = QuantumNetwork("My Quantum Backbone")

# Add cities (lat, lon)
net.add_node("London",    51.5074, -0.1278,  role=NodeRole.BACKBONE)
net.add_node("Frankfurt", 50.1109,  8.6821,  role=NodeRole.BACKBONE)
net.add_node("Singapore",  1.3521,  103.8198, role=NodeRole.EDGE)
net.add_node("Sydney",   -33.8688, 151.2093, role=NodeRole.EDGE)

# Auto-compute fiber distances from GPS coordinates
net.add_link("London",    "Frankfurt", fidelity=0.97)
net.add_link("Frankfurt", "Singapore",  fidelity=0.95)
net.add_link("Singapore", "Sydney",     fidelity=0.96)

# Simulate end-to-end with quantum repeaters
result = net.end_to_end("London", "Sydney")
print(f"Fidelity: {result['fidelity']:.4f}")
print(f"QBER:     {result['qber']:.5f}")
print(f"Key rate: {result['key_rate']:.1f} bit/s")
print(f"Path:     {' → '.join(result['path'])}")
```

### Use the CLI

```bash
# Show network info
quipeg info

# Run demo simulation
quipeg simulate --from London --to Tokyo

# Generate interactive HTML map
quipeg render --output network.html --title "Global Quantum Backbone"

# Export to GeoJSON for GIS tools
quipeg export --format geojson --output network.geojson

# Export to JSON for data analysis
quipeg export --format json --output network.json
```

### Use realistic physics

```python
from quipeg.physics import (
    decohere_t1_t2,       # Realistic qubit memory decoherence
    swap_fidelity_bell,   # Bell-corrected entanglement swap
    dejmps_purify,        # DEJMPS entanglement purification
    secret_key_rate,      # BB84 key rate estimation
    haversine,            # GPS distance
)

# How much fidelity is left after 100km of fiber?
import math
distance_km = 100
loss_db = 0.2 * distance_km          # 0.2 dB/km standard fiber
eta = 10 ** (-loss_db / 10)          # Transmittance: ~0.01
photon_speed_fiber = 2e5              # km/s
time_s = distance_km / photon_speed_fiber  # ~0.5 ms

# Simulate decoherence during transit
f_after = decohere_t1_t2(0.99, time_s, T1=1e-3, T2=1e-3)
print(f"Fidelity after 100km: {f_after:.4f}")
```

---

## 🔬 Physics Model

QuIPEG implements **real quantum communication physics**, not toy models:

| Component | Model | Reference |
|-----------|-------|-----------|
| **Fibre loss** | 0.2 dB/km (ITU-T G.652) | Standard telecom |
| **Decoherence** | T1 (energy) + T2 (phase) independent channels | Open quantum systems |
| **Entanglement swap** | Bell-corrected: `F₁F₂ + (1-F₁)(1-F₂)/3` | Pan et al., RMP 84, 777 |
| **Purification** | DEJMPS protocol | Deutsch et al., PRL 77, 2818 |
| **QBER** | `(1-F)/2` from Werner state | Standard QKD theory |
| **Key rate** | BB84 decoy-state bound | Ma et al., PRL 94, 050501 |

### Entanglement Swapping

```
Before swap:  A ←[F₁]→ R₁ ←[F₂]→ B
After swap:   A ←[F_swap]→ B

F_swap = F₁ · F₂ + (1-F₁)(1-F₂) / 3
```

This is the **correct quantum formula**, not the arithmetic mean approximation.

### BB84 Secret Key Rate

```
SKR = ½ · η · μ · p_swap · [1 - H₂(e) - H₂(e)] · clock_rate

where:
  η     = fiber transmittance × detector efficiency
  e     = QBER = (1 - F) / 2
  H₂(e) = binary entropy
```

---

## 🗺️ Rendering

`quipeg render` generates a **self-contained HTML file** with an interactive SVG map:

- 🌍 Nodes placed by real GPS coordinates
- 🎨 Link colors from green (high fidelity) → red (low)
- 💬 Hover tooltips show distance, fidelity, QBER, key rate
- 🔌 Fully offline — no CDN, no external resources
- 📱 Mouse/keyboard interactive

Ideal for papers, presentations, and demos.

---

## 🧪 Tests

151 tests across 4 modules, CI on Python 3.9–3.12:

```bash
pip install pytest
pytest tests/ -v
```

```
========================= 151 passed in 0.94s =========================
```

---

## 🎯 Use Cases

- 🎓 **Teaching**: demonstrate quantum networking in lectures
- 🔬 **Research**: prototype network topologies for papers
- 📊 **Analysis**: evaluate real-world fiber routes for quantum networks
- 🛡️ **Security**: estimate eavesdropping detection capability
- 🏗️ **Planning**: simulate before building real quantum infrastructure

---

## 🤝 Contributing

Contributions welcome! Whether it's:

- 🐛 Bug reports
- 💡 Feature requests
- 🌍 New demo networks for different regions
- 📝 Documentation improvements
- 🔬 More physics models

Fork → Commit → Pull Request. Tests must pass.

```bash
pip install -e ".[dev]"
pytest tests/ -v        # All tests green?
ruff check src/ tests/  # Style clean?
```

---

## 📄 License

Apache 2.0 — free for commercial and academic use. See [LICENSE](LICENSE).

---

<div align="center">

**[⬆ Back to top](#-quipeg-v3--quantum-internet-simulator)**

Made with 🧠 · ⚛️ · 🇮🇹

⭐ Star this repo if you find it useful!

</div>
