"""
Quipeg — Planetary Quantum Communication Backbone Simulator v3.0.0

A lightweight, dependency-free core engine for modelling QKD networks,
quantum repeaters, entanglement swapping, fidelity-aware routing,
DEJMPS purification, and BB84 secret-key-rate estimation.
"""

__version__ = "3.0.0"

# Core physics
from quipeg.physics import (
    haversine,
    fiber_loss_db,
    transmittance,
    decohere,
    decohere_t1_t2,
    qber_from_fidelity,
    swap_fidelity,
    swap_fidelity_bell,
    swap_fidelity_avg,
    dejmps_purify,
    secret_key_rate,
    skr_bb84,
)

# Network
from quipeg.network import (
    QuantumNetwork,
    QuantumNode,
    QuantumLink,
    NodeRole,
    load_csv,
)

# Rendering
from quipeg.render import to_html, save_html

# Backward-compatibility aliases (routing module removed in v3.0)
try:
    from quipeg.routing import shortest_path as _sp, fidelity_path as _fp
    shortest_path = _sp          # noqa: F401
    fidelity_path = _fp          # noqa: F401
except ImportError:
    # routing.py no longer ships; use QuantumNetwork.shortest_path instead
    pass

try:
    from quipeg.repeater import QuantumRepeater, EntanglementSwapping
except ImportError:
    QuantumRepeater = None      # noqa: F401
    EntanglementSwapping = None  # noqa: F401

__all__ = [
    # Version
    "__version__",
    # Physics
    "haversine",
    "fiber_loss_db",
    "transmittance",
    "decohere",
    "decohere_t1_t2",
    "qber_from_fidelity",
    "swap_fidelity",
    "swap_fidelity_bell",
    "swap_fidelity_avg",
    "dejmps_purify",
    "secret_key_rate",
    "skr_bb84",
    # Network
    "QuantumNetwork",
    "QuantumNode",
    "QuantumLink",
    "NodeRole",
    "load_csv",
    # Rendering
    "to_html",
    "save_html",
]
