"""Page 07 — Export PDF Report."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st

st.header("Export Report")

# Status checklist
st.subheader("Analysis Status")

checks = {
    "Wind Parameters": st.session_state.get("wind_result") is not None,
    "Chain Link Design": st.session_state.get("cl_result") is not None,
    "Wood Fence Design": st.session_state.get("wood_result") is not None,
    "Post Spacing (CLFMI)": st.session_state.get("spacing_result") is not None,
    "Footing Design": st.session_state.get("footing_result") is not None,
}

for name, done in checks.items():
    if done:
        st.write(f"\u2705 {name} — Complete")
    else:
        st.write(f"\u2b1c {name} — Not yet run")

any_complete = any(checks.values())

st.divider()

if any_complete:
    st.subheader("Report Summary")

    wr = st.session_state.get("wind_result")
    if wr:
        st.write(f"**Wind:** qz = {wr.qz:.2f} psf ({wr.asce_edition.value})")

    cr = st.session_state.get("cl_result")
    if cr:
        status = "PASS" if cr.is_adequate else "FAIL"
        st.write(f"**Chain Link:** Axial={cr.axial_load:.1f} lb, "
                 f"Shear={cr.shear:.1f} lb, Moment={cr.moment:.1f} lb-ft, "
                 f"Ratio={cr.moment_ratio:.3f} [{status}]")

    wd = st.session_state.get("wood_result")
    if wd:
        status = "PASS" if wd.is_adequate else "FAIL"
        st.write(f"**Wood Fence:** Axial={wd.axial_load:.1f} lb, "
                 f"Shear={wd.shear:.1f} lb, Moment={wd.moment:.1f} lb-ft, "
                 f"Combined Ratio={wd.combined_ratio:.3f} [{status}]")

    sr = st.session_state.get("spacing_result")
    if sr:
        status = "ADEQUATE" if sr.is_adequate else "NOT ADEQUATE"
        st.write(f"**Spacing:** S'={sr.S_prime_calc:.1f} ft, "
                 f"Actual={sr.actual_spacing:.1f} ft [{status}]")

    fr = st.session_state.get("footing_result")
    if fr:
        status = "ADEQUATE" if fr.is_adequate else "NOT ADEQUATE"
        st.write(f"**Footing:** D(req)={fr.D_calc:.2f} ft, "
                 f"D(actual)={fr.D_actual:.2f} ft [{status}]")

    st.divider()

    if st.button("Generate PDF Report", type="primary"):
        from core.models import (
            ASCEEdition,
            ExposureCategory,
            FenceReportData,
            FenceType,
            FootingInput,
            IBCEdition,
            ProjectInfo,
            WindInput,
        )
        from core.pdf_export import generate_report

        project = ProjectInfo(
            project_name=st.session_state.project_name,
            project_location=st.session_state.project_location,
            project_number=st.session_state.project_number,
            designer=st.session_state.designer,
            reviewer=st.session_state.reviewer,
        )
        wind_input = WindInput(
            asce_edition=ASCEEdition(st.session_state.asce_edition),
            wind_speed=st.session_state.wind_speed,
            exposure_category=ExposureCategory(st.session_state.exposure_category),
            Kd=st.session_state.Kd, Kzt=st.session_state.Kzt, Kz=st.session_state.Kz,
            G=st.session_state.G, Cf=st.session_state.Cf, Ke=st.session_state.Ke,
        )
        fence_type = FenceType.WOOD if st.session_state.wood_result else FenceType.CHAIN_LINK

        footing_input = None
        if st.session_state.footing_result:
            footing_input = FootingInput(
                ibc_edition=IBCEdition(st.session_state.ibc_edition),
                soil_bearing_pressure=st.session_state.ft_soil_bearing,
                footing_diameter=st.session_state.ft_footing_diam,
                fence_height=st.session_state.ft_fence_height,
                actual_depth=st.session_state.ft_actual_depth,
            )

        report_data = FenceReportData(
            project=project,
            wind_input=wind_input,
            wind_result=st.session_state.wind_result,
            fence_type=fence_type,
            chain_link_result=st.session_state.cl_result,
            wood_result=st.session_state.wood_result,
            spacing_result=st.session_state.spacing_result,
            footing_input=footing_input,
            footing_result=st.session_state.footing_result,
        )

        pdf_bytes = generate_report(report_data)
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=f"FORK_{st.session_state.project_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
        )

else:
    st.info("Run at least one analysis to see results here.")
