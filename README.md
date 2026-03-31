# FORK — Fence Optimization Resource Kit

A Streamlit-hosted structural engineering tool for fence post design. Converts manual Excel-based fence calculations into a unified web application with automated optimization.

## Features

- **Wind Load Analysis** — ASCE 7-16/7-22 velocity pressure calculation with selectable code editions
- **Chain Link Design** — Line, pull, and gate post analysis with CLFMI Table 16 section adequacy checks
- **Wood Fence Design** — Full NDS 2018 stress analysis with column stability (Cp), combined stress ratio, and deflection limits
- **Post Spacing** — CLFMI WLG 2445 (2023) spacing formula: S' = S x Cf1 x Cf2 x Cf3 with all 12 wind speed tables
- **Footing Design** — IBC Eq. 18-1 and ASTM F567 methods with IBC Table 1806.2 soil type selector
- **Post Optimizer** — Exhaustive sweep of all post groups/sizes to find the lightest passing combination
- **Fence Run Planner** — Layout-based quantity takeoff: post counts, concrete volume, fabric area, steel weight
- **PDF Report** — Professional calculation report with color-coded pass/fail indicators
- **Project Save/Load** — JSON project files for saving and restoring all inputs

## Engineering Standards

| Standard | Application |
|----------|------------|
| ASCE 7-16 / 7-22 | Wind loads, velocity pressure, exposure categories |
| IBC 2009 / 2018 | Footing depth, soil bearing (Table 1806.2) |
| NDS 2018 | Wood post stress analysis, adjustment factors |
| ASTM F1043 | Steel chain link fence framework |
| ASTM F1083 | Galvanized steel fence pipe |
| ASTM F567 | Chain link fence installation |
| CLFMI WLG 2445 (2023) | Chain link fence wind load guide |

## Quick Start

```bash
pip install -r requirements.txt
streamlit run streamlit_app/streamlit_app.py
```

## Running Tests

```bash
pytest tests/ -v
```

## Architecture

```
core/               Calculation engine (Python modules with dataclasses)
  wind.py           ASCE 7 velocity pressure
  chain_link.py     Chain link post design
  wood.py           NDS 2018 wood post analysis
  spacing.py        CLFMI post spacing
  footing.py        IBC/ASTM F567 footing depth
  optimize.py       Post optimization sweep
  fence_run.py      Fence run planner / quantity takeoff
  sections.py       Section property lookups
  pdf_export.py     PDF report generation
  models.py         Dataclasses and enums

data/               Reference tables as JSON
  clfmi_*.json      CLFMI WLG 2445 Tables 1-17
  steel_pipe_sections.json
  wood_species.json
  ibc_soil_table.json
  kz_table.json

streamlit_app/      Streamlit web interface
  streamlit_app.py  Main entry point
  pages/            9 application pages
  core/             Synced copy of core/ (for Streamlit Cloud)
  data/             Synced copy of data/ (for Streamlit Cloud)

tests/              pytest unit tests
```

## Key Formulas

- **Velocity pressure:** `qz = 0.00256 x Kz x Kzt x Kd x [Ke x] V^2`
- **Post spacing:** `S' = S x Cf1 x Cf2 x Cf3`
- **Footing depth (IBC):** `D = 0.5A x {1 + [1 + (4.36c/A)]^0.5}`
- **NDS column stability:** `Cp = (1+FcE/Fc*)/(2c) - sqrt[((1+FcE/Fc*)/(2c))^2 - FcE/(Fc*c)]`
- **NDS combined stress:** `(fc/Fc')^2 + fb/(Fb'(1-fc/FcE)) <= 1.0`
