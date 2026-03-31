"""Section property database for steel pipe and wood fence posts.

Loads reference data from JSON files and provides lookup functions.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from .models import (
    SteelPipeSection,
    SteelPostGroup,
    WoodDesignValues,
    WoodSectionProperties,
    WoodSpecies,
)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(filename: str) -> dict:
    with open(_DATA_DIR / filename, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Steel pipe sections
# ---------------------------------------------------------------------------

def load_steel_pipe_sections() -> dict[str, list[SteelPipeSection]]:
    """Load all steel pipe sections from CLFMI Table 16 JSON.

    Returns a dict keyed by group enum value -> list of SteelPipeSection.
    """
    data = _load_json("clfmi_post_properties.json")
    result: dict[str, list[SteelPipeSection]] = {}
    for group_key, group_data in data.items():
        if group_key.startswith("_"):
            continue
        fy = group_data["Fy_ksi"]
        sections = []
        for p in group_data["posts"]:
            sections.append(SteelPipeSection(
                trade_size=p["trade_size"],
                group=SteelPostGroup(group_key),
                OD=p["OD"] or 0.0,
                ID=p["ID"] or 0.0,
                Sx=p["Sx"],
                Ix=p["Ix"],
                Fy=fy,
                Mallow=p["Mallow_kipft"],
                Em=p["Em_ksi"],
                weight=p.get("weight_plf", 0.0),
            ))
        result[group_key] = sections
    return result


def get_steel_pipe_section(
    trade_size: str,
    group: SteelPostGroup,
) -> SteelPipeSection | None:
    """Look up a specific steel pipe section by trade size and group."""
    all_sections = load_steel_pipe_sections()
    group_sections = all_sections.get(group.value, [])
    for s in group_sections:
        if s.trade_size == trade_size:
            return s
    return None


def get_available_trade_sizes(group: SteelPostGroup) -> list[str]:
    """Return list of available trade sizes for a given post group."""
    all_sections = load_steel_pipe_sections()
    return [s.trade_size for s in all_sections.get(group.value, [])]


# ---------------------------------------------------------------------------
# Wood section properties
# ---------------------------------------------------------------------------

def compute_wood_section(diameter_in: float) -> WoodSectionProperties:
    """Compute section properties for a round wood post."""
    return WoodSectionProperties(diameter=diameter_in)


def get_wood_design_values(species: WoodSpecies) -> WoodDesignValues:
    """Get NDS 2018 reference design values for a wood species."""
    data = _load_json("wood_species.json")
    sp = data.get(species.value)
    if sp is None:
        raise ValueError(f"No reference data for species: {species.value}")
    return WoodDesignValues(
        species=species.value,
        Fc=sp["Fc_psi"],
        Fc_perp=sp["Fc_perp_psi"],
        Fb=sp["Fb_psi"],
        Fv=sp["Fv_psi"],
        E=sp["E_psi"],
        Emin=sp["Emin_psi"],
    )


# ---------------------------------------------------------------------------
# Steel pipe dimensions (for weight/area lookups)
# ---------------------------------------------------------------------------

def get_pipe_weight(trade_size: str) -> float:
    """Get pipe weight (plf) from steel_pipe_sections.json."""
    data = _load_json("steel_pipe_sections.json")
    pipe = data["pipes"].get(trade_size)
    if pipe is None:
        raise ValueError(f"No pipe data for trade size: {trade_size}")
    return pipe["weight_plf"]


def get_pipe_od(trade_size: str) -> float:
    """Get pipe outer diameter (in) from steel_pipe_sections.json."""
    data = _load_json("steel_pipe_sections.json")
    pipe = data["pipes"].get(trade_size)
    if pipe is None:
        raise ValueError(f"No pipe data for trade size: {trade_size}")
    return pipe["OD"]
