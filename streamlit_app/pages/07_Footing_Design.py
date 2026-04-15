"""Page 06 - Footing Design per Post Type.

Line posts: driven (no concrete), minimum embedment per ASTM F567.
Pull/terminal and gate posts: concrete footing per IBC Eq. 18-1 or ASTM F567.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from core.models import FootingInput, IBCEdition
from core.footing import calculate_footing_depth_ibc, calculate_footing_depth_astm_f567
from core.soil import SoilProfile, build_soil_layer_from_dict
from core.soil_lateral import (
    S1DerivationMethod,
    weighted_s1_for_footing,
    describe_s1_derivation,
)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Load soil types
with open(_DATA_DIR / "ibc_soil_table.json", encoding="utf-8") as f:
    _SOIL_DATA = json.load(f)
_SOIL_TYPES = {s["name"]: s["lateral_psf_per_ft"] for s in _SOIL_DATA["soil_types"]}

st.header("Footing Design")

st.info(
    "**Line posts** are typically driven (no concrete) with minimum embedment per ASTM F567. "
    "**Pull/terminal and gate posts** require concrete footings designed per IBC Eq. 18-1."
)

# --- Line Posts (Driven) ---
st.subheader("Line Posts (Driven - No Concrete)")

lc1, lc2 = st.columns(2)
with lc1:
    st.number_input("Fence Height for Line Posts (ft)", key="ft_line_fence_height",
        min_value=1.0, max_value=25.0, step=0.5)
with lc2:
    st.number_input("Actual Driven Depth (ft)", key="ft_line_actual_depth",
        min_value=0.5, max_value=12.0, step=0.25)

if st.button("Check Line Post Embedment", type="secondary"):
    # ASTM F567 minimum: 24" + 3" per foot over 4'
    H = st.session_state.ft_line_fence_height
    if H <= 4.0:
        min_depth_in = 24.0
    else:
        min_depth_in = 24.0 + 3.0 * (H - 4.0)
    min_depth_ft = min_depth_in / 12.0

    actual = st.session_state.ft_line_actual_depth

    st.write(f"**ASTM F567 Minimum Embedment:** {min_depth_in:.0f}\" ({min_depth_ft:.2f} ft)")
    st.write(f"**Actual Driven Depth:** {actual:.2f} ft")

    if actual >= min_depth_ft:
        st.success(f"Driven depth ({actual:.2f} ft) >= minimum ({min_depth_ft:.2f} ft) - **ADEQUATE**")
    else:
        st.error(f"Driven depth ({actual:.2f} ft) < minimum ({min_depth_ft:.2f} ft) - **NOT ADEQUATE**")

    st.caption("Line posts are driven without concrete. Embedment per ASTM F567 Section 8.1.")

st.divider()

# --- Pull/Terminal & Gate Posts (Concrete Footing) ---
st.subheader("Pull/Terminal & Gate Posts (Concrete Footing)")

if "ft_method_label" not in st.session_state:
    st.session_state.ft_method_label = "IBC Eq. 18-1"
st.radio("Calculation Method", ["IBC Eq. 18-1", "ASTM F567 (Simplified)"],
    key="ft_method_label", horizontal=True)
ft_method = "IBC" if "IBC" in st.session_state.ft_method_label else "ASTM F567"

# Post type sub-selector
post_calc_type = st.radio("Calculate For", ["Pull/Terminal Post", "Gate Post"],
    horizontal=True, key="ft_post_calc_type")

col1, col2 = st.columns(2)

with col1:
    st.number_input("Fence Height (ft)",
        key="ft_fence_height", min_value=1.0, max_value=25.0, step=0.5)
    st.number_input("Actual Footing Depth (ft)",
        key="ft_actual_depth", min_value=0.5, max_value=15.0, step=0.25)

if ft_method == "IBC":
    # Soil input mode toggle — Simple or Soil Profile
    st.radio(
        "Soil Input Mode",
        ["Simple", "Soil Profile"],
        key="ft_soil_input_mode",
        horizontal=True,
        help="Simple: manual lateral bearing entry or IBC Table 1806.2 lookup.\n"
             "Soil Profile: derive S1 from a layered soil model (define on Soil Profile page).",
    )

    with col2:
        if st.session_state.ft_soil_input_mode == "Simple":
            # --- Simple mode: IBC dropdown + manual S1 (original behavior) ---
            soil_names = ["Custom"] + list(_SOIL_TYPES.keys())
            st.selectbox("Soil Type (IBC Table 1806.2)", soil_names, key="ft_soil_choice",
                help="Select soil type to auto-fill lateral bearing pressure, or choose Custom.")
            soil_choice = st.session_state.ft_soil_choice

            if soil_choice != "Custom":
                base_pressure = _SOIL_TYPES[soil_choice]
                st.caption(f"Base lateral bearing: {base_pressure} psf/ft")
            else:
                base_pressure = None

            st.checkbox("Apply 2x for isolated fence posts (IBC 1806.3.4)", key="ft_apply_2x",
                help="IBC 1806.3.4: Isolated poles not adversely affected by 1/2\" "
                     "ground motion from short-term lateral loads may use 2x lateral bearing.")
            apply_2x = st.session_state.ft_apply_2x

            if base_pressure is not None:
                effective = base_pressure * (2 if apply_2x else 1)
                st.session_state.ft_soil_bearing = float(effective)
                st.caption(f"Effective lateral bearing: **{effective} psf**"
                           + (" (2x applied)" if apply_2x else ""))

            st.number_input("Allowable Lateral Soil Bearing (psf)",
                key="ft_soil_bearing", min_value=50.0, max_value=5000.0, step=25.0)

        else:
            # --- Soil Profile mode: compute S1 from layered profile ---
            soil_layers = st.session_state.get("soil_layers", [])
            if not soil_layers:
                st.warning(
                    "No soil layers defined. Go to the **Soil Profile** page "
                    "(under Inputs) to define your soil stratigraphy, then return here."
                )
                st.session_state.ft_soil_bearing = 100.0
            else:
                st.radio(
                    "S1 Derivation Method",
                    ["Engineering properties", "IBC Table 1806.2"],
                    key="ft_profile_derivation",
                    horizontal=True,
                    help="Engineering: Rankine Kp for sand, 9*cu/10 for clay, using SPT "
                         "correlations if phi/cu not entered.\n"
                         "IBC Table: maps SoilType to presumptive values from IBC 1806.2.",
                )

                # Build the profile and compute S1
                try:
                    layer_objs = [build_soil_layer_from_dict(ld) for ld in soil_layers]
                    profile = SoilProfile(
                        layers=layer_objs,
                        water_table_depth=st.session_state.get("water_table_depth"),
                    )
                    method = (
                        S1DerivationMethod.ENGINEERING
                        if st.session_state.ft_profile_derivation == "Engineering properties"
                        else S1DerivationMethod.IBC_TABLE
                    )
                    footing_depth = st.session_state.get("ft_actual_depth", 4.0)
                    s1_computed = weighted_s1_for_footing(profile, footing_depth, method)

                    # Optional 2x multiplier still applies
                    st.checkbox(
                        "Apply 2x for isolated fence posts (IBC 1806.3.4)",
                        key="ft_apply_2x",
                    )
                    apply_2x = st.session_state.ft_apply_2x
                    s1_effective = s1_computed * (2 if apply_2x else 1)
                    st.session_state.ft_soil_bearing = float(s1_effective)

                    st.metric(
                        "Computed Lateral Bearing S1",
                        f"{s1_effective:.0f} psf/ft",
                        help="Weighted average across the footing depth."
                             + (" (2x applied)" if apply_2x else ""),
                    )

                    # Show per-layer breakdown
                    with st.expander("S1 Derivation Breakdown"):
                        rows = describe_s1_derivation(profile, footing_depth, method)
                        if rows:
                            df = pd.DataFrame([
                                {
                                    "Layer (ft)": f"{r['top_ft']:.1f} - {r['bot_ft']:.1f}",
                                    "Soil": r["soil_type"],
                                    "Thickness (ft)": f"{r['thickness_ft']:.2f}",
                                    "S1 (psf/ft)": f"{r['s1_psf_per_ft']:.0f}",
                                    "Weight": f"{r['weight_fraction']:.1%}",
                                }
                                for r in rows
                            ])
                            st.dataframe(df, width="stretch", hide_index=True)
                        st.caption(
                            "S1 is computed per layer and weighted by thickness "
                            "within the footing embedment depth."
                        )
                except Exception as e:
                    st.error(f"Failed to compute S1 from profile: {e}")
                    st.session_state.ft_soil_bearing = 100.0

        st.number_input("Footing Diameter (ft)",
            key="ft_footing_diam", min_value=0.5, max_value=5.0, step=0.25,
            help="ASTM F567: 3x pipe OD (min 12\"). CLFMI recommends 30\" for high wind.")

    st.divider()

    if st.button("Calculate Footing Depth", type="primary"):
        footing = FootingInput(
            ibc_edition=IBCEdition(st.session_state.get("ibc_edition", "IBC 2018")),
            soil_bearing_pressure=st.session_state.ft_soil_bearing,
            footing_diameter=st.session_state.ft_footing_diam,
            fence_height=st.session_state.ft_fence_height,
            actual_depth=st.session_state.ft_actual_depth,
        )

        # Get wind force — use the appropriate post type result
        P = 0.0
        cl_result = st.session_state.get("cl_result")
        wood_result = st.session_state.get("wood_result")
        if cl_result is not None:
            P = cl_result.shear
        elif wood_result is not None:
            P = wood_result.shear

        # Gate posts see higher loads (free head, eccentricity)
        if post_calc_type == "Gate Post" and P > 0:
            st.caption("Using wind shear from design page. Gate posts may have "
                       "additional dead load eccentricity from gate leaf.")

        if P <= 0:
            st.warning("No wind shear available. Run Chain Link or Wood Fence design first, "
                       "or enter a manual wind force below.")
            P = st.number_input("Manual Wind Force P (lb)", value=100.0, min_value=0.0)

        result = calculate_footing_depth_ibc(footing, P)
        st.session_state.footing_result = result

        st.subheader(f"Results - {post_calc_type}")
        st.latex(r"A = \frac{2.34 P}{S_1 \cdot d} = " + f"{result.A_intermediate:.3f}")
        st.latex(r"c = 0.55 \times H = " + f"{result.c_arm:.2f} \\text{{ ft}}")
        st.latex(r"D = 0.5A \left\{1 + \sqrt{1 + \frac{4.36c}{A}}\right\} = " + f"{result.D_calc:.2f} \\text{{ ft}}")

        rc1, rc2 = st.columns(2)
        rc1.metric("Required Depth", f"{result.D_calc:.2f} ft")
        rc2.metric("Actual Depth", f"{result.D_actual:.2f} ft")

        if result.is_adequate:
            st.success(f"Actual ({result.D_actual:.2f} ft) >= Required ({result.D_calc:.2f} ft) - **ADEQUATE**")
        else:
            st.error(f"Actual ({result.D_actual:.2f} ft) < Required ({result.D_calc:.2f} ft) - **NOT ADEQUATE**")

else:
    st.divider()

    if st.button("Calculate Footing Depth", type="primary"):
        footing = FootingInput(
            fence_height=st.session_state.ft_fence_height,
            actual_depth=st.session_state.ft_actual_depth,
        )
        result = calculate_footing_depth_astm_f567(footing)
        st.session_state.footing_result = result

        st.subheader(f"Results - {post_calc_type}")
        H = st.session_state.ft_fence_height
        if H > 4.0:
            st.latex(r"D = 24'' + 3'' \times (H - 4') = 24 + 3 \times " + f"({H:.1f} - 4) = {result.D_calc * 12:.0f}''")
        else:
            st.latex(r"D = 24'' \\text{{ (minimum)}}")

        rc1, rc2 = st.columns(2)
        rc1.metric("Required Depth", f"{result.D_calc:.2f} ft ({result.D_calc * 12:.0f} in)")
        rc2.metric("Actual Depth", f"{result.D_actual:.2f} ft")

        if result.is_adequate:
            st.success(f"Actual ({result.D_actual:.2f} ft) >= Required ({result.D_calc:.2f} ft) - **ADEQUATE**")
        else:
            st.error(f"Actual ({result.D_actual:.2f} ft) < Required ({result.D_calc:.2f} ft) - **NOT ADEQUATE**")
