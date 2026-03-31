"""FORK — Fence Optimization Resource Kit

Main Streamlit application entry point.
Run with: streamlit run streamlit_app/streamlit_app.py
"""

import streamlit as st

st.set_page_config(
    page_title="FORK — Fence Optimization Resource Kit",
    page_icon=":fence:",
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


init_session_state()

# Navigation
pages = {
    "Inputs": [
        st.Page("pages/01_Project_Setup.py", title="Project Setup", icon=":clipboard:"),
        st.Page("pages/02_Wind_Parameters.py", title="Wind Parameters", icon=":cyclone:"),
    ],
    "Design": [
        st.Page("pages/03_Chain_Link_Design.py", title="Chain Link Design", icon=":chains:"),
        st.Page("pages/04_Wood_Fence_Design.py", title="Wood Fence Design", icon=":deciduous_tree:"),
    ],
    "Analysis": [
        st.Page("pages/05_Post_Spacing.py", title="Post Spacing (CLFMI)", icon=":straight_ruler:"),
        st.Page("pages/06_Footing_Design.py", title="Footing Design", icon=":brick:"),
    ],
    "Output": [
        st.Page("pages/07_Export_Report.py", title="Export Report", icon=":page_facing_up:"),
    ],
}

pg = st.navigation(pages)
pg.run()
