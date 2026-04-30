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
- FastAPI backend with registration, login, saved simulation runs, optimizer API, and health check
- SQLite persistence for users and saved runs
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
5. Turn grid availability off to demonstrate island mode and unmet-demand alerts.
6. Open Energy Flow for the Sankey diagram.
7. Open Forecast to show tomorrow's projected dispatch.
8. Save a simulation run and show it in the Admin view.

## Impact

Indra-Grid demonstrates how intelligent energy management can reduce electricity bills, avoid outage losses, improve renewable self-consumption, and make energy decisions understandable for operators.
