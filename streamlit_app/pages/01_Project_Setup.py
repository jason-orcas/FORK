"""Page 01 — Project Setup and Code Edition Selection."""

import streamlit as st

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

st.info(
    "**FORK** — Fence Optimization Resource Kit\n\n"
    "Navigate using the sidebar to configure wind parameters, "
    "design chain link or wood fence posts, check spacing, "
    "calculate footing depth, and export a PDF report."
)
