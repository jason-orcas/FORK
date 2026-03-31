"""Page 02 — Wind Load Parameters and Velocity Pressure Calculation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from core.models import ASCEEdition, ExposureCategory, WindInput
from core.wind import calculate_velocity_pressure, get_kz

st.header("Wind Parameters")

asce = st.session_state.get("asce_edition", "ASCE 7-22")

# Apply pending auto-Kz value BEFORE the widget renders
if "_auto_kz" in st.session_state:
    st.session_state.Kz = st.session_state.pop("_auto_kz")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Basic Inputs")
    st.number_input(
        "Basic Wind Speed, V (mph)",
        min_value=50.0, max_value=300.0,
        key="wind_speed",
        help="Ultimate wind speed per ASCE 7. Use asce7hazardtool.online for site-specific values.",
    )
    st.selectbox(
        "Exposure Category",
        ["B", "C", "D"],
        key="exposure_category",
        help="B=Urban/suburban, C=Open terrain, D=Flat/unobstructed",
    )
    st.selectbox(
        "Risk Category",
        ["I", "II", "III", "IV"],
        key="risk_category",
    )

with col2:
    st.subheader("K-Factors")
    st.number_input(
        "Kd (Directionality)", key="Kd",
        min_value=0.1, max_value=2.0, step=0.01,
        help="ASCE 7 Table 26.6-1. Default 0.85 for open signs/lattice.",
    )
    st.number_input(
        "Kzt (Topographic)", key="Kzt",
        min_value=0.5, max_value=3.0, step=0.01,
        help="ASCE 7 Section 26.8. Default 1.0 (flat terrain).",
    )
    st.number_input(
        "Kz (Velocity Pressure Exposure)", key="Kz",
        min_value=0.1, max_value=3.0, step=0.01,
        help="ASCE 7 Table 26.10-1. Auto-lookup available below.",
    )

    # Auto Kz lookup — sets a flag and reruns; value applied at top of page
    exp_enum = ExposureCategory(st.session_state.exposure_category)
    if st.button("Auto-calculate Kz from Exposure & Height"):
        height = st.session_state.get("cl_post_height", 7.0)
        auto_kz = get_kz(exp_enum, height)
        st.session_state["_auto_kz"] = round(auto_kz, 2)
        st.rerun()

with col3:
    st.subheader("Force Coefficients")
    st.number_input(
        "G (Gust-Effect Factor)", key="G",
        min_value=0.1, max_value=2.0, step=0.01,
        help="ASCE 7 Section 26.11. Default 0.85.",
    )
    st.number_input(
        "Cf (Force Coefficient)", key="Cf",
        min_value=0.1, max_value=3.0, step=0.01,
        help="ASCE 7 Figure 29.3-1. CLFMI uses 1.458 average; spreadsheets use 1.3.",
    )
    if asce == "ASCE 7-22":
        st.number_input(
            "Ke (Ground Elevation)", key="Ke",
            min_value=0.5, max_value=1.5, step=0.01,
            help="ASCE 7-22 Table 26.9-1. Default 1.0 (sea level).",
        )
    else:
        st.session_state.Ke = 1.0

st.divider()

# Calculate
if st.button("Calculate Velocity Pressure", type="primary"):
    wind = WindInput(
        asce_edition=ASCEEdition(asce),
        wind_speed=st.session_state.wind_speed,
        exposure_category=exp_enum,
        risk_category=st.session_state.risk_category,
        Kd=st.session_state.Kd,
        Kzt=st.session_state.Kzt,
        Kz=st.session_state.Kz,
        G=st.session_state.G,
        Cf=st.session_state.Cf,
        Ke=st.session_state.Ke,
    )
    result = calculate_velocity_pressure(wind)
    st.session_state.wind_result = result

    st.success(f"**qz = {result.qz:.2f} psf**")
    st.code(result.formula_used, language=None)

elif st.session_state.get("wind_result") is not None:
    r = st.session_state.get("wind_result")
    st.info(f"**Previous result: qz = {r.qz:.2f} psf** ({r.asce_edition.value})")
