"""Tests for section property lookups."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import SteelPostGroup, WoodSpecies
from core.sections import (
    compute_wood_section,
    get_steel_pipe_section,
    get_wood_design_values,
    load_steel_pipe_sections,
)


class TestSteelSections:
    def test_load_all_groups(self):
        """Should load sections for all 4 post groups."""
        sections = load_steel_pipe_sections()
        assert len(sections) == 4

    def test_group_ia_regular_2375(self):
        """Group IA Regular, 2-3/8" -> Sx=0.56, Mallow=0.93."""
        s = get_steel_pipe_section("2-3/8", SteelPostGroup.GROUP_IA_REGULAR)
        assert s is not None
        assert abs(s.Sx - 0.56) < 0.01
        assert abs(s.Mallow - 0.93) < 0.01
        assert abs(s.Fy - 30.0) < 0.01

    def test_group_ic_4inch(self):
        """Group IC, 4" -> Mallow=4.90."""
        s = get_steel_pipe_section("4", SteelPostGroup.GROUP_IC)
        assert s is not None
        assert abs(s.Mallow - 4.90) < 0.01

    def test_nonexistent_returns_none(self):
        s = get_steel_pipe_section("99", SteelPostGroup.GROUP_IA_REGULAR)
        assert s is None


class TestWoodSections:
    def test_douglas_fir_values(self):
        """NDS 2018 Table 6a: Douglas Fir reference values."""
        dv = get_wood_design_values(WoodSpecies.DOUGLAS_FIR)
        assert dv.Fc == 1300
        assert dv.Fb == 2050
        assert dv.Fv == 160
        assert dv.E == 1_700_000
        assert dv.Emin == 690_000

    def test_round_section_properties(self):
        """4" diameter: A=12.57, Ix=12.57, Sx=6.28."""
        import math
        s = compute_wood_section(4.0)
        assert abs(s.area - math.pi * 4.0) < 0.01  # pi*r^2 = pi*4
        assert abs(s.Ix - math.pi * 4.0) < 0.01    # pi*r^4/4 = pi*(2)^4/4 = 4*pi
        assert abs(s.Sx - math.pi * 2.0) < 0.01    # pi*r^3/4 = pi*(2)^3/4 = 2*pi
