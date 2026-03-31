"""PDF report generation for FORK fence design calculations.

Uses fpdf2 to produce professional engineering calculation reports
with color-coded pass/fail indicators.

References the SPORK pattern for layout and formatting.
"""

from __future__ import annotations

import io
from datetime import date

from fpdf import FPDF

from .models import (
    ChainLinkResult,
    FenceReportData,
    FenceType,
    FootingResult,
    SpacingResult,
    WindResult,
    WoodStressResult,
)


# Colors
_GREEN = (200, 240, 200)
_RED = (255, 200, 200)
_YELLOW = (255, 245, 200)
_HEADER_BG = (50, 80, 120)
_HEADER_FG = (255, 255, 255)
_ALT_ROW = (240, 245, 250)


class FenceReportPDF(FPDF):
    """Custom PDF class for FORK fence design reports."""

    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="letter")
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, "FORK - Fence Optimization Resource Kit", align="L")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f"Page {self.page_no()}/{{nb}}", align="C")

    def _section_title(self, title: str):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(30, 60, 100)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 60, 100)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def _kv_row(self, label: str, value: str):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(0, 0, 0)
        self.cell(70, 6, label, new_x="RIGHT")
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

    def _table_header(self, headers: list[str], widths: list[int]):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*_HEADER_BG)
        self.set_text_color(*_HEADER_FG)
        for h, w in zip(headers, widths):
            self.cell(w, 7, h, border=1, fill=True, align="C")
        self.ln()

    def _table_row(self, values: list[str], widths: list[int], fill_color=None):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(0, 0, 0)
        if fill_color:
            self.set_fill_color(*fill_color)
        for v, w in zip(values, widths):
            self.cell(w, 6, v, border=1, fill=fill_color is not None, align="C")
        self.ln()

    def _pass_fail_banner(self, text: str, passed: bool):
        color = _GREEN if passed else _RED
        self.set_fill_color(*color)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(0, 0, 0)
        self.cell(0, 8, text, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)


def generate_report(data: FenceReportData) -> bytes:
    """Generate a PDF report from fence design results.

    Args:
        data: FenceReportData with all inputs and results.

    Returns:
        PDF file contents as bytes.
    """
    pdf = FenceReportPDF()
    pdf.alias_nb_pages()

    # --- Cover page ---
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(30, 60, 100)
    pdf.ln(30)
    pdf.cell(0, 15, "FORK", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "Fence Optimization Resource Kit", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, data.project.project_name, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, data.project.project_location, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Project Number: {data.project.project_number}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Designer: {data.project.designer}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Reviewer: {data.project.reviewer}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Date: {data.project.date or date.today().isoformat()}", align="C", new_x="LMARGIN", new_y="NEXT")

    # --- Basis of Design ---
    pdf.add_page()
    pdf._section_title("1. Basis of Design")
    pdf._kv_row("ASCE Edition:", data.wind_input.asce_edition.value)
    if data.footing_input:
        pdf._kv_row("IBC Edition:", data.footing_input.ibc_edition.value)
    pdf._kv_row("Fence Type:", data.fence_type.value.replace("_", " ").title())
    pdf.ln(3)

    # --- Wind Parameters ---
    pdf._section_title("2. Wind Load Parameters")
    wi = data.wind_input
    pdf._kv_row("Wind Speed (V):", f"{wi.wind_speed:.0f} mph")
    pdf._kv_row("Exposure Category:", wi.exposure_category.value)
    pdf._kv_row("Kd (Directionality):", f"{wi.Kd:.2f}")
    pdf._kv_row("Kzt (Topographic):", f"{wi.Kzt:.2f}")
    pdf._kv_row("Kz (Velocity Pressure):", f"{wi.Kz:.2f}")
    pdf._kv_row("G (Gust Effect):", f"{wi.G:.2f}")
    pdf._kv_row("Cf (Force Coefficient):", f"{wi.Cf:.2f}")
    if wi.asce_edition.value == "ASCE 7-22":
        pdf._kv_row("Ke (Ground Elevation):", f"{wi.Ke:.2f}")
    pdf.ln(3)

    if data.wind_result:
        pdf._kv_row("Velocity Pressure (qz):", f"{data.wind_result.qz:.2f} psf")
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, data.wind_result.formula_used)
        pdf.ln(3)

    # --- Chain Link Results ---
    if data.chain_link_result:
        pdf._section_title("3. Chain Link Post Analysis")
        cr = data.chain_link_result
        pdf._kv_row("Post Type:", cr.post_type.value.title())

        widths = [50, 40, 40]
        pdf._table_header(["Load", "Value", "Unit"], widths)
        pdf._table_row(["Axial", f"{cr.axial_load:.1f}", "lb"], widths)
        pdf._table_row(["Shear", f"{cr.shear:.1f}", "lb"], widths)
        pdf._table_row(["Moment", f"{cr.moment:.1f}", "lb-ft"], widths)
        pdf.ln(3)

        if cr.Mallow > 0:
            pdf._kv_row("Moment Demand:", f"{cr.M_demand:.3f} kip-ft")
            pdf._kv_row("Moment Capacity:", f"{cr.Mallow:.3f} kip-ft")
            pdf._kv_row("Moment Ratio:", f"{cr.moment_ratio:.3f}")
            pdf._pass_fail_banner(
                f"Moment Check: {'PASS' if cr.is_adequate else 'FAIL'} (Ratio = {cr.moment_ratio:.3f})",
                cr.is_adequate,
            )

    # --- Wood Results ---
    if data.wood_result:
        pdf._section_title("4. Wood Fence Post Analysis (NDS 2018)")
        wd = data.wood_result
        pdf._kv_row("Post Type:", wd.post_type.value.title())

        # Loads table
        widths = [50, 40, 40]
        pdf._table_header(["Load", "Value", "Unit"], widths)
        pdf._table_row(["Axial", f"{wd.axial_load:.1f}", "lb"], widths)
        pdf._table_row(["Shear", f"{wd.shear:.1f}", "lb"], widths)
        pdf._table_row(["Moment", f"{wd.moment:.1f}", "lb-ft"], widths)
        pdf.ln(3)

        # Stress check table
        widths = [40, 30, 30, 25, 25]
        pdf._table_header(["Stress", "Applied", "Allowable", "Ratio", "Status"], widths)
        for label, applied, allow, ratio in [
            ("Compression", wd.fc, wd.Fc_prime, wd.compression_ratio),
            ("Bending", wd.fb, wd.Fb_prime, wd.bending_ratio),
            ("Shear", wd.fv, wd.Fv_prime, wd.shear_ratio),
        ]:
            status = "PASS" if ratio <= 1.0 else "FAIL"
            color = _GREEN if ratio <= 0.9 else (_YELLOW if ratio <= 1.0 else _RED)
            pdf._table_row(
                [label, f"{applied:.1f}", f"{allow:.1f}", f"{ratio:.3f}", status],
                widths, fill_color=color,
            )
        pdf.ln(3)

        pdf._kv_row("Combined Ratio (NDS 3.9.2):", f"{wd.combined_ratio:.3f}")
        pdf._kv_row("Deflection at Top:", f"{wd.deflection:.3f} in")
        pdf._pass_fail_banner(
            f"Combined Check: {'PASS' if wd.is_adequate else 'FAIL'} (Ratio = {wd.combined_ratio:.3f})",
            wd.is_adequate,
        )

    # --- Spacing Results ---
    if data.spacing_result:
        pdf._section_title("5. CLFMI Post Spacing Check")
        sr = data.spacing_result
        pdf._kv_row("S (Table):", f"{sr.S_table:.1f} ft")
        pdf._kv_row("Cf1 (Mesh):", f"{sr.Cf1:.2f}")
        pdf._kv_row("Cf2 (Exposure):", f"{sr.Cf2:.2f}")
        pdf._kv_row("Cf3 (Ice):", f"{sr.Cf3:.2f}")
        pdf._kv_row("S' (Max Spacing):", f"{sr.S_prime_calc:.1f} ft")
        pdf._kv_row("Actual Spacing:", f"{sr.actual_spacing:.1f} ft")
        pdf._pass_fail_banner(
            f"Spacing: {'ADEQUATE' if sr.is_adequate else 'NOT ADEQUATE'}",
            sr.is_adequate,
        )

    # --- Footing Results ---
    if data.footing_result:
        pdf._section_title("6. Footing Depth Check")
        fr = data.footing_result
        pdf._kv_row("Method:", fr.method)
        if fr.P_wind > 0:
            pdf._kv_row("Wind Force (P):", f"{fr.P_wind:.1f} lb")
            pdf._kv_row("Moment Arm (c):", f"{fr.c_arm:.2f} ft")
        pdf._kv_row("Required Depth:", f"{fr.D_calc:.2f} ft")
        pdf._kv_row("Actual Depth:", f"{fr.D_actual:.2f} ft")
        pdf._pass_fail_banner(
            f"Footing: {'ADEQUATE' if fr.is_adequate else 'NOT ADEQUATE'}",
            fr.is_adequate,
        )

    # --- Optimizer Results ---
    if data.optimizer_results:
        pdf.add_page()
        pdf._section_title("7. Post Optimization Results")
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5,
            "Exhaustive sweep of all available post sizes. "
            "Ranked by lightest weight, then maximum spacing.")
        pdf.ln(3)

        # Table header depends on fence type
        if data.fence_type == FenceType.CHAIN_LINK:
            widths = [10, 30, 18, 18, 22, 22, 22, 22]
            pdf._table_header(
                ["", "Group", "Size", "Wt(plf)", "S'(ft)", "M-Ratio", "D(ft)", "Status"],
                widths,
            )
            for r in data.optimizer_results:
                status = "PASS" if r.get("passes") else "FAIL"
                color = _GREEN if r.get("is_optimal") else (
                    _ALT_ROW if r.get("passes") else _RED)
                pdf._table_row([
                    "*" if r.get("is_optimal") else "",
                    r.get("post_group", "")[:20],
                    str(r.get("trade_size", "")),
                    f"{r.get('weight_plf', 0):.1f}",
                    f"{r.get('max_spacing', 0):.1f}",
                    f"{r.get('moment_ratio', 0):.3f}",
                    f"{r.get('footing_depth_ft', 0):.2f}",
                    status,
                ], widths, fill_color=color)
        else:
            widths = [10, 25, 20, 25, 22, 22, 22, 22]
            pdf._table_header(
                ["", "Diameter", "Wt(plf)", "Combined", "Shear", "Defl(in)", "D(ft)", "Status"],
                widths,
            )
            for r in data.optimizer_results:
                status = "PASS" if r.get("passes") else "FAIL"
                color = _GREEN if r.get("is_optimal") else (
                    _ALT_ROW if r.get("passes") else _RED)
                pdf._table_row([
                    "*" if r.get("is_optimal") else "",
                    str(r.get("trade_size", "")),
                    f"{r.get('weight_plf', 0):.1f}",
                    f"{r.get('combined_ratio', 0):.3f}",
                    f"{r.get('shear_ratio', 0):.3f}",
                    f"{r.get('deflection_in', 0):.3f}",
                    f"{r.get('footing_depth_ft', 0):.2f}",
                    status,
                ], widths, fill_color=color)

        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(0, 5, "* = Optimal (lightest passing post)", new_x="LMARGIN", new_y="NEXT")

    # --- Fence Run Results ---
    if data.fence_run_result:
        pdf.add_page()
        pdf._section_title("8. Fence Run Quantity Takeoff")
        fr = data.fence_run_result

        pdf._kv_row("Line Posts:", str(getattr(fr, 'num_line_posts', 0)))
        pdf._kv_row("Pull/Terminal Posts:", str(getattr(fr, 'num_pull_posts', 0)))
        pdf._kv_row("Gate Posts:", str(getattr(fr, 'num_gate_posts', 0)))
        pdf._kv_row("Total Posts:", str(getattr(fr, 'total_posts', 0)))
        pdf.ln(3)

        pdf._kv_row("Fence Fabric:", f"{getattr(fr, 'fabric_length_ft', 0):.0f} LF")
        pdf._kv_row("Fabric Area:", f"{getattr(fr, 'fabric_area_sqft', 0):.0f} SF")
        pdf._kv_row("Top Rail:", f"{getattr(fr, 'top_rail_length_ft', 0):.0f} LF")
        pdf.ln(3)

        pdf._kv_row("Concrete (Total):", f"{getattr(fr, 'concrete_total_cuft', 0):.1f} CF "
                     f"({getattr(fr, 'concrete_total_cuyd', 0):.2f} CY)")
        pdf._kv_row("Steel Weight (approx.):", f"{getattr(fr, 'total_steel_lbs', 0):.0f} lbs")

    # Return bytes
    return bytes(pdf.output())
