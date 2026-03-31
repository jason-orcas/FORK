"""Tests for the optimization sweep engine."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def _make_wind():
    return WindInput(
        asce_edition=ASCEEdition.ASCE_7_22,
        wind_speed=115.0,
        exposure_category=ExposureCategory.C,
        Kd=0.85, Kzt=1.0, Kz=0.85, G=0.85, Cf=1.3, Ke=1.0,
    )


def _make_footing():
    return FootingInput(
        ibc_edition=IBCEdition.IBC_2018,
        soil_bearing_pressure=200.0,
        footing_diameter=1.5,
        fence_height=7.0,
        actual_depth=10.0,
    )


class TestChainLinkOptimizer:
    def test_returns_results(self):
        """Should return at least some combinations."""
        results = optimize_chain_link(
            wind=_make_wind(),
            fence_height=7.0,
            wire_gauge=11,
            mesh_size=2.0,
            mesh_weight=0.154,
            exposure=ExposureCategory.C,
            ice=IceExposure.NONE,
            footing_input=_make_footing(),
        )
        assert len(results) > 0, "Should return some combinations"

    def test_has_passing_results(self):
        """At 7' height, 115 mph, should have some passing posts."""
        results = optimize_chain_link(
            wind=_make_wind(),
            fence_height=7.0,
            wire_gauge=11,
            mesh_size=2.0,
            mesh_weight=0.154,
            exposure=ExposureCategory.C,
            ice=IceExposure.NONE,
            footing_input=_make_footing(),
        )
        passing = [r for r in results if r.passes]
        assert len(passing) > 0, "Should have at least one passing combination"

    def test_optimal_is_lightest(self):
        """Optimal row should be the lightest passing post."""
        results = optimize_chain_link(
            wind=_make_wind(),
            fence_height=7.0,
            wire_gauge=11,
            mesh_size=2.0,
            mesh_weight=0.154,
            exposure=ExposureCategory.C,
            ice=IceExposure.NONE,
            footing_input=_make_footing(),
        )
        optimal = [r for r in results if r.is_optimal]
        assert len(optimal) == 1, "Should have exactly one optimal"
        passing = [r for r in results if r.passes]
        lightest = min(passing, key=lambda r: r.weight_plf)
        assert optimal[0].weight_plf == lightest.weight_plf

    def test_sorted_by_weight(self):
        """Passing results should be sorted by weight ascending."""
        results = optimize_chain_link(
            wind=_make_wind(),
            fence_height=7.0,
            wire_gauge=11,
            mesh_size=2.0,
            mesh_weight=0.154,
            exposure=ExposureCategory.C,
            ice=IceExposure.NONE,
            footing_input=_make_footing(),
        )
        passing = [r for r in results if r.passes]
        weights = [r.weight_plf for r in passing]
        assert weights == sorted(weights), "Should be sorted by weight"

    def test_moment_ratio_below_one(self):
        """All passing results should have moment ratio <= 1.0."""
        results = optimize_chain_link(
            wind=_make_wind(),
            fence_height=7.0,
            wire_gauge=11,
            mesh_size=2.0,
            mesh_weight=0.154,
            exposure=ExposureCategory.C,
            ice=IceExposure.NONE,
            footing_input=_make_footing(),
        )
        for r in results:
            if r.passes:
                assert r.moment_ratio <= 1.0, f"{r.trade_size} has ratio {r.moment_ratio}"


class TestWoodOptimizer:
    def test_returns_results(self):
        results = optimize_wood(
            wind=_make_wind(),
            fence_height=8.0,
            post_spacing=10.0,
            wire_diam=0.192,
            mesh_size=5.5,
            mesh_weight=0.154,
            footing_input=_make_footing(),
        )
        assert len(results) == 7, "Should check 7 diameters"

    def test_has_passing(self):
        results = optimize_wood(
            wind=_make_wind(),
            fence_height=8.0,
            post_spacing=10.0,
            wire_diam=0.192,
            mesh_size=5.5,
            mesh_weight=0.154,
            footing_input=_make_footing(),
        )
        passing = [r for r in results if r.passes]
        assert len(passing) > 0

    def test_combined_ratio_below_one(self):
        results = optimize_wood(
            wind=_make_wind(),
            fence_height=8.0,
            post_spacing=10.0,
            wire_diam=0.192,
            mesh_size=5.5,
            mesh_weight=0.154,
            footing_input=_make_footing(),
        )
        for r in results:
            if r.passes:
                assert r.combined_ratio <= 1.0
