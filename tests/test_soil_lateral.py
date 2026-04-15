"""Tests for S1 derivation from soil profile."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math

from core.soil import SoilType, SoilLayer, SoilProfile
from core.soil_lateral import (
    IBC_1806_2_LATERAL,
    S1DerivationMethod,
    compute_s1_engineering,
    compute_s1_ibc,
    weighted_s1_for_footing,
    describe_s1_derivation,
)


class TestIBCLookup:
    def test_gravel(self):
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.GRAVEL, N_spt=30)
        assert compute_s1_ibc(layer) == 200.0

    def test_sand(self):
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15)
        assert compute_s1_ibc(layer) == 150.0

    def test_clay(self):
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.CLAY, N_spt=8)
        assert compute_s1_ibc(layer) == 100.0

    def test_silt(self):
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SILT, N_spt=10)
        assert compute_s1_ibc(layer) == 100.0


class TestEngineeringMethod:
    def test_sand_rankine_kp(self):
        """Sand N=15 -> phi~37, Kp=tan^2(63.5)~4.04, gamma=110, S1~445 psf/ft."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15)
        s1 = compute_s1_engineering(layer)
        # Sanity: should be in the 400-500 range for N=15 sand
        assert 400 < s1 < 500

    def test_sand_higher_density(self):
        """N=30 sand produces larger Kp than N=15."""
        sparse = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15)
        dense = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=30)
        assert compute_s1_engineering(dense) > compute_s1_engineering(sparse)

    def test_clay_from_cu(self):
        """Clay N=8 -> cu=1000, S1 = 9*1000/10 = 900 -> clamped to 500."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.CLAY, N_spt=8)
        s1 = compute_s1_engineering(layer)
        assert s1 == 500.0  # clamped

    def test_soft_clay_below_clamp(self):
        """Soft clay N=2 -> cu=250, S1 = 225 psf/ft."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.CLAY, N_spt=2)
        s1 = compute_s1_engineering(layer)
        assert abs(s1 - 225.0) < 1.0

    def test_organic(self):
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.ORGANIC, N_spt=3)
        assert compute_s1_engineering(layer) == 50.0

    def test_sand_explicit_phi(self):
        """User-set phi=30 gives Kp = tan^2(60) = 3.0"""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND,
                          N_spt=15, phi=30.0, gamma=110.0)
        s1 = compute_s1_engineering(layer)
        expected = 3.0 * 110.0  # Kp * gamma
        assert abs(s1 - expected) < 1.0


class TestWeightedAverage:
    def test_single_layer(self):
        """Single layer footing should return that layer's S1."""
        layer = SoilLayer(top_depth=0, thickness=10, soil_type=SoilType.SAND, N_spt=15)
        profile = SoilProfile(layers=[layer])
        s1 = weighted_s1_for_footing(profile, 5.0, S1DerivationMethod.IBC_TABLE)
        assert s1 == 150.0

    def test_two_layer_partial(self):
        """4 ft footing fully in top sand layer."""
        layers = [
            SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15),
            SoilLayer(top_depth=5, thickness=10, soil_type=SoilType.CLAY, N_spt=8),
        ]
        profile = SoilProfile(layers=layers)
        s1 = weighted_s1_for_footing(profile, 4.0, S1DerivationMethod.IBC_TABLE)
        # All sand, 150 psf/ft
        assert s1 == 150.0

    def test_two_layer_spanning(self):
        """8 ft footing spans 5 ft sand + 3 ft clay."""
        layers = [
            SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15),
            SoilLayer(top_depth=5, thickness=10, soil_type=SoilType.CLAY, N_spt=8),
        ]
        profile = SoilProfile(layers=layers)
        s1 = weighted_s1_for_footing(profile, 8.0, S1DerivationMethod.IBC_TABLE)
        # Weighted: (150*5 + 100*3) / 8 = (750 + 300) / 8 = 131.25
        assert abs(s1 - 131.25) < 0.5

    def test_empty_profile_fallback(self):
        profile = SoilProfile(layers=[])
        s1 = weighted_s1_for_footing(profile, 4.0, S1DerivationMethod.IBC_TABLE)
        assert s1 == 100.0

    def test_zero_depth_fallback(self):
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15)
        profile = SoilProfile(layers=[layer])
        s1 = weighted_s1_for_footing(profile, 0.0, S1DerivationMethod.IBC_TABLE)
        assert s1 == 100.0

    def test_engineering_method_weighted(self):
        """Verify engineering method also weights correctly."""
        layers = [
            SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15),
            SoilLayer(top_depth=5, thickness=10, soil_type=SoilType.CLAY, N_spt=8),
        ]
        profile = SoilProfile(layers=layers)
        s1 = weighted_s1_for_footing(profile, 8.0, S1DerivationMethod.ENGINEERING)
        # Sand S1 ~ 450, clay S1 = 500 (clamped)
        # (~450*5 + 500*3) / 8 ~ 469
        assert 450 < s1 < 500


class TestDescribeDerivation:
    def test_breakdown_rows(self):
        """describe_s1_derivation returns per-layer dicts."""
        layers = [
            SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15),
            SoilLayer(top_depth=5, thickness=10, soil_type=SoilType.CLAY, N_spt=8),
        ]
        profile = SoilProfile(layers=layers)
        rows = describe_s1_derivation(profile, 8.0, S1DerivationMethod.IBC_TABLE)
        assert len(rows) == 2
        # First layer: 0-5 ft sand
        assert rows[0]["soil_type"] == "Sand"
        assert rows[0]["thickness_ft"] == 5.0
        assert rows[0]["s1_psf_per_ft"] == 150.0
        # Second layer: 5-8 ft clay (partial)
        assert rows[1]["soil_type"] == "Clay"
        assert rows[1]["thickness_ft"] == 3.0

    def test_empty_profile_breakdown(self):
        profile = SoilProfile(layers=[])
        rows = describe_s1_derivation(profile, 4.0, S1DerivationMethod.IBC_TABLE)
        assert rows == []
