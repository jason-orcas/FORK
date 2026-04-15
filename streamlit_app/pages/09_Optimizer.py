"""Page 08 - Post Optimization Tool.

Sweeps all available post sizes for given site conditions and ranks
results by lightest passing post with maximum spacing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from core.models import (
    ASCEEdition,
    ExposureCategory,
    FootingInput,
    IBCEdition,
    IceExposure,
    WindInput,
    WoodSpecies,
)
from core.optimize import optimize_chain_link, optimize_wood

st.header("Post Optimizer")
st.caption("Finds the lightest post that passes all structural checks for your site conditions.")

# Fence type selector
if "opt_fence_type_label" not in st.session_state:
    st.session_state.opt_fence_type_label = "Chain Link"
st.radio("Fence Type", ["Chain Link", "Wood"], key="opt_fence_type_label", horizontal=True)
fence_type = st.session_state.opt_fence_type_label

col1, col2 = st.columns(2)

with col1:
    st.subheader("Site Conditions")
    st.number_input("Fence Height (ft)", key="opt_fence_height",
        min_value=3.0, max_value=20.0, step=0.5)
    st.number_input("Wind Speed (mph)", key="opt_wind_speed",
        min_value=50.0, max_value=210.0, step=5.0)
    st.selectbox("Exposure Category", ["B", "C", "D"], key="opt_exposure")
    st.selectbox("Ice Exposure", ["none", "moderate", "heavy"], key="opt_ice")

with col2:
    st.subheader("Mesh & Footing")
    if fence_type == "Chain Link":
        st.number_input("Wire Gauge", key="opt_wire_gauge",
            min_value=5, max_value=14, step=1)
        st.number_input("Mesh Size (in)", key="opt_mesh_size",
            min_value=0.25, max_value=4.0, step=0.25)
    else:
        st.number_input("Wire Diameter (in)", key="opt_wire_diam",
            min_value=0.01, max_value=0.5, step=0.001, format="%.3f")
        st.number_input("Mesh Size (in)", key="opt_wood_mesh_size",
            min_value=0.25, max_value=10.0, step=0.25)
        st.number_input("Post Spacing (ft)", key="opt_wood_spacing",
            min_value=4.0, max_value=20.0, step=0.5,
            help="Fixed spacing for wood fence optimization")

    st.number_input("Mesh Weight (psf)", key="opt_mesh_weight",
        min_value=0.01, max_value=5.0, step=0.01, format="%.3f")
    st.number_input("Soil Bearing Pressure (psf)", key="opt_soil_bearing",
        min_value=50.0, max_value=2000.0, step=25.0)
    st.number_input("Footing Diameter (ft)", key="opt_footing_diam",
        min_value=0.5, max_value=5.0, step=0.25)
    st.number_input("Factor of Safety", key="opt_fos",
        min_value=0.5, max_value=5.0, step=0.1)

st.divider()

if st.button("Optimize", type="primary"):
    wind = WindInput(
        asce_edition=ASCEEdition(st.session_state.get("asce_edition", "ASCE 7-22")),
        wind_speed=st.session_state.opt_wind_speed,
        exposure_category=ExposureCategory(st.session_state.opt_exposure),
        Kd=st.session_state.get("Kd", 0.85),
        Kzt=st.session_state.get("Kzt", 1.0),
        Kz=st.session_state.get("Kz", 0.85),
        G=st.session_state.get("G", 0.85),
        Cf=st.session_state.get("Cf", 1.3),
        Ke=st.session_state.get("Ke", 1.0),
    )
    footing = FootingInput(
        ibc_edition=IBCEdition(st.session_state.get("ibc_edition", "IBC 2018")),
        soil_bearing_pressure=st.session_state.opt_soil_bearing,
        footing_diameter=st.session_state.opt_footing_diam,
        fence_height=st.session_state.opt_fence_height,
        actual_depth=10.0,  # generous actual for optimizer comparison
    )

    if fence_type == "Chain Link":
        results = optimize_chain_link(
            wind=wind,
            fence_height=st.session_state.opt_fence_height,
            wire_gauge=st.session_state.opt_wire_gauge,
            mesh_size=st.session_state.opt_mesh_size,
            mesh_weight=st.session_state.opt_mesh_weight,
            exposure=ExposureCategory(st.session_state.opt_exposure),
            ice=IceExposure(st.session_state.opt_ice),
            footing_input=footing,
            fos=st.session_state.opt_fos,
        )

        passing = [r for r in results if r.passes]
        st.write(f"**{len(results)} combinations checked, {len(passing)} pass all checks.**")

        # Diagnostic feedback when nothing passes
        if not passing:
            st.error("**No post combinations pass all checks.**")
            with st.expander("Why did all combinations fail?", expanded=True):
                # Group failure reasons
                overstressed = [r for r in results if "overstressed" in getattr(r, "failure_reason", "").lower()]
                moment_fail = [r for r in results if "moment demand" in getattr(r, "failure_reason", "").lower()]

                if overstressed:
                    st.write(
                        f"- **{len(overstressed)} posts were overstressed** per the CLFMI "
                        f"Table 16 allowable moment at this fence height and wind speed."
                    )
                if moment_fail:
                    st.write(
                        f"- **{len(moment_fail)} posts** had moment demand exceeding "
                        f"their allowable moment at the calculated spacing."
                    )

                # Show the single failure reason closest to passing
                closest = min(
                    (r for r in results if r.moment_ratio > 0),
                    key=lambda r: r.moment_ratio,
                    default=None,
                )
                if closest:
                    st.write(
                        f"- **Closest to passing:** {closest.trade_size}\" "
                        f"{closest.post_group} with moment ratio {closest.moment_ratio:.2f}. "
                        f"{closest.failure_reason}"
                    )

                st.markdown("**Try one or more:**")
                st.markdown(
                    "- **Reduce fence height** (taller fences mean more wind moment)\n"
                    "- **Reduce wind speed** if overly conservative (check ASCE 7 Hazard Tool)\n"
                    "- **Lower exposure category** if the site is sheltered (B vs C vs D)\n"
                    "- **Use higher-strength post group** (Group IA High Strength 50 ksi vs Regular 30 ksi)\n"
                    "- **Reduce FoS** if it was set above the CLFMI default of 1.5\n"
                    "- **Check ice exposure** — heavy ice reduces allowable spacing significantly\n"
                    "- **Use denser mesh/smaller wire** to reduce the Cf1 projected area"
                )

        # Build dataframe (include failure reason column)
        rows = []
        for r in results:
            rows.append({
                "Status": "\u2705 OPTIMAL" if r.is_optimal else ("\u2705 Pass" if r.passes else "\u274c Fail"),
                "Post Group": r.post_group.replace(" (30 ksi)", "").replace(" (50 ksi)", ""),
                "Trade Size": r.trade_size + '"',
                "OD (in)": f"{r.post_od:.3f}",
                "Weight (plf)": f"{r.weight_plf:.2f}",
                "Mallow (kip-ft)": f"{r.Mallow_kipft:.2f}",
                "Max Spacing S' (ft)": f"{r.max_spacing:.1f}" if r.max_spacing > 0 else "-",
                "Moment Ratio": f"{r.moment_ratio:.3f}" if r.moment_ratio > 0 else "-",
                "Footing Depth (ft)": f"{r.footing_depth_ft:.2f}" if r.footing_depth_ft > 0 else "-",
                "Notes": getattr(r, "failure_reason", "") if not r.passes else "",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)

        # Highlight optimal
        optimal = next((r for r in results if r.is_optimal), None)
        if optimal:
            st.success(
                f"**Optimal:** {optimal.trade_size}\" {optimal.post_group} "
                f"@ {optimal.max_spacing:.1f} ft spacing, "
                f"{optimal.weight_plf:.2f} plf, "
                f"moment ratio = {optimal.moment_ratio:.3f}, "
                f"footing depth = {optimal.footing_depth_ft:.2f} ft"
            )

    else:
        # Wood optimization
        results = optimize_wood(
            wind=wind,
            fence_height=st.session_state.opt_fence_height,
            post_spacing=st.session_state.opt_wood_spacing,
            wire_diam=st.session_state.opt_wire_diam,
            mesh_size=st.session_state.opt_wood_mesh_size,
            mesh_weight=st.session_state.opt_mesh_weight,
            footing_input=footing,
            fos=st.session_state.opt_fos,
        )

        passing = [r for r in results if r.passes]
        st.write(f"**{len(results)} diameters checked, {len(passing)} pass all checks.**")

        # Diagnostic feedback when nothing passes
        if not passing:
            st.error("**No wood post diameters pass all checks.**")
            with st.expander("Why did all diameters fail?", expanded=True):
                closest = min(
                    results,
                    key=lambda r: r.combined_ratio if r.combined_ratio > 0 else 999,
                    default=None,
                )
                if closest:
                    st.write(
                        f"- **Closest to passing:** {closest.trade_size} with combined "
                        f"ratio {closest.combined_ratio:.2f}. {closest.failure_reason}"
                    )

                # Check which ratio is the binding constraint
                combined_fails = sum(1 for r in results if r.combined_ratio > 1.0)
                shear_fails = sum(1 for r in results if r.shear_ratio > 1.0)
                if combined_fails:
                    st.write(f"- **{combined_fails} diameters failed combined stress** "
                             "(NDS 3.9.2 axial + bending interaction)")
                if shear_fails:
                    st.write(f"- **{shear_fails} diameters failed shear**")

                st.markdown("**Try one or more:**")
                st.markdown(
                    "- **Reduce fence height** to reduce wind moment\n"
                    "- **Reduce post spacing** (more posts = less tributary wind area per post)\n"
                    "- **Reduce wind speed** if overly conservative\n"
                    "- **Reduce FoS** if above the default 1.0/2.0\n"
                    "- **Check mesh density** — denser mesh increases projected area"
                )

        rows = []
        for r in results:
            rows.append({
                "Status": "\u2705 OPTIMAL" if r.is_optimal else ("\u2705 Pass" if r.passes else "\u274c Fail"),
                "Diameter (in)": r.trade_size,
                "Weight (plf)": f"{r.weight_plf:.1f}",
                "Combined Ratio": f"{r.combined_ratio:.3f}",
                "Shear Ratio": f"{r.shear_ratio:.3f}",
                "Deflection (in)": f"{r.deflection_in:.3f}",
                "Footing Depth (ft)": f"{r.footing_depth_ft:.2f}",
                "Notes": getattr(r, "failure_reason", "") if not r.passes else "",
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, width="stretch", hide_index=True)

        optimal = next((r for r in results if r.is_optimal), None)
        if optimal:
            st.success(
                f"**Optimal:** {optimal.trade_size} Douglas Fir "
                f"@ {optimal.max_spacing:.1f} ft spacing, "
                f"combined ratio = {optimal.combined_ratio:.3f}, "
                f"deflection = {optimal.deflection_in:.3f} in, "
                f"footing depth = {optimal.footing_depth_ft:.2f} ft"
            )
