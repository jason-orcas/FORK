"""Chain link fence post design calculations.

Computes axial load, wind shear, and moment at base for line, pull, and gate
posts. Checks section adequacy against CLFMI Table 16 allowable moment.

References:
    ASCE 7-16/7-22 Section 29.3 (open signs and lattice frameworks)
    CLFMI WLG 2445 (2023) — Wind Load Guide
    Spreadsheets: Line Post.xlsx, Pull post.xlsx, Gate Post Basic.xlsx
"""

from __future__ import annotations

from .models import (
    ChainLinkInput,
    ChainLinkResult,
    PostType,
    SteelPipeSection,
    WindInput,
    WindResult,
)
from .wind import calculate_velocity_pressure


def calculate_chain_link_post(
    wind: WindInput,
    cl: ChainLinkInput,
    section: SteelPipeSection | None = None,
) -> ChainLinkResult:
    """Full chain link post analysis: axial, shear, moment, adequacy check.

    Args:
        wind: Wind load parameters.
        cl: Chain link fence geometry and material inputs.
        section: Optional steel pipe section for adequacy check. If None,
                 adequacy check is skipped (moment_ratio = 0).

    Returns:
        ChainLinkResult with all computed values.
    """
    wind_result = calculate_velocity_pressure(wind)
    qz = wind_result.qz

    axial = _calc_axial(cl)
    shear = _calc_shear(qz, wind, cl)
    moment = _calc_moment(shear, cl)

    # Apply factor of safety to loads
    axial *= cl.fos
    shear *= cl.fos
    moment *= cl.fos

    # Section adequacy check
    M_demand_kipft = moment / 1000.0  # lb-ft -> kip-ft
    Mallow = section.Mallow if section else 0.0
    if Mallow > 0:
        moment_ratio = M_demand_kipft / Mallow
        is_adequate = moment_ratio <= 1.0
    else:
        moment_ratio = 0.0
        is_adequate = True

    return ChainLinkResult(
        post_type=cl.post_type,
        axial_load=axial,
        shear=shear,
        moment=moment,
        qz=qz,
        Mallow=Mallow,
        M_demand=M_demand_kipft,
        moment_ratio=moment_ratio,
        is_adequate=is_adequate,
    )


def _calc_axial(cl: ChainLinkInput) -> float:
    """Calculate axial (gravity) load on fence post (lb).

    Line/Pull: mesh_weight * H * spacing + post_weight * H
    Gate: adds gate leaf mesh weight + gate frame weight

    Source: Line Post.xlsx B30, Gate Post Basic.xlsx B32
    """
    H = cl.post_height  # ft
    S = cl.post_spacing  # ft

    # Self-weight of mesh fabric tributary to this post
    mesh_axial = cl.mesh_weight * H * S  # psf * ft * ft = lb
    # Self-weight of post
    post_axial = cl.post_weight * H  # plf * ft = lb

    axial = mesh_axial + post_axial

    if cl.post_type == PostType.GATE and cl.gate_leaf_length > 0:
        # Gate leaf mesh weight
        gate_mesh = cl.mesh_weight * cl.gate_leaf_height * cl.gate_leaf_length
        # Gate frame weight (perimeter of gate leaf)
        gate_perimeter = 2.0 * (cl.gate_leaf_height + cl.gate_leaf_length)
        gate_frame = cl.gate_frame_post_weight * gate_perimeter
        axial += gate_mesh + gate_frame

    return axial


def _calc_shear(qz: float, wind: WindInput, cl: ChainLinkInput) -> float:
    """Calculate wind shear force on fence post (lb).

    Shear = qz * G * Cf * (post projected area + mesh projected area)

    The mesh projected area accounts for the solidity ratio of the chain link
    fabric. For an open mesh, the projected area is:
        mesh_area = H * S * solidity_ratio

    The solidity ratio for chain link is approximately:
        solidity = 2 * wire_diameter / mesh_size (for diamond pattern)

    Source: Line Post.xlsx B32, matching the decomposed formula
    """
    H = cl.post_height  # ft
    S = cl.post_spacing  # ft
    post_od_ft = cl.post_od / 12.0  # in -> ft

    # Post projected area (cylinder facing wind)
    post_area = post_od_ft * H  # sq ft

    # Mesh solidity ratio for diamond chain link
    # Each diamond has 2 wire crossings per mesh_size opening
    solidity = 2.0 * cl.wire_diameter / cl.mesh_size
    mesh_area = H * S * solidity  # sq ft

    total_area = post_area + mesh_area

    # Wind force: F = qz * G * Cf * As (ASCE 7 Eq. 29.3-1, Kd already in qz)
    shear = qz * wind.G * wind.Cf * total_area

    return shear


def _calc_moment(shear: float, cl: ChainLinkInput) -> float:
    """Calculate moment at post base (lb-ft).

    Boundary conditions determine the moment arm:
    - Line posts: RESTRICTED head (top rail + fabric provide lateral restraint)
      M = Shear * H / 2 (uniform load on propped cantilever, resultant at H/2)
    - Pull/Gate posts: FREE head (no lateral restraint at top)
      M = Shear * H * 2/3 (uniform load on cantilever, resultant at 2/3 H)

    Gate posts also include dead load eccentricity from gate leaf.

    Source: Line Post.xlsx B33, Gate Post Basic.xlsx B35
    """
    H = cl.post_height  # ft

    if cl.post_type == PostType.LINE:
        # Restricted head: top rail + fabric provide lateral support
        # Effective moment arm = H/2 for uniform load
        moment = shear * H / 2.0
    else:
        # Free head (pull/gate): no top restraint
        # Effective moment arm = 2H/3 for uniform load
        moment = shear * H * 2.0 / 3.0

    if cl.post_type == PostType.GATE and cl.gate_leaf_length > 0:
        # Gate dead load eccentricity about the post
        gate_mesh_wt = cl.mesh_weight * cl.gate_leaf_height * cl.gate_leaf_length
        gate_perimeter = 2.0 * (cl.gate_leaf_height + cl.gate_leaf_length)
        gate_frame_wt = cl.gate_frame_post_weight * gate_perimeter
        gate_dead = gate_mesh_wt + gate_frame_wt
        # Eccentricity = half the gate leaf length
        eccentricity = cl.gate_leaf_length / 2.0
        moment += gate_dead * eccentricity

    return moment
