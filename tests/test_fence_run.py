"""Tests for fence run planner and quantity takeoff."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.fence_run import FenceRunInput, GateSpec, calculate_fence_run


class TestBasicRun:
    def test_simple_200ft_run(self):
        """200 ft run, 10 ft spacing, no gates, no corners."""
        inp = FenceRunInput(
            total_length_ft=200.0,
            post_spacing_ft=10.0,
            num_corners=0,
            gates=[],
            post_height_ft=7.0,
            post_weight_plf=3.65,
            footing_diameter_ft=1.5,
            footing_depth_line_ft=3.0,
            footing_depth_pull_ft=3.5,
            footing_depth_gate_ft=4.0,
            fabric_height_ft=6.0,
        )
        result = calculate_fence_run(inp)

        # 2 pull posts (ends)
        assert result.num_pull_posts == 2
        # 0 gate posts
        assert result.num_gate_posts == 0
        # Line posts: 200/10 - 1 = 19
        assert result.num_line_posts == 19
        assert result.total_posts == 21
        # Fabric
        assert result.fabric_length_ft == 200.0
        assert result.fabric_area_sqft == 200.0 * 6.0

    def test_with_corners(self):
        """Run with 2 corners should add 2 pull posts."""
        inp = FenceRunInput(
            total_length_ft=200.0,
            post_spacing_ft=10.0,
            num_corners=2,
        )
        result = calculate_fence_run(inp)
        # 2 ends + 2 corners = 4 pull posts
        assert result.num_pull_posts == 4

    def test_with_gates(self):
        """Run with 1 gate should add 2 gate posts and reduce fenceable length."""
        inp = FenceRunInput(
            total_length_ft=200.0,
            post_spacing_ft=10.0,
            gates=[GateSpec(width_ft=10.0)],
        )
        result = calculate_fence_run(inp)
        assert result.num_gate_posts == 2
        # Fenceable = 200 - 10 = 190 ft
        assert result.fabric_length_ft == 190.0

    def test_two_gates(self):
        """Two gates should add 4 gate posts."""
        inp = FenceRunInput(
            total_length_ft=300.0,
            post_spacing_ft=10.0,
            gates=[GateSpec(width_ft=12.0), GateSpec(width_ft=20.0)],
        )
        result = calculate_fence_run(inp)
        assert result.num_gate_posts == 4
        assert result.fabric_length_ft == 300.0 - 32.0


class TestConcrete:
    def test_concrete_volume(self):
        """Concrete volume should be pi/4 * d^2 * depth * count."""
        inp = FenceRunInput(
            total_length_ft=100.0,
            post_spacing_ft=10.0,
            footing_diameter_ft=1.5,
            footing_depth_line_ft=3.0,
            footing_depth_pull_ft=3.5,
        )
        result = calculate_fence_run(inp)

        footing_area = math.pi / 4.0 * 1.5**2
        expected_line = result.num_line_posts * footing_area * 3.0
        assert abs(result.concrete_line_cuft - expected_line) < 0.1

        expected_pull = result.num_pull_posts * footing_area * 3.5
        assert abs(result.concrete_pull_cuft - expected_pull) < 0.1

    def test_cubic_yards(self):
        """Total CY = total CF / 27."""
        inp = FenceRunInput(total_length_ft=200.0, post_spacing_ft=10.0)
        result = calculate_fence_run(inp)
        assert abs(result.concrete_total_cuyd - result.concrete_total_cuft / 27.0) < 0.01


class TestTopRail:
    def test_top_rail_included(self):
        inp = FenceRunInput(total_length_ft=200.0, has_top_rail=True)
        result = calculate_fence_run(inp)
        assert result.top_rail_length_ft == 200.0
        assert result.top_rail_steel_lbs > 0

    def test_no_top_rail(self):
        inp = FenceRunInput(total_length_ft=200.0, has_top_rail=False)
        result = calculate_fence_run(inp)
        assert result.top_rail_length_ft == 0.0
        assert result.top_rail_steel_lbs == 0.0
