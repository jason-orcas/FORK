"""CLFMI chain link fence post spacing calculations.

Implements the spacing formula: S' = S * Cf1 * Cf2 * Cf3
per CLFMI WLG 2445 (2023).

Tables 1-12 provide base spacing S for different wind speeds and post groups.
Tables 13-15 provide correction factors Cf1 (mesh), Cf2 (exposure), Cf3 (ice).

References:
    CLFMI WLG 2445 (2023) — Chain Link Fence Wind Load Guide
    Spreadsheet: Fence Post Spacing.xlsx
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import (
    ExposureCategory,
    IceExposure,
    SpacingInput,
    SpacingResult,
    SteelPostGroup,
)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str) -> dict:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


# Heights used in the CLFMI tables
_CLFMI_HEIGHTS = [3, 3.5, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
_CLFMI_SPEEDS = [105, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210]


def calculate_spacing(spacing_input: SpacingInput) -> SpacingResult:
    """Calculate recommended post spacing per CLFMI WLG 2445.

    S' = S * Cf1 * Cf2 * Cf3

    Args:
        spacing_input: All inputs for the spacing calculation.

    Returns:
        SpacingResult with S, Cf1, Cf2, Cf3, S', and adequacy check.
    """
    # Look up S from tables (or use override)
    if spacing_input.s_override is not None:
        S = spacing_input.s_override
    else:
        S = lookup_S(
            spacing_input.wind_speed,
            spacing_input.post_group,
            spacing_input.post_od,
            spacing_input.fence_height,
        )

    if S is None:
        return SpacingResult(
            S_table=0.0,
            Cf1=0.0,
            Cf2=0.0,
            Cf3=0.0,
            S_prime_calc=0.0,
            actual_spacing=spacing_input.actual_spacing,
            is_adequate=False,
        )

    Cf1 = lookup_cf1(spacing_input.wire_gauge, spacing_input.mesh_size)
    Cf2 = lookup_cf2(spacing_input.exposure_category, spacing_input.fence_height)
    Cf3 = lookup_cf3(spacing_input.ice_exposure)

    S_prime = S * Cf1 * Cf2 * Cf3

    return SpacingResult(
        S_table=S,
        Cf1=Cf1,
        Cf2=Cf2,
        Cf3=Cf3,
        S_prime_calc=S_prime,
        actual_spacing=spacing_input.actual_spacing,
        is_adequate=spacing_input.actual_spacing <= S_prime,
    )


def lookup_S(
    wind_speed: float,
    post_group: SteelPostGroup,
    post_od: float,
    fence_height: float,
) -> float | None:
    """Look up base spacing S from CLFMI Tables 1-12.

    Supports linear interpolation for intermediate wind speeds and heights.
    Returns None if the post is overstressed at the given height/speed.
    """
    data = _load_json("clfmi_spacing_tables.json")
    group_data = data.get(post_group.value)
    if group_data is None:
        return None

    # Find the post size key — match by OD value
    # Trade sizes in the JSON use the naming convention from the tables
    post_key = _find_post_key(group_data, post_od)
    if post_key is None:
        return None

    post_data = group_data[post_key]

    # Find height index
    h_idx = _interpolate_index(_CLFMI_HEIGHTS, fence_height)
    if h_idx is None:
        return None

    # Find wind speed — interpolate between available speeds
    speed_idx = _interpolate_index(_CLFMI_SPEEDS, wind_speed)
    if speed_idx is None:
        return None

    # Get S value, handling interpolation
    return _get_interpolated_S(post_data, speed_idx, h_idx)


def _find_post_key(group_data: dict, post_od: float) -> str | None:
    """Find the post key in spacing table data that matches the given OD.

    Matches by parsing the trade size string to find the corresponding OD
    from the post properties data.
    """
    props = _load_json("clfmi_post_properties.json")
    # Build a map of trade_size -> OD across all groups
    od_map: dict[str, float] = {}
    for group_key, group_info in props.items():
        if group_key.startswith("_"):
            continue
        for p in group_info["posts"]:
            if p["OD"] is not None:
                od_map[p["trade_size"]] = p["OD"]

    # Also handle C-shape sizes that don't have OD
    for key in group_data:
        if key.startswith("_"):
            continue
        # Check if this key matches by OD
        if key in od_map:
            if abs(od_map[key] - post_od) < 0.01:
                return key
        # For C-shapes, match by the key string directly
        # (user would need to provide exact trade size)

    # Fallback: try matching OD directly in pipe sections
    pipes = _load_json("steel_pipe_sections.json")["pipes"]
    for trade_size, pipe_info in pipes.items():
        if abs(pipe_info["OD"] - post_od) < 0.01:
            if trade_size in group_data:
                return trade_size

    return None


def _interpolate_index(values: list, target: float) -> tuple[int, float] | None:
    """Find interpolation position in a sorted list.

    Returns (lower_index, fraction) where fraction is 0.0-1.0.
    Returns None if target is out of range.
    """
    if target < values[0] or target > values[-1]:
        return None

    for i in range(len(values) - 1):
        if values[i] <= target <= values[i + 1]:
            if values[i] == values[i + 1]:
                return (i, 0.0)
            frac = (target - values[i]) / (values[i + 1] - values[i])
            return (i, frac)

    return (len(values) - 1, 0.0)


def _get_interpolated_S(
    post_data: dict,
    speed_idx: tuple[int, float],
    h_idx: tuple[int, float],
) -> float | None:
    """Get interpolated S value from post data.

    Handles bilinear interpolation between wind speeds and heights.
    Returns None if any corner value is null (overstressed).
    """
    si, sf = speed_idx
    hi, hf = h_idx

    speed_keys = [str(s) for s in _CLFMI_SPEEDS]

    def get_val(speed_i: int, height_i: int) -> float | None:
        if speed_i >= len(speed_keys):
            speed_i = len(speed_keys) - 1
        key = speed_keys[speed_i]
        if key not in post_data:
            return None
        arr = post_data[key]
        if height_i >= len(arr):
            return None
        return arr[height_i]

    # Get the four corner values for bilinear interpolation
    v00 = get_val(si, hi)
    v01 = get_val(si, min(hi + 1, len(_CLFMI_HEIGHTS) - 1))
    v10 = get_val(min(si + 1, len(_CLFMI_SPEEDS) - 1), hi)
    v11 = get_val(min(si + 1, len(_CLFMI_SPEEDS) - 1), min(hi + 1, len(_CLFMI_HEIGHTS) - 1))

    # If any corner is null, post is overstressed
    if any(v is None for v in [v00, v01, v10, v11]):
        return None

    # Bilinear interpolation
    if sf == 0.0 and hf == 0.0:
        return v00

    v_h0 = v00 + hf * (v01 - v00)  # interpolate along height at lower speed
    v_h1 = v10 + hf * (v11 - v10)  # interpolate along height at upper speed
    return v_h0 + sf * (v_h1 - v_h0)  # interpolate along speed


def lookup_cf1(wire_gauge: int, mesh_size: float) -> float:
    """Look up mesh/fabric size coefficient Cf1 from CLFMI Table 13.

    Returns 1.0 for solid panel fence (when no mesh data available).
    Uses nearest available mesh size if exact match not found.
    """
    data = _load_json("clfmi_cf1_mesh.json")
    gauge_data = data["wire_gauges"].get(str(wire_gauge))
    if gauge_data is None:
        return 1.0

    coeffs = gauge_data["mesh_coefficients"]

    # Build a numeric-keyed dict to avoid float/string mismatch issues
    numeric_coeffs: dict[float, float] = {}
    for k, v in coeffs.items():
        numeric_coeffs[float(k)] = v

    # Exact match
    for k, v in numeric_coeffs.items():
        if abs(k - mesh_size) < 0.001:
            return v

    # Find nearest mesh size
    available = sorted(numeric_coeffs.keys())
    if mesh_size <= available[0]:
        return numeric_coeffs[available[0]]
    if mesh_size >= available[-1]:
        return numeric_coeffs[available[-1]]

    # Interpolate between nearest sizes
    for i in range(len(available) - 1):
        if available[i] <= mesh_size <= available[i + 1]:
            lo_val = numeric_coeffs[available[i]]
            hi_val = numeric_coeffs[available[i + 1]]
            frac = (mesh_size - available[i]) / (available[i + 1] - available[i])
            return lo_val + frac * (hi_val - lo_val)

    return 1.0


def lookup_cf2(exposure: ExposureCategory, fence_height: float) -> float:
    """Look up wind exposure category coefficient Cf2 from CLFMI Table 14.

    Args:
        exposure: Wind exposure category (B, C, or D).
        fence_height: Fence height in feet (determines 0-15 or 15-20 range).

    Returns:
        Cf2 value.
    """
    data = _load_json("clfmi_cf2_exposure.json")
    exp_data = data.get(exposure.value)
    if exp_data is None:
        return 1.0

    if fence_height <= 15.0:
        return exp_data["0-15"]["Cf2"]
    else:
        return exp_data["15-20"]["Cf2"]


def lookup_cf3(ice_exposure: IceExposure) -> float:
    """Return ice exposure coefficient Cf3 from CLFMI Table 15."""
    data = _load_json("clfmi_cf3_ice.json")
    return data.get(ice_exposure.value, 1.0)
