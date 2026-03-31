"""Tests for chain link post calculations.

Validates against Line Post.xlsx, Pull post.xlsx, Gate Post Basic.xlsx.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import (
    ASCEEdition,
    ChainLinkInput,
    PostType,
    SteelPipeSection,
    SteelPostGroup,
    WindInput,
)
from core.chain_link import calculate_chain_link_post


def _make_wind_line_post():
    """Wind inputs matching Line Post.xlsx."""
    return WindInput(
        asce_edition=ASCEEdition.ASCE_7_16,
        wind_speed=100.0,
        Kz=0.85,
        Kzt=1.15,
        Kd=0.85,
        G=0.85,
        Cf=1.3,
    )


def _make_wind_gate_post():
    """Wind inputs matching Gate Post Basic.xlsx."""
    return WindInput(
        asce_edition=ASCEEdition.ASCE_7_16,
        wind_speed=100.0,
        Kz=0.85,
        Kzt=1.0,
        Kd=0.85,
        G=0.85,
        Cf=1.3,
    )


class TestLinePost:
    def test_loads(self):
        """Line Post.xlsx: 2-3/8" post, 7' height, 10' spacing, FoS=1.0 for comparison."""
        wind = _make_wind_line_post()
        cl = ChainLinkInput(
            post_type=PostType.LINE,
            post_od=2.375,
            post_height=7.0,
            post_spacing=10.0,
            post_weight=3.65,
            wire_diameter=0.192,
            mesh_size=4.0,
            mesh_weight=0.154,
            fos=1.0,  # no FoS for raw comparison
        )
        result = calculate_chain_link_post(wind, cl)

        # Axial = 0.154*7*10 + 3.65*7 = 10.78 + 25.55 = 36.33 lb
        assert abs(result.axial_load - 36.33) < 1.0, f"Axial: {result.axial_load:.2f}"

        # Shear and moment depend on the exact projected area calculation
        assert result.shear > 0, "Shear should be positive"
        assert result.moment > 0, "Moment should be positive"

    def test_fos_applied(self):
        """FoS should multiply all loads."""
        wind = _make_wind_line_post()
        cl_no_fos = ChainLinkInput(
            post_type=PostType.LINE, post_od=2.375, post_height=7.0,
            post_spacing=10.0, post_weight=3.65, wire_diameter=0.192,
            mesh_size=4.0, mesh_weight=0.154, fos=1.0,
        )
        cl_fos = ChainLinkInput(
            post_type=PostType.LINE, post_od=2.375, post_height=7.0,
            post_spacing=10.0, post_weight=3.65, wire_diameter=0.192,
            mesh_size=4.0, mesh_weight=0.154, fos=1.5,
        )
        r1 = calculate_chain_link_post(wind, cl_no_fos)
        r2 = calculate_chain_link_post(wind, cl_fos)

        assert abs(r2.axial_load - r1.axial_load * 1.5) < 0.1
        assert abs(r2.shear - r1.shear * 1.5) < 0.1
        assert abs(r2.moment - r1.moment * 1.5) < 0.1


class TestGatePost:
    def test_gate_adds_leaf_loads(self):
        """Gate post should have higher axial due to gate leaf."""
        wind = _make_wind_gate_post()
        cl_line = ChainLinkInput(
            post_type=PostType.LINE, post_od=4.0, post_height=7.0,
            post_spacing=10.0, post_weight=9.12, wire_diameter=0.192,
            mesh_size=4.0, mesh_weight=0.154, fos=1.0,
        )
        cl_gate = ChainLinkInput(
            post_type=PostType.GATE, post_od=4.0, post_height=7.0,
            post_spacing=10.0, post_weight=9.12, wire_diameter=0.192,
            mesh_size=4.0, mesh_weight=0.154,
            gate_leaf_length=11.75, gate_leaf_height=6.67,
            gate_frame_post_diam=1.375, gate_frame_post_weight=1.68,
            fos=1.0,
        )
        r_line = calculate_chain_link_post(wind, cl_line)
        r_gate = calculate_chain_link_post(wind, cl_gate)

        assert r_gate.axial_load > r_line.axial_load, "Gate axial should be higher"
        assert r_gate.moment > r_line.moment, "Gate moment should include eccentricity"


class TestSectionAdequacy:
    def test_adequate_section(self):
        """A large section should pass."""
        wind = _make_wind_line_post()
        cl = ChainLinkInput(
            post_type=PostType.LINE, post_od=2.375, post_height=7.0,
            post_spacing=10.0, post_weight=3.65, wire_diameter=0.192,
            mesh_size=4.0, mesh_weight=0.154, fos=1.5,
        )
        section = SteelPipeSection(
            trade_size="4", group=SteelPostGroup.GROUP_IA_REGULAR,
            OD=4.0, ID=3.548, Sx=2.39, Ix=4.79, Fy=30.0,
            Mallow=3.95, Em=29000.0, weight=9.12,
        )
        result = calculate_chain_link_post(wind, cl, section)
        assert result.is_adequate, f"Should be adequate, ratio={result.moment_ratio:.3f}"
