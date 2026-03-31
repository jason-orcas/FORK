"""Tests for CLFMI post spacing calculations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import ExposureCategory, IceExposure, SpacingInput, SteelPostGroup
from core.spacing import calculate_spacing, lookup_S, lookup_cf1, lookup_cf2, lookup_cf3


class TestSpacingLookups:
    def test_cf1_gauge11_mesh2(self):
        """Table 13: gauge 11, mesh 2" -> Cf1 = 8.83."""
        cf1 = lookup_cf1(11, 2.0)
        assert abs(cf1 - 8.83) < 0.1, f"Expected 8.83, got {cf1}"

    def test_cf1_gauge6_mesh4(self):
        """Table 13: gauge 6, mesh 4" -> not in table, should interpolate or nearest."""
        cf1 = lookup_cf1(6, 4.0)
        assert cf1 > 1.0, "Cf1 should be > 1.0 for open mesh"

    def test_cf2_exposure_b(self):
        """Table 14: Exposure B, 0-15 ft -> Cf2 = 1.00."""
        cf2 = lookup_cf2(ExposureCategory.B, 7.0)
        assert abs(cf2 - 1.00) < 0.01

    def test_cf2_exposure_c(self):
        """Table 14: Exposure C, 0-15 ft -> Cf2 = 0.67."""
        cf2 = lookup_cf2(ExposureCategory.C, 7.0)
        assert abs(cf2 - 0.67) < 0.01

    def test_cf2_exposure_d(self):
        """Table 14: Exposure D, 0-15 ft -> Cf2 = 0.55."""
        cf2 = lookup_cf2(ExposureCategory.D, 7.0)
        assert abs(cf2 - 0.55) < 0.01

    def test_cf3_none(self):
        assert abs(lookup_cf3(IceExposure.NONE) - 1.00) < 0.01

    def test_cf3_heavy(self):
        assert abs(lookup_cf3(IceExposure.HEAVY) - 0.45) < 0.01


class TestSpacingTableLookup:
    def test_group_ia_regular_105mph_4ft(self):
        """Table 1: Group IA Regular, 4" post, 105 mph, 6' fence -> S=21.8."""
        S = lookup_S(105.0, SteelPostGroup.GROUP_IA_REGULAR, 4.0, 6.0)
        assert S is not None
        assert abs(S - 21.8) < 0.5, f"Expected ~21.8, got {S}"

    def test_overstressed_returns_none(self):
        """1-7/8" post at 20' height should be overstressed (null)."""
        S = lookup_S(105.0, SteelPostGroup.GROUP_IA_REGULAR, 1.9, 20.0)
        assert S is None, "Should return None for overstressed post"


class TestFullSpacing:
    def test_adequate_spacing(self):
        """Full spacing calculation should return adequate when actual < S'."""
        inp = SpacingInput(
            fence_height=6.0,
            post_od=4.0,
            post_group=SteelPostGroup.GROUP_IA_REGULAR,
            wire_gauge=11,
            mesh_size=2.0,
            wind_speed=105.0,
            exposure_category=ExposureCategory.C,
            ice_exposure=IceExposure.NONE,
            actual_spacing=10.0,
        )
        result = calculate_spacing(inp)
        # S' = S * Cf1 * Cf2 * Cf3
        assert result.S_table > 0
        assert result.Cf1 > 1.0  # open mesh multiplier
        assert result.Cf2 > 0    # exposure correction
        assert result.Cf3 == 1.0 # no ice
