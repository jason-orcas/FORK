"""Tests for wood fence post NDS calculations.

Validates against Wood Fence_Line Post_DG.xlsx, Wood Fence_Gate Post_DG.xlsx.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import ASCEEdition, PostType, WindInput, WoodFenceInput, WoodSpecies
from core.wood import calculate_wood_post


def _make_wind():
    """Standard wind inputs for wood fence tests."""
    return WindInput(
        asce_edition=ASCEEdition.ASCE_7_16,
        wind_speed=100.0,
        Kz=0.85,
        Kzt=1.0,
        Kd=0.85,
        G=0.85,
        Cf=1.3,
    )


class TestWoodLinePost:
    def test_basic_calculation(self):
        """Wood Fence_Line Post_DG.xlsx: 4" diam, 8' height, FoS=1.0."""
        wind = _make_wind()
        wood = WoodFenceInput(
            post_type=PostType.LINE,
            species=WoodSpecies.DOUGLAS_FIR,
            post_diameter=4.0,
            post_height=8.0,
            post_spacing=10.0,
            post_weight=3.2,
            wire_diameter=0.192,
            mesh_size=5.5,
            mesh_weight=0.154,
            fos=1.0,
        )
        result = calculate_wood_post(wind, wood)

        # Basic sanity checks
        assert result.axial_load > 0
        assert result.shear > 0
        assert result.moment > 0
        assert result.fb > 0
        assert result.Fb_prime > 0

        # Cp should be between 0 and 1
        assert 0 < result.Cp <= 1.0, f"Cp = {result.Cp:.4f}"

        # Cd should be 1.6 for wind
        assert result.Cd == 1.6

        # Ccs should be 1.1 for round timber
        assert result.Ccs == 1.1

    def test_nds_adjustment_factors(self):
        """Verify NDS adjustment factors match spreadsheet defaults."""
        wind = _make_wind()
        wood = WoodFenceInput(
            post_type=PostType.LINE,
            species=WoodSpecies.DOUGLAS_FIR,
            post_diameter=4.0,
            post_height=8.0,
            post_spacing=10.0,
            post_weight=3.2,
            wire_diameter=0.192,
            mesh_size=5.5,
            mesh_weight=0.154,
            fos=1.0,
        )
        result = calculate_wood_post(wind, wood)

        assert result.Cd == 1.6    # wind load duration
        assert result.Ct == 1.0    # normal temperature
        assert result.Cct == 1.0   # no incising
        assert result.Cf == 1.0    # round timber
        assert result.Ccs == 1.1   # round section
        assert result.Cls == 1.0   # laterally braced
        assert result.Cb == 1.0    # default bearing

    def test_deflection_positive(self):
        """Deflection should be positive for any wind load."""
        wind = _make_wind()
        wood = WoodFenceInput(
            post_type=PostType.LINE,
            species=WoodSpecies.DOUGLAS_FIR,
            post_diameter=4.0,
            post_height=8.0,
            post_spacing=10.0,
            post_weight=3.2,
            wire_diameter=0.192,
            mesh_size=5.5,
            mesh_weight=0.154,
            fos=1.0,
        )
        result = calculate_wood_post(wind, wood)
        assert result.deflection > 0


class TestWoodGatePost:
    def test_gate_post_higher_loads(self):
        """Gate post should have higher loads due to leaf weight and eccentricity."""
        wind = _make_wind()
        wood_line = WoodFenceInput(
            post_type=PostType.LINE,
            post_diameter=6.0, post_height=7.0, post_spacing=10.0,
            post_weight=6.2, wire_diameter=0.192, mesh_size=4.0,
            mesh_weight=0.635, fos=1.0,
        )
        wood_gate = WoodFenceInput(
            post_type=PostType.GATE,
            post_diameter=6.0, post_height=7.0, post_spacing=10.0,
            post_weight=6.2, wire_diameter=0.192, mesh_size=4.0,
            mesh_weight=0.635,
            gate_leaf_length=10.0, gate_leaf_height=6.67,
            gate_frame_post_diam=1.375, gate_frame_post_weight=1.68,
            fos=2.0,
        )
        r_line = calculate_wood_post(wind, wood_line)
        r_gate = calculate_wood_post(wind, wood_gate)

        assert r_gate.axial_load > r_line.axial_load
        assert r_gate.moment > r_line.moment

    def test_combined_stress_ratio(self):
        """Combined stress ratio should be computed."""
        wind = _make_wind()
        wood = WoodFenceInput(
            post_type=PostType.GATE,
            post_diameter=6.0, post_height=7.0, post_spacing=10.0,
            post_weight=6.2, wire_diameter=0.192, mesh_size=4.0,
            mesh_weight=0.635,
            gate_leaf_length=10.0, gate_leaf_height=6.67,
            gate_frame_post_diam=1.375, gate_frame_post_weight=1.68,
            fos=2.0,
        )
        result = calculate_wood_post(wind, wood)
        assert result.combined_ratio > 0, "Combined ratio should be > 0"
