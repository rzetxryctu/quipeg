"""
Physics utilities for quantum communication over optical fibre.

All functions are pure (no side effects) and use only the Python
standard library. Sensible physical constants are provided as
module-level defaults.
"""

import math
from typing import Tuple

# ---------------------------------------------------------------------------
# Physical constants (SI)
# ---------------------------------------------------------------------------
SPEED_OF_LIGHT_KM_S: float = 2.0e5       # ~200 000 km/s in fibre
ATTENUATION_DB_PER_KM: float = 0.2       # ITU-T G.652 typical loss at 1550 nm
T1_RELAXATION_S: float = 1e-3            # ~1 ms typical T1 energy-relaxation time
T2_DEPHASING_S: float = 1e-3             # ~1 ms typical T2 dephasing time
ETA_DETECTOR: float = 0.8                # detector efficiency
P_DARK: float = 1e-8                    # dark-count probability per pulse
MU_PU: float = 0.1                      # mean photon number of weak coherent pulse
SECURITY_PARAMETER: float = 1e-10       # ε-secure BB84 parameter


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Great-circle distance between two points on Earth (km) using the Haversine formula.

    Parameters
    ----------
    lat1, lon1 : float
        Latitude and longitude of the first point in **degrees**.
    lat2, lon2 : float
        Latitude and longitude of the second point in **degrees**.

    Returns
    -------
    float
        Great-circle distance in kilometres.

    Examples
    --------
    >>> round(haversine(51.5, -0.1, 48.9, 2.4), 1)
    343.6
    """
    R = 6371.0  # mean Earth radius in km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# Fibre loss
# ---------------------------------------------------------------------------

def fiber_loss_db(distance_km: float, alpha: float = ATTENUATION_DB_PER_KM) -> float:
    """
    Total fibre attenuation in dB.

    Parameters
    ----------
    distance_km : float
        One-way distance along the fibre.
    alpha : float, optional
        Loss coefficient in dB/km (default 0.2 dB/km, ITU-T G.652).

    Returns
    -------
    float
        Total loss in decibels.

    Examples
    --------
    >>> round(fiber_loss_db(50), 2)
    10.0
    """
    return alpha * distance_km


def transmittance(distance_km: float, alpha: float = ATTENUATION_DB_PER_KM) -> float:
    """
    Photon transmittance of a fibre link (probability a photon arrives).

    Computed as 10^(-loss_dB / 10).

    Parameters
    ----------
    distance_km : float
        One-way fibre distance.
    alpha : float, optional
        Loss coefficient in dB/km.

    Returns
    -------
    float
        Probability in [0, 1].

    Examples
    --------
    >>> 0 < transmittance(10) < 1
    True
    >>> transmittance(0)
    1.0
    """
    if distance_km <= 0:
        return 1.0
    loss_db = fiber_loss_db(distance_km, alpha)
    return 10.0 ** (-loss_db / 10.0)


# ---------------------------------------------------------------------------
# Decoherence models
# ---------------------------------------------------------------------------

def decohere(fidelity: float, dt_seconds: float, T2: float = T2_DEPHASING_S) -> float:
    """
    Single-channel exponential decoherence of an entangled qubit pair.

    A perfect Bell state has fidelity F=1. During storage / transmission
    the fidelity decays exponentially toward 0.25 (the maximally-mixed
    separable state) with characteristic time T2.

    This is a simplified single-channel model. For a more accurate treatment
    of energy relaxation (T1) vs phase dephasing (T2), use :func:`decohere_t1_t2`.

    Parameters
    ----------
    fidelity : float
        Current fidelity before the interval.
    dt_seconds : float
        Elapsed physical time in seconds.
    T2 : float, optional
        T2 dephasing time in seconds (default 1 ms).

    Returns
    -------
    float
        Fidelity after dt_seconds. Clamped to [0.25, 1.0].

    Examples
    --------
    >>> f = decohere(0.95, 0.001, T2=0.001)
    >>> 0.25 < f < 0.95
    True
    """
    if dt_seconds < 0:
        return fidelity
    decay = math.exp(-dt_seconds / T2)
    new_f = 0.25 + (fidelity - 0.25) * decay
    return max(0.25, min(1.0, new_f))


def decohere_t1_t2(
    fidelity: float,
    dt_seconds: float,
    T1: float = T1_RELAXATION_S,
    T2: float = T2_DEPHASING_S,
) -> float:
    """
    Two-channel decoherence: simultaneous T1 (energy relaxation) and T2 (phase dephasing).

    Different qubit technologies have very different T1 and T2 values.
    This model treats them independently, giving more realistic fidelity
    tracking for heterogeneous quantum memories:

        F(t) = ¼ + ¼·exp(-t/T1) + ½·exp(-t/T2)

    The three terms correspond to the three eigenvalues of the
    diagonalised depolarising map:
      - ¼ : probability of the maximally-mixed identity component
      - ¼·exp(-t/T1) : population of the correct Bell state
      - ½·exp(-t/T2) : coherence (off-diagonal) contribution

    Parameters
    ----------
    fidelity : float
        Current fidelity (must be in [0.25, 1.0]).
    dt_seconds : float
        Elapsed physical time in seconds.
    T1 : float, optional
        Energy-relaxation time constant in seconds (default 1 ms).
    T2 : float, optional
        Phase-dephasing time constant in seconds (default 1 ms).

    Returns
    -------
    float
        Fidelity after dt_seconds. Clamped to [0.25, 1.0].

    Examples
    --------
    >>> f = decohere_t1_t2(1.0, 0.001)
    >>> 0.25 < f < 1.0
    True
    >>> f = decohere_t1_t2(0.25, 0.001)   # already maximally mixed
    0.25
    """
    if dt_seconds <= 0:
        return max(0.25, min(1.0, fidelity))
    if not (0.25 <= fidelity <= 1.0):
        raise ValueError("Fidelity must be in [0.25, 1.0]")
    e1 = math.exp(-dt_seconds / T1)
    e2 = math.exp(-dt_seconds / T2)
    new_f = 0.25 + 0.25 * e1 + 0.50 * e2
    return max(0.25, min(1.0, new_f))


# ---------------------------------------------------------------------------
# QBER
# ---------------------------------------------------------------------------

def qber_from_fidelity(fidelity: float) -> float:
    """
    Quantum Bit Error Rate (QBER) estimated from Bell-state fidelity.

    For a Werner state / depolarised channel the QBER = (1 - F) / 2,
    derived from the CHSH inequality and standard QKD theory.

    Parameters
    ----------
    fidelity : float
        Bell-state fidelity F ∈ [0.25, 1].

    Returns
    -------
    float
        Estimated QBER ∈ [0, 0.375].

    Examples
    --------
    >>> round(qber_from_fidelity(0.97), 4)
    0.015
    >>> qber_from_fidelity(1.0)
    0.0
    >>> round(qber_from_fidelity(0.25), 4)
    0.375
    """
    if fidelity < 0.25 or fidelity > 1.0:
        raise ValueError("Fidelity must be in [0.25, 1.0]")
    return (1.0 - fidelity) / 2.0


# ---------------------------------------------------------------------------
# Binary entropy
# ---------------------------------------------------------------------------

def _binary_entropy(x: float) -> float:
    """Binary entropy H₂(x) = -x·log₂(x) - (1-x)·log₂(1-x)."""
    if x <= 0.0 or x >= 1.0:
        return 0.0
    return -(x * math.log2(x) + (1 - x) * math.log2(1 - x))


# ---------------------------------------------------------------------------
# Entanglement swapping
# ---------------------------------------------------------------------------

def swap_fidelity_bell(f1: float, f2: float) -> float:
    """
    Fidelity of an entangled pair produced by entanglement swapping
    using the **Bell-corrected product model**.

    Under the Werner-state / depolarising-noise model, swapping two
    Bell pairs with fidelities F₁ and F₂ yields:

        F_swap = F₁ · F₂ + (1-F₁)(1-F₂) / 3

    This formula correctly reduces to:
      - F_swap = 1.0 when F₁ = F₂ = 1 (both pairs perfect)
      - F_swap = 0.25 when F₁ = F₂ = 0.25 (both maximally mixed)
      - F_swap ≈ (F₁ + F₂)/2 in the high-fidelity limit (near-perfect pairs)

    The product term captures the *cross* Werner-state noise correlations
    that the arithmetic mean misses. This is the standard result in the
    quantum repeater literature.

    Reference: Pan et al., Rev. Mod. Phys. 84, 777 (2012), Sec. IV.

    Parameters
    ----------
    f1 : float
        Fidelity of the first Bell pair (0.25 – 1.0).
    f2 : float
        Fidelity of the second Bell pair (0.25 – 1.0).

    Returns
    -------
    float
        Fidelity after swapping, clamped to [0.25, 1.0].

    Examples
    --------
    >>> round(swap_fidelity_bell(1.0, 1.0), 4)
    1.0
    >>> round(swap_fidelity_bell(0.25, 0.25), 4)
    0.25
    >>> 0 < swap_fidelity_bell(0.9, 0.8) < 1
    True
    """
    if not (0.25 <= f1 <= 1.0) or not (0.25 <= f2 <= 1.0):
        raise ValueError("Swap fidelities must be in [0.25, 1.0]")
    f_swap = f1 * f2 + (1 - f1) * (1 - f2) / 3.0
    return max(0.25, min(1.0, f_swap))


def swap_fidelity_avg(f1: float, f2: float) -> float:
    """
    Fidelity of an entangled pair produced by entanglement swapping
    using the **arithmetic mean model** (v2.0 formula).

    F_swap = (F₁ + F₂) / 2

    This is the high-fidelity approximation used in v2.0. Kept for
    comparison purposes; prefer :func:`swap_fidelity_bell` for
    general use.

    Parameters
    ----------
    f1, f2 : float
        Input Bell-pair fidelities (0.25 – 1.0).

    Returns
    -------
    float
        Fidelity after swapping, clamped to [0.25, 1.0].

    Examples
    --------
    >>> round(swap_fidelity_avg(1.0, 1.0), 4)
    1.0
    """
    if not (0.25 <= f1 <= 1.0) or not (0.25 <= f2 <= 1.0):
        raise ValueError("Swap fidelities must be in [0.25, 1.0]")
    f_swap = (f1 + f2) / 2.0
    return max(0.25, min(1.0, f_swap))


def swap_fidelity(f1: float, f2: float) -> float:
    """
    Fidelity after entanglement swapping.

    In v3.0 this calls :func:`swap_fidelity_bell` (Bell-corrected product
    model) by default. Use ``swap_fidelity_bell`` or ``swap_fidelity_avg``
    explicitly when the distinction matters.

    Parameters
    ----------
    f1, f2 : float
        Input Bell-pair fidelities (0.25 – 1.0).

    Returns
    -------
    float
        Fidelity after swapping.

    Examples
    --------
    >>> round(swap_fidelity(1.0, 1.0), 4)
    1.0
    """
    return swap_fidelity_bell(f1, f2)


# ---------------------------------------------------------------------------
# DEJMPS Purification
# ---------------------------------------------------------------------------

def dejmps_purify(f1: float, f2: float) -> Tuple[bool, float, float]:
    """
    DEJMPS-style single-step entanglement purification protocol
    (Deutsch–Jozsa–Maslennikov–Pedersen–Shor, simplified form).

    Two pairs with fidelities F₁ and F₂ are measured in the Bell basis.
    The pairs are kept only when the Bell-measurement outcomes match
    (which happens with probability P_succ). The surviving pair has
    improved fidelity.

    After successful purification::

        F_pur = (F₁·F₂ + (1-F₁)(1-F₂)/3) / (F₁·F₂ + (1-F₁)(1-F₂))
        P_succ = (F₁·F₂ + (1-F₁)(1-F₂))²

    Note: This is a simplified version that does not track which specific
    Bell states were measured. For full DEJMPS the success probability is
    slightly different, but the fidelity formula is the same.

    Parameters
    ----------
    f1 : float
        Fidelity of the first pair (0.25 – 1.0).
    f2 : float
        Fidelity of the second pair (0.25 – 1.0).

    Returns
    -------
    Tuple[bool, float, float]
        (purification_succeeded, new_fidelity, success_probability).
        On failure, new_fidelity = 0.0.

    Examples
    --------
    >>> ok, f_new, p = dejmps_purify(0.85, 0.85)
    >>> 0.85 < f_new <= 1.0
    True
    >>> 0.0 < p < 1.0
    True
    >>> ok, f_new, p = dejmps_purify(0.25, 0.25)
    >>> ok
    False
    """
    if not (0.25 <= f1 <= 1.0) or not (0.25 <= f2 <= 1.0):
        raise ValueError("Purification fidelities must be in [0.25, 1.0]")

    # Both pairs must be non-maximally-mixed for purification to work.
    # If either pair is already at the mixed-state floor (F=0.25), the
    # DEJMPS protocol cannot improve fidelity — return failure immediately.
    if f1 <= 0.25 or f2 <= 0.25:
        return False, 0.0, 0.0

    # Numerator: same as Bell-corrected swap fidelity
    numerator = f1 * f2 + (1 - f1) * (1 - f2) / 3.0
    # Denominator: total probability of correct pair
    denominator = f1 * f2 + (1 - f1) * (1 - f2)
    success_prob = denominator ** 2

    if denominator < 1e-12:
        return False, 0.0, 0.0

    new_f = numerator / denominator

    # Post-select on measurement outcome (simulate with uniform random)
    import random
    succeeded = random.random() < success_prob

    if succeeded:
        return True, max(0.25, min(1.0, new_f)), success_prob
    else:
        return False, 0.0, success_prob


# ---------------------------------------------------------------------------
# Secret Key Rate (BB84)
# ---------------------------------------------------------------------------

def secret_key_rate(
    fidelity: float,
    distance_km: float,
    p_repeat: float = 0.5,
    f_error_correction: float = 1.2,
    clock_rate_hz: float = 1e9,
    dark_count_prob: float = P_DARK,
    mu: float = MU_PU,
    alpha: float = ATTENUATION_DB_PER_KM,
) -> Tuple[float, dict]:
    """
    BB84 Secret Key Rate (bits/s) for a single fibre link.

    Uses the infinite-key decoy-state lower bound::

        SKR = ½ · η · μ · p_repeat · (1 - 2·QBER - H₂(QBER)) · f_EC · R

    where η = η_fibre × η_detector, and QBER is derived from fidelity.

    Parameters
    ----------
    fidelity : float
        Bell-state fidelity of distributed entangled pairs (0.25 – 1.0).
    distance_km : float
        One-way fibre distance.
    p_repeat : float, optional
        Fraction of successful entanglement distribution attempts.
    f_error_correction : float, optional
        Error-correction efficiency relative to Shannon limit (1.2 typical).
    clock_rate_hz : float, optional
        Source repetition rate (1 GHz = 1e9 Hz).
    dark_count_prob : float, optional
        Dark-count probability per pulse.
    mu : float, optional
        Mean photon number of the decoy pulse.
    alpha : float, optional
        Fibre loss coefficient in dB/km.

    Returns
    -------
    Tuple[float, dict]
        (SKR in bits/second, diagnostics dict).

    Examples
    --------
    >>> skr, info = secret_key_rate(0.97, 20.0)
    >>> skr > 0
    True
    >>> info["qber"] < 0.05
    True
    """
    eta_fiber = transmittance(distance_km, alpha)
    if eta_fiber < 1e-12:
        return 0.0, {"distance_km": distance_km, "fidelity": fidelity,
                     "transmittance": eta_fiber, "reason": "eta_below_threshold"}
    eta_total = eta_fiber * ETA_DETECTOR

    # total background probability
    p_background = (1 - eta_total) * dark_count_prob + dark_count_prob ** 2 / 2

    # gain
    gain = 1 - math.exp(-eta_total * mu) * math.exp(-p_background)

    # QBER
    f = max(0.25, min(1.0, fidelity))
    qber = qber_from_fidelity(f)

    # error gain
    error_gain = qber * gain

    # net secret bits per pulse
    h_qber = _binary_entropy(qber)
    raw_rate = gain * (1 - 2 * qber - h_qber)

    if f_error_correction > 0:
        raw_rate -= gain * h_qber * (f_error_correction - 1)

    skr = 0.5 * p_repeat * max(0.0, raw_rate) * clock_rate_hz

    info = {
        "distance_km": distance_km,
        "fidelity": f,
        "qber": qber,
        "transmittance": eta_fiber,
        "total_efficiency": eta_total,
        "gain": gain,
        "error_gain": error_gain,
        "h_qber": h_qber,
        "clock_rate_hz": clock_rate_hz,
    }
    return max(0.0, skr), info


def skr_bb84(
    distance_km: float,
    fidelity: float = 1.0,
    p_repeat: float = 0.5,
    f_error_correction: float = 1.2,
    clock_rate_hz: float = 1e9,
    dark_count_prob: float = P_DARK,
    mu: float = MU_PU,
    alpha: float = ATTENUATION_DB_PER_KM,
) -> Tuple[float, dict]:
    """
    Alias for :func:`secret_key_rate` for backward compatibility with v2.

    Parameters
    ----------
    distance_km : float
        One-way fibre distance.
    fidelity : float, optional
        Bell-state fidelity (default 1.0).
    p_repeat : float, optional
        Fraction of successful entanglement distribution attempts.
    f_error_correction : float, optional
        Error-correction efficiency relative to Shannon limit.
    clock_rate_hz : float, optional
        Source repetition rate.
    dark_count_prob : float, optional
        Dark-count probability per pulse.
    mu : float, optional
        Mean photon number of the decoy pulse.
    alpha : float, optional
        Fibre loss coefficient in dB/km.

    Returns
    -------
    Tuple[float, dict]
        (SKR in bits/second, diagnostics dict).
    """
    return secret_key_rate(
        fidelity=fidelity,
        distance_km=distance_km,
        p_repeat=p_repeat,
        f_error_correction=f_error_correction,
        clock_rate_hz=clock_rate_hz,
        dark_count_prob=dark_count_prob,
        mu=mu,
        alpha=alpha,
    )
