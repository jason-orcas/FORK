"""Tests for footing depth calculations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import FootingInput, IBCEdition
from core.footing import calculate_footing_depth_ibc, calculate_footing_depth_astm_f567


class TestIBCFooting:
    def test_basic_calculation(self):
        """Verify IBC footing depth formula produces reasonable results."""
        footing = FootingInput(
            ibc_edition=IBCEdition.IBC_2018,
            soil_bearing_pressure=200.0,  # psf
            footing_diameter=1.5,          # ft
            fence_height=7.0,              # ft
            actual_depth=4.0,              # ft
        )
        # Typical wind force on a 7' chain link fence
        P = 150.0  # lb (approximate)
        result = calculate_footing_depth_ibc(footing, P)

        assert result.D_calc > 0, "Calculated depth should be positive"
        assert result.c_arm == 0.55 * 7.0, f"c should be {0.55*7.0}"
        assert result.method.startswith("IBC")

    def test_adequacy_check(self):
        """Actual depth >= calculated depth should pass."""
        footing = FootingInput(
            soil_bearing_pressure=200.0,
            footing_diameter=1.5,
            fence_height=7.0,
            actual_depth=10.0,  # very deep
        )
        result = calculate_footing_depth_ibc(footing, 100.0)
        assert result.is_adequate

    def test_inadequate_depth(self):
        """Shallow footing with large wind force should fail."""
        footing = FootingInput(
            soil_bearing_pressure=100.0,  # poor soil
            footing_diameter=1.0,
            fence_height=10.0,
            actual_depth=2.0,  # very shallow
        )
        result = calculate_footing_depth_ibc(footing, 500.0)
        assert not result.is_adequate


class TestASTMF567Footing:
    def test_4ft_fence(self):
        """4' fence: D = 24" = 2.0 ft."""
        footing = FootingInput(fence_height=4.0, actual_depth=2.0)
        result = calculate_footing_depth_astm_f567(footing)
        assert abs(result.D_calc - 2.0) < 0.01

    def test_6ft_fence(self):
        """6' fence: D = 24 + 3*(6-4) = 30" = 2.5 ft."""
        footing = FootingInput(fence_height=6.0, actual_depth=3.0)
        result = calculate_footing_depth_astm_f567(footing)
        assert abs(result.D_calc - 2.5) < 0.01

    def test_8ft_fence(self):
        """8' fence: D = 24 + 3*(8-4) = 36" = 3.0 ft."""
        footing = FootingInput(fence_height=8.0, actual_depth=3.0)
        result = calculate_footing_depth_astm_f567(footing)
        assert abs(result.D_calc - 3.0) < 0.01
