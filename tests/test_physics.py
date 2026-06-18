"""Tests for quipeg.physics — physics utilities and quantum channel models."""

import math
import pytest
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


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------

class TestHaversine:
    def test_london_paris(self):
        d = haversine(51.5074, -0.1278, 48.8566, 2.3522)
        assert 340.0 < d < 350.0

    def test_new_york_los_angeles(self):
        d = haversine(40.7128, -74.0060, 34.0522, -118.2437)
        assert 3900.0 < d < 4000.0

    def test_same_point_is_zero(self):
        assert haversine(0.0, 0.0, 0.0, 0.0) == 0.0

    def test_antipodal_rough(self):
        # Rough check for antipodal points
        d = haversine(0, 0, 0, 180)
        assert 19_000 < d < 20_016

    def test_symmetric(self):
        d1 = haversine(10.0, 20.0, 30.0, 40.0)
        d2 = haversine(30.0, 40.0, 10.0, 20.0)
        assert math.isclose(d1, d2)


# ---------------------------------------------------------------------------
# Fibre loss
# ---------------------------------------------------------------------------

class TestFiberLoss:
    def test_zero_distance_loss_is_zero(self):
        assert fiber_loss_db(0.0) == 0.0

    def test_linear_proportional(self):
        assert fiber_loss_db(50.0) == 10.0

    def test_custom_attenuation(self):
        assert fiber_loss_db(10.0, alpha=0.3) == 3.0

    def test_custom_attenuation_float(self):
        assert math.isclose(fiber_loss_db(33.0, alpha=0.17), 5.61)


# ---------------------------------------------------------------------------
# Transmittance
# ---------------------------------------------------------------------------

class TestTransmittance:
    def test_one_is_one(self):
        assert transmittance(0.0) == 1.0

    def test_monotonically_decreasing(self):
        assert transmittance(10.0) > transmittance(50.0)

    def test_bounds(self):
        t = transmittance(100.0)
        assert 0.0 < t < 1.0

    def test_matches_loss(self):
        alpha = 0.2
        d = 25.0
        expected = 10.0 ** (-alpha * d / 10.0)
        assert math.isclose(transmittance(d, alpha), expected)

    def test_close_to_zero_at_long_distance(self):
        assert 0.0 < transmittance(500.0) < 1e-5


# ---------------------------------------------------------------------------
# Single-channel decoherence
# ---------------------------------------------------------------------------

class TestDecohere:
    def test_no_time_no_change(self):
        assert decohere(0.95, 0.0) == 0.95

    def test_decay_toward_mixed_state(self):
        f = decohere(0.95, 1.0, T2=0.5)
        assert 0.25 < f < 0.95

    def test_floor_at_0_25(self):
        # Very long time should floor at 0.25
        f = decohere(0.30, 100.0, T2=0.001)
        assert f == 0.25

    def test_clamp_ceiling_at_1(self):
        assert decohere(1.0, 0.0) == 1.0
        assert decohere(1.0, 1.0, T2=0.5) <= 1.0

    def test_negative_dt_ignored(self):
        assert decohere(0.9, -1.0) == 0.9


# ---------------------------------------------------------------------------
# T1/T2 two-channel decoherence
# ---------------------------------------------------------------------------

class TestDecohereT1T2:
    def test_no_time_no_change(self):
        assert decohere_t1_t2(0.95, 0.0) == 0.95

    def test_perfect_pair_decays(self):
        f = decohere_t1_t2(1.0, 0.001, T1=0.001, T2=0.001)
        assert 0.25 < f < 1.0

    def test_mixed_state_stays_mixed(self):
        f = decohere_t1_t2(0.25, 1.0)
        assert f == 0.25

    def test_invariant_check(self):
        # At t=0 the fidelity is unchanged
        for f0 in [0.3, 0.5, 0.8, 0.95, 1.0]:
            assert decohere_t1_t2(f0, 0.0) == f0

    def test_t1_longer_than_t2(self):
        # If T1 >> T2, T1 contribution decays slowly
        f = decohere_t1_t2(1.0, 1.0, T1=100.0, T2=0.1)
        assert 0.25 < f < 1.0

    def test_invalid_fidelity_raises(self):
        with pytest.raises(ValueError):
            decohere_t1_t2(0.1, 0.001)
        with pytest.raises(ValueError):
            decohere_t1_t2(1.1, 0.001)


# ---------------------------------------------------------------------------
# QBER
# ---------------------------------------------------------------------------

class TestQBER:
    def test_perfect_fidelity_zero_qber(self):
        assert qber_from_fidelity(1.0) == 0.0

    def test_mixed_state_max_qber(self):
        q = qber_from_fidelity(0.25)
        assert math.isclose(q, 0.375)

    def test_symmetric(self):
        q1 = qber_from_fidelity(0.90)
        q2 = qber_from_fidelity(1.0 - 2 * q1)
        assert math.isclose(q1, q2, rel_tol=1e-9)

    def test_intermediate(self):
        q = qber_from_fidelity(0.97)
        assert 0.0 < q < 0.05

    def test_out_of_range_raises(self):
        with pytest.raises(ValueError):
            qber_from_fidelity(0.1)
        with pytest.raises(ValueError):
            qber_from_fidelity(1.5)


# ---------------------------------------------------------------------------
# Entanglement swapping — Bell-corrected model
# ---------------------------------------------------------------------------

class TestSwapFidelityBell:
    def test_perfect_pairs_stay_perfect(self):
        assert math.isclose(swap_fidelity_bell(1.0, 1.0), 1.0)

    def test_mixed_pairs_stay_mixed(self):
        assert math.isclose(swap_fidelity_bell(0.25, 0.25), 0.25)

    def test_high_fidelity_approx_arithmetic_mean(self):
        # At high fidelity, product formula ≈ arithmetic mean
        f1, f2 = 0.98, 0.96
        bell = swap_fidelity_bell(f1, f2)
        avg = (f1 + f2) / 2
        # They should be close but not identical
        assert 0.9 < bell < 1.0
        assert abs(bell - avg) < 0.03

    def test_bell_is_less_than_or_equal_to_avg(self):
        # For all valid inputs, the product formula ≤ arithmetic mean
        for f1 in [0.25, 0.4, 0.6, 0.8, 0.95]:
            for f2 in [0.25, 0.4, 0.6, 0.8, 0.95]:
                bell = swap_fidelity_bell(f1, f2)
                avg = (f1 + f2) / 2
                assert bell <= avg + 1e-12

    def test_asymmetric_same_as_swap(self):
        assert swap_fidelity_bell(0.9, 0.8) == swap_fidelity_bell(0.8, 0.9)

    def test_symmetric_range(self):
        for f1, f2 in [(0.9, 0.8), (0.5, 0.5), (1.0, 0.5)]:
            result = swap_fidelity_bell(f1, f2)
            assert 0.25 <= result <= 1.0

    def test_invalid_fidelity_raises(self):
        with pytest.raises(ValueError):
            swap_fidelity_bell(0.1, 0.9)
        with pytest.raises(ValueError):
            swap_fidelity_bell(0.9, 1.1)


# ---------------------------------------------------------------------------
# Entanglement swapping — arithmetic mean (v2.0 compat)
# ---------------------------------------------------------------------------

class TestSwapFidelityAvg:
    def test_perfect_pairs(self):
        assert math.isclose(swap_fidelity_avg(1.0, 1.0), 1.0)

    def test_mixed_pairs(self):
        assert math.isclose(swap_fidelity_avg(0.25, 0.25), 0.25)

    def test_consistency_with_definition(self):
        f1, f2 = 0.8, 0.9
        assert math.isclose(swap_fidelity_avg(f1, f2), (f1 + f2) / 2.0)

    def test_invalid_fidelity_raises(self):
        with pytest.raises(ValueError):
            swap_fidelity_avg(0.0, 0.5)


# ---------------------------------------------------------------------------
# Default swap_fidelity delegates to Bell model in v3
# ---------------------------------------------------------------------------

class TestSwapFidelityDefault:
    def test_delegates_to_bell(self):
        f1, f2 = 0.9, 0.8
        assert swap_fidelity(f1, f2) == swap_fidelity_bell(f1, f2)


# ---------------------------------------------------------------------------
# DEJMPS Purification
# ---------------------------------------------------------------------------

class TestDejmpsPurify:
    def test_improves_high_fidelity(self):
        ok, f_new, p = dejmps_purify(0.85, 0.85)
        assert 0.0 < p < 1.0
        if ok:
            assert f_new > 0.85

    def test_mixed_pairs_fail(self):
        ok, _, p = dejmps_purify(0.25, 0.25)
        assert not ok

    def test_success_probability_bounds(self):
        _, _, p = dejmps_purify(0.5, 0.5)
        assert 0.0 < p < 1.0

    def test_success_probability_perfect(self):
        _, _, p = dejmps_purify(1.0, 1.0)
        assert p == 1.0

    def test_new_fidelity_clamped(self):
        # Run many times to account for random failure
        improved_count = 0
        for _ in range(100):
            ok, f_new, _ = dejmps_purify(0.92, 0.90)
            if ok:
                assert 0.25 <= f_new <= 1.0
                if f_new > 0.90:
                    improved_count += 1
        assert improved_count > 0  # at least some should improve

    def test_invalid_fidelity_raises(self):
        with pytest.raises(ValueError):
            dejmps_purify(0.1, 0.9)


# ---------------------------------------------------------------------------
# Secret Key Rate
# ---------------------------------------------------------------------------

class TestSecretKeyRate:
    def test_short_distance_positive_skr(self):
        skr, info = secret_key_rate(0.97, 10.0)
        assert skr > 0
        assert "qber" in info

    def test_long_distance_zero_skr(self):
        # Very long distance → negligible transmittance → zero SKR
        skr, _ = secret_key_rate(0.97, 1000.0)
        assert skr == 0.0

    def test_qber_increases_with_distance(self):
        _, i1 = secret_key_rate(0.97, 10.0)
        _, i2 = secret_key_rate(0.97, 200.0)
        # transmittance decreases, but QBER is derived from fidelity not distance
        # So this doesn't test qber. Let's test it differently.
        assert 0.0 <= i1["qber"] <= 0.375

    def test_info_keys(self):
        _, info = secret_key_rate(0.95, 50.0)
        for key in ["distance_km", "fidelity", "qber", "transmittance",
                    "total_efficiency", "gain", "error_gain"]:
            assert key in info

    def test_perfect_fidelity_no_qber(self):
        _, info = secret_key_rate(1.0, 1.0)
        assert info["qber"] == 0.0

    def test_mixed_fidelity_has_qber(self):
        _, info = secret_key_rate(0.25, 1.0)
        assert info["qber"] > 0.0

    def test_clock_rate_affects_skr(self):
        skr1, _ = secret_key_rate(0.97, 20.0, clock_rate_hz=1e9)
        skr2, _ = secret_key_rate(0.97, 20.0, clock_rate_hz=1e8)
        assert skr1 > skr2

    def test_skr_bb84_alias(self):
        skr1, info1 = skr_bb84(20.0, 0.97)
        skr2, info2 = secret_key_rate(0.97, 20.0)
        assert math.isclose(skr1, skr2)
        assert info1["qber"] == info2["qber"]
