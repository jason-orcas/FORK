"""Compute lateral bearing pressure S1 from a soil profile for footing design.

Bridges SPORK-style soil profiles (layered SoilLayer objects with SPT data
and engineering properties) into the single S1 value that FORK's IBC Eq. 18-1
footing depth calculation requires.

Two derivation methods are supported, user-selectable on the Footing page:

1. ENGINEERING properties (Rankine/Broms):
   - Sand/gravel: S1 = Kp * gamma_eff  where Kp = tan^2(45 + phi/2)
   - Clay/silt:   S1 derived from 9*cu (Broms short-pile ultimate resistance)

2. IBC_TABLE lookup:
   - Uses the IBC 2018 Table 1806.2 presumptive values mapped from SoilType.

The profile is weighted-averaged over the footing embedment depth to produce
a single S1 value in psf/ft that can be fed directly to
`calculate_footing_depth_ibc()` as `footing.soil_bearing_pressure`.
"""

from __future__ import annotations

import math
from enum import Enum

from .soil import SoilLayer, SoilProfile, SoilType

# IBC 2018 / IBC 2009 Table 1806.2 — presumptive lateral bearing values (psf/ft).
# These are the same values baked into FORK's existing data/ibc_soil_table.json.
IBC_1806_2_LATERAL: dict[SoilType, float] = {
    SoilType.GRAVEL: 200.0,   # Sandy gravel / gravel (GW, GP)
    SoilType.SAND: 150.0,     # Sand, silty sand, clayey sand (SW, SP, SM, SC)
    SoilType.SILT: 100.0,     # Silt (ML, MH)
    SoilType.CLAY: 100.0,     # Clay, sandy clay, silty clay (CL, CH)
    SoilType.ORGANIC: 50.0,   # Not in IBC — conservative placeholder
}


class S1DerivationMethod(str, Enum):
    """User-selectable method for computing S1 from soil properties."""
    ENGINEERING = "Engineering properties"
    IBC_TABLE = "IBC Table 1806.2"


def compute_s1_engineering(layer: SoilLayer) -> float:
    """Compute S1 (psf/ft of depth) for a single layer from soil properties.

    Cohesionless (sand/gravel):
        Rankine passive pressure gradient:
        Kp = tan^2(45 + phi/2)
        S1 = Kp * gamma_eff

    Cohesive (clay/silt):
        Broms short-pile ultimate lateral resistance per unit depth is
        approximately 9 * cu (in units of psf). Dividing by a nominal 10 ft
        embedment converts that total capacity to a per-foot gradient that
        can be combined with the IBC 18-1 formula.

    Organic: conservative 50 psf/ft.

    Args:
        layer: A SoilLayer with either explicit phi/c_u or SPT data for
               correlation-based estimation.

    Returns:
        S1 in psf per foot of depth below grade.
    """
    if layer.soil_type in (SoilType.SAND, SoilType.GRAVEL):
        phi_deg = layer.get_phi(0)
        phi_rad = math.radians(phi_deg)
        Kp = math.tan(math.pi / 4.0 + phi_rad / 2.0) ** 2
        gamma_eff = layer.gamma_effective
        return Kp * gamma_eff

    if layer.soil_type in (SoilType.CLAY, SoilType.SILT):
        cu = layer.get_cu()
        # Broms ultimate short-pile lateral resistance per unit width ~ 9*cu
        # Express as a per-foot gradient (nominal 10 ft reference) and clamp
        # to a reasonable upper bound to prevent very stiff clays from
        # producing unrealistic footing reductions.
        return min(9.0 * cu / 10.0, 500.0)

    # Organic / unknown
    return 50.0


def compute_s1_ibc(layer: SoilLayer) -> float:
    """Look up S1 (psf/ft) from IBC Table 1806.2 by SoilType."""
    return IBC_1806_2_LATERAL.get(layer.soil_type, 100.0)


def weighted_s1_for_footing(
    profile: SoilProfile,
    footing_depth_ft: float,
    method: S1DerivationMethod,
) -> float:
    """Compute a single weighted-average S1 over the footing embedment depth.

    Iterates through layers in the profile, accumulates each layer's S1
    weighted by the portion of the layer within the footing range, and
    returns the weighted mean. Returns psf/ft — feed this directly to
    `FootingInput.soil_bearing_pressure` for the IBC Eq. 18-1 calculation.

    Args:
        profile: SoilProfile with at least one layer.
        footing_depth_ft: Embedment depth below grade (ft).
        method: S1DerivationMethod.ENGINEERING or IBC_TABLE.

    Returns:
        Weighted-average S1 (psf/ft). Returns 100.0 as a conservative
        fallback if the profile is empty or the depth is invalid.
    """
    if not profile.layers or footing_depth_ft <= 0:
        return 100.0

    derive = (
        compute_s1_engineering
        if method == S1DerivationMethod.ENGINEERING
        else compute_s1_ibc
    )

    total_thickness = 0.0
    weighted_sum = 0.0

    for layer in profile.layers:
        top = layer.top_depth
        bot = min(layer.bottom_depth, footing_depth_ft)
        if bot <= top:
            continue
        thickness = bot - top
        s1 = derive(layer)
        weighted_sum += s1 * thickness
        total_thickness += thickness
        if bot >= footing_depth_ft:
            break

    if total_thickness <= 0:
        return 100.0

    return weighted_sum / total_thickness


def describe_s1_derivation(
    profile: SoilProfile,
    footing_depth_ft: float,
    method: S1DerivationMethod,
) -> list[dict]:
    """Return per-layer breakdown of how S1 was computed, for UI display.

    Useful for showing the engineer exactly which layers contributed to
    the final S1 and what each layer's computed value was.

    Returns:
        List of dicts with keys: top_ft, bot_ft, thickness_ft, soil_type,
        s1_psf_per_ft, weight (fraction of footing depth).
    """
    if not profile.layers or footing_depth_ft <= 0:
        return []

    derive = (
        compute_s1_engineering
        if method == S1DerivationMethod.ENGINEERING
        else compute_s1_ibc
    )

    rows = []
    for layer in profile.layers:
        top = layer.top_depth
        bot = min(layer.bottom_depth, footing_depth_ft)
        if bot <= top:
            continue
        thickness = bot - top
        s1 = derive(layer)
        rows.append({
            "top_ft": top,
            "bot_ft": bot,
            "thickness_ft": thickness,
            "soil_type": layer.soil_type.value,
            "description": layer.description,
            "s1_psf_per_ft": s1,
            "weight_fraction": thickness / footing_depth_ft,
        })
        if bot >= footing_depth_ft:
            break

    return rows
