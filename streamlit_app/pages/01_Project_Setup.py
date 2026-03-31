"""Page 01 - Project Setup, Code Edition Selection, and Project Save/Load."""

import json

import streamlit as st

# Keys to save/load (all user inputs, no result objects)
SAVEABLE_KEYS = [
    # Project
    "project_name", "project_location", "project_number",
    "designer", "reviewer", "project_notes",
    # Code editions
    "asce_edition", "ibc_edition",
    # Wind
    "wind_speed", "exposure_category", "risk_category",
    "Kd", "Kzt", "Kz", "G", "Cf", "Ke",
    # Chain link
    "cl_post_type", "cl_post_group", "cl_trade_size",
    "cl_post_height", "cl_post_spacing",
    "cl_wire_gauge", "cl_mesh_size", "cl_mesh_weight", "cl_fos",
    "cl_gate_leaf_length", "cl_gate_leaf_height",
    "cl_gate_frame_diam", "cl_gate_frame_weight",
    # Wood
    "wood_post_type", "wood_species",
    "wood_post_diam", "wood_post_height", "wood_post_spacing",
    "wood_post_weight", "wood_wire_diam", "wood_mesh_size",
    "wood_mesh_weight", "wood_fos",
    "wood_gate_leaf_length", "wood_gate_leaf_height",
    "wood_gate_frame_diam", "wood_gate_frame_weight",
    # Spacing
    "sp_fence_height", "sp_post_group", "sp_post_od",
    "sp_wire_gauge", "sp_mesh_size", "sp_wind_speed",
    "sp_exposure", "sp_ice", "sp_actual_spacing",
    # Footing
    "ft_method", "ft_soil_bearing", "ft_footing_diam",
    "ft_fence_height", "ft_actual_depth",
]


def build_project_json() -> str:
    """Serialize saveable session state keys to JSON."""
    data = {}
    for key in SAVEABLE_KEYS:
        if key in st.session_state:
            data[key] = st.session_state[key]
    return json.dumps(data, indent=2, default=str)


st.header("Project Setup")

col1, col2 = st.columns(2)
with col1:
    st.text_input("Project Name", key="project_name")
    st.text_input("Project Location", key="project_location")
    st.text_input("Project Number", key="project_number")

with col2:
    st.text_input("Designer", key="designer")
    st.text_input("Reviewer", key="reviewer")

st.text_area("Notes", key="project_notes")

st.divider()
st.subheader("Design Code Editions")

col1, col2 = st.columns(2)
with col1:
    st.radio(
        "ASCE 7 Edition",
        ["ASCE 7-16", "ASCE 7-22"],
        key="asce_edition",
        help="ASCE 7-22 includes ground elevation factor Ke. CLFMI WLG 2023 is based on ASCE 7-22.",
    )

with col2:
    st.radio(
        "IBC Edition (for footing design)",
        ["IBC 2009", "IBC 2018"],
        key="ibc_edition",
    )

st.divider()
st.subheader("Project File")

save_col, load_col = st.columns(2)

with save_col:
    project_json = build_project_json()
    filename = st.session_state.get("project_name", "project").replace(" ", "_")
    st.download_button(
        label="Download Project File",
        data=project_json,
        file_name=f"{filename}.json",
        mime="application/json",
        type="primary",
    )

with load_col:
    uploaded = st.file_uploader("Load Project File", type=["json"])
    if uploaded is not None:
        cache_key = f"{uploaded.name}:{uploaded.size}"
        if st.session_state.get("_project_upload_key") != cache_key:
            try:
                data = json.loads(uploaded.read())
                for key in SAVEABLE_KEYS:
                    if key in data:
                        st.session_state[key] = data[key]
                st.session_state["_project_upload_key"] = cache_key
                # Clear previous results since inputs changed
                for rk in ["wind_result", "cl_result", "wood_result",
                           "spacing_result", "footing_result"]:
                    st.session_state[rk] = None
                st.success(f"Loaded project: {data.get('project_name', uploaded.name)}")
                st.rerun()
            except (json.JSONDecodeError, Exception) as e:
                st.error(f"Failed to load project file: {e}")

st.info(
    "**FORK** - Fence Optimization Resource Kit\n\n"
    "Navigate using the sidebar to configure wind parameters, "
    "design chain link or wood fence posts, check spacing, "
    "calculate footing depth, and export a PDF report."
)
