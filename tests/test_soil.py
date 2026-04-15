"""Tests for soil profile model ported from SPORK."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.soil import (
    SoilType,
    SoilLayer,
    SoilProfile,
    build_soil_layer_from_dict,
    correct_N_overburden,
    n_to_phi_hatanaka,
    n_to_cu,
    GAMMA_WATER,
)


class TestSoilLayer:
    def test_N_60_correction(self):
        """Energy correction applied to raw N."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND,
                          N_spt=10, energy_ratio=60.0)
        assert abs(layer.N_60 - 10.0) < 0.01

    def test_N_60_non_standard_energy(self):
        """75% energy ratio boosts N by 1.25x."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND,
                          N_spt=10, energy_ratio=75.0)
        assert abs(layer.N_60 - 12.5) < 0.01

    def test_gamma_auto_estimate_sand(self):
        """SPT N=15 sand -> gamma around 110 pcf."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15)
        # Implementation: n<30 -> 110 pcf (dry)
        assert layer.gamma_effective == 110.0

    def test_gamma_effective_submerged(self):
        """Submerged sand -> gamma - 62.4."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND,
                          N_spt=15, is_submerged=True)
        # Dry value minus water
        assert layer.gamma_effective == 125.0 - GAMMA_WATER

    def test_phi_from_spt_sand(self):
        """Hatanaka & Uchida: N=15 -> phi ~ sqrt(300)+20 ~ 37.3 degrees."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15)
        phi = layer.get_phi(0)
        assert 36 < phi < 38

    def test_phi_from_explicit_value(self):
        """If phi is set directly, don't correlate."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND,
                          N_spt=15, phi=32.0)
        assert layer.get_phi(0) == 32.0

    def test_cu_from_spt_clay(self):
        """Terzaghi & Peck: N=8 clay -> cu = 125 * 8 = 1000 psf."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.CLAY, N_spt=8)
        assert abs(layer.get_cu() - 1000.0) < 1.0

    def test_cu_clay_explicit(self):
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.CLAY,
                          N_spt=8, c_u=1500.0)
        assert layer.get_cu() == 1500.0

    def test_sand_cu_zero(self):
        """Cohesionless soils have cu = 0."""
        layer = SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15)
        assert layer.get_cu() == 0.0


class TestSoilProfile:
    def test_empty_profile(self):
        profile = SoilProfile(layers=[])
        assert profile.total_depth == 0.0

    def test_total_depth(self):
        layers = [
            SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15),
            SoilLayer(top_depth=5, thickness=10, soil_type=SoilType.CLAY, N_spt=8),
        ]
        profile = SoilProfile(layers=layers)
        assert profile.total_depth == 15.0

    def test_layer_at_depth(self):
        layers = [
            SoilLayer(top_depth=0, thickness=5, soil_type=SoilType.SAND, N_spt=15),
            SoilLayer(top_depth=5, thickness=10, soil_type=SoilType.CLAY, N_spt=8),
        ]
        profile = SoilProfile(layers=layers)
        assert profile.layer_at_depth(3.0).soil_type == SoilType.SAND
        assert profile.layer_at_depth(10.0).soil_type == SoilType.CLAY

    def test_effective_stress_no_water(self):
        """Effective stress = gamma * depth for dry soil."""
        layers = [SoilLayer(top_depth=0, thickness=10, soil_type=SoilType.SAND,
                            N_spt=15, gamma=120.0)]
        profile = SoilProfile(layers=layers)
        # At 5 ft: 120 * 5 = 600 psf
        assert abs(profile.effective_stress_at(5.0) - 600.0) < 1.0

    def test_effective_stress_with_water_table(self):
        """Below water table, effective stress reduces by gamma_water per foot."""
        layers = [SoilLayer(top_depth=0, thickness=20, soil_type=SoilType.SAND,
                            N_spt=15, gamma=120.0)]
        profile = SoilProfile(layers=layers, water_table_depth=5.0)
        # At 10 ft: 120*5 (above WT) + (120-62.4)*5 (below WT) = 600 + 288 = 888
        result = profile.effective_stress_at(10.0)
        assert abs(result - 888.0) < 5.0


class TestBuildFromDict:
    def test_minimum_fields(self):
        """Construct layer from minimal dict."""
        ld = {
            "top_depth": 0.0,
            "thickness": 5.0,
            "soil_type": "Sand",
            "N_spt": 15,
        }
        layer = build_soil_layer_from_dict(ld)
        assert layer.soil_type == SoilType.SAND
        assert layer.N_spt == 15
        assert layer.top_depth == 0.0

    def test_with_description(self):
        ld = {
            "top_depth": 0.0,
            "thickness": 5.0,
            "soil_type": "Clay",
            "description": "Brown silty clay",
            "N_spt": 8,
            "c_u": 1200.0,
        }
        layer = build_soil_layer_from_dict(ld)
        assert layer.description == "Brown silty clay"
        assert layer.c_u == 1200.0

    def test_round_trip(self):
        """Build -> dataclass -> still correct."""
        ld = {
            "top_depth": 5.0, "thickness": 10.0, "soil_type": "Gravel",
            "N_spt": 30, "gamma": 125.0, "phi": 38.0,
        }
        layer = build_soil_layer_from_dict(ld)
        assert layer.bottom_depth == 15.0
        assert layer.get_phi(0) == 38.0


class TestSPTCorrelations:
    def test_overburden_correction(self):
        """Liao & Whitman C_N formula."""
        # At atmospheric pressure (2116 psf), C_N should be 1.0
        result = correct_N_overburden(10.0, 2116.0)
        assert abs(result - 10.0) < 0.1

    def test_overburden_capped_at_2(self):
        """C_N caps at 2.0 for very low stress."""
        result = correct_N_overburden(10.0, 100.0)
        assert abs(result - 20.0) < 0.1

    def test_hatanaka_phi_correlation(self):
        """N1_60 = 15 -> phi = sqrt(300) + 20 ~ 37.3"""
        phi = n_to_phi_hatanaka(15)
        assert 36 < phi < 38

    def test_n_to_cu_correlation(self):
        """Terzaghi & Peck: 125 * N_60."""
        assert n_to_cu(10) == 1250.0
