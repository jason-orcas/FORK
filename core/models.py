"""Data models for FORK fence design calculations.

All input/output dataclasses and enumerations used across the calculation engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class FenceType(Enum):
    CHAIN_LINK = "chain_link"
    WOOD = "wood"


class PostType(Enum):
    LINE = "line"
    PULL = "pull"
    GATE = "gate"


class ASCEEdition(Enum):
    ASCE_7_16 = "ASCE 7-16"
    ASCE_7_22 = "ASCE 7-22"


class IBCEdition(Enum):
    IBC_2009 = "IBC 2009"
    IBC_2018 = "IBC 2018"


class ExposureCategory(Enum):
    B = "B"
    C = "C"
    D = "D"


class IceExposure(Enum):
    HEAVY = "heavy"        # Cf3 = 0.45
    MODERATE = "moderate"  # Cf3 = 0.85
    NONE = "none"          # Cf3 = 1.00


class SteelPostGroup(Enum):
    GROUP_IA_REGULAR = "Group IA Regular (30 ksi)"
    GROUP_IA_HIGH = "Group IA High Strength (50 ksi)"
    GROUP_IC = "Group IC (50 ksi)"
    GROUP_II = "Group II C-Shape (50 ksi)"


class WoodSpecies(Enum):
    DOUGLAS_FIR = "Douglas Fir"


# ---------------------------------------------------------------------------
# Project & Wind Inputs
# ---------------------------------------------------------------------------

@dataclass
class ProjectInfo:
    project_name: str = "New Project"
    project_location: str = ""
    project_number: str = ""
    designer: str = ""
    reviewer: str = ""
    date: str = ""
    notes: str = ""


@dataclass
class WindInput:
    """Wind load parameters per ASCE 7-16 or ASCE 7-22."""
    asce_edition: ASCEEdition = ASCEEdition.ASCE_7_22
    wind_speed: float = 100.0          # mph (ultimate/LRFD)
    exposure_category: ExposureCategory = ExposureCategory.C
    risk_category: str = "II"
    Kd: float = 0.85                   # directionality factor
    Kzt: float = 1.0                   # topographic factor
    Kz: float = 0.85                   # velocity pressure coefficient
    G: float = 0.85                    # gust-effect factor
    Cf: float = 1.3                    # force coefficient (ASCE 7 Fig 29.3-1)
    Ke: float = 1.0                    # ground elevation factor (ASCE 7-22 only)


# ---------------------------------------------------------------------------
# Chain Link Inputs
# ---------------------------------------------------------------------------

@dataclass
class ChainLinkInput:
    """Chain link fence geometry and material inputs."""
    post_type: PostType = PostType.LINE
    post_group: SteelPostGroup = SteelPostGroup.GROUP_IA_REGULAR
    post_od: float = 2.375             # in (outer diameter)
    post_height: float = 7.0           # ft (above ground)
    post_spacing: float = 10.0         # ft
    post_weight: float = 3.65          # plf
    wire_gauge: int = 11
    wire_diameter: float = 0.192       # in
    mesh_size: float = 4.0             # in (diamond size)
    mesh_weight: float = 0.154         # psf
    fence_fabric_gap: float = 0.0      # ft (gap between bottom of fabric and ground)
    # Gate-specific fields
    gate_leaf_length: float = 0.0      # ft
    gate_leaf_height: float = 0.0      # ft
    gate_frame_post_diam: float = 0.0  # in
    gate_frame_post_weight: float = 0.0  # plf
    # Safety factor
    fos: float = 1.5                   # per CLFMI WLG


# ---------------------------------------------------------------------------
# Wood Fence Inputs
# ---------------------------------------------------------------------------

@dataclass
class WoodFenceInput:
    """Wood fence geometry and material inputs."""
    post_type: PostType = PostType.LINE
    species: WoodSpecies = WoodSpecies.DOUGLAS_FIR
    post_diameter: float = 4.0         # in (round post)
    post_height: float = 8.0           # ft (above ground)
    post_spacing: float = 10.0         # ft
    post_weight: float = 3.2           # plf
    wire_diameter: float = 0.192       # in
    mesh_size: float = 5.5             # in
    mesh_weight: float = 0.154         # psf
    fence_fabric_gap: float = 0.0      # ft
    # Gate-specific fields
    gate_leaf_length: float = 0.0      # ft
    gate_leaf_height: float = 0.0      # ft
    gate_frame_post_diam: float = 0.0  # in
    gate_frame_post_weight: float = 0.0  # plf
    # Safety factor (user-configurable; defaults differ by post type)
    fos: float = 1.0
    # NDS adjustment factor overrides (None = use defaults)
    Cd: float | None = None            # load duration factor
    Ct: float = 1.0                    # temperature factor
    Cct: float = 1.0                   # incising factor


# ---------------------------------------------------------------------------
# Spacing Inputs
# ---------------------------------------------------------------------------

@dataclass
class SpacingInput:
    """CLFMI post spacing calculation inputs."""
    fence_height: float = 6.0          # ft
    post_od: float = 2.875             # in
    post_group: SteelPostGroup = SteelPostGroup.GROUP_IA_REGULAR
    wire_gauge: int = 11
    mesh_size: float = 2.0             # in
    wind_speed: float = 115.0          # mph
    exposure_category: ExposureCategory = ExposureCategory.C
    ice_exposure: IceExposure = IceExposure.NONE
    actual_spacing: float = 10.0       # ft (user's design spacing)
    s_override: float | None = None    # manual override for S table value


# ---------------------------------------------------------------------------
# Footing Inputs
# ---------------------------------------------------------------------------

@dataclass
class FootingInput:
    """Footing depth calculation inputs."""
    ibc_edition: IBCEdition = IBCEdition.IBC_2018
    soil_bearing_pressure: float = 200.0   # psf (S1 - allowable lateral)
    footing_diameter: float = 1.5          # ft
    ground_gap: float = 0.0               # ft (h - gap below fabric)
    fence_height: float = 7.0             # ft
    use_astm_f567: bool = False
    actual_depth: float = 4.0             # ft (user-specified)


# ---------------------------------------------------------------------------
# Section Properties
# ---------------------------------------------------------------------------

@dataclass
class SteelPipeSection:
    """Steel pipe post section properties per CLFMI Table 16."""
    trade_size: str               # e.g., "2-3/8"
    group: SteelPostGroup
    OD: float                     # in
    ID: float                     # in
    Sx: float                     # in^3 (section modulus)
    Ix: float                     # in^4 (moment of inertia)
    Fy: float                     # ksi (yield strength)
    Mallow: float                 # kip-ft (allowable moment)
    Em: float                     # ksi (modulus of elasticity)
    weight: float = 0.0           # plf


@dataclass
class WoodSectionProperties:
    """Computed properties for a round wood post."""
    diameter: float               # in
    area: float = 0.0             # in^2
    Ix: float = 0.0              # in^4
    Sx: float = 0.0              # in^3

    def __post_init__(self):
        r = self.diameter / 2.0
        self.area = math.pi * r ** 2
        self.Ix = math.pi * r ** 4 / 4.0
        self.Sx = math.pi * r ** 3 / 4.0


@dataclass
class WoodDesignValues:
    """NDS 2018 reference design values for a wood species."""
    species: str = "Douglas Fir"
    Fc: float = 1300.0            # psi (compression parallel to grain)
    Fc_perp: float = 490.0       # psi (compression perpendicular)
    Fb: float = 2050.0           # psi (bending)
    Fv: float = 160.0            # psi (shear parallel to grain)
    E: float = 1_700_000.0       # psi (modulus of elasticity)
    Emin: float = 690_000.0      # psi (minimum modulus of elasticity)


# ---------------------------------------------------------------------------
# Result Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class WindResult:
    """Velocity pressure calculation result."""
    qz: float                     # psf
    asce_edition: ASCEEdition = ASCEEdition.ASCE_7_22
    formula_used: str = ""


@dataclass
class ChainLinkResult:
    """Chain link post analysis results."""
    post_type: PostType = PostType.LINE
    axial_load: float = 0.0       # lb
    shear: float = 0.0            # lb
    moment: float = 0.0           # lb-ft
    qz: float = 0.0              # psf
    Mallow: float = 0.0          # kip-ft (allowable from Table 16)
    M_demand: float = 0.0        # kip-ft
    moment_ratio: float = 0.0    # M_demand / Mallow (< 1.0 = pass)
    is_adequate: bool = True


@dataclass
class WoodStressResult:
    """Wood post NDS 2018 stress check results."""
    post_type: PostType = PostType.LINE
    # Applied loads
    axial_load: float = 0.0       # lb
    shear: float = 0.0            # lb
    moment: float = 0.0           # lb-ft
    # Applied stresses
    fc: float = 0.0               # psi (actual compression)
    fc_perp: float = 0.0         # psi (actual bearing)
    fb: float = 0.0              # psi (actual bending)
    fv: float = 0.0              # psi (actual shear)
    # Adjusted allowable stresses
    Fc_prime: float = 0.0        # psi
    Fc_perp_prime: float = 0.0   # psi
    Fb_prime: float = 0.0        # psi
    Fv_prime: float = 0.0        # psi
    # Key adjustment factors
    Cp: float = 1.0              # column stability
    Cd: float = 1.6              # load duration (wind)
    Ct: float = 1.0              # temperature
    Cct: float = 1.0             # incising
    Cf: float = 1.0              # size factor
    Ccs: float = 1.1             # round section factor
    Cls: float = 1.0             # lateral stability
    Cb: float = 1.0              # bearing area
    # Stress ratios
    compression_ratio: float = 0.0  # fc / Fc'
    bending_ratio: float = 0.0     # fb / Fb'
    shear_ratio: float = 0.0       # fv / Fv'
    combined_ratio: float = 0.0    # (fc/Fc')^2 + fb/Fb' per NDS 3.9.2
    # Deflection
    deflection: float = 0.0       # in
    is_adequate: bool = True


@dataclass
class SpacingResult:
    """CLFMI post spacing calculation result."""
    S_table: float = 0.0          # ft (from Tables 1-12)
    Cf1: float = 1.0             # mesh coefficient
    Cf2: float = 1.0             # exposure coefficient
    Cf3: float = 1.0             # ice coefficient
    S_prime_calc: float = 0.0    # ft = S * Cf1 * Cf2 * Cf3
    actual_spacing: float = 0.0  # ft
    is_adequate: bool = True     # actual <= S_prime


@dataclass
class FootingResult:
    """Footing depth calculation result."""
    method: str = "IBC"
    P_wind: float = 0.0          # lb
    A_intermediate: float = 0.0
    c_arm: float = 0.0           # ft (moment arm)
    D_calc: float = 0.0          # ft (required depth)
    D_actual: float = 0.0        # ft (user-specified)
    is_adequate: bool = True


@dataclass
class FenceReportData:
    """Aggregated data for PDF report generation."""
    project: ProjectInfo = field(default_factory=ProjectInfo)
    wind_input: WindInput = field(default_factory=WindInput)
    wind_result: WindResult | None = None
    fence_type: FenceType = FenceType.CHAIN_LINK
    # Chain link
    chain_link_input: ChainLinkInput | None = None
    chain_link_result: ChainLinkResult | None = None
    spacing_input: SpacingInput | None = None
    spacing_result: SpacingResult | None = None
    # Wood
    wood_input: WoodFenceInput | None = None
    wood_result: WoodStressResult | None = None
    # Footing
    footing_input: FootingInput | None = None
    footing_result: FootingResult | None = None
