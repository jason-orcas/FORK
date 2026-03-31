"""Page 09 - Fence Run Planner and Quantity Takeoff."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

from core.fence_run import FenceRunInput, GateSpec, calculate_fence_run

st.header("Fence Run Planner")
st.caption("Define your fence layout to calculate post quantities, concrete, and material takeoff.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Run Layout")
    total_length = st.number_input("Total Run Length (ft)", value=200.0,
        min_value=10.0, max_value=10000.0, step=10.0)
    post_spacing = st.number_input("Post Spacing (ft)", value=10.0,
        min_value=4.0, max_value=20.0, step=0.5)
    num_corners = st.number_input("Number of Corners", value=0,
        min_value=0, max_value=20, step=1)
    num_gates = st.number_input("Number of Gates", value=0,
        min_value=0, max_value=20, step=1)

with col2:
    st.subheader("Post & Footing")
    post_height = st.number_input("Post Height (ft)", value=7.0,
        min_value=3.0, max_value=20.0, step=0.5)
    post_weight = st.number_input("Post Weight (plf)", value=3.65,
        min_value=0.1, max_value=30.0, step=0.1)
    footing_diam = st.number_input("Footing Diameter (ft)", value=1.5,
        min_value=0.5, max_value=5.0, step=0.25)
    fabric_height = st.number_input("Fabric Height (ft)", value=6.0,
        min_value=1.0, max_value=20.0, step=0.5)
    has_top_rail = st.checkbox("Include Top Rail", value=True)

# Gate widths
gates = []
if num_gates > 0:
    st.subheader("Gate Openings")
    gate_cols = st.columns(min(num_gates, 4))
    for i in range(int(num_gates)):
        with gate_cols[i % len(gate_cols)]:
            w = st.number_input(f"Gate {i+1} Width (ft)", value=10.0,
                min_value=3.0, max_value=40.0, step=0.5, key=f"gate_w_{i}")
            gates.append(GateSpec(width_ft=w))

# Footing depths (use from design pages if available, or defaults)
with st.expander("Footing Depths (per post type)"):
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        depth_line = st.number_input("Line Post Depth (ft)", value=3.0,
            min_value=1.0, max_value=12.0, step=0.25)
    with fc2:
        depth_pull = st.number_input("Pull Post Depth (ft)", value=3.5,
            min_value=1.0, max_value=12.0, step=0.25)
    with fc3:
        depth_gate = st.number_input("Gate Post Depth (ft)", value=4.0,
            min_value=1.0, max_value=12.0, step=0.25)

st.divider()

if st.button("Calculate Quantities", type="primary"):
    inp = FenceRunInput(
        total_length_ft=total_length,
        post_spacing_ft=post_spacing,
        num_corners=int(num_corners),
        gates=gates,
        post_height_ft=post_height,
        post_weight_plf=post_weight,
        footing_diameter_ft=footing_diam,
        footing_depth_line_ft=depth_line,
        footing_depth_pull_ft=depth_pull,
        footing_depth_gate_ft=depth_gate,
        fabric_height_ft=fabric_height,
        has_top_rail=has_top_rail,
    )
    result = calculate_fence_run(inp)

    # Post Summary
    st.subheader("Post Summary")
    post_data = {
        "Post Type": ["Line Posts", "Pull/Terminal Posts", "Gate Posts", "**Total**"],
        "Count": [result.num_line_posts, result.num_pull_posts,
                  result.num_gate_posts, result.total_posts],
    }
    st.dataframe(pd.DataFrame(post_data), width="stretch", hide_index=True)

    # Material Takeoff
    st.subheader("Quantity Takeoff")
    takeoff = {
        "Item": [
            "Fence Fabric",
            "Fence Fabric Area",
            "Top Rail" if has_top_rail else "Top Rail (none)",
            "Concrete - Line Posts",
            "Concrete - Pull Posts",
            "Concrete - Gate Posts",
            "**Concrete Total**",
            "**Concrete Total**",
            "Post Steel (approx.)",
            "Top Rail Steel" if has_top_rail else "Top Rail Steel (none)",
            "**Total Steel (approx.)**",
        ],
        "Quantity": [
            f"{result.fabric_length_ft:.0f}",
            f"{result.fabric_area_sqft:.0f}",
            f"{result.top_rail_length_ft:.0f}" if has_top_rail else "0",
            f"{result.concrete_line_cuft:.1f}",
            f"{result.concrete_pull_cuft:.1f}",
            f"{result.concrete_gate_cuft:.1f}",
            f"{result.concrete_total_cuft:.1f}",
            f"{result.concrete_total_cuyd:.2f}",
            f"{result.post_steel_lbs:.0f}",
            f"{result.top_rail_steel_lbs:.0f}" if has_top_rail else "0",
            f"{result.total_steel_lbs:.0f}",
        ],
        "Unit": [
            "LF", "SF", "LF",
            "CF", "CF", "CF", "CF", "CY",
            "lbs", "lbs", "lbs",
        ],
    }
    st.dataframe(pd.DataFrame(takeoff), width="stretch", hide_index=True)
