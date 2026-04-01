"""Wood fence post design calculations per NDS 2018.

Computes axial, shear, and moment loads, then performs full NDS stress analysis
with adjustment factors (Cd, Ct, Cct, Cf, Cp, Ccs, Cls, Cb) for round timber
posts.

References:
    2018 NDS — National Design Specification for Wood Construction
    NDS Supplement Table 6a — Round Timber Poles and Piles
    Spreadsheets: Wood Fence_Line Post_DG.xlsx, Wood Fence_Gate Post_DG.xlsx,
                  Wood Fence_Pull Post_DG.xlsx
"""

from __future__ import annotations

import math

from .models import (
    PostType,
    WindInput,
    WoodDesignValues,
    WoodFenceInput,
    WoodSectionProperties,
    WoodStressResult,
)
from .sections import compute_wood_section, get_wood_design_values
from .wind import calculate_velocity_pressure


def calculate_wood_post(
    wind: WindInput,
    wood: WoodFenceInput,
) -> WoodStressResult:
    """Full wood post NDS 2018 analysis.

    Calculates loads, applied stresses, NDS adjustment factors,
    adjusted allowable stresses, stress ratios, and deflection.

    Args:
        wind: Wind load parameters.
        wood: Wood fence geometry and material inputs.

    Returns:
        WoodStressResult with all computed values.
    """
    wind_result = calculate_velocity_pressure(wind)
    qz = wind_result.qz

    section = compute_wood_section(wood.post_diameter)
    design_values = get_wood_design_values(wood.species)

    # --- Load calculations ---
    axial = _calc_axial(wood)
    shear = _calc_shear(qz, wind, wood)
    moment = _calc_moment(shear, wood)

    # Apply factor of safety
    axial *= wood.fos
    shear *= wood.fos
    moment *= wood.fos

    # --- Applied stresses ---
    fc = axial / section.area if section.area > 0 else 0.0          # psi
    fb = moment * 12.0 / section.Sx if section.Sx > 0 else 0.0     # lb-ft * 12 in/ft / in^3 = psi
    fv = shear / section.area if section.area > 0 else 0.0          # psi (conservative; exact = 4V/3A for round)
    fc_perp = 0.0  # bearing stress — computed if needed for base plate

    # --- NDS adjustment factors ---
    Cd = wood.Cd if wood.Cd is not None else _default_Cd(wind)
    Ct = wood.Ct
    Cct = wood.Cct
    Cf = 1.0       # size factor — 1.0 for round timber per NDS
    Ccs = 1.1      # round section factor per NDS 6.3.11
    Cls = 1.0      # lateral stability factor — 1.0 for posts braced by fabric
    Cb = 1.0       # bearing area factor — 1.0 default

    # Column stability factor Cp (NDS 3.7.1)
    Cp = _calc_Cp(
        Fc=design_values.Fc,
        Emin=design_values.Emin,
        diameter=wood.post_diameter,
        height_ft=wood.post_height,
        Cd=Cd, Ct=Ct, Cct=Cct, Ccs=Ccs, Cls=Cls,
    )

    # --- Adjusted allowable stresses ---
    Fc_prime = design_values.Fc * Cd * Ct * Cct * Cp * Ccs * Cls   # NDS 2018 Table 6.3.1
    Fc_perp_prime = design_values.Fc_perp * Ct * Cct * Cb
    Fb_prime = design_values.Fb * Cd * Ct * Cct * Cf * Cls          # NDS 6.3.5
    Fv_prime = design_values.Fv * Cd * Ct * Cct                     # NDS 6.3.9

    # --- Stress ratios ---
    comp_ratio = fc / Fc_prime if Fc_prime > 0 else 0.0
    bend_ratio = fb / Fb_prime if Fb_prime > 0 else 0.0
    shear_ratio = fv / Fv_prime if Fv_prime > 0 else 0.0

    # Combined stress ratio per NDS 3.9.2:
    # (fc/Fc')^2 + fb / (Fb' * (1 - fc/FcE))
    FcE = _calc_FcE(design_values.Emin, wood.post_diameter, wood.post_height)
    if FcE > 0 and (1.0 - fc / FcE) > 0:
        combined = (fc / Fc_prime) ** 2 + fb / (Fb_prime * (1.0 - fc / FcE))
    else:
        combined = comp_ratio ** 2 + bend_ratio

    # --- Deflection ---
    deflection = _calc_deflection(
        shear=shear,
        height_ft=wood.post_height,
        Emin=design_values.Emin,
        Ix=section.Ix,
    )

    is_adequate = combined <= 1.0 and shear_ratio <= 1.0

    return WoodStressResult(
        post_type=wood.post_type,
        axial_load=axial,
        shear=shear,
        moment=moment,
        fc=fc,
        fc_perp=fc_perp,
        fb=fb,
        fv=fv,
        Fc_prime=Fc_prime,
        Fc_perp_prime=Fc_perp_prime,
        Fb_prime=Fb_prime,
        Fv_prime=Fv_prime,
        Cp=Cp,
        Cd=Cd,
        Ct=Ct,
        Cct=Cct,
        Cf=Cf,
        Ccs=Ccs,
        Cls=Cls,
        Cb=Cb,
        compression_ratio=comp_ratio,
        bending_ratio=bend_ratio,
        shear_ratio=shear_ratio,
        combined_ratio=combined,
        deflection=deflection,
        is_adequate=is_adequate,
    )


# ---------------------------------------------------------------------------
# Load calculations
# ---------------------------------------------------------------------------

def _calc_axial(wood: WoodFenceInput) -> float:
    """Calculate axial (gravity) load on wood fence post (lb)."""
    H = wood.post_height
    S = wood.post_spacing

    axial = wood.mesh_weight * H * S + wood.post_weight * H

    if wood.post_type == PostType.GATE and wood.gate_leaf_length > 0:
        gate_mesh = wood.mesh_weight * wood.gate_leaf_height * wood.gate_leaf_length
        gate_perimeter = 2.0 * (wood.gate_leaf_height + wood.gate_leaf_length)
        gate_frame = wood.gate_frame_post_weight * gate_perimeter
        axial += gate_mesh + gate_frame

    return axial


def _calc_shear(qz: float, wind: WindInput, wood: WoodFenceInput) -> float:
    """Calculate wind shear force on wood fence post (lb)."""
    H = wood.post_height
    S = wood.post_spacing
    post_diam_ft = wood.post_diameter / 12.0

    post_area = post_diam_ft * H
    solidity = 2.0 * wood.wire_diameter / wood.mesh_size if wood.mesh_size > 0 else 1.0
    mesh_area = H * S * solidity
    total_area = post_area + mesh_area

    shear = qz * wind.G * wind.Cf * total_area
    return shear


def _calc_moment(shear: float, wood: WoodFenceInput) -> float:
    """Calculate moment at post base (lb-ft).

    Line posts: RESTRICTED head (fabric/rail provides lateral support)
        M = V * H / 2 (propped cantilever)
    Pull/Gate posts: FREE head (no lateral restraint at top)
        M = V * H * 2/3 (cantilever)
    """
    H = wood.post_height
    if wood.post_type == PostType.LINE:
        moment = shear * H / 2.0
    else:
        moment = shear * H * 2.0 / 3.0

    if wood.post_type == PostType.GATE and wood.gate_leaf_length > 0:
        gate_mesh_wt = wood.mesh_weight * wood.gate_leaf_height * wood.gate_leaf_length
        gate_perimeter = 2.0 * (wood.gate_leaf_height + wood.gate_leaf_length)
        gate_frame_wt = wood.gate_frame_post_weight * gate_perimeter
        gate_dead = gate_mesh_wt + gate_frame_wt
        eccentricity = wood.gate_leaf_length / 2.0
        moment += gate_dead * eccentricity

    return moment


# ---------------------------------------------------------------------------
# NDS adjustment factors
# ---------------------------------------------------------------------------

def _default_Cd(wind: WindInput) -> float:
    """Default load duration factor Cd.

    Per NDS 2018 Table 2.3.2:
    - Wind loads: Cd = 1.6
    - Normal (10 yr): Cd = 1.0
    - Permanent: Cd = 0.9

    For fence design controlled by wind, Cd = 1.6 is appropriate.
    """
    return 1.6


def _calc_FcE(Emin: float, diameter: float, height_ft: float) -> float:
    """Calculate Euler critical buckling stress FcE per NDS 3.7.1.

    FcE = 0.822 * Emin / (Le/d)^2

    For round timber: Le = effective length (assume Ke=1.0 for cantilever
    with bracing from fence fabric), d = diameter.

    NDS uses Le/d for round sections.
    """
    Le = height_ft * 12.0  # in (effective length)
    if diameter <= 0:
        return 0.0
    slenderness = Le / diameter
    if slenderness <= 0:
        return 0.0
    return 0.822 * Emin / (slenderness ** 2)


def _calc_Cp(
    Fc: float,
    Emin: float,
    diameter: float,
    height_ft: float,
    Cd: float,
    Ct: float,
    Cct: float,
    Ccs: float,
    Cls: float,
) -> float:
    """Calculate column stability factor Cp per NDS 3.7.1.

    Cp = (1 + FcE/Fc*) / (2c) - sqrt[((1 + FcE/Fc*) / (2c))^2 - FcE/(Fc* * c)]

    Where:
        FcE = 0.822 * Emin / (Le/d)^2
        Fc* = Fc * Cd * Ct * Cct * Ccs * Cls  (all factors except Cp)
        c = 0.85 for round timber (sawn lumber = 0.80, glulam = 0.90)
    """
    c = 0.85  # round timber

    Fc_star = Fc * Cd * Ct * Cct * Ccs * Cls
    if Fc_star <= 0:
        return 1.0

    FcE = _calc_FcE(Emin, diameter, height_ft)
    if FcE <= 0:
        return 0.0

    ratio = FcE / Fc_star
    term1 = (1.0 + ratio) / (2.0 * c)
    term2 = term1 ** 2 - ratio / c

    if term2 < 0:
        return 0.0

    Cp = term1 - math.sqrt(term2)
    return max(0.0, min(1.0, Cp))


# ---------------------------------------------------------------------------
# Deflection
# ---------------------------------------------------------------------------

def _calc_deflection(
    shear: float,
    height_ft: float,
    Emin: float,
    Ix: float,
) -> float:
    """Calculate cantilever deflection at post top (in).

    For a cantilever with uniform load w:
        delta = w * L^4 / (8 * E * I)

    Where w = distributed wind load = shear / height (lb/in per inch).
    Matches the spreadsheet formula: delta = wL^4 / (8*E*I)

    Source: Wood Fence_Line Post_DG.xlsx
    """
    L = height_ft * 12.0  # in
    if L <= 0 or Emin <= 0 or Ix <= 0:
        return 0.0

    w = shear / L  # lb/in (distributed load per unit length)
    delta = w * L ** 4 / (8.0 * Emin * Ix)
    return delta
