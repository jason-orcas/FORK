"""Page 03 — Chain Link Fence Post Design."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from core.models import (
    ASCEEdition,
    ChainLinkInput,
    ExposureCategory,
    PostType,
    SteelPostGroup,
    WindInput,
)
from core.chain_link import calculate_chain_link_post
from core.sections import get_steel_pipe_section, get_available_trade_sizes

st.header("Chain Link Fence Post Design")

# Post type selector
post_type_labels = ["Line Post", "Pull/Terminal Post", "Gate Post"]
post_type_map = {"Line Post": "line", "Pull/Terminal Post": "pull", "Gate Post": "gate"}
if "cl_post_type_label" not in st.session_state:
    st.session_state.cl_post_type_label = "Line Post"
st.radio("Post Type", post_type_labels, key="cl_post_type_label", horizontal=True)
st.session_state.cl_post_type = post_type_map[st.session_state.cl_post_type_label]

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Post Properties")
    groups = [
        "Group IA Regular (30 ksi)",
        "Group IA High Strength (50 ksi)",
        "Group IC (50 ksi)",
        "Group II C-Shape (50 ksi)",
    ]
    st.selectbox("Post Group", groups, key="cl_post_group")

    group_enum = SteelPostGroup(st.session_state.cl_post_group)
    available_sizes = get_available_trade_sizes(group_enum)

    if st.session_state.cl_trade_size not in available_sizes and available_sizes:
        st.session_state.cl_trade_size = available_sizes[0]

    st.selectbox("Trade Size", available_sizes, key="cl_trade_size")

    section = get_steel_pipe_section(st.session_state.cl_trade_size, group_enum)
    if section:
        st.caption(f"OD={section.OD}\", Sx={section.Sx} in\u00b3, Mallow={section.Mallow} kip-ft")

with col2:
    st.subheader("Geometry")
    st.number_input("Post Height (ft)", key="cl_post_height",
        min_value=1.0, max_value=25.0, step=0.5)
    st.number_input("Post Spacing (ft)", key="cl_post_spacing",
        min_value=1.0, max_value=30.0, step=0.5)

with col3:
    st.subheader("Mesh/Fabric")
    st.number_input("Wire Gauge", key="cl_wire_gauge",
        min_value=5, max_value=14, step=1)
    st.number_input("Mesh Size (in)", key="cl_mesh_size",
        min_value=0.25, max_value=4.0, step=0.25)
    st.number_input("Mesh Weight (psf)", key="cl_mesh_weight",
        min_value=0.01, max_value=5.0, step=0.01, format="%.3f")

# Gate-specific inputs
if st.session_state.cl_post_type == "gate":
    st.subheader("Gate Leaf Properties")
    gc1, gc2 = st.columns(2)
    with gc1:
        st.number_input("Gate Leaf Length (ft)",
            key="cl_gate_leaf_length", min_value=0.0, max_value=30.0, step=0.25)
        st.number_input("Gate Leaf Height (ft)",
            key="cl_gate_leaf_height", min_value=0.0, max_value=25.0, step=0.25)
    with gc2:
        st.number_input("Gate Frame Post Diam (in)",
            key="cl_gate_frame_diam", min_value=0.0, max_value=10.0, step=0.125)
        st.number_input("Gate Frame Post Weight (plf)",
            key="cl_gate_frame_weight", min_value=0.0, max_value=30.0, step=0.01)

st.number_input("Factor of Safety", key="cl_fos",
    min_value=0.5, max_value=5.0, step=0.1,
    help="CLFMI default = 1.5")

st.divider()

# Calculate
if st.button("Calculate", type="primary"):
    if st.session_state.wind_result is None:
        st.error("Please calculate wind parameters first (Wind Parameters page).")
    else:
        wind = WindInput(
            asce_edition=ASCEEdition(st.session_state.asce_edition),
            wind_speed=st.session_state.wind_speed,
            exposure_category=ExposureCategory(st.session_state.exposure_category),
            risk_category=st.session_state.risk_category,
            Kd=st.session_state.Kd, Kzt=st.session_state.Kzt, Kz=st.session_state.Kz,
            G=st.session_state.G, Cf=st.session_state.Cf, Ke=st.session_state.Ke,
        )

        # Wire diameter lookup by gauge
        gauge_diameters = {5: 0.207, 6: 0.192, 8: 0.162, 9: 0.148,
                          10: 0.135, 11: 0.120, 12: 0.113, 14: 0.080}
        wire_diam = gauge_diameters.get(st.session_state.cl_wire_gauge, 0.12)

        cl = ChainLinkInput(
            post_type=PostType(st.session_state.cl_post_type),
            post_group=group_enum,
            post_od=section.OD if section else 2.375,
            post_height=st.session_state.cl_post_height,
            post_spacing=st.session_state.cl_post_spacing,
            post_weight=section.weight if section else 3.65,
            wire_gauge=st.session_state.cl_wire_gauge,
            wire_diameter=wire_diam,
            mesh_size=st.session_state.cl_mesh_size,
            mesh_weight=st.session_state.cl_mesh_weight,
            gate_leaf_length=st.session_state.cl_gate_leaf_length,
            gate_leaf_height=st.session_state.cl_gate_leaf_height,
            gate_frame_post_diam=st.session_state.cl_gate_frame_diam,
            gate_frame_post_weight=st.session_state.cl_gate_frame_weight,
            fos=st.session_state.cl_fos,
        )

        result = calculate_chain_link_post(wind, cl, section)
        st.session_state.cl_result = result

        # Display results
        st.subheader("Results")

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Axial Load", f"{result.axial_load:.1f} lb")
        rc2.metric("Shear", f"{result.shear:.1f} lb")
        rc3.metric("Moment", f"{result.moment:.1f} lb-ft")

        st.metric("Velocity Pressure (qz)", f"{result.qz:.2f} psf")

        if section:
            st.subheader("Section Adequacy")
            col_a, col_b = st.columns(2)
            col_a.metric("Moment Demand", f"{result.M_demand:.3f} kip-ft")
            col_b.metric("Moment Capacity", f"{result.Mallow:.3f} kip-ft")

            ratio = result.moment_ratio
            if ratio <= 0.9:
                st.success(f"Moment Ratio = {ratio:.3f} \u2264 1.0 \u2014 **PASS**")
            elif ratio <= 1.0:
                st.warning(f"Moment Ratio = {ratio:.3f} \u2264 1.0 \u2014 **MARGINAL**")
            else:
                st.error(f"Moment Ratio = {ratio:.3f} > 1.0 \u2014 **FAIL**")
