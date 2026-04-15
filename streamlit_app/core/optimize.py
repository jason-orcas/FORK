"""Fence post optimization tool.

Sweeps all available post groups/sizes (chain link) or common diameters (wood)
for given site conditions, returning ranked results sorted by lightest post
weight and maximum allowable spacing.

Follows the SPORK exhaustive brute-force pattern.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .models import (
    ASCEEdition,
    ChainLinkInput,
    ExposureCategory,
    FootingInput,
    IBCEdition,
    IceExposure,
    PostType,
    SteelPostGroup,
    WindInput,
    WoodFenceInput,
    WoodSpecies,
)
from .chain_link import calculate_chain_link_post
from .footing import calculate_footing_depth_ibc
from .sections import load_steel_pipe_sections, get_wood_design_values, compute_wood_section
from .spacing import lookup_S, lookup_cf1, lookup_cf2, lookup_cf3
from .wood import calculate_wood_post


@dataclass
class OptimizationResult:
    """Single row in the optimization results table."""
    fence_type: str = "chain_link"
    post_group: str = ""
    trade_size: str = ""
    post_od: float = 0.0
    weight_plf: float = 0.0
    Mallow_kipft: float = 0.0
    max_spacing: float = 0.0       # S' for chain link, user spacing for wood
    moment_ratio: float = 0.0      # chain link
    combined_ratio: float = 0.0    # wood
    shear_ratio: float = 0.0       # wood
    deflection_in: float = 0.0     # wood
    footing_depth_ft: float = 0.0
    passes: bool = False
    is_optimal: bool = False
    failure_reason: str = ""       # human-readable explanation if passes=False


def optimize_chain_link(
    wind: WindInput,
    fence_height: float,
    wire_gauge: int,
    mesh_size: float,
    mesh_weight: float,
    exposure: ExposureCategory,
    ice: IceExposure,
    footing_input: FootingInput,
    fos: float = 1.5,
) -> list[OptimizationResult]:
    """Sweep all steel post groups and sizes for chain link fence.

    For each post: lookup max spacing from CLFMI tables, check moment
    adequacy, compute required footing depth. Returns all combinations
    sorted by weight (ascending) then max spacing (descending).

    Args:
        wind: Wind load parameters.
        fence_height: Fence height above ground (ft).
        wire_gauge: Wire gauge number.
        mesh_size: Mesh opening size (in).
        mesh_weight: Mesh fabric weight (psf).
        exposure: Wind exposure category for Cf2.
        ice: Ice exposure for Cf3.
        footing_input: Footing design parameters (soil bearing, diameter).
        fos: Factor of safety (default 1.5 per CLFMI).

    Returns:
        List of OptimizationResult, sorted by weight then spacing.
    """
    all_sections = load_steel_pipe_sections()
    Cf1 = lookup_cf1(wire_gauge, mesh_size)
    Cf2 = lookup_cf2(exposure, fence_height)
    Cf3 = lookup_cf3(ice)

    # Wire diameter lookup
    gauge_diameters = {
        5: 0.207, 6: 0.192, 8: 0.162, 9: 0.148,
        10: 0.135, 11: 0.120, 12: 0.113, 14: 0.080,
    }
    wire_diam = gauge_diameters.get(wire_gauge, 0.12)

    results: list[OptimizationResult] = []

    for group_name, sections in all_sections.items():
        group_enum = SteelPostGroup(group_name)
        for section in sections:
            # Step 1: CLFMI spacing lookup
            S = lookup_S(wind.wind_speed, group_enum, section.OD, fence_height)
            if S is None:
                # Post is overstressed at this height/speed per CLFMI table
                results.append(OptimizationResult(
                    fence_type="chain_link",
                    post_group=group_name,
                    trade_size=section.trade_size,
                    post_od=section.OD,
                    weight_plf=section.weight,
                    Mallow_kipft=section.Mallow,
                    max_spacing=0.0,
                    moment_ratio=0.0,
                    footing_depth_ft=0.0,
                    passes=False,
                    failure_reason=(
                        f"CLFMI table shows post overstressed at "
                        f"{fence_height:.0f} ft height with {wind.wind_speed:.0f} mph wind. "
                        f"Allowable moment ({section.Mallow:.2f} kip-ft) exceeded."
                    ),
                ))
                continue

            S_prime = S * Cf1 * Cf2 * Cf3

            # Cap spacing at reasonable maximum (CLFMI recommends 10 ft max)
            spacing = min(S_prime, 10.0)

            # Step 2: Chain link post analysis at the calculated spacing
            cl = ChainLinkInput(
                post_type=PostType.LINE,
                post_group=group_enum,
                post_od=section.OD,
                post_height=fence_height,
                post_spacing=spacing,
                post_weight=section.weight,
                wire_gauge=wire_gauge,
                wire_diameter=wire_diam,
                mesh_size=mesh_size,
                mesh_weight=mesh_weight,
                fos=fos,
            )
            cl_result = calculate_chain_link_post(wind, cl, section)

            # Step 3: Footing depth
            footing = FootingInput(
                ibc_edition=footing_input.ibc_edition,
                soil_bearing_pressure=footing_input.soil_bearing_pressure,
                footing_diameter=footing_input.footing_diameter,
                fence_height=fence_height,
                actual_depth=footing_input.actual_depth,
            )
            ft_result = calculate_footing_depth_ibc(footing, cl_result.shear)

            passes = cl_result.is_adequate
            failure_reason = ""
            if not passes:
                failure_reason = (
                    f"Moment demand ({cl_result.M_demand:.2f} kip-ft) exceeds "
                    f"allowable ({section.Mallow:.2f} kip-ft) at "
                    f"{spacing:.1f} ft spacing. Moment ratio = {cl_result.moment_ratio:.2f}."
                )

            results.append(OptimizationResult(
                fence_type="chain_link",
                post_group=group_name,
                trade_size=section.trade_size,
                post_od=section.OD,
                weight_plf=section.weight,
                Mallow_kipft=section.Mallow,
                max_spacing=S_prime,
                moment_ratio=cl_result.moment_ratio,
                footing_depth_ft=ft_result.D_calc,
                passes=passes,
                failure_reason=failure_reason,
            ))

    # Sort: lightest weight first, then widest spacing (descending)
    results.sort(key=lambda r: (not r.passes, r.weight_plf, -r.max_spacing))

    # Mark the optimal row (first passing)
    for r in results:
        if r.passes:
            r.is_optimal = True
            break

    return results


# Common wood post diameters to sweep (inches)
_WOOD_DIAMETERS = [3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0]

# Approximate weight per linear foot for round Douglas Fir by diameter
# Based on specific gravity 0.50 and density ~31 lb/ft^3
_WOOD_WEIGHTS = {
    3.0: 1.5, 4.0: 2.7, 5.0: 4.3, 6.0: 6.1,
    8.0: 10.9, 10.0: 17.0, 12.0: 24.4,
}


def optimize_wood(
    wind: WindInput,
    fence_height: float,
    post_spacing: float,
    wire_diam: float,
    mesh_size: float,
    mesh_weight: float,
    footing_input: FootingInput,
    fos: float = 1.0,
    species: WoodSpecies = WoodSpecies.DOUGLAS_FIR,
) -> list[OptimizationResult]:
    """Sweep common wood post diameters.

    Args:
        wind: Wind load parameters.
        fence_height: Fence height above ground (ft).
        post_spacing: Design post spacing (ft) — fixed for wood.
        wire_diam: Wire diameter (in).
        mesh_size: Mesh opening size (in).
        mesh_weight: Mesh fabric weight (psf).
        footing_input: Footing design parameters.
        fos: Factor of safety.
        species: Wood species (default Douglas Fir).

    Returns:
        List of OptimizationResult, sorted by weight then diameter.
    """
    results: list[OptimizationResult] = []

    for diam in _WOOD_DIAMETERS:
        weight = _WOOD_WEIGHTS.get(diam, 0.0)

        wood = WoodFenceInput(
            post_type=PostType.LINE,
            species=species,
            post_diameter=diam,
            post_height=fence_height,
            post_spacing=post_spacing,
            post_weight=weight,
            wire_diameter=wire_diam,
            mesh_size=mesh_size,
            mesh_weight=mesh_weight,
            fos=fos,
        )

        wd_result = calculate_wood_post(wind, wood)

        # Footing depth
        footing = FootingInput(
            ibc_edition=footing_input.ibc_edition,
            soil_bearing_pressure=footing_input.soil_bearing_pressure,
            footing_diameter=footing_input.footing_diameter,
            fence_height=fence_height,
            actual_depth=footing_input.actual_depth,
        )
        ft_result = calculate_footing_depth_ibc(footing, wd_result.shear)

        passes = wd_result.is_adequate
        failure_reason = ""
        if not passes:
            reasons = []
            if wd_result.combined_ratio > 1.0:
                reasons.append(
                    f"Combined stress ratio {wd_result.combined_ratio:.2f} > 1.0 "
                    f"(NDS 3.9.2 interaction)"
                )
            if wd_result.shear_ratio > 1.0:
                reasons.append(
                    f"Shear ratio {wd_result.shear_ratio:.2f} > 1.0"
                )
            failure_reason = "; ".join(reasons) if reasons else "Strength check failed."

        results.append(OptimizationResult(
            fence_type="wood",
            post_group="Douglas Fir",
            trade_size=f'{diam:.0f}" round',
            post_od=diam,
            weight_plf=weight,
            max_spacing=post_spacing,
            combined_ratio=wd_result.combined_ratio,
            shear_ratio=wd_result.shear_ratio,
            deflection_in=wd_result.deflection,
            footing_depth_ft=ft_result.D_calc,
            passes=passes,
            failure_reason=failure_reason,
        ))

    # Sort: passing first, then lightest weight
    results.sort(key=lambda r: (not r.passes, r.weight_plf))

    # Mark optimal
    for r in results:
        if r.passes:
            r.is_optimal = True
            break

    return results
