"""Page 04 — Wood Fence Post Design (NDS 2018)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from core.models import (
    ASCEEdition,
    ExposureCategory,
    PostType,
    WindInput,
    WoodFenceInput,
    WoodSpecies,
)
from core.wood import calculate_wood_post

st.header("Wood Fence Post Design")
st.caption("NDS 2018 — National Design Specification for Wood Construction")

# Post type selector
post_types = {"Line Post": "line", "Pull/Terminal Post": "pull", "Gate Post": "gate"}
selected_type = st.radio("Post Type", list(post_types.keys()), horizontal=True)
st.session_state.wood_post_type = post_types[selected_type]

# Auto-set FoS default based on post type
if st.session_state.wood_post_type == "gate":
    default_fos = 2.0
else:
    default_fos = 1.0

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Post Properties")
    st.selectbox("Wood Species", ["Douglas Fir"], key="wood_species",
        help="Additional species can be added to data/wood_species.json")
    st.number_input("Post Diameter (in)",
        key="wood_post_diam", min_value=1.0, max_value=24.0, step=0.5)
    st.number_input("Post Weight (plf)",
        key="wood_post_weight", min_value=0.1, max_value=50.0, step=0.1)

with col2:
    st.subheader("Geometry")
    st.number_input("Post Height (ft)",
        key="wood_post_height", min_value=1.0, max_value=25.0, step=0.5)
    st.number_input("Post Spacing (ft)",
        key="wood_post_spacing", min_value=1.0, max_value=30.0, step=0.5)

with col3:
    st.subheader("Mesh/Fabric")
    st.number_input("Wire Diameter (in)",
        key="wood_wire_diam", min_value=0.01, max_value=0.5, step=0.001, format="%.3f")
    st.number_input("Mesh Size (in)",
        key="wood_mesh_size", min_value=0.25, max_value=10.0, step=0.25)
    st.number_input("Mesh Weight (psf)",
        key="wood_mesh_weight", min_value=0.01, max_value=5.0, step=0.01, format="%.3f")

# Gate-specific inputs
if st.session_state.wood_post_type == "gate":
    st.subheader("Gate Leaf Properties")
    gc1, gc2 = st.columns(2)
    with gc1:
        st.number_input("Gate Leaf Length (ft)",
            key="wood_gate_leaf_length", min_value=0.0, max_value=30.0, step=0.25)
        st.number_input("Gate Leaf Height (ft)",
            key="wood_gate_leaf_height", min_value=0.0, max_value=25.0, step=0.25)
    with gc2:
        st.number_input("Gate Frame Post Diam (in)",
            key="wood_gate_frame_diam", min_value=0.0, max_value=10.0, step=0.125)
        st.number_input("Gate Frame Post Weight (plf)",
            key="wood_gate_frame_weight", min_value=0.0, max_value=30.0, step=0.01)

st.number_input("Factor of Safety", key="wood_fos",
    min_value=0.5, max_value=5.0, step=0.1,
    help=f"Default: {default_fos:.1f} for {selected_type.lower()}")

defl_options = {"L/60": 60, "L/120": 120, "L/180": 180, "L/240": 240, "No Limit": 0}
defl_choice = st.selectbox("Deflection Limit", list(defl_options.keys()), index=2,
    help="Allowable deflection = post height / selected ratio. Common: L/120 to L/240.")

st.divider()

if st.button("Calculate", type="primary"):
    if st.session_state.wind_result is None:
        st.error("Please calculate wind parameters first (Wind Parameters page).")
    else:
        wind = WindInput(
            asce_edition=ASCEEdition(st.session_state.asce_edition),
            wind_speed=st.session_state.wind_speed,
            exposure_category=ExposureCategory(st.session_state.exposure_category),
            Kd=st.session_state.Kd, Kzt=st.session_state.Kzt, Kz=st.session_state.Kz,
            G=st.session_state.G, Cf=st.session_state.Cf, Ke=st.session_state.Ke,
        )

        wood = WoodFenceInput(
            post_type=PostType(st.session_state.wood_post_type),
            species=WoodSpecies(st.session_state.wood_species),
            post_diameter=st.session_state.wood_post_diam,
            post_height=st.session_state.wood_post_height,
            post_spacing=st.session_state.wood_post_spacing,
            post_weight=st.session_state.wood_post_weight,
            wire_diameter=st.session_state.wood_wire_diam,
            mesh_size=st.session_state.wood_mesh_size,
            mesh_weight=st.session_state.wood_mesh_weight,
            gate_leaf_length=st.session_state.wood_gate_leaf_length,
            gate_leaf_height=st.session_state.wood_gate_leaf_height,
            gate_frame_post_diam=st.session_state.wood_gate_frame_diam,
            gate_frame_post_weight=st.session_state.wood_gate_frame_weight,
            fos=st.session_state.wood_fos,
        )

        result = calculate_wood_post(wind, wood)
        st.session_state.wood_result = result

        # Load results
        st.subheader("Applied Loads")
        lc1, lc2, lc3 = st.columns(3)
        lc1.metric("Axial Load", f"{result.axial_load:.1f} lb")
        lc2.metric("Shear", f"{result.shear:.1f} lb")
        lc3.metric("Moment", f"{result.moment:.1f} lb-ft")

        # NDS Stress Analysis Table
        st.subheader("NDS 2018 Stress Analysis")
        stress_data = {
            "Stress Type": ["Compression (fc)", "Bending (fb)", "Shear (fv)"],
            "Applied (psi)": [f"{result.fc:.1f}", f"{result.fb:.1f}", f"{result.fv:.1f}"],
            "Allowable (psi)": [f"{result.Fc_prime:.1f}", f"{result.Fb_prime:.1f}", f"{result.Fv_prime:.1f}"],
            "Ratio": [f"{result.compression_ratio:.3f}", f"{result.bending_ratio:.3f}", f"{result.shear_ratio:.3f}"],
            "Status": [
                "PASS" if result.compression_ratio <= 1.0 else "FAIL",
                "PASS" if result.bending_ratio <= 1.0 else "FAIL",
                "PASS" if result.shear_ratio <= 1.0 else "FAIL",
            ],
        }
        st.dataframe(pd.DataFrame(stress_data), width="stretch", hide_index=True)

        # Adjustment factors
        st.subheader("NDS Adjustment Factors")
        factors_data = {
            "Factor": ["Cd (Duration)", "Ct (Temperature)", "Cct (Incising)",
                       "Cf (Size)", "Cp (Column Stability)", "Ccs (Round Section)",
                       "Cls (Lateral Stability)", "Cb (Bearing)"],
            "Value": [f"{result.Cd:.2f}", f"{result.Ct:.2f}", f"{result.Cct:.2f}",
                      f"{result.Cf:.2f}", f"{result.Cp:.4f}", f"{result.Ccs:.2f}",
                      f"{result.Cls:.2f}", f"{result.Cb:.2f}"],
            "Reference": ["NDS 2.3.2", "NDS 2.3.3", "NDS Table 4.3.8",
                          "NDS Table 6.3.1", "NDS 3.7.1", "NDS 6.3.11",
                          "NDS 3.3.3", "NDS 3.10.4"],
        }
        st.dataframe(pd.DataFrame(factors_data), width="stretch", hide_index=True)

        # Combined stress and deflection
        st.subheader("Combined Check")
        combined = result.combined_ratio
        if combined <= 0.9:
            st.success(f"Combined Ratio = {combined:.3f} \u2264 1.0 \u2014 **PASS** (NDS 3.9.2)")
        elif combined <= 1.0:
            st.warning(f"Combined Ratio = {combined:.3f} \u2264 1.0 \u2014 **MARGINAL** (NDS 3.9.2)")
        else:
            st.error(f"Combined Ratio = {combined:.3f} > 1.0 \u2014 **FAIL** (NDS 3.9.2)")

        # Deflection check
        st.subheader("Deflection Check")
        defl_ratio = defl_options[defl_choice]
        height_in = st.session_state.wood_post_height * 12.0
        if defl_ratio > 0:
            allowable_defl = height_in / defl_ratio
            defl_unity = result.deflection / allowable_defl if allowable_defl > 0 else 0
            dc1, dc2, dc3 = st.columns(3)
            dc1.metric("Actual Deflection", f"{result.deflection:.3f} in")
            dc2.metric("Allowable ({})".format(defl_choice), f"{allowable_defl:.3f} in")
            dc3.metric("Deflection Ratio", f"{defl_unity:.3f}")
            if defl_unity <= 0.9:
                st.success(f"Deflection ratio = {defl_unity:.3f} <= 1.0 - **PASS**")
            elif defl_unity <= 1.0:
                st.warning(f"Deflection ratio = {defl_unity:.3f} <= 1.0 - **MARGINAL**")
            else:
                st.error(f"Deflection ratio = {defl_unity:.3f} > 1.0 - **FAIL**")
        else:
            st.metric("Deflection at Top", f"{result.deflection:.3f} in")
            st.caption("No deflection limit applied.")
