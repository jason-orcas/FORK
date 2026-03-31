"""Page 05 — CLFMI Post Spacing Calculation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from core.models import ExposureCategory, IceExposure, SpacingInput, SteelPostGroup
from core.spacing import calculate_spacing

st.header("Post Spacing (CLFMI)")
st.caption("Chain Link Fence Wind Load Guide — WLG 2445 (2023)")
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
    st.session_state.sp_post_group = st.selectbox("Post Group", groups,
        index=groups.index(st.session_state.sp_post_group))
    st.session_state.sp_post_od = st.number_input("Post O.D. (in)",
        value=st.session_state.sp_post_od, min_value=1.0, max_value=10.0, step=0.125)
    st.session_state.sp_fence_height = st.number_input("Fence Height (ft)",
        value=st.session_state.sp_fence_height, min_value=3.0, max_value=20.0, step=0.5)

with col2:
    st.subheader("Wind & Environment")
    st.session_state.sp_wind_speed = st.number_input("Wind Speed (mph)",
        value=st.session_state.sp_wind_speed, min_value=105.0, max_value=210.0, step=5.0,
        help="ASCE 7-22 ultimate wind speed (105-210 mph)")
    st.session_state.sp_exposure = st.selectbox("Exposure Category",
        ["B", "C", "D"], index=["B", "C", "D"].index(st.session_state.sp_exposure))
    st.session_state.sp_ice = st.selectbox("Ice Exposure",
        ["none", "moderate", "heavy"], index=["none", "moderate", "heavy"].index(st.session_state.sp_ice))

st.subheader("Mesh")
mc1, mc2 = st.columns(2)
with mc1:
    st.session_state.sp_wire_gauge = st.number_input("Wire Gauge",
        value=st.session_state.sp_wire_gauge, min_value=5, max_value=14, step=1)
with mc2:
    st.session_state.sp_mesh_size = st.number_input("Mesh Size (in)",
        value=st.session_state.sp_mesh_size, min_value=0.25, max_value=4.0, step=0.25)

st.session_state.sp_actual_spacing = st.number_input("Actual Design Spacing (ft)",
    value=st.session_state.sp_actual_spacing, min_value=1.0, max_value=30.0, step=0.5)

use_override = st.checkbox("Override S table value (manual entry)")
if use_override:
    override_val = st.number_input("S override (ft)", value=10.0, min_value=0.1, max_value=200.0)
    st.session_state.sp_s_override = override_val
else:
    st.session_state.sp_s_override = None

st.divider()

if st.button("Calculate Spacing", type="primary"):
    inp = SpacingInput(
        fence_height=st.session_state.sp_fence_height,
        post_od=st.session_state.sp_post_od,
        post_group=SteelPostGroup(st.session_state.sp_post_group),
        wire_gauge=st.session_state.sp_wire_gauge,
        mesh_size=st.session_state.sp_mesh_size,
        wind_speed=st.session_state.sp_wind_speed,
        exposure_category=ExposureCategory(st.session_state.sp_exposure),
        ice_exposure=IceExposure(st.session_state.sp_ice),
        actual_spacing=st.session_state.sp_actual_spacing,
        s_override=st.session_state.sp_s_override,
    )
    result = calculate_spacing(inp)
    st.session_state.spacing_result = result

    if result.S_table == 0.0 and result.S_prime_calc == 0.0:
        st.error("Post is **overstressed** at this height/wind speed combination. "
                 "Select a larger post or reduce fence height.")
    else:
        st.subheader("Results")

        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("S (Table)", f"{result.S_table:.1f} ft")
        rc2.metric("Cf1 (Mesh)", f"{result.Cf1:.2f}")
        rc3.metric("Cf2 (Exposure)", f"{result.Cf2:.2f}")
        rc4.metric("Cf3 (Ice)", f"{result.Cf3:.2f}")

        s_prime = result.S_prime_calc
        actual = result.actual_spacing

        st.metric("S' (Recommended Max Spacing)", f"{s_prime:.1f} ft")
        st.metric("Actual Spacing", f"{actual:.1f} ft")

        if result.is_adequate:
            st.success(f"Actual spacing ({actual:.1f} ft) \u2264 S' ({s_prime:.1f} ft) \u2014 **ADEQUATE**")
        else:
            st.error(f"Actual spacing ({actual:.1f} ft) > S' ({s_prime:.1f} ft) \u2014 **NOT ADEQUATE**")
