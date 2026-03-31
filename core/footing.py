"""Footing depth calculations for fence posts.

Implements two methods:
1. IBC method (2009/2018 Eq. 18-1): D = 0.5A * {1 + [1 + (4.36*c/A)]^0.5}
2. ASTM F567 simplified: D = 24" + 3" * (H_ft - 4')

References:
    2009 IBC Section 1806, Eq. 18-1
    2018 IBC Section 1806
    ASTM F567 — Standard Practice for Installation of Chain Link Fence
    CLFMI WLG 2445 (2023) — Footing depth examples
    Spreadsheet: Fence Post Spacing.xlsx rows 35-51
"""

from __future__ import annotations

import math

from .models import FootingInput, FootingResult


def calculate_footing_depth_ibc(
    footing: FootingInput,
    wind_force_P: float,
) -> FootingResult:
    """Calculate required footing depth per IBC Eq. 18-1.

    D = 0.5A * {1 + [1 + (4.36 * c / A)]^0.5}
    A = 2.34 * P / (S1 * d)

    Where:
        P = resultant concentrated wind force applied to post (lb)
        S1 = allowable lateral soil bearing pressure (psf)
        d = diameter of post footing (ft)
        c = distance above top of footing at which P is applied
          = 0.55 * H (fence height) per CLFMI convention
        H = fence post height above top of footing (ft)

    Per IBC 1806.3.4: For isolated poles (including fence posts) not
    adversely affected by 1/2" ground motion from short-term lateral loads,
    lateral bearing pressures may be taken as 2x the presumptive values.

    Args:
        footing: Footing design parameters.
        wind_force_P: Wind force on the post in pounds.

    Returns:
        FootingResult with calculated and actual depths.
    """
    S1 = footing.soil_bearing_pressure  # psf
    d = footing.footing_diameter        # ft
    H = footing.fence_height            # ft
    c = 0.55 * H                        # ft (moment arm per CLFMI)

    if S1 <= 0 or d <= 0:
        return FootingResult(
            method=f"IBC ({footing.ibc_edition.value})",
            P_wind=wind_force_P,
            A_intermediate=0.0,
            c_arm=c,
            D_calc=0.0,
            D_actual=footing.actual_depth,
            is_adequate=False,
        )

    A = 2.34 * wind_force_P / (S1 * d)

    if A <= 0:
        D_calc = 0.0
    else:
        inner = 1.0 + (4.36 * c / A)
        D_calc = 0.5 * A * (1.0 + math.sqrt(inner))

    return FootingResult(
        method=f"IBC ({footing.ibc_edition.value}) Eq. 18-1",
        P_wind=wind_force_P,
        A_intermediate=A,
        c_arm=c,
        D_calc=D_calc,
        D_actual=footing.actual_depth,
        is_adequate=footing.actual_depth >= D_calc,
    )


def calculate_footing_depth_astm_f567(
    footing: FootingInput,
) -> FootingResult:
    """Calculate minimum footing depth per ASTM F567.

    D = 24" + 3" * (H_ft - 4')

    For fence heights over 4 ft, minimum depth is 24".
    For fence heights <= 4 ft, minimum depth is 24".

    Args:
        footing: Footing design parameters (uses fence_height).

    Returns:
        FootingResult with calculated depth in feet.
    """
    H = footing.fence_height  # ft

    if H <= 4.0:
        D_inches = 24.0
    else:
        D_inches = 24.0 + 3.0 * (H - 4.0)

    # Maximum embedment: 12 ft per CLFMI
    D_ft = min(D_inches / 12.0, 12.0)

    return FootingResult(
        method="ASTM F567",
        P_wind=0.0,
        A_intermediate=0.0,
        c_arm=0.0,
        D_calc=D_ft,
        D_actual=footing.actual_depth,
        is_adequate=footing.actual_depth >= D_ft,
    )


def calculate_footing_wind_force(
    shear: float,
    fence_height: float,
    fence_fabric_gap: float,
    post_od_ft: float,
    mesh_weight: float,
    post_spacing: float,
    Cf1: float,
    q_psf: float,
) -> float:
    """Calculate the concentrated wind force P for footing depth calculation.

    Per CLFMI WLG 2445:
    P = (1/Cf1) * ((S' - p/12)*(H - h) + H*p/12) * q

    Where:
        Cf1 = mesh size coefficient (reciprocal of solidity)
        S' = actual post spacing (ft)
        p = post diameter (in)
        H = fence height above ground (ft)
        h = gap between bottom of fabric and ground (ft)
        q = design wind pressure (psf)

    Args:
        shear: Wind shear force from post analysis (lb). Can be used directly
               as P if the CLFMI detailed formula is not needed.
        fence_height: Fence height (ft).
        fence_fabric_gap: Gap below fabric (ft).
        post_od_ft: Post outer diameter (ft).
        mesh_weight: Not used in this formula, reserved for future.
        post_spacing: Actual post spacing (ft).
        Cf1: Mesh size coefficient from CLFMI Table 13.
        q_psf: Design wind pressure (psf).

    Returns:
        Concentrated wind force P in pounds.
    """
    H = fence_height
    h = fence_fabric_gap
    p_ft = post_od_ft

    if Cf1 <= 0:
        return shear  # fallback to simple shear

    # CLFMI formula
    P = (1.0 / Cf1) * ((post_spacing - p_ft) * (H - h) + H * p_ft) * q_psf

    return P
