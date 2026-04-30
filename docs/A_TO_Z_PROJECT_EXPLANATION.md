# Indra-Grid A-to-Z Project Explanation

Indra-Grid is an energy management simulator for MSMEs and small campuses. It shows how a site can combine solar, battery storage, and grid power to reduce electricity cost, survive outages, and track sustainability impact.

## End-to-End Flow

1. `data/simulator.py` creates hourly solar, demand, and grid-price scenarios.
2. `logic/optimizer.py` decides how much energy should come from solar, battery, and grid.
3. `backend/api.py` exposes login, registration, saved-run history, health, and optimizer APIs.
4. `backend/api.py` also exposes protected admin APIs, database-backed fault events, and a weather forecast API.
5. `dashboard/app.py` handles login/register and launches the Streamlit dashboard.
6. `dashboard/dashboard.py` renders the enterprise dashboard, demo scenarios, ROI/payback metrics, weather-aware forecasts, charts, reports, recommendations, admin view, and account view.
6. `integration/run.py` regenerates data, starts the backend, and opens the Streamlit app.

## Important Functions

### Backend

- `clean_username`: trims and normalizes usernames so duplicate accounts are avoided.
- `clean_role`: accepts only known roles and falls back to `Operator`.
- `migrate_sqlite_schema`: updates old SQLite databases by adding the `role` column if needed.
- `health`: returns API readiness metadata for demos and deployment checks.
- `bearer_token`: extracts the JWT from an `Authorization: Bearer ...` header.
- `current_user`: validates a token and returns the logged-in user's role.
- `require_admin`: blocks admin-only APIs unless the current user is an Admin.
- `register`: creates a user with a hashed password and role.
- `login`: verifies credentials, upgrades old plaintext passwords to hashes, and returns a JWT token.
- `users`: lists users for the admin dashboard and requires an Admin token.
- `save_run`: persists a simulation summary to SQLite and requires a login token.
- `runs`: returns recent saved simulations and requires an Admin token.
- `faults`: returns database-backed fault events for Admin users.
- `create_fault`: stores a new fault event for Admin users.
- `weather_forecast`: returns a 24-hour weather forecast for latitude/longitude using Open-Meteo, with an offline fallback.
- `optimize`: runs one optimizer decision through the API.
- `hash_password`: stores passwords using PBKDF2-HMAC-SHA256 with a random salt.
- `verify_password`: checks hashed passwords and supports legacy plaintext migration.
- `create_token`: creates a short-lived JWT login token.
- `verify_token`: decodes a token and returns the logged-in username.

### Simulator And Optimizer

- `EnergySimulator.generate`: produces realistic 24-hour cycles with daylight solar, morning/evening demand peaks, and higher evening tariffs.
- `EnergyOptimizer.optimize`: dispatches solar first, charges the battery from surplus solar, uses battery during high-price/outage/peak periods, imports remaining demand from grid, and records unmet demand if the grid is down.
- `EnergyOptimizer._decision_for`: converts numeric dispatch into a readable operational decision.

### Dashboard

- `run`: orchestrates the selected view and recomputes the simulation.
- `init_state`: initializes Streamlit session defaults.
- `entity_config`: provides plant/building/data-centre/residential sizing, tariffs, labels, and equipment metadata.
- `sidebar`: renders navigation and scenario controls.
- `optimized_frame`: creates the full simulation table by applying the optimizer hour by hour.
- `apply_demo_scenario`: modifies the simulation for peak tariff, grid outage, or monsoon solar demos.
- `summarize`: computes total solar, demand, grid import, battery flow, unmet demand, export, CO2 avoided, self-sufficiency, cost, savings, and final SOC.
- `auth_headers`: attaches the login JWT to protected backend calls.
- `fetch_weather_forecast`: calls the backend weather API.
- `weather_adjusted_frame`: changes tomorrow's solar and demand forecast using cloud cover and rain probability.
- `report_frame`: adds cost, savings, and CO2 columns to the exportable CSV.
- `recommendations`: generates action-oriented operational advice.
- `inject_css`: applies the custom enterprise visual design.
- `topbar`, `alert`, `bottom_bar`: render persistent dashboard chrome and warnings.
- `dashboard_view`: main KPI, dispatch, recommendations, report, equipment, and performance page.
- `dispatch_chart`: Plotly chart for solar, battery, grid, and demand.
- `live_inspector`: lets judges inspect any simulated hour.
- `recommendation_panel`: displays optimizer recommendations.
- `battery_soc_chart`: plots battery state-of-charge and reserve.
- `report_actions`: downloads CSV/report and saves runs to the backend.
- `build_text_report`: generates a text summary for judges or operators.
- `equipment_panel`: shows current equipment status.
- `performance_panel`: visualizes PR, self-sufficiency, SOC, grid dependency, and utilisation.
- `energy_flow_view`: shows current energy flow, Sankey chart, costs, and source mix.
- `fault_data`, `active_faults`, `fault_log_view`: provide a searchable operational fault log.
- `analytics_view`, `make_monthly`: generate six-month comparative analytics.
- `forecast_view`: simulates tomorrow using a changed seed.
- `weather_panel`: displays the weather API status, cloud cover, rain probability, and temperature.
- `admin_view`: shows users and saved runs for Admin users.
- `account_view`: shows plant registration, technical specs, and support contacts.
- `rows_panel`, `pct`, `kpi`, `flow_node`, `flow_card`, `chart_layout`: reusable UI helpers.

## Winning-Worthy Improvements Already Added

- Added a `/health` API endpoint for demo readiness checks.
- Moved the JWT secret to `INDRA_GRID_SECRET_KEY` with a development fallback.
- Added role sanitization so unexpected role strings do not enter the database.
- Replaced the hardcoded dashboard timestamp with the current generated time.
- Added optimizer tests for solar charging, peak shaving, and island-mode deficits.
- Added JWT protection for saved runs, users, fault history, and admin-only endpoints.
- Added demo scenario modes for peak tariff events, grid outage drills, and monsoon solar dips.
- Added ROI, payback, annualized savings, and battery arbitrage metrics.
- Added database-backed fault events.
- Added a weather forecast API and weather-aware forecast dashboard.

## Next Best Improvements

- Add a true IoT ingestion endpoint for live meter readings.
- Add ML forecasting for tomorrow's demand and solar instead of weather-adjusted seed-shifted simulation.
- Add deeper economic metrics: battery degradation cost, demand-charge reduction, and financing options.
- Add deployment files such as `.env.example`, Dockerfile, and GitHub Actions.
