"""Fence run planner and quantity takeoff calculations.

Given a fence run layout (total length, gates, corners), computes the
number of each post type, concrete volume, fabric area, and material weights.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class GateSpec:
    """Single gate opening."""
    width_ft: float = 10.0
    num_leaves: int = 2  # single or double gate


@dataclass
class FenceRunInput:
    """Inputs for a fence run layout."""
    total_length_ft: float = 200.0
    post_spacing_ft: float = 10.0
    num_corners: int = 0
    gates: list[GateSpec] = field(default_factory=list)
    # Post properties
    post_height_ft: float = 7.0
    post_weight_plf: float = 3.65
    # Footing
    footing_diameter_ft: float = 1.5
    footing_depth_line_ft: float = 3.0
    footing_depth_pull_ft: float = 3.5
    footing_depth_gate_ft: float = 4.0
    # Fabric
    fabric_height_ft: float = 6.0  # may differ from post height
    # Top rail
    has_top_rail: bool = True
    top_rail_weight_plf: float = 2.27  # 1-5/8" pipe default


@dataclass
class FenceRunResult:
    """Quantity takeoff results."""
    # Post counts
    num_line_posts: int = 0
    num_pull_posts: int = 0
    num_gate_posts: int = 0
    total_posts: int = 0
    # Fence fabric
    fabric_area_sqft: float = 0.0
    fabric_length_ft: float = 0.0
    # Top rail
    top_rail_length_ft: float = 0.0
    # Concrete
    concrete_line_cuft: float = 0.0
    concrete_pull_cuft: float = 0.0
    concrete_gate_cuft: float = 0.0
    concrete_total_cuft: float = 0.0
    concrete_total_cuyd: float = 0.0
    # Weights
    post_steel_lbs: float = 0.0
    top_rail_steel_lbs: float = 0.0
    total_steel_lbs: float = 0.0


def calculate_fence_run(inp: FenceRunInput) -> FenceRunResult:
    """Calculate quantities for a fence run layout.

    Layout logic:
    - Pull/terminal posts at each end of the run (2)
    - Pull posts at each corner
    - Gate posts: 2 per gate opening
    - Line posts: fill remaining length at design spacing

    Args:
        inp: Fence run layout inputs.

    Returns:
        FenceRunResult with all quantities.
    """
    result = FenceRunResult()

    # Gate posts: 2 per gate
    num_gates = len(inp.gates)
    result.num_gate_posts = num_gates * 2

    # Pull posts: 2 ends + corners
    result.num_pull_posts = 2 + inp.num_corners

    # Total gate width
    total_gate_width = sum(g.width_ft for g in inp.gates)

    # Fenceable length (total minus gate openings)
    fenceable_length = inp.total_length_ft - total_gate_width
    if fenceable_length < 0:
        fenceable_length = 0

    # Number of line post segments
    # Pull and gate posts create segment breaks. Total segments =
    # (num_pull_posts + num_gate_posts - 1) but it's simpler to just
    # divide fenceable length by spacing
    if inp.post_spacing_ft > 0 and fenceable_length > 0:
        num_segments = fenceable_length / inp.post_spacing_ft
        # Line posts = total internal posts (between pull/gate posts)
        # Subtract the terminal/corner/gate posts from the count
        total_fixed_posts = result.num_pull_posts + result.num_gate_posts
        result.num_line_posts = max(0, round(num_segments) - 1)
        # Adjust: if segments > fixed posts, we need line posts to fill
        result.num_line_posts = max(0, int(round(fenceable_length / inp.post_spacing_ft)) - 1)

    result.total_posts = result.num_line_posts + result.num_pull_posts + result.num_gate_posts

    # Fence fabric area
    result.fabric_length_ft = fenceable_length
    result.fabric_area_sqft = fenceable_length * inp.fabric_height_ft

    # Top rail
    if inp.has_top_rail:
        result.top_rail_length_ft = fenceable_length

    # Concrete volumes (cylindrical footings: V = pi/4 * d^2 * depth)
    footing_area = math.pi / 4.0 * inp.footing_diameter_ft ** 2  # sq ft

    result.concrete_line_cuft = result.num_line_posts * footing_area * inp.footing_depth_line_ft
    result.concrete_pull_cuft = result.num_pull_posts * footing_area * inp.footing_depth_pull_ft
    result.concrete_gate_cuft = result.num_gate_posts * footing_area * inp.footing_depth_gate_ft

    result.concrete_total_cuft = (result.concrete_line_cuft +
                                   result.concrete_pull_cuft +
                                   result.concrete_gate_cuft)
    result.concrete_total_cuyd = result.concrete_total_cuft / 27.0

    # Steel/material weights
    total_post_height = inp.post_height_ft + inp.footing_depth_line_ft  # approximate total length
    result.post_steel_lbs = result.total_posts * inp.post_weight_plf * total_post_height

    if inp.has_top_rail:
        result.top_rail_steel_lbs = result.top_rail_length_ft * inp.top_rail_weight_plf

    result.total_steel_lbs = result.post_steel_lbs + result.top_rail_steel_lbs

    return result
