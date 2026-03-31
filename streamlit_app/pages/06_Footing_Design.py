"""Page 06 — Footing Depth Calculation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

from core.models import FootingInput, IBCEdition
from core.footing import calculate_footing_depth_ibc, calculate_footing_depth_astm_f567

st.header("Footing Design")

method = st.radio("Calculation Method", ["IBC Eq. 18-1", "ASTM F567 (Simplified)"],
    horizontal=True)
st.session_state.ft_method = "IBC" if "IBC" in method else "ASTM F567"

col1, col2 = st.columns(2)

with col1:
    st.session_state.ft_fence_height = st.number_input("Fence Height (ft)",
        value=st.session_state.ft_fence_height, min_value=1.0, max_value=25.0, step=0.5)
    st.session_state.ft_actual_depth = st.number_input("Actual Footing Depth (ft)",
        value=st.session_state.ft_actual_depth, min_value=0.5, max_value=15.0, step=0.25)

if st.session_state.ft_method == "IBC":
    with col2:
        st.session_state.ft_soil_bearing = st.number_input("Allowable Lateral Soil Bearing (psf)",
            value=st.session_state.ft_soil_bearing, min_value=50.0, max_value=2000.0, step=25.0,
            help="IBC Table 1806.2. Clay ~100 psf/ft, Sand ~150-200 psf/ft, Gravel ~200 psf/ft.")
        st.session_state.ft_footing_diam = st.number_input("Footing Diameter (ft)",
            value=st.session_state.ft_footing_diam, min_value=0.5, max_value=5.0, step=0.25,
            help="ASTM F567: 3x pipe OD (min 12\"). CLFMI recommends 30\" for high wind.")

    st.divider()

    if st.button("Calculate Footing Depth", type="primary"):
        footing = FootingInput(
            ibc_edition=IBCEdition(st.session_state.ibc_edition),
            soil_bearing_pressure=st.session_state.ft_soil_bearing,
            footing_diameter=st.session_state.ft_footing_diam,
            fence_height=st.session_state.ft_fence_height,
            actual_depth=st.session_state.ft_actual_depth,
        )

        # Get wind force from chain link or wood result
        P = 0.0
        if st.session_state.cl_result is not None:
            P = st.session_state.cl_result.shear
        elif st.session_state.wood_result is not None:
            P = st.session_state.wood_result.shear

        if P <= 0:
            st.warning("No wind shear available. Run Chain Link or Wood Fence design first, "
                       "or enter a manual wind force below.")
            P = st.number_input("Manual Wind Force P (lb)", value=100.0, min_value=0.0)

        result = calculate_footing_depth_ibc(footing, P)
        st.session_state.footing_result = result

        st.subheader("Results")
        st.latex(r"A = \frac{2.34 P}{S_1 \cdot d} = " + f"{result.A_intermediate:.3f}")
        st.latex(r"c = 0.55 \times H = " + f"{result.c_arm:.2f} \text{{ ft}}")
        st.latex(r"D = 0.5A \left\{1 + \sqrt{1 + \frac{4.36c}{A}}\right\} = " + f"{result.D_calc:.2f} \text{{ ft}}")

        rc1, rc2 = st.columns(2)
        rc1.metric("Required Depth", f"{result.D_calc:.2f} ft")
        rc2.metric("Actual Depth", f"{result.D_actual:.2f} ft")

        if result.is_adequate:
            st.success(f"Actual ({result.D_actual:.2f} ft) \u2265 Required ({result.D_calc:.2f} ft) \u2014 **ADEQUATE**")
        else:
            st.error(f"Actual ({result.D_actual:.2f} ft) < Required ({result.D_calc:.2f} ft) \u2014 **NOT ADEQUATE**")

else:
    st.divider()

    if st.button("Calculate Footing Depth", type="primary"):
        footing = FootingInput(
            fence_height=st.session_state.ft_fence_height,
            actual_depth=st.session_state.ft_actual_depth,
        )
        result = calculate_footing_depth_astm_f567(footing)
        st.session_state.footing_result = result

        st.subheader("Results")
        H = st.session_state.ft_fence_height
        if H > 4.0:
            st.latex(r"D = 24'' + 3'' \times (H - 4') = 24 + 3 \times " + f"({H:.1f} - 4) = {result.D_calc * 12:.0f}''")
        else:
            st.latex(r"D = 24'' \text{ (minimum)}")

        rc1, rc2 = st.columns(2)
        rc1.metric("Required Depth", f"{result.D_calc:.2f} ft ({result.D_calc * 12:.0f} in)")
        rc2.metric("Actual Depth", f"{result.D_actual:.2f} ft")

        if result.is_adequate:
            st.success(f"Actual ({result.D_actual:.2f} ft) \u2265 Required ({result.D_calc:.2f} ft) \u2014 **ADEQUATE**")
        else:
            st.error(f"Actual ({result.D_actual:.2f} ft) < Required ({result.D_calc:.2f} ft) \u2014 **NOT ADEQUATE**")
