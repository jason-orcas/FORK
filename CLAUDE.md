# FORK — Fence Optimization Resource Kit

## Project Overview
FORK is a Streamlit-hosted structural engineering tool for fence post design.
It converts manual Excel-based fence calculations into a unified web application.

## Architecture
- `core/` — Authoritative calculation engine (Python modules with dataclasses)
- `data/` — Reference tables as JSON (CLFMI, NDS, ASTM)
- `streamlit_app/` — Streamlit web interface with synced copies of core/ and data/
- `tests/` — pytest unit tests validated against original spreadsheet values

## Engineering Standards
- **ASCE 7-16 / 7-22** — Wind loads (velocity pressure, exposure categories)
- **IBC 2009 / 2018** — Footing depth, soil bearing
- **CBC 2022** — California Building Code
- **NDS 2018** — National Design Specification for Wood Construction
- **ASTM F1043** — Steel chain link fence framework
- **ASTM F1083** — Galvanized steel fence pipe
- **ASTM F567** — Chain link fence installation
- **CLFMI WLG 2445 (2023)** — Chain Link Fence Wind Load Guide

## Key Engineering Formulas
- Velocity pressure: `qz = 0.00256 * Kz * Kzt * Kd * [Ke *] V^2`
- Post spacing: `S' = S * Cf1 * Cf2 * Cf3` (CLFMI)
- Footing depth (IBC): `D = 0.5A * {1 + [1 + (4.36*c/A)]^0.5}`
- NDS column stability: `Cp = (1+FcE/Fc*)/(2c) - sqrt[((1+FcE/Fc*)/(2c))^2 - FcE/(Fc*c)]`

## Conventions
- All calculations must cite the specific code section/equation number
- Dataclass-based inputs and outputs for every calculation module
- FoS is user-configurable with sensible defaults
- Code editions are selectable (ASCE 7-16 vs 7-22, IBC 2009 vs 2018)
- Results must include pass/fail determination with unity ratios

## Running
```bash
pip install -r requirements.txt
streamlit run streamlit_app/streamlit_app.py
pytest tests/
```
