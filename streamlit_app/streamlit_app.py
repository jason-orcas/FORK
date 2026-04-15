"""FORK — Fence Optimization Resource Kit

Main Streamlit application entry point.
Run with: streamlit run streamlit_app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="FORK — Fence Optimization Resource Kit",
    page_icon="\U0001f3e1",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    """Initialize all session state defaults."""
    defaults = {
        # Project
        "project_name": "New Project",
        "project_location": "",
        "project_number": "",
        "designer": "",
        "reviewer": "",
        "project_notes": "",
        # Code editions
        "asce_edition": "ASCE 7-22",
        "ibc_edition": "IBC 2018",
        # Wind parameters
        "wind_speed": 100.0,
        "exposure_category": "C",
        "risk_category": "II",
        "Kd": 0.85,
        "Kzt": 1.0,
        "Kz": 0.85,
        "G": 0.85,
        "Cf": 1.3,
        "Ke": 1.0,
        # Chain link
        "cl_post_type": "line",
        "cl_post_group": "Group IA Regular (30 ksi)",
        "cl_trade_size": "2-3/8",
        "cl_post_height": 7.0,
        "cl_post_spacing": 10.0,
        "cl_wire_gauge": 11,
        "cl_mesh_size": 2.0,
        "cl_mesh_weight": 0.154,
        "cl_fos": 1.5,
        "cl_gate_leaf_length": 0.0,
        "cl_gate_leaf_height": 0.0,
        "cl_gate_frame_diam": 0.0,
        "cl_gate_frame_weight": 0.0,
        # Wood
        "wood_post_type": "line",
        "wood_species": "Douglas Fir",
        "wood_post_diam": 4.0,
        "wood_post_height": 8.0,
        "wood_post_spacing": 10.0,
        "wood_post_weight": 3.2,
        "wood_wire_diam": 0.192,
        "wood_mesh_size": 5.5,
        "wood_mesh_weight": 0.154,
        "wood_fos": 1.0,
        "wood_gate_leaf_length": 0.0,
        "wood_gate_leaf_height": 0.0,
        "wood_gate_frame_diam": 0.0,
        "wood_gate_frame_weight": 0.0,
        # Spacing
        "sp_fence_height": 6.0,
        "sp_post_group": "Group IA Regular (30 ksi)",
        "sp_post_od": 2.875,
        "sp_wire_gauge": 11,
        "sp_mesh_size": 2.0,
        "sp_wind_speed": 115.0,
        "sp_exposure": "C",
        "sp_ice": "none",
        "sp_actual_spacing": 10.0,
        "sp_s_override": None,
        # Footing
        "ft_method": "IBC",
        "ft_soil_bearing": 200.0,
        "ft_footing_diam": 1.5,
        "ft_fence_height": 7.0,
        "ft_actual_depth": 4.0,
        # Fence Run
        "fr_total_length": 200.0,
        "fr_post_spacing": 10.0,
        "fr_num_corners": 0,
        "fr_num_gates": 0,
        "fr_post_height": 7.0,
        "fr_post_weight": 3.65,
        "fr_footing_diam": 1.5,
        "fr_fabric_height": 6.0,
        "fr_has_top_rail": True,
        "fr_depth_line": 3.0,
        "fr_depth_pull": 3.5,
        "fr_depth_gate": 4.0,
        # Deflection limit
        "wood_defl_choice": "L/180",
        # Post Spacing extras
        "sp_use_override": False,
        "sp_override_val": 10.0,
        # Footing extras
        "ft_line_fence_height": 7.0,
        "ft_line_actual_depth": 3.0,
        "ft_post_calc_type": "Pull/Terminal Post",
        "ft_soil_choice": "Custom",
        "ft_apply_2x": True,
        "ft_soil_input_mode": "Simple",
        "ft_profile_derivation": "Engineering properties",
        # Soil profile
        "soil_layers": [],
        "water_table_depth": None,
        "axial_zones": [],
        "use_axial_zones": False,
        # Frost
        "frost_depth_in": 36.0,
        "frost_method": "Regional lookup",
        "frost_region": "Midwest",
        "frost_depth_manual": 36.0,
        "tau_af_psi": 0.0,
        "frost_result": None,
        # Optimizer
        "opt_fence_height": 7.0,
        "opt_wind_speed": 115.0,
        "opt_exposure": "C",
        "opt_ice": "none",
        "opt_wire_gauge": 11,
        "opt_mesh_size": 2.0,
        "opt_mesh_weight": 0.154,
        "opt_wire_diam": 0.192,
        "opt_wood_mesh_size": 5.5,
        "opt_wood_spacing": 10.0,
        "opt_soil_bearing": 200.0,
        "opt_footing_diam": 1.5,
        "opt_fos": 1.5,
        # Results
        "wind_result": None,
        "cl_result": None,
        "wood_result": None,
        "spacing_result": None,
        "footing_result": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def persist_widget_state():
    """Re-commit widget-keyed session state to prevent Streamlit from
    garbage-collecting widget values on multi-page navigation.

    Streamlit's MPA behavior can drop widget state for widgets that aren't
    currently rendered. Re-assigning the value to itself forces Streamlit
    to keep the entry around.

    This MUST run on every script rerun (before pg.run()), not just once.
    """
    persistent_keys = [
        # Project info
        "project_name", "project_location", "project_number",
        "designer", "reviewer", "project_notes",
        "asce_edition", "ibc_edition",
        # Wind parameters
        "wind_speed", "exposure_category", "risk_category",
        "Kd", "Kzt", "Kz", "G", "Cf", "Ke",
        # Chain link
        "cl_post_type_label", "cl_post_group", "cl_trade_size",
        "cl_post_height", "cl_post_spacing",
        "cl_wire_gauge", "cl_mesh_size", "cl_mesh_weight", "cl_fos",
        "cl_gate_leaf_length", "cl_gate_leaf_height",
        "cl_gate_frame_diam", "cl_gate_frame_weight",
        # Wood
        "wood_post_type_label", "wood_species",
        "wood_post_diam", "wood_post_height", "wood_post_spacing",
        "wood_post_weight", "wood_wire_diam", "wood_mesh_size",
        "wood_mesh_weight", "wood_fos", "wood_defl_choice",
        "wood_gate_leaf_length", "wood_gate_leaf_height",
        "wood_gate_frame_diam", "wood_gate_frame_weight",
        # Spacing
        "sp_fence_height", "sp_post_group", "sp_post_od",
        "sp_wire_gauge", "sp_mesh_size", "sp_wind_speed",
        "sp_exposure", "sp_ice", "sp_actual_spacing",
        "sp_use_override", "sp_override_val", "sp_post_label",
        # Footing
        "ft_method_label", "ft_soil_bearing", "ft_footing_diam",
        "ft_fence_height", "ft_actual_depth",
        "ft_soil_input_mode", "ft_profile_derivation",
        "ft_soil_choice", "ft_apply_2x",
        "ft_line_fence_height", "ft_line_actual_depth",
        "ft_post_calc_type",
        # Soil profile
        "soil_layers", "water_table_depth",
        "axial_zones", "use_axial_zones",
        # Frost
        "frost_depth_in", "frost_method", "frost_region",
        "frost_depth_manual", "tau_af_psi",
        # Fence Run
        "fr_total_length", "fr_post_spacing", "fr_num_corners",
        "fr_num_gates", "fr_post_height", "fr_post_weight",
        "fr_footing_diam", "fr_fabric_height", "fr_has_top_rail",
        "fr_depth_line", "fr_depth_pull", "fr_depth_gate",
        # Optimizer
        "opt_fence_type_label", "opt_fence_height", "opt_wind_speed",
        "opt_exposure", "opt_ice", "opt_wire_gauge", "opt_mesh_size",
        "opt_mesh_weight", "opt_wire_diam", "opt_wood_mesh_size",
        "opt_wood_spacing", "opt_soil_bearing", "opt_footing_diam", "opt_fos",
    ]
    for key in persistent_keys:
        if key in st.session_state:
            st.session_state[key] = st.session_state[key]


init_session_state()
persist_widget_state()

# Navigation
pages = {
    "Inputs": [
        st.Page("pages/01_Project_Setup.py", title="Project Setup", icon="\U0001f4cb"),
        st.Page("pages/02_Soil_Profile.py", title="Soil Profile", icon="\U0001f3d4"),
        st.Page("pages/03_Wind_Parameters.py", title="Wind Parameters", icon="\U0001f300"),
    ],
    "Design": [
        st.Page("pages/04_Chain_Link_Design.py", title="Chain Link Design", icon="\u26d3"),
        st.Page("pages/05_Wood_Fence_Design.py", title="Wood Fence Design", icon="\U0001f333"),
    ],
    "Analysis": [
        st.Page("pages/06_Post_Spacing.py", title="Post Spacing (CLFMI)", icon="\U0001f4cf"),
        st.Page("pages/07_Footing_Design.py", title="Footing Design", icon="\U0001f9f1"),
        st.Page("pages/09_Optimizer.py", title="Optimizer", icon="\u2699"),
    ],
    "Planning": [
        st.Page("pages/10_Fence_Run.py", title="Fence Run Planner", icon="\U0001f4d0"),
    ],
    "Output": [
        st.Page("pages/11_Export_Report.py", title="Export Report", icon="\U0001f4c4"),
    ],
}

pg = st.navigation(pages)
pg.run()
