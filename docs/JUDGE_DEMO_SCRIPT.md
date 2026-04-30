# Indra-Grid Judge Demo Script

## 20-Second Opening

Indra-Grid is an energy autopilot for small factories and campuses. In India, many MSMEs pay high peak-hour electricity rates and also face grid interruptions. Our system simulates solar, battery, grid price, demand, and weather, then decides the best energy source hour by hour.

## What To Show First

1. Open the Dashboard.
2. Point to Solar Used, Grid Import, CO2 Avoided, and Battery SOC.
3. Say: "These KPIs are not static cards. They come from the optimizer running hour by hour."

## Explain The Optimizer

Use this simple line:

"The logic is solar first, then charge the battery from surplus solar, then use battery during peak tariff or grid outage, while keeping a 20% reserve for safety."

## Winning Demo Flow

1. Keep Entity Type as Industrial Plant.
2. Change Demo Scenario to Peak Tariff Event.
3. Explain that evening grid prices rise, so the battery reduces expensive imports.
4. Change Demo Scenario to Grid Outage Drill.
5. Explain island mode and unmet demand if the battery is not enough.
6. Open Energy Flow to show the Sankey chart.
7. Open Forecast to show the weather API.
8. Open Pitch for the full project explanation.

## Weather API Explanation

Say:

"We call the backend `/weather/forecast` API for latitude and longitude. It uses cloud cover and rain probability to adjust tomorrow's solar and demand forecast. If the internet is unavailable during demo, the backend falls back to synthetic Kanpur weather so the project still works."

## Business Explanation

Say:

"This is not only a technical dispatch project. We also calculate grid cost, savings, annualized savings, simple payback, ROI, battery arbitrage, and CO2 avoided so an MSME owner can decide whether the system is worth deploying."

## Judge Questions

- Why does this matter?
  MSMEs lose money from peak tariffs and downtime.

- What is intelligent about it?
  It makes hour-by-hour dispatch decisions using tariff, solar, battery SOC, outage status, and weather forecast.

- What is the next step?
  Live IoT meter ingestion, ML forecasting, battery degradation cost, and real deployment with smart relays.

## One-Line Close

Indra-Grid turns energy data into decisions that save money, reduce emissions, and keep small businesses running.
