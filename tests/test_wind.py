"""Tests for wind load calculations.

Validates against spreadsheet values from Line Post.xlsx and Gate Post Basic.xlsx.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import ASCEEdition, ExposureCategory, WindInput
from core.wind import calculate_velocity_pressure, get_kz


class TestVelocityPressure:
    def test_line_post_qz(self):
        """Line Post.xlsx: V=100, Kz=0.85, Kzt=1.15, Kd=0.85 -> qz=21.27 psf."""
        wind = WindInput(
            asce_edition=ASCEEdition.ASCE_7_16,
            wind_speed=100.0,
            Kz=0.85,
            Kzt=1.15,
            Kd=0.85,
        )
        result = calculate_velocity_pressure(wind)
        assert abs(result.qz - 21.27) < 0.1, f"Expected ~21.27, got {result.qz:.2f}"

    def test_gate_post_qz(self):
        """Gate Post Basic.xlsx: V=100, Kz=0.85, Kzt=1.0, Kd=0.85 -> qz=18.50 psf."""
        wind = WindInput(
            asce_edition=ASCEEdition.ASCE_7_16,
            wind_speed=100.0,
            Kz=0.85,
            Kzt=1.0,
            Kd=0.85,
        )
        result = calculate_velocity_pressure(wind)
        expected = 0.00256 * 0.85 * 1.0 * 0.85 * 100**2  # = 18.4960
        assert abs(result.qz - expected) < 0.1, f"Expected ~{expected:.2f}, got {result.qz:.2f}"

    def test_asce_7_22_with_ke(self):
        """ASCE 7-22 includes Ke factor."""
        wind = WindInput(
            asce_edition=ASCEEdition.ASCE_7_22,
            wind_speed=100.0,
            Kz=0.85,
            Kzt=1.0,
            Kd=0.85,
            Ke=1.0,
        )
        result = calculate_velocity_pressure(wind)
        expected = 0.00256 * 0.85 * 1.0 * 0.85 * 1.0 * 100**2
        assert abs(result.qz - expected) < 0.01

    def test_asce_7_22_ke_effect(self):
        """Ke < 1.0 should reduce qz for high altitude."""
        wind = WindInput(
            asce_edition=ASCEEdition.ASCE_7_22,
            wind_speed=100.0,
            Kz=0.85,
            Kzt=1.0,
            Kd=0.85,
            Ke=0.95,
        )
        result = calculate_velocity_pressure(wind)
        expected = 0.00256 * 0.85 * 1.0 * 0.85 * 0.95 * 100**2
        assert abs(result.qz - expected) < 0.01


class TestKzLookup:
    def test_exposure_b_0ft(self):
        assert abs(get_kz(ExposureCategory.B, 0) - 0.57) < 0.01

    def test_exposure_c_15ft(self):
        assert abs(get_kz(ExposureCategory.C, 15) - 0.85) < 0.01

    def test_exposure_d_20ft(self):
        assert abs(get_kz(ExposureCategory.D, 20) - 1.08) < 0.01

    def test_interpolation(self):
        """Kz at 17.5 ft for Exposure B should be between 0.57 and 0.62."""
        kz = get_kz(ExposureCategory.B, 17.5)
        assert 0.57 <= kz <= 0.62
