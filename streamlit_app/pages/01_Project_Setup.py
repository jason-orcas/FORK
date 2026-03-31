"""Page 01 — Project Setup and Code Edition Selection."""

import streamlit as st

st.header("Project Setup")

col1, col2 = st.columns(2)
with col1:
    st.session_state.project_name = st.text_input("Project Name", st.session_state.project_name)
    st.session_state.project_location = st.text_input("Project Location", st.session_state.project_location)
    st.session_state.project_number = st.text_input("Project Number", st.session_state.project_number)

with col2:
    st.session_state.designer = st.text_input("Designer", st.session_state.designer)
    st.session_state.reviewer = st.text_input("Reviewer", st.session_state.reviewer)

st.session_state.project_notes = st.text_area("Notes", st.session_state.project_notes)

st.divider()
st.subheader("Design Code Editions")

col1, col2 = st.columns(2)
with col1:
    st.session_state.asce_edition = st.radio(
        "ASCE 7 Edition",
        ["ASCE 7-16", "ASCE 7-22"],
        index=["ASCE 7-16", "ASCE 7-22"].index(st.session_state.asce_edition),
        help="ASCE 7-22 includes ground elevation factor Ke. CLFMI WLG 2023 is based on ASCE 7-22.",
    )

with col2:
    st.session_state.ibc_edition = st.radio(
        "IBC Edition (for footing design)",
        ["IBC 2009", "IBC 2018"],
        index=["IBC 2009", "IBC 2018"].index(st.session_state.ibc_edition),
    )

st.info(
    "**FORK** — Fence Optimization Resource Kit\n\n"
    "Navigate using the sidebar to configure wind parameters, "
    "design chain link or wood fence posts, check spacing, "
    "calculate footing depth, and export a PDF report."
)
