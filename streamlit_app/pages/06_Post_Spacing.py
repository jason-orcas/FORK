"""Page 05 - CLFMI Post Spacing Calculation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from core.models import ExposureCategory, IceExposure, SpacingInput, SteelPostGroup
from core.spacing import (
    calculate_spacing,
    lookup_S,
    lookup_cf1,
    lookup_cf2,
    lookup_cf3,
)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _get_available_posts(group_name: str) -> dict[str, float]:
    """Get available post trade sizes and ODs for a group from spacing tables."""
    with open(_DATA_DIR / "clfmi_spacing_tables.json", encoding="utf-8") as f:
        data = json.load(f)
    with open(_DATA_DIR / "clfmi_post_properties.json", encoding="utf-8") as f:
        props = json.load(f)

    group_data = data.get(group_name, {})
    # Build trade_size -> OD map from properties
    od_map = {}
    group_props = props.get(group_name, {})
    for p in group_props.get("posts", []):
        od_map[p["trade_size"]] = p["OD"]

    # Return only posts that exist in the spacing tables
    result = {}
    for key in group_data:
        if key.startswith("_"):
            continue
        od = od_map.get(key)
        if od:
            result[key] = od
        else:
            result[key] = 0.0  # C-shapes without OD
    return result


st.header("Post Spacing (CLFMI)")
st.caption("Chain Link Fence Wind Load Guide - WLG 2445 (2023)")
st.latex(r"S' = S \times C_{f1} \times C_{f2} \times C_{f3}")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Post & Fence")
    groups = [
        "Group IA Regular (30 ksi)",
        "Group IA High Strength (50 ksi)",
        "Group IC (50 ksi)",
        "Group II C-Shape (50 ksi)",
    ]
    st.selectbox("Post Group", groups, key="sp_post_group")

    # Build post size dropdown from actual CLFMI table data
    available_posts = _get_available_posts(st.session_state.sp_post_group)
    post_labels = []
    post_ods = {}
    for trade_size, od in available_posts.items():
        if od and od > 0:
            label = f'{trade_size}" (OD={od}")'
        else:
            label = f'{trade_size}"'
        post_labels.append(label)
        post_ods[label] = od if od else 0.0

    if "sp_post_label" not in st.session_state or st.session_state.sp_post_label not in post_labels:
        st.session_state.sp_post_label = post_labels[0] if post_labels else ""

    st.selectbox("Post Size", post_labels, key="sp_post_label")

    selected_od = post_ods.get(st.session_state.sp_post_label, 0.0)
    # Extract trade size from label
    selected_trade_size = st.session_state.sp_post_label.split('"')[0] if st.session_state.sp_post_label else ""

    st.number_input("Fence Height (ft)",
        key="sp_fence_height", min_value=3.0, max_value=20.0, step=0.5)

with col2:
    st.subheader("Wind & Environment")
    st.number_input("Wind Speed (mph)",
        key="sp_wind_speed", min_value=105.0, max_value=210.0, step=5.0,
        help="ASCE 7-22 ultimate wind speed (105-210 mph)")
    st.selectbox("Exposure Category",
        ["B", "C", "D"], key="sp_exposure")
    st.selectbox("Ice Exposure",
        ["none", "moderate", "heavy"], key="sp_ice")

st.subheader("Mesh")
mc1, mc2 = st.columns(2)
with mc1:
    st.number_input("Wire Gauge",
        key="sp_wire_gauge", min_value=5, max_value=14, step=1)
with mc2:
    st.number_input("Mesh Size (in)",
        key="sp_mesh_size", min_value=0.25, max_value=4.0, step=0.25)

st.number_input("Actual Design Spacing (ft)",
    key="sp_actual_spacing", min_value=1.0, max_value=30.0, step=0.5)

st.checkbox("Override S table value (manual entry)", key="sp_use_override")
if st.session_state.sp_use_override:
    st.number_input("S override (ft)", key="sp_override_val",
        min_value=0.1, max_value=200.0, step=0.5)
    st.session_state.sp_s_override = st.session_state.sp_override_val
else:
    st.session_state.sp_s_override = None

st.divider()

if st.button("Calculate Spacing", type="primary"):
    group_enum = SteelPostGroup(st.session_state.sp_post_group)
    fence_h = st.session_state.sp_fence_height
    wind_v = st.session_state.sp_wind_speed
    wire_g = st.session_state.sp_wire_gauge
    mesh_s = st.session_state.sp_mesh_size
    exp = ExposureCategory(st.session_state.sp_exposure)
    ice = IceExposure(st.session_state.sp_ice)

    # Show diagnostic info
    st.subheader("Calculation Details")

    # Step 1: S table lookup
    if st.session_state.sp_s_override is not None:
        S = st.session_state.sp_s_override
        st.write(f"**S (override):** {S:.1f} ft (user-entered)")
    else:
        S = lookup_S(wind_v, group_enum, selected_od, fence_h)
        if S is not None:
            st.write(f"**S (from Table):** {S:.1f} ft "
                     f"(Post: {selected_trade_size}\", "
                     f"Height: {fence_h:.0f} ft, "
                     f"Wind: {wind_v:.0f} mph, "
                     f"Group: {st.session_state.sp_post_group})")
        else:
            st.error(
                f"**S = N/A** - Post {selected_trade_size}\" is overstressed at "
                f"{fence_h:.0f} ft height with {wind_v:.0f} mph wind.\n\n"
                f"The CLFMI tables show '---' for this combination, meaning "
                f"the post's allowable moment capacity is exceeded.\n\n"
                f"**Try:** Larger post size, lower fence height, or lower wind speed."
            )

    # Step 2: Correction factors
    Cf1 = lookup_cf1(wire_g, mesh_s)
    Cf2 = lookup_cf2(exp, fence_h)
    Cf3 = lookup_cf3(ice)

    st.write(f"**Cf1 (Mesh):** {Cf1:.2f} (Gauge {wire_g}, {mesh_s}\" mesh)")
    st.write(f"**Cf2 (Exposure):** {Cf2:.2f} (Exposure {st.session_state.sp_exposure}, "
             f"{'0-15 ft' if fence_h <= 15 else '15-20 ft'} range)")
    st.write(f"**Cf3 (Ice):** {Cf3:.2f} ({st.session_state.sp_ice})")

    # Step 3: Calculate S'
    if S is not None:
        S_prime = S * Cf1 * Cf2 * Cf3
        actual = st.session_state.sp_actual_spacing

        st.divider()
        st.subheader("Results")
        st.latex(rf"S' = {S:.1f} \times {Cf1:.2f} \times {Cf2:.2f} \times {Cf3:.2f} = {S_prime:.1f} \text{{ ft}}")

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("S (Table)", f"{S:.1f} ft")
        rc2.metric("Cf1 (Mesh)", f"{Cf1:.2f}")
        rc3.metric("Cf2 (Exposure)", f"{Cf2:.2f}")
        rc4.metric("Cf3 (Ice)", f"{Cf3:.2f}")

        st.metric("S' (Recommended Max Spacing)", f"{S_prime:.1f} ft")
        st.metric("Actual Spacing", f"{actual:.1f} ft")

        if actual <= S_prime:
            st.success(f"Actual spacing ({actual:.1f} ft) <= S' ({S_prime:.1f} ft) - **ADEQUATE**")
        else:
            st.error(f"Actual spacing ({actual:.1f} ft) > S' ({S_prime:.1f} ft) - **NOT ADEQUATE**")

        # Store result
        from core.models import SpacingResult
        st.session_state.spacing_result = SpacingResult(
            S_table=S,
            Cf1=Cf1,
            Cf2=Cf2,
            Cf3=Cf3,
            S_prime_calc=S_prime,
            actual_spacing=actual,
            is_adequate=actual <= S_prime,
        )
    else:
        st.session_state.spacing_result = None
