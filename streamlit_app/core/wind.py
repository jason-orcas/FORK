"""Wind load calculations per ASCE 7-16 and ASCE 7-22.

Primary function: calculate_velocity_pressure() computes qz (psf) from wind
parameters. Supports both ASCE 7-16 (without Ke) and ASCE 7-22 (with Ke).

References:
    ASCE 7-16 Eq. 26.10-1: qz = 0.00256 * Kz * Kzt * Kd * V^2
    ASCE 7-22 Eq. 26.10-1: qz = 0.00256 * Kz * Kzt * Kd * Ke * V^2
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import ASCEEdition, ExposureCategory, WindInput, WindResult

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def calculate_velocity_pressure(wind: WindInput) -> WindResult:
    """Calculate velocity pressure qz per ASCE 7.

    Args:
        wind: WindInput with all wind parameters.

    Returns:
        WindResult with qz in psf and formula reference.
    """
    qz = 0.00256 * wind.Kz * wind.Kzt * wind.Kd * wind.wind_speed ** 2

    if wind.asce_edition == ASCEEdition.ASCE_7_22:
        qz *= wind.Ke
        formula = (
            f"qz = 0.00256 x Kz x Kzt x Kd x Ke x V^2 "
            f"= 0.00256 x {wind.Kz} x {wind.Kzt} x {wind.Kd} x {wind.Ke} x {wind.wind_speed}^2 "
            f"= {qz:.2f} psf (ASCE 7-22 Eq. 26.10-1)"
        )
    else:
        formula = (
            f"qz = 0.00256 x Kz x Kzt x Kd x V^2 "
            f"= 0.00256 x {wind.Kz} x {wind.Kzt} x {wind.Kd} x {wind.wind_speed}^2 "
            f"= {qz:.2f} psf (ASCE 7-16 Eq. 26.10-1)"
        )

    return WindResult(
        qz=qz,
        asce_edition=wind.asce_edition,
        formula_used=formula,
    )


def get_kz(
    exposure: ExposureCategory,
    height_ft: float,
) -> float:
    """Look up velocity pressure exposure coefficient Kz from ASCE 7 Table 26.10-1.

    Uses linear interpolation between table heights.

    Args:
        exposure: Wind exposure category (B, C, or D).
        height_ft: Height above ground level in feet.

    Returns:
        Kz value (dimensionless).
    """
    with open(_DATA_DIR / "kz_table.json", encoding="utf-8") as f:
        data = json.load(f)

    heights = data["heights_ft"]
    values = data[exposure.value]

    if height_ft <= heights[0]:
        return values[0]
    if height_ft >= heights[-1]:
        return values[-1]

    for i in range(len(heights) - 1):
        if heights[i] <= height_ft <= heights[i + 1]:
            frac = (height_ft - heights[i]) / (heights[i + 1] - heights[i])
            return values[i] + frac * (values[i + 1] - values[i])

    return values[0]


def calculate_design_wind_force(
    qz: float,
    Kd: float,
    G: float,
    Cf: float,
    projected_area_sqft: float,
) -> float:
    """Calculate design wind force per ASCE 7-22 Eq. 29.3-1.

    F = qz * Kd * G * Cf * As

    Note: Kd is already included in qz if using calculate_velocity_pressure(),
    so pass Kd=1.0 if qz already includes directionality. The CLFMI guide
    applies Kd separately in the force equation, so this function allows both.

    Args:
        qz: Velocity pressure (psf).
        Kd: Directionality factor (use 1.0 if already in qz).
        G: Gust-effect factor.
        Cf: Force coefficient.
        projected_area_sqft: Projected area normal to wind (sq ft).

    Returns:
        Wind force F in pounds.
    """
    return qz * Kd * G * Cf * projected_area_sqft
