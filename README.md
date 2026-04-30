# Indra-Grid

AI-driven energy management for MSMEs, factories, commercial buildings, data centres, and residential campuses.

Indra-Grid simulates solar generation, electricity demand, grid prices, battery storage, and grid availability. It then decides how to dispatch solar, battery, and grid power to reduce electricity cost, preserve battery reserve, and keep critical loads running during outages.

## Why It Matters

Small and medium businesses often lose money through peak-hour tariffs, grid outages, and manual energy decisions. Indra-Grid acts like an energy autopilot: it uses solar first, stores surplus energy, uses the battery during expensive or failed-grid periods, and reports cost, carbon, and reliability impact.

## Features

- Solar, battery, and grid dispatch optimizer
- Peak shaving during expensive tariff windows
- Island-mode behavior when the grid is unavailable
- Battery reserve protection
- CO2 avoided, grid cost, savings, self-sufficiency, and final SOC metrics
- Enterprise Streamlit dashboard with KPIs, charts, Sankey energy flow, analytics, forecast, admin console, account view, reports, and CSV export
- FastAPI backend with registration, login, JWT-protected admin APIs, saved simulation runs, optimizer API, health check, fault events, and weather forecast API
- SQLite persistence for users and saved runs
- Demo scenario modes for peak-tariff events, grid-outage drills, and monsoon solar dips
- Weather-aware forecast using the backend `/weather/forecast` API
- ROI, payback, annualized savings, and battery arbitrage estimates
- Judge Pitch view that explains the problem, optimizer, weather layer, business case, and demo flow in one place
- Regression tests for core optimizer behavior

## Project Structure

```text
backend/       FastAPI app, auth, database models
dashboard/     Streamlit login and enterprise dashboard
data/          Scenario simulator and generated CSV
logic/         Energy optimizer
integration/   One-command local runner
tests/         Optimizer regression tests
docs/          Project explanation and judging notes
```

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the full demo:

```bash
python integration/run.py
```

Or start services separately:

```bash
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8001 --reload
streamlit run dashboard/app.py
```

Run tests:

```bash
python -m unittest discover -s tests
```

Optional production-style secret:

```bash
set INDRA_GRID_SECRET_KEY=replace-with-a-long-random-secret
```

## Demo Story

1. Register or log in.
2. Select an entity type such as Industrial Plant or Data Centre.
3. Change demand multiplier, initial battery SOC, grid availability, and simulation seed.
4. Show the main dashboard KPIs and dispatch chart.
5. Switch Demo Scenario to `Grid Outage Drill` or `Peak Tariff Event` to show resilience and peak shaving.
6. Open Energy Flow for the Sankey diagram and ROI/payback metrics.
7. Open Forecast to show weather-adjusted dispatch from the weather API.
8. Open Pitch to explain the full project story in under two minutes.
9. Save a simulation run and show it in the Admin view.

## Key APIs

- `GET /health` - backend readiness check
- `POST /register` - create a user
- `POST /login` - login and receive a JWT token
- `POST /optimize` - optimize one dispatch state
- `GET /weather/forecast` - 24-hour weather forecast for latitude/longitude
- `POST /runs` - save a simulation run, requires login token
- `GET /users` - list users, requires Admin token
- `GET /runs` - list saved runs, requires Admin token
- `GET /faults` and `POST /faults` - fault event history, requires Admin token

## Impact

Indra-Grid demonstrates how intelligent energy management can reduce electricity bills, avoid outage losses, improve renewable self-consumption, and make energy decisions understandable for operators.
