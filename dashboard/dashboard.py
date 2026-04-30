import base64
from pathlib import Path
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.simulator import EnergySimulator
from logic.optimizer import EnergyOptimizer, EnergyState


API = "http://127.0.0.1:8001"
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "indra_grid_logo.png"


def brand_logo_data_uri():
    if not LOGO_PATH.exists():
        return ""
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def brand_logo_html(class_name="brand-logo", size=48):
    src = brand_logo_data_uri()
    if not src:
        return ""
    return f'<img class="{class_name}" src="{src}" width="{size}" height="{size}" alt="Indra-Grid logo">'


def run(username="Operator", role="Operator"):
    init_state()
    if st.session_state.get("view") not in {"Live Simulator", "Energy Flow", "Account"}:
        st.session_state.view = "Live Simulator"
    if st.session_state.get("range_sel") not in {"Day", "Week", "Month"}:
        st.session_state.range_sel = "Day"
    st.session_state.dark_mode = True

    entity_type = st.session_state.entity_type
    cfg = entity_config(entity_type)
    controls = sidebar(username, role, cfg)
    with st.spinner("Running energy optimizer..."):
        df = optimized_frame(cfg, controls)
        summary = summarize(df, cfg)

    inject_css()
    topbar(entity_type, st.session_state.view)

    if summary["unmet"] > 0:
        alert(f"{summary['unmet']:.1f} kWh unmet demand in selected simulation window")
    elif len(active_faults(df, cfg, summary)) > 0:
        alert(f"{len(active_faults(df, cfg, summary))} active operational events detected")

    view = st.session_state.view
    if view == "Live Simulator":
        dashboard_view(df, cfg, summary, username, entity_type)
    elif view == "Energy Flow":
        energy_flow_view(df, cfg, summary)
    elif view == "Account":
        account_view(username, role, cfg, entity_type)

    bottom_bar(view)


def init_state():
    defaults = {
        "range_sel": "Day",
        "entity_type": "Industrial Plant",
        "view": "Live Simulator",
        "dark_mode": True,
        "demand_multiplier": 1.0,
        "grid_available": True,
        "battery_soc": 76,
        "seed": 42,
        "scenario_mode": "Normal",
        "weather_lat": 26.4499,
        "weather_lon": 80.3319,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def entity_config(etype):
    configs = {
        "Industrial Plant": {
            "scale": 120,
            "capacity_kw": 10000,
            "battery_capacity": 8000,
            "battery_label": "Li-Ion Battery Bank",
            "solar_label": "Rooftop + Ground Mount Solar",
            "load_label": "Factory Floor + HVAC + Lighting",
            "grid_label": "DISCOM HT Grid 33 kV",
            "grid_conn": "HT - 33 kV Substation",
            "tariff": 6.20,
            "co2_factor": 0.82,
            "pr": 84.1,
            "transformers": 3,
            "feeders": 8,
            "capex_rs": 640_000_000,
        },
        "Commercial Building": {
            "scale": 12,
            "capacity_kw": 500,
            "battery_capacity": 500,
            "battery_label": "UPS + Battery Storage",
            "solar_label": "Rooftop Solar Array",
            "load_label": "Offices + AC + Elevators",
            "grid_label": "Utility Grid LT",
            "grid_conn": "LT - 415 V",
            "tariff": 7.50,
            "co2_factor": 0.82,
            "pr": 81.5,
            "transformers": 1,
            "feeders": 4,
            "capex_rs": 32_000_000,
        },
        "Data Centre": {
            "scale": 65,
            "capacity_kw": 2000,
            "battery_capacity": 2200,
            "battery_label": "UPS + Li-Ion Backup",
            "solar_label": "On-Site Solar",
            "load_label": "Server Halls + Precision Cooling",
            "grid_label": "Utility Grid Dual Feed",
            "grid_conn": "HT - Redundant 11 kV",
            "tariff": 5.80,
            "co2_factor": 0.82,
            "pr": 76.2,
            "transformers": 4,
            "feeders": 12,
            "capex_rs": 155_000_000,
        },
        "Residential Campus": {
            "scale": 1,
            "capacity_kw": 50,
            "battery_capacity": 40,
            "battery_label": "Home Battery System",
            "solar_label": "Rooftop Solar",
            "load_label": "Residential + Common Area",
            "grid_label": "Net Metered Grid LT",
            "grid_conn": "LT - Net Metering",
            "tariff": 8.00,
            "co2_factor": 0.82,
            "pr": 83.4,
            "transformers": 1,
            "feeders": 2,
            "capex_rs": 3_000_000,
        },
    }
    return configs[etype]


def sidebar(username, role, cfg):
    with st.sidebar:
        st.markdown(
            f'<div class="side-brand">{brand_logo_html("side-logo", 54)}<div class="side-brand-text">INDRA-GRID</div></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="slabel">Entity Type</div>', unsafe_allow_html=True)
        st.selectbox(
            "Entity",
            ["Industrial Plant", "Commercial Building", "Data Centre", "Residential Campus"],
            key="entity_type",
            label_visibility="collapsed",
        )

        st.markdown('<div class="slabel">Navigation</div>', unsafe_allow_html=True)
        st.radio(
            "View",
            ["Live Simulator", "Energy Flow", "Account"],
            key="view",
            label_visibility="collapsed",
        )

        st.markdown('<div class="slabel">Optimizer Controls</div>', unsafe_allow_html=True)
        st.selectbox(
            "Demo Scenario",
            ["Normal", "Peak Tariff Event", "Grid Outage Drill", "Monsoon Solar Dip"],
            key="scenario_mode",
        )
        st.slider("Demand Multiplier", 0.5, 2.0, key="demand_multiplier", step=0.05)
        st.slider("Initial Battery SOC", 0, 100, key="battery_soc")
        st.toggle("Grid Available", key="grid_available")

        st.markdown('<div class="slabel">Weather API</div>', unsafe_allow_html=True)
        weather_df = get_solar_forecast(st.session_state.weather_lat, st.session_state.weather_lon)
        if weather_df is not None and not weather_df.empty:
            solar_days = summarize_solar_forecast(weather_df)
            current = current_or_next_solar_hour(weather_df)
            today = solar_days.iloc[0]
            st.metric("Next Solar Irradiance", f"{current['Radiation (W/m2)']:.0f} W/m2")
            st.metric("Today Peak", f"{today['Peak Radiation']:.0f} W/m2")
            st.metric("Cloud Cover", f"{today['Avg Cloud']:.0f}%")
        else:
            st.caption("Weather update unavailable")

        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.rerun()

        st.markdown(
            f"""
            <div class="status-box">
                <div class="status-title">Live Status</div>
                <div class="status-row"><span class="pulse-dot"></span> Optimizer online</div>
                <div class="status-meta">{username or "Operator"} | {role} | Battery cap {cfg['battery_capacity']:.0f} kWh</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return {
        "demand_multiplier": st.session_state.demand_multiplier,
        "grid_available": st.session_state.grid_available,
        "battery_soc": st.session_state.battery_soc,
        "seed": st.session_state.seed,
        "scenario_mode": st.session_state.scenario_mode,
        "weather_lat": st.session_state.weather_lat,
        "weather_lon": st.session_state.weather_lon,
    }


def optimized_frame(cfg, controls, hours=None):
    hours = hours or {"Day": 24, "Week": 24 * 7, "Month": 24 * 30, "Year": 24 * 30}[st.session_state.range_sel]
    sim = EnergySimulator(hours=hours, seed=int(controls["seed"]))
    raw = sim.generate()

    raw["solar"] = raw["solar"] * cfg["scale"]
    raw["demand"] = raw["demand"] * cfg["scale"] * controls["demand_multiplier"]
    raw["grid_available"] = bool(controls["grid_available"])
    raw = apply_demo_scenario(raw, controls.get("scenario_mode", "Normal"))

    optimizer = EnergyOptimizer()
    battery = cfg["battery_capacity"] * controls["battery_soc"] / 100
    rows = []

    for _, row in raw.iterrows():
        hour = int(row["hour"])
        state = EnergyState(
            solar=float(row["solar"]),
            demand=float(row["demand"]),
            battery_level=battery,
            battery_capacity=cfg["battery_capacity"],
            grid_available=bool(row["grid_available"]),
            grid_price=float(row["grid_price"]),
            peak_hour=6 <= hour <= 9 or 18 <= hour <= 22,
        )
        usage, battery = optimizer.optimize(state)
        rows.append(
            {
                "step": int(row["step"]),
                "hour": hour,
                "time": row["time"],
                "solar": state.solar,
                "demand": state.demand,
                "grid_price": state.grid_price,
                "solar_used": usage.solar_used,
                "battery_used": usage.battery_used,
                "grid_used": usage.grid_used,
                "battery_charged": usage.battery_charged,
                "unmet_demand": usage.unmet_demand,
                "battery_level": battery,
                "grid_available": state.grid_available,
                "decision": usage.decision,
            }
        )

    return pd.DataFrame(rows)


def apply_demo_scenario(raw, scenario_mode):
    raw = raw.copy()
    evening = raw["hour"].between(18, 22)

    if scenario_mode == "Peak Tariff Event":
        raw.loc[evening, "grid_price"] *= 1.75
        raw.loc[evening, "demand"] *= 1.15
    elif scenario_mode == "Grid Outage Drill":
        outage = raw["hour"].between(19, 21)
        raw.loc[outage, "grid_available"] = False
        raw.loc[outage, "demand"] *= 1.10
    elif scenario_mode == "Monsoon Solar Dip":
        daylight = raw["hour"].between(8, 17)
        raw.loc[daylight, "solar"] *= 0.55
        raw.loc[daylight, "grid_price"] *= 1.12

    return raw


def summarize(df, cfg):
    solar = df["solar_used"].sum()
    demand = df["demand"].sum()
    grid = df["grid_used"].sum()
    battery = df["battery_used"].sum() + df["battery_charged"].sum()
    unmet = df["unmet_demand"].sum()
    served = max(demand - unmet, 0)
    export = np.maximum(df["solar"] - df["solar_used"] - df["battery_charged"] / 0.9, 0).sum()
    battery_arbitrage = df["battery_used"].sum() * cfg["tariff"] * 0.15
    annual_factor = 8760 / max(len(df), 1)
    annual_savings = (solar * cfg["tariff"] + battery_arbitrage) * annual_factor
    payback_years = cfg["capex_rs"] / annual_savings if annual_savings > 0 else 0
    roi_pct = annual_savings / cfg["capex_rs"] * 100 if cfg["capex_rs"] > 0 else 0
    outage_rows = df[df["grid_available"] == False] if "grid_available" in df else df.iloc[0:0]
    peak_unmet = df["unmet_demand"].max()
    reserve_gap = max(0, 30 - (0 if cfg["battery_capacity"] == 0 else df["battery_level"].iloc[-1] / cfg["battery_capacity"] * 100))
    battery_addition = max(0, unmet / 0.9 + reserve_gap / 100 * cfg["battery_capacity"])
    return {
        "solar": solar,
        "demand": demand,
        "served": served,
        "grid": grid,
        "battery": battery,
        "unmet": unmet,
        "reliability": 100 if demand == 0 else served / demand * 100,
        "peak_unmet": peak_unmet,
        "outage_hours": len(outage_rows),
        "recommended_battery_addition": battery_addition,
        "export": export,
        "co2": solar * cfg["co2_factor"],
        "self_suff": 0 if demand == 0 else min(100, (solar + df["battery_used"].sum()) / demand * 100),
        "cost": grid * cfg["tariff"],
        "savings": solar * cfg["tariff"],
        "soc": 0 if cfg["battery_capacity"] == 0 else df["battery_level"].iloc[-1] / cfg["battery_capacity"] * 100,
        "battery_arbitrage": battery_arbitrage,
        "annual_savings": annual_savings,
        "payback_years": payback_years,
        "roi_pct": roi_pct,
    }


def report_frame(df, cfg):
    out = df.copy()
    out["grid_cost_rs"] = out["grid_used"] * cfg["tariff"]
    out["solar_savings_rs"] = out["solar_used"] * cfg["tariff"]
    out["co2_avoided_kg"] = out["solar_used"] * cfg["co2_factor"]
    return out


def recommendations(df, cfg, summary):
    latest = df.iloc[-1]
    peak_grid = df[(df["hour"].between(18, 22)) & (df["grid_used"] > 0)]["grid_used"].sum()
    recs = []

    if summary["unmet"] > 0:
        recs.append(("Critical", f"{summary['unmet']:.0f} kWh demand is unserved. Shed non-critical load or add about {summary['recommended_battery_addition']:.0f} kWh usable battery."))
    if summary["soc"] < 30:
        recs.append(("Warning", "Battery SOC is near reserve. Avoid deep discharge and schedule grid charging before the next evening peak."))
    if peak_grid > 0:
        savings = peak_grid * cfg["tariff"] * 0.20
        recs.append(("Peak", f"Evening peak still imports {peak_grid:.0f} kWh. Shifting flexible load can save about Rs {savings:,.0f}."))
    if summary["self_suff"] >= 60:
        recs.append(("Green", "Self-sufficiency is strong. Keep battery reserve active and export excess solar only after storage is full."))
    if latest["grid_price"] > 8 and latest["grid_used"] > 0:
        recs.append(("Tariff", "Current grid price is high while grid is being used. Increase battery SOC before this hour in future runs."))
    if summary["payback_years"] and summary["payback_years"] <= 6:
        recs.append(("ROI", f"Projected payback is {summary['payback_years']:.1f} years at current dispatch savings."))
    if not recs:
        recs.append(("Stable", "Solar, battery, and grid dispatch are balanced for this scenario."))
    return recs


def operator_actions(df, cfg, summary):
    actions = []
    peak_grid = df[(df["hour"].between(18, 22)) & (df["grid_used"] > 0)]["grid_used"].sum()
    flexible_load = summary["demand"] * 0.12

    if summary["unmet"] > 0:
        actions.append(("Immediate", f"Shed or reschedule {min(summary['peak_unmet'], flexible_load):.0f} kWh non-critical load during outage hours."))
        actions.append(("Sizing", f"Add roughly {summary['recommended_battery_addition']:.0f} kWh usable battery to cover this scenario with reserve."))
    if summary["soc"] < 30:
        actions.append(("Battery", "Start pre-charging before evening peak and keep reserve above 30% for outage readiness."))
    if peak_grid > 0:
        actions.append(("Tariff", f"Shift {min(peak_grid * 0.25, flexible_load):.0f} kWh flexible load away from 18:00-22:00."))
    if summary["export"] > summary["demand"] * 0.05:
        actions.append(("Solar", f"{summary['export']:.0f} kWh solar is unused/exported. Move daytime loads or increase storage."))
    if not actions:
        actions.append(("Operate", "No urgent action. Keep current dispatch profile and monitor weather forecast before peak hours."))
    return actions


def auth_headers():
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


@st.cache_data(ttl=3600)
def get_solar_forecast(lat=26.4499, lon=80.3319):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "forecast_days": 7, "timezone": "auto"}
    try:
        response = requests.get(
            url,
            params={**params, "hourly": "shortwave_radiation,cloud_cover,precipitation_probability,temperature_2m"},
            timeout=6,
        ).json()
        hourly = response["hourly"]
        return pd.DataFrame(
            {
                "Time": pd.to_datetime(hourly["time"]),
                "Radiation (W/m2)": hourly["shortwave_radiation"],
                "Cloud Cover (%)": hourly["cloud_cover"],
                "Rain Probability (%)": hourly.get("precipitation_probability", [0] * len(hourly["time"])),
                "Temperature (C)": hourly.get("temperature_2m", [0] * len(hourly["time"])),
            }
        )
    except Exception as exc:
        st.warning(f"Weather update failed: {exc}")
        return None


def current_or_next_solar_hour(weather_df):
    now = pd.Timestamp.now()
    upcoming = weather_df[weather_df["Time"] >= now]
    daylight = upcoming[upcoming["Radiation (W/m2)"] > 25]
    if not daylight.empty:
        return daylight.iloc[0]
    if not upcoming.empty:
        return upcoming.iloc[0]
    return weather_df.iloc[-1]


def summarize_solar_forecast(weather_df):
    df = weather_df.copy()
    df["Date"] = df["Time"].dt.date
    rows = []
    for day, group in df.groupby("Date", sort=True):
        daylight = group[group["Radiation (W/m2)"] > 25]
        source = daylight if not daylight.empty else group
        peak_radiation = float(group["Radiation (W/m2)"].max())
        avg_daylight = float(source["Radiation (W/m2)"].mean())
        avg_cloud = float(source["Cloud Cover (%)"].mean())
        rain_risk = float(source["Rain Probability (%)"].max())
        solar_score = max(0, min(100, (avg_daylight / 750 * 100) - (avg_cloud * 0.35) - (rain_risk * 0.15)))
        if solar_score >= 70:
            plan = "High solar: run flexible loads in daytime"
        elif solar_score >= 45:
            plan = "Moderate solar: keep battery reserve ready"
        else:
            plan = "Low solar: reduce daytime dependency"
        rows.append(
            {
                "Day": pd.Timestamp(day).strftime("%a %d %b"),
                "Peak Radiation": peak_radiation,
                "Avg Daylight": avg_daylight,
                "Avg Cloud": avg_cloud,
                "Rain Risk": rain_risk,
                "Solar Score": solar_score,
                "Plan": plan,
            }
        )
    return pd.DataFrame(rows).head(7)


def fetch_weather_forecast(lat, lon):
    try:
        res = requests.get(
            f"{API}/weather/forecast",
            params={"latitude": lat, "longitude": lon},
            timeout=6,
        )
        return res.json()
    except Exception:
        return {"status": "offline", "source": "dashboard-fallback", "hours": []}


def weather_adjusted_frame(cfg, controls, weather):
    df = optimized_frame(cfg, controls, hours=24)
    hours = weather.get("hours", [])
    if not hours:
        return df

    cloud = pd.Series([float(item.get("cloud_cover_pct", 50)) for item in hours[: len(df)]])
    rain = pd.Series([float(item.get("precipitation_probability_pct", 0)) for item in hours[: len(df)]])
    solar_factor = (1 - cloud.reindex(df.index, fill_value=50) / 100 * 0.55).clip(lower=0.35, upper=1.0)
    demand_factor = (1 + rain.reindex(df.index, fill_value=0) / 100 * 0.08).clip(lower=1.0, upper=1.12)

    adjusted_controls = dict(controls)
    raw = EnergySimulator(hours=24, seed=int(controls["seed"]) + 1).generate()
    raw["solar"] = raw["solar"] * cfg["scale"] * solar_factor.to_numpy()
    raw["demand"] = raw["demand"] * cfg["scale"] * controls["demand_multiplier"] * demand_factor.to_numpy()
    raw["grid_available"] = bool(controls["grid_available"])
    raw = apply_demo_scenario(raw, adjusted_controls.get("scenario_mode", "Normal"))

    optimizer = EnergyOptimizer()
    battery = cfg["battery_capacity"] * controls["battery_soc"] / 100
    rows = []
    for _, row in raw.iterrows():
        hour = int(row["hour"])
        state = EnergyState(
            solar=float(row["solar"]),
            demand=float(row["demand"]),
            battery_level=battery,
            battery_capacity=cfg["battery_capacity"],
            grid_available=bool(row["grid_available"]),
            grid_price=float(row["grid_price"]),
            peak_hour=6 <= hour <= 9 or 18 <= hour <= 22,
        )
        usage, battery = optimizer.optimize(state)
        rows.append(
            {
                "step": int(row["step"]),
                "hour": hour,
                "time": row["time"],
                "solar": state.solar,
                "demand": state.demand,
                "grid_price": state.grid_price,
                "solar_used": usage.solar_used,
                "battery_used": usage.battery_used,
                "grid_used": usage.grid_used,
                "battery_charged": usage.battery_charged,
                "unmet_demand": usage.unmet_demand,
                "battery_level": battery,
                "grid_available": state.grid_available,
                "decision": usage.decision,
            }
        )
    return pd.DataFrame(rows)


def inject_css():
    dk = st.session_state.dark_mode
    bg = "#0F0D0A" if dk else "#F7F5F2"
    surface = "#1C1A16" if dk else "#FFFFFF"
    border = "#2E2A22" if dk else "#E8DDD0"
    text = "#F0EAE0" if dk else "#1A1008"
    muted = "#9A8568" if dk else "#7A6A50"
    accent = "#C87000"
    red = "#C84000"
    green = "#3A8C50"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700;800&display=swap');
        .stApp {{ background:{bg}; color:{text}; font-family:'Barlow',sans-serif; }}
        #MainMenu, footer {{ visibility:hidden; }}
        header {{ background:transparent !important; }}
        [data-testid="collapsedControl"] {{
            visibility:visible !important;
            display:flex !important;
            position:fixed !important;
            top:12px !important;
            left:12px !important;
            z-index:9999 !important;
            width:36px !important;
            height:36px !important;
            align-items:center !important;
            justify-content:center !important;
            border:1.5px solid {border} !important;
            border-radius:6px !important;
            background:{surface} !important;
            box-shadow:0 6px 18px rgba(0,0,0,.08) !important;
        }}
        [data-testid="collapsedControl"] svg {{
            color:{accent} !important;
            stroke:{accent} !important;
        }}
        .block-container {{ padding:0 !important; max-width:100% !important; }}
        .stApp::before {{
            content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
            background-image:linear-gradient(rgba(200,140,50,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(200,140,50,.04) 1px,transparent 1px);
            background-size:40px 40px;
        }}
        section[data-testid="stSidebar"] > div {{ background:{'#131109' if dk else '#FDFBF8'} !important; border-right:2px solid {border}; }}
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] {{
            color:{text} !important;
        }}
        section[data-testid="stSidebar"] .stRadio label,
        section[data-testid="stSidebar"] .stCheckbox label,
        section[data-testid="stSidebar"] .stToggle label,
        section[data-testid="stSidebar"] .stSlider label,
        section[data-testid="stSidebar"] .stNumberInput label,
        section[data-testid="stSidebar"] .stSelectbox label {{
            color:{text} !important;
            font-weight:600;
        }}
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {{
            color:{text} !important;
        }}
        section[data-testid="stSidebar"] [role="radiogroup"] label p,
        section[data-testid="stSidebar"] [data-testid="stThumbValue"],
        section[data-testid="stSidebar"] [data-testid="stTickBarMin"],
        section[data-testid="stSidebar"] [data-testid="stTickBarMax"] {{
            color:{text} !important;
        }}
        section[data-testid="stSidebar"] input {{
            color:{text} !important;
            background:{'#0F1117' if dk else '#FFFFFF'} !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button {{
            background:{'#242018' if dk else '#F7F5F2'} !important;
            color:{text} !important;
            border-color:{border} !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stNumberInput"] button svg {{
            fill:{text} !important;
            color:{text} !important;
        }}
        section[data-testid="stSidebar"] button {{
            color:{'#FFFFFF' if dk else text} !important;
        }}
        section[data-testid="stSidebar"] .stButton button {{
            background:{'#2A2933' if dk else '#FFFFFF'} !important;
            color:{text} !important;
            border:1.5px solid {border} !important;
        }}
        section[data-testid="stSidebar"] .stButton button:hover {{
            border-color:{accent} !important;
            color:{accent} !important;
        }}
        .side-brand {{ display:flex; align-items:center; justify-content:center; gap:10px; padding:18px 0 14px; color:{accent}; font-family:'Barlow Condensed'; font-weight:800; font-size:22px; letter-spacing:3px; }}
        .side-logo {{ width:54px; height:54px; object-fit:cover; border-radius:8px; border:1px solid {border}; }}
        .side-brand-text {{ line-height:1; text-align:left; }}
        .side-brand-text div {{ margin-top:4px; font-size:9px; color:{muted}; letter-spacing:2.5px; text-transform:uppercase; }}
        .topbar {{ position:sticky; top:0; z-index:600; height:56px; background:{surface}; border-bottom:2px solid {border}; display:flex; align-items:center; }}
        .brand-zone {{ padding:0 24px; min-width:230px; border-right:1.5px solid {border}; display:flex; align-items:center; gap:10px; }}
        .top-logo {{ width:40px; height:40px; object-fit:cover; border-radius:7px; border:1px solid {border}; }}
        .brand-name {{ font-family:'Barlow Condensed'; font-size:18px; font-weight:800; letter-spacing:3px; color:{accent}; text-transform:uppercase; }}
        .topbar-center {{ flex:1; padding:0 24px; display:flex; gap:9px; align-items:center; }}
        .view-crumb {{ font-family:'Barlow Condensed'; font-size:12px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{muted}; }}
        .view-crumb-active {{ color:{accent}; background:rgba(200,112,0,.08); padding:2px 10px; border-radius:3px; }}
        .topbar-right {{ display:flex; align-items:center; gap:12px; padding:0 20px; border-left:1.5px solid {border}; }}
        .page {{ padding:18px 24px 78px; }}
        .page-pad {{ height:18px; }}
        .slabel {{ font-family:'Barlow Condensed'; font-size:10px; font-weight:700; letter-spacing:3px; text-transform:uppercase; color:{muted}; margin:16px 0 10px; display:flex; align-items:center; gap:10px; }}
        .slabel::after {{ content:''; flex:1; height:1px; background:{border}; }}
        .panel, .kpi-card, .flow-card {{ background:{surface}; border:1.5px solid {border}; border-radius:8px; }}
        .panel {{ padding:18px 20px; margin-bottom:14px; }}
        .panel-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; padding-bottom:12px; border-bottom:1px solid {border}; }}
        .solo-head {{ background:{surface}; border:1.5px solid {border}; border-radius:8px 8px 0 0; padding:14px 16px; margin-bottom:0; }}
        .panel-title {{ font-family:'Barlow Condensed'; font-size:13px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{text}; }}
        .kpi-grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:16px; }}
        .kpi-card {{ border-top:3px solid {accent}; padding:16px; }}
        .kpi-label, .flow-label {{ font-family:'Barlow Condensed'; font-size:9px; font-weight:700; letter-spacing:2.2px; text-transform:uppercase; color:{muted}; margin-bottom:8px; }}
        .kpi-val {{ font-family:'DM Mono'; font-size:24px; color:{text}; line-height:1; }}
        .kpi-unit {{ font-size:11px; color:{muted}; margin-left:3px; }}
        .kpi-delta {{ font-size:10px; font-weight:700; color:{accent}; margin-top:6px; }}
        .neg {{ color:{red}; }}
        .drow {{ display:flex; justify-content:space-between; align-items:center; gap:10px; padding:10px 0; border-bottom:1px solid {'#242018' if dk else '#F5F0E8'}; font-size:12px; }}
        .drow:last-child {{ border-bottom:none; }}
        .drow-label {{ font-weight:600; color:{text}; }}
        .drow-val {{ font-family:'DM Mono'; font-size:11px; color:{muted}; text-align:right; }}
        .tag {{ font-family:'Barlow Condensed'; font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; padding:3px 9px; border-radius:3px; white-space:nowrap; }}
        .tag-on {{ background:rgba(58,140,80,.12); color:{green}; border:1px solid rgba(58,140,80,.3); }}
        .tag-warn {{ background:rgba(200,112,0,.12); color:{accent}; border:1px solid rgba(200,112,0,.3); }}
        .tag-err {{ background:rgba(200,64,0,.12); color:{red}; border:1px solid rgba(200,64,0,.3); }}
        .prog-wrap {{ margin-bottom:12px; }}
        .prog-meta {{ display:flex; justify-content:space-between; font-size:10px; font-weight:700; letter-spacing:.8px; text-transform:uppercase; color:{muted}; margin-bottom:4px; }}
        .prog-track, .flow-bar-track {{ height:5px; background:{border}; border-radius:3px; overflow:hidden; }}
        .prog-fill {{ height:100%; background:linear-gradient(90deg,{accent},#E8A840); }}
        .flow-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin-bottom:14px; }}
        .flow-card {{ padding:16px; }}
        .flow-val {{ font-family:'DM Mono'; font-size:20px; color:{text}; }}
        .flow-bar-fill {{ height:100%; background:{accent}; }}
        .flow-diagram {{ display:grid; grid-template-columns:1fr auto 1fr auto 1fr; align-items:center; gap:12px; padding:24px 16px; }}
        .flow-node {{ text-align:center; }}
        .flow-node-icon {{ width:58px; height:58px; margin:0 auto 8px; border:2px solid {border}; border-radius:8px; display:flex; align-items:center; justify-content:center; color:{accent}; font-weight:800; font-size:18px; }}
        .flow-node-label {{ font-family:'Barlow Condensed'; font-size:10px; font-weight:700; letter-spacing:2px; color:{muted}; text-transform:uppercase; }}
        .flow-node-val {{ font-family:'DM Mono'; font-size:13px; color:{text}; }}
        .flow-arrow {{ color:{accent}; font-family:'DM Mono'; }}
        .alert-banner {{ background:rgba(200,64,0,.08); border:1.5px solid rgba(200,64,0,.3); border-radius:8px; padding:12px 16px; display:flex; align-items:center; gap:12px; margin:14px 24px 0; }}
        .alert-text {{ font-size:12px; font-weight:700; color:{red}; }}
        .pulse-dot, .alert-dot {{ width:9px; height:9px; border-radius:50%; background:{accent}; display:inline-block; }}
        .alert-dot {{ background:{red}; }}
        .status-box {{ margin-top:18px; padding:12px; background:rgba(200,112,0,.08); border:1px solid rgba(200,112,0,.2); border-radius:6px; }}
        .status-title {{ font-size:9px; font-weight:700; letter-spacing:2px; color:{accent}; text-transform:uppercase; margin-bottom:6px; }}
        .status-row {{ display:flex; gap:8px; align-items:center; font-size:11px; color:{muted}; font-weight:600; }}
        .status-meta {{ font-family:'DM Mono'; font-size:10px; color:{muted}; margin-top:6px; }}
        .range-strip {{ display:inline-flex; background:{surface}; border:1.5px solid {border}; border-radius:6px; overflow:hidden; margin-bottom:8px; }}
        .range-btn {{ padding:7px 20px; font-family:'Barlow Condensed'; font-size:11px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{muted}; border-right:1px solid {border}; }}
        .range-active {{ background:{accent}; color:white; }}
        div[role="radiogroup"] {{
            display:inline-flex;
            background:{surface};
            border:1.5px solid {border};
            border-radius:6px;
            overflow:hidden;
            margin-bottom:14px;
        }}
        div[role="radiogroup"] label {{
            min-width:76px;
            justify-content:center;
            padding:7px 18px;
            border-right:1px solid {border};
            font-family:'Barlow Condensed';
            font-size:11px;
            font-weight:700;
            letter-spacing:1.5px;
            text-transform:uppercase;
            color:{text} !important;
        }}
        div[role="radiogroup"] label p {{
            color:{text} !important;
        }}
        div[role="radiogroup"] label:last-child {{ border-right:none; }}
        div[role="radiogroup"] label:has(input:checked) {{
            background:{accent};
            color:#fff !important;
        }}
        div[role="radiogroup"] label:has(input:checked) p {{
            color:#fff !important;
        }}
        .bottom-bar {{ position:fixed; bottom:0; left:0; right:0; z-index:500; background:{surface}; border-top:2px solid {border}; display:flex; justify-content:center; padding:8px 0; }}
        .bb-item {{ padding:4px 36px; border-right:1px solid {border}; font-family:'Barlow Condensed'; font-size:9px; font-weight:700; letter-spacing:2px; text-transform:uppercase; color:{muted}; }}
        .bb-active {{ color:{accent}; }}
        .analytics-table {{ width:100%; border-collapse:collapse; font-size:12px; }}
        .analytics-table th {{ text-align:left; padding:10px 14px; font-family:'Barlow Condensed'; font-size:9px; letter-spacing:2px; color:{muted}; text-transform:uppercase; border-bottom:2px solid {border}; }}
        .analytics-table td {{ padding:10px 14px; font-family:'DM Mono'; font-size:11px; color:{text}; border-bottom:1px solid {'#242018' if dk else '#F5F0E8'}; }}
        @media (max-width: 980px) {{ .kpi-grid, .flow-grid {{ grid-template-columns:1fr 1fr; }} .topbar-right {{ display:none; }} .bb-item {{ padding:4px 14px; }} }}
        @media (max-width: 640px) {{ .kpi-grid, .flow-grid {{ grid-template-columns:1fr; }} .flow-diagram {{ grid-template-columns:1fr; }} .flow-arrow {{ display:none; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def topbar(entity_type, view):
    timestamp = datetime.now().strftime("%d %b %Y %H:%M IST")
    st.markdown(
        f"""
        <div class="topbar">
            <div class="brand-zone">{brand_logo_html("top-logo", 40)}<div class="brand-name">Indra-Grid</div></div>
            <div class="topbar-center"><span class="view-crumb">{entity_type}</span><span class="view-crumb">/</span><span class="view-crumb view-crumb-active">{view}</span></div>
            <div class="topbar-right"><span class="pulse-dot"></span><span class="view-crumb">Optimizer Live</span><span class="view-crumb">{timestamp}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def alert(text):
    st.markdown(
        f'<div class="alert-banner"><div class="alert-dot"></div><div class="alert-text">{text}</div></div>',
        unsafe_allow_html=True,
    )


def range_selector():
    ranges = ["Day", "Week", "Month"]
    st.radio("Range", ranges, key="range_sel", horizontal=True, label_visibility="collapsed")


def dashboard_view(df, cfg, summary, username, entity_type):
    st.markdown('<div class="page-pad"></div>', unsafe_allow_html=True)
    range_selector()

    st.markdown('<div class="slabel">Live Simulator Summary</div>', unsafe_allow_html=True)
    kpis = "".join(
        [
            kpi("Solar Used", summary["solar"], "kWh", f"PR {cfg['pr']}%"),
            kpi("Total Demand", summary["demand"], "kWh", f"self-suff {summary['self_suff']:.0f}%", "neg"),
            kpi("Grid Import", summary["grid"], "kWh", f"Rs {summary['cost']/1000:.1f}K cost", "neg"),
            kpi("Reliability", summary["reliability"], "%", f"unmet {summary['unmet']:.0f} kWh", "neg" if summary["unmet"] else ""),
        ]
    )
    st.markdown(f'<div class="kpi-grid">{kpis}</div>', unsafe_allow_html=True)

    st.markdown('<div class="slabel">Optimizer Dispatch - Solar / Battery / Grid / Demand</div>', unsafe_allow_html=True)
    fig = dispatch_chart(df)
    st.markdown('<div class="panel-head solo-head"><span class="panel-title">Real-Time Energy Mix</span></div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    solar_forecast_panel()

    c1, c2 = st.columns([1.1, 1])
    with c1:
        live_inspector(df, cfg)
        battery_soc_chart(df, cfg)
    with c2:
        recommendation_panel(df, cfg, summary)
        action_plan_panel(df, cfg, summary)


def kpi(label, value, unit, delta, cls=""):
    display = value / 1000 if unit == "kWh" and value >= 10000 else value
    unit_display = "MWh" if unit == "kWh" and value >= 10000 else unit
    return f'<div class="kpi-card"><div class="kpi-label">{label}</div><div class="kpi-val">{display:.1f}<span class="kpi-unit">{unit_display}</span></div><div class="kpi-delta {cls}">{delta}</div></div>'


def dispatch_chart(df):
    plot_df = df.tail(48).copy()
    x = plot_df["step"].astype(str) if len(plot_df) > 30 else plot_df["time"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=plot_df["solar_used"], name="Solar Used", mode="lines", fill="tozeroy", line=dict(color="#C87000", width=2.5, shape="spline")))
    fig.add_trace(go.Scatter(x=x, y=plot_df["battery_used"], name="Battery Discharge", mode="lines", line=dict(color="#4A90D9", width=2, dash="dot", shape="spline")))
    fig.add_trace(go.Scatter(x=x, y=plot_df["grid_used"], name="Grid Import", mode="lines", line=dict(color="#C84000", width=2, dash="dash", shape="spline")))
    fig.add_trace(go.Scatter(x=x, y=plot_df["demand"], name="Demand", mode="lines", line=dict(color="#E8A840", width=2.2, shape="spline")))
    fig.update_layout(**chart_layout(280))
    fig.update_yaxes(ticksuffix=" kWh")
    return fig


def live_inspector(df, cfg):
    st.markdown('<div class="slabel">Hourly Inspector</div>', unsafe_allow_html=True)
    idx = st.slider("Inspect Hour", 0, len(df) - 1, min(len(df) - 1, 12))
    row = df.iloc[idx]
    rows = [
        ("Time", f"Step {int(row['step'])} | {row['time']}"),
        ("Demand", f"{row['demand']:.1f} kWh"),
        ("Solar Used", f"{row['solar_used']:.1f} kWh"),
        ("Battery Used", f"{row['battery_used']:.1f} kWh"),
        ("Battery Charged", f"{row['battery_charged']:.1f} kWh"),
        ("Grid Used", f"{row['grid_used']:.1f} kWh"),
        ("Grid Price", f"Rs {row['grid_price']:.2f}/kWh"),
        ("Decision", row["decision"]),
    ]
    rows_panel("Live Simulation State", rows)


def solar_forecast_panel():
    weather_df = get_solar_forecast(st.session_state.weather_lat, st.session_state.weather_lon)
    if weather_df is None or weather_df.empty:
        return

    forecast = summarize_solar_forecast(weather_df)
    rows = ""
    for _, day in forecast.iterrows():
        score = float(day["Solar Score"])
        tag = "tag-on" if score >= 70 else ("tag-warn" if score >= 45 else "tag-err")
        rows += (
            f'<div class="drow">'
            f'<span class="drow-label">{day["Day"]}<br><span class="drow-val">{day["Plan"]}</span></span>'
            f'<span class="drow-val">Peak {day["Peak Radiation"]:.0f} W/m2</span>'
            f'<span class="drow-val">Cloud {day["Avg Cloud"]:.0f}%</span>'
            f'<span class="drow-val">Rain {day["Rain Risk"]:.0f}%</span>'
            f'<span class="tag {tag}">{score:.0f}</span>'
            f'</div>'
        )
    st.markdown(f'<div class="slabel">7-Day Solar Weather Forecast</div><div class="panel">{rows}</div>', unsafe_allow_html=True)


def recommendation_panel(df, cfg, summary):
    rec_html = ""
    for label, text in recommendations(df, cfg, summary):
        tag = "tag-err" if label == "Critical" else ("tag-warn" if label in {"Warning", "Peak", "Tariff"} else "tag-on")
        rec_html += f'<div class="drow"><span class="tag {tag}">{label}</span><span class="drow-label" style="flex:1;">{text}</span></div>'
    st.markdown(f'<div class="slabel">AI Recommendations</div><div class="panel">{rec_html}</div>', unsafe_allow_html=True)


def action_plan_panel(df, cfg, summary):
    rows = ""
    for label, text in operator_actions(df, cfg, summary):
        tag = "tag-err" if label == "Immediate" else ("tag-warn" if label in {"Sizing", "Battery", "Tariff"} else "tag-on")
        rows += f'<div class="drow"><span class="tag {tag}">{label}</span><span class="drow-label" style="flex:1;">{text}</span></div>'
    st.markdown(f'<div class="slabel">Operator Action Plan</div><div class="panel">{rows}</div>', unsafe_allow_html=True)


def battery_soc_chart(df, cfg):
    fig = go.Figure()
    soc = df["battery_level"] / cfg["battery_capacity"] * 100
    fig.add_trace(go.Scatter(x=df["step"], y=soc, name="Battery SOC", mode="lines", fill="tozeroy", line=dict(color="#4A90D9", width=2.5)))
    fig.add_hline(y=20, line_dash="dash", line_color="#C84000")
    fig.update_layout(**chart_layout(210))
    fig.update_yaxes(ticksuffix="%")
    st.markdown('<div class="slabel">Battery Health</div><div class="panel-head solo-head"><span class="panel-title">SOC Trend and Reserve</span></div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def report_actions(df, cfg, summary, username, entity_type):
    st.markdown('<div class="slabel">Reports & Persistence</div>', unsafe_allow_html=True)
    report = report_frame(df, cfg)
    st.download_button(
        "Download Optimized CSV",
        report.to_csv(index=False).encode("utf-8"),
        file_name=f"indra_grid_{entity_type.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    report_text = build_text_report(summary, cfg, entity_type)
    st.download_button(
        "Download Summary Report",
        report_text,
        file_name="indra_grid_summary.txt",
        mime="text/plain",
        use_container_width=True,
    )

    if st.button("Save Simulation Run", use_container_width=True):
        payload = {
            "username": username or "operator",
            "entity_type": entity_type,
            "range_sel": st.session_state.range_sel,
            "solar_kwh": summary["solar"],
            "demand_kwh": summary["demand"],
            "grid_kwh": summary["grid"],
            "battery_kwh": summary["battery"],
            "co2_kg": summary["co2"],
            "cost_rs": summary["cost"],
            "self_sufficiency": summary["self_suff"],
            "final_soc": summary["soc"],
            "notes": recommendations(df, cfg, summary)[0][1],
        }
        try:
            with st.spinner("Saving simulation run..."):
                res = requests.post(f"{API}/runs", json=payload, headers=auth_headers(), timeout=4).json()
            if res.get("status") == "success":
                st.success(f"Saved run #{res['id']}")
            else:
                st.error("Could not save run.")
        except Exception:
            st.error("Backend not available, run was not saved.")


def build_text_report(summary, cfg, entity_type):
    carbon_credit_rate = 1200
    credits = summary["co2"] / 1000 * carbon_credit_rate
    return (
        f"Indra-Grid Summary\n"
        f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}\n"
        f"Entity: {entity_type}\n\n"
        f"Solar Used: {summary['solar']:.1f} kWh\n"
        f"Demand: {summary['demand']:.1f} kWh\n"
        f"Grid Import: {summary['grid']:.1f} kWh\n"
        f"Battery Flow: {summary['battery']:.1f} kWh\n"
        f"Final SOC: {summary['soc']:.1f}%\n"
        f"Self-Sufficiency: {summary['self_suff']:.1f}%\n"
        f"Grid Cost: Rs {summary['cost']:,.0f}\n"
        f"Solar Savings: Rs {summary['savings']:,.0f}\n"
        f"Battery Arbitrage: Rs {summary['battery_arbitrage']:,.0f}\n"
        f"Annualized Savings: Rs {summary['annual_savings']:,.0f}\n"
        f"Simple Payback: {summary['payback_years']:.1f} years\n"
        f"Annual ROI: {summary['roi_pct']:.1f}%\n"
        f"CO2 Avoided: {summary['co2'] / 1000:.2f} t\n"
        f"Carbon Credit Estimate: Rs {credits:,.0f}\n"
        f"Tariff: Rs {cfg['tariff']:.2f}/kWh\n"
    )


def chart_layout(height):
    dk = st.session_state.dark_mode
    text = "#F0EAE0" if dk else "#1A1008"
    muted = "#BBA98F" if dk else "#5E4B38"
    grid = "rgba(232,168,64,0.14)" if dk else "rgba(126,88,42,0.18)"
    zero = "#2E2A22" if dk else "#D8C7B3"
    return dict(
        height=height,
        margin=dict(l=0, r=0, t=4, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono, monospace", size=10, color=muted),
        legend=dict(orientation="h", x=0, y=1.12, font=dict(size=10, color=text), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(showgrid=True, gridcolor=grid, zeroline=False, showline=False, tickfont=dict(size=10, color=muted)),
        yaxis=dict(showgrid=True, gridcolor=grid, zeroline=True, zerolinecolor=zero, showline=False, tickfont=dict(size=10, color=muted)),
        hovermode="x unified",
    )


def equipment_panel(df, cfg):
    latest = df.iloc[-1]
    status = [
        (cfg["solar_label"], f"{latest['solar']:.0f} kWh", "on", "Online"),
        (cfg["battery_label"], f"{latest['battery_level']:.0f} kWh", "warn" if latest["battery_level"] < cfg["battery_capacity"] * 0.3 else "on", "Managed"),
        (cfg["grid_label"], f"{latest['grid_used']:.0f} kWh", "on" if latest["grid_used"] > 0 else "warn", "Import" if latest["grid_used"] > 0 else "Idle"),
        (cfg["load_label"], f"{latest['demand']:.0f} kWh", "on", "Served"),
        ("Optimizer Decision", latest["decision"], "warn" if latest["grid_used"] > 0 else "on", "Auto"),
    ]
    rows = ""
    for name, val, kind, label in status:
        rows += f'<div class="drow"><span class="drow-label">{name}</span><span class="drow-val">{val}</span><span class="tag tag-{kind}">{label}</span></div>'
    st.markdown(f'<div class="slabel">Equipment Status</div><div class="panel">{rows}</div>', unsafe_allow_html=True)


def performance_panel(summary, cfg):
    grid_dep = max(0, 100 - summary["self_suff"])
    items = [
        ("Plant PR", cfg["pr"]),
        ("Self-Sufficiency Ratio", summary["self_suff"]),
        ("Battery State of Charge", summary["soc"]),
        ("Grid Dependency", grid_dep),
        ("Solar Capacity Utilisation", min(100, summary["solar"] / max(cfg["capacity_kw"] * 24, 1) * 100)),
        ("Annual ROI", min(100, summary["roi_pct"])),
    ]
    rows = ""
    for label, value in items:
        rows += f'<div class="prog-wrap"><div class="prog-meta"><span>{label}</span><span>{value:.0f}%</span></div><div class="prog-track"><div class="prog-fill" style="width:{min(100, max(0, value)):.0f}%"></div></div></div>'
    st.markdown(f'<div class="slabel">Performance Indices</div><div class="panel">{rows}</div>', unsafe_allow_html=True)


def energy_flow_view(df, cfg, summary):
    latest = df.iloc[-1]
    st.markdown('<div class="page-pad"></div>', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Live Energy Flow</div>', unsafe_allow_html=True)
    flow_html = (
        f'<div class="panel flow-diagram">'
        f'{flow_node("SOL", cfg["solar_label"], latest["solar_used"])}'
        f'<div class="flow-arrow">--></div>'
        f'{flow_node("BUS", "Energy Bus", latest["demand"])}'
        f'<div class="flow-arrow">--></div>'
        f'{flow_node("LOD", cfg["load_label"], latest["demand"])}'
        f'</div>'
    )
    st.markdown(flow_html, unsafe_allow_html=True)

    flow_cards = "".join(
        [
            flow_card(cfg["solar_label"], latest["solar_used"], cfg["capacity_kw"], "Source available"),
            flow_card(cfg["battery_label"], latest["battery_level"], cfg["battery_capacity"], f"{summary['soc']:.0f}% SOC"),
            flow_card(cfg["grid_label"], latest["grid_used"], max(df["grid_used"].max(), 1), f"Rs {cfg['tariff']:.2f}/kWh"),
        ]
    )
    st.markdown(f'<div class="flow-grid">{flow_cards}</div>', unsafe_allow_html=True)

    sankey = go.Figure(
        go.Sankey(
            arrangement="fixed",
            node=dict(
                pad=24,
                thickness=20,
                line=dict(color="#E8DDD0", width=0.5),
                label=["Solar", "Grid", "Battery", "Facility Load", "Unmet"],
                color=["#C87000", "#C84000", "#4A90D9", "#E8A840", "#777777"],
                x=[0.02, 0.02, 0.02, 0.92, 0.92],
                y=[0.18, 0.48, 0.76, 0.34, 0.78],
            ),
            link=dict(
                source=[0, 1, 2, 4],
                target=[3, 3, 3, 3],
                value=[
                    max(summary["solar"], 0.1),
                    max(summary["grid"], 0.1),
                    max(df["battery_used"].sum(), 0.1),
                    max(summary["unmet"], 0.1),
                ],
                color=["rgba(200,112,0,.25)", "rgba(200,64,0,.2)", "rgba(74,144,217,.25)", "rgba(80,80,80,.2)"],
            ),
        )
    )
    sankey.update_layout(height=380, margin=dict(l=20, r=20, t=10, b=30), paper_bgcolor="rgba(0,0,0,0)")
    st.markdown('<div class="slabel">Energy Sankey - Selected Range</div><div class="panel-head solo-head"><span class="panel-title">Source to Load Sankey</span></div>', unsafe_allow_html=True)
    st.plotly_chart(sankey, use_container_width=True, config={"displayModeBar": False})

    col1, col2 = st.columns(2)
    with col1:
        rows_panel("Costs & Savings", [
            ("Grid Import Cost", f"Rs {summary['cost']:,.0f}"),
            ("Solar Savings", f"Rs {summary['savings']:,.0f}"),
            ("Export Estimate", f"{summary['export']:.1f} kWh"),
            ("Battery Arbitrage", f"Rs {summary['battery_arbitrage']:,.0f}"),
            ("Annualized Savings", f"Rs {summary['annual_savings']:,.0f}"),
            ("Simple Payback", f"{summary['payback_years']:.1f} years"),
        ])
    with col2:
        rows_panel("Energy Source Mix", [
            ("Solar Share", pct(summary["solar"], summary["demand"])),
            ("Grid Share", pct(summary["grid"], summary["demand"])),
            ("Battery Share", pct(df["battery_used"].sum(), summary["demand"])),
            ("Unmet Demand", f"{summary['unmet']:.1f} kWh"),
            ("CO2 Intensity", f"{summary['grid'] * cfg['co2_factor'] / max(summary['demand'], 1) * 1000:.0f} gCO2/kWh"),
        ])

def flow_node(code, label, value):
    return f'<div class="flow-node"><div class="flow-node-icon">{code}</div><div class="flow-node-label">{label}</div><div class="flow-node-val">{value:.1f} kWh</div></div>'


def flow_card(label, value, max_value, meta):
    width = min(100, value / max(max_value, 1) * 100)
    return f'<div class="flow-card"><div class="flow-label">{label}</div><div class="flow-val">{value:.1f} kWh</div><div class="flow-bar-track"><div class="flow-bar-fill" style="width:{width:.0f}%"></div></div><div class="drow-val" style="text-align:left;margin-top:6px;">{meta}</div></div>'


def active_faults(df, cfg, summary):
    return [f for f in fault_data(df, cfg, summary) if f[3] == "active"]


def fault_data(df, cfg, summary):
    now = datetime.now().strftime("%d %b %Y %H:%M IST")
    faults = []

    if summary["unmet"] > 0:
        worst = df.loc[df["unmet_demand"].idxmax()]
        faults.append((
            "Unserved Load During Outage",
            f"{cfg['load_label']} | Step {int(worst['step'])} {worst['time']}",
            now,
            "active",
            "P1",
        ))

    if summary["soc"] < 25:
        faults.append((
            "Battery SOC Below Operating Reserve",
            cfg["battery_label"],
            now,
            "active",
            "P2",
        ))

    if "grid_available" in df and not bool(df["grid_available"].all()):
        outage_hours = df[df["grid_available"] == False]["time"].tolist()
        faults.append((
            "Grid Outage Window Detected",
            f"{cfg['grid_label']} | {', '.join(outage_hours[:3])}",
            now,
            "active" if summary["unmet"] > 0 else "resolved",
            "P2",
        ))

    evening_grid = df[(df["hour"].between(18, 22)) & (df["grid_used"] > 0)]["grid_used"].sum()
    if evening_grid > summary["demand"] * 0.08:
        faults.append((
            "High Peak-Hour Grid Import",
            f"{cfg['grid_label']} | {evening_grid:.0f} kWh evening import",
            now,
            "active",
            "P3",
        ))

    if summary["export"] > summary["demand"] * 0.05:
        faults.append((
            "Solar Surplus Not Fully Stored",
            f"{cfg['solar_label']} | {summary['export']:.0f} kWh export",
            now,
            "resolved",
            "P3",
        ))

    if not faults:
        faults.append((
            "No Critical Operational Faults",
            "Optimizer dispatch is within reserve and reliability limits",
            now,
            "resolved",
            "P3",
        ))

    return faults


def fault_log_view(df, cfg, summary):
    faults = fault_data(df, cfg, summary)
    st.markdown('<div class="page-pad"></div>', unsafe_allow_html=True)
    total = len(faults)
    active = len(active_faults(df, cfg, summary))
    resolved = total - active
    fault_kpis = "".join(
        [
            kpi("Total Events", total, "", "all logged"),
            kpi("Active", active, "", "needs attention", "neg"),
            kpi("Resolved", resolved, "", "closed"),
        ]
    )
    st.markdown(f'<div class="kpi-grid" style="grid-template-columns:repeat(3,1fr);">{fault_kpis}</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 2])
    filt = col1.selectbox("Filter", ["All", "Active", "Resolved"])
    search = col2.text_input("Search", placeholder="fault name, location")
    filtered = faults
    if filt != "All":
        filtered = [f for f in filtered if f[3] == filt.lower()]
    if search:
        q = search.lower()
        filtered = [f for f in filtered if q in f[0].lower() or q in f[1].lower()]

    rows = ""
    for i, (title, loc, ts, status, priority) in enumerate(filtered, 1):
        tag = "tag-err" if status == "active" else "tag-on"
        rows += f'<div class="drow"><span class="drow-val">{i:02d}</span><span class="drow-label">{title}<br><span class="drow-val">{loc} | {ts}</span></span><span class="tag {tag}">{status}</span><span class="drow-val">{priority}</span></div>'
    st.markdown(f'<div class="slabel">Fault Event Log</div><div class="panel">{rows}</div>', unsafe_allow_html=True)
    if not filtered:
        st.info("No faults match this filter.")


def analytics_view(df, cfg):
    st.markdown('<div class="page-pad"></div>', unsafe_allow_html=True)
    monthly = make_monthly(df, cfg)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly["month"], y=monthly["solar_mwh"], name="Solar MWh", marker_color="#C87000"))
    fig.add_trace(go.Bar(x=monthly["month"], y=monthly["grid_mwh"], name="Grid MWh", marker_color="#C84000", opacity=0.75))
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["load_mwh"], name="Load MWh", mode="lines+markers", line=dict(color="#E8A840", width=2.5)))
    fig.update_layout(**chart_layout(300), barmode="group")
    fig.update_yaxes(ticksuffix=" MWh")
    st.markdown('<div class="slabel">6-Month Energy Summary</div><div class="panel-head solo-head"><span class="panel-title">Solar vs Grid vs Load</span></div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    rows = ""
    for _, r in monthly.iterrows():
        rows += f"<tr><td>{r['month']}</td><td>{r['solar_mwh']:.1f}</td><td>{r['grid_mwh']:.1f}</td><td>{r['self_suff']:.0f}%</td><td>{r['co2_t']:.1f}</td><td>Rs {r['grid_cost']:,.0f}</td></tr>"
    st.markdown(
        f"""
        <div class="slabel">Monthly Statistics</div>
        <div class="panel" style="overflow-x:auto;">
            <table class="analytics-table">
                <thead><tr><th>Month</th><th>Solar MWh</th><th>Grid MWh</th><th>Self-Suff.</th><th>CO2 Avoided t</th><th>Grid Cost</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )


def make_monthly(df, cfg):
    base_solar = df["solar_used"].sum() / 1000
    base_grid = df["grid_used"].sum() / 1000
    base_load = df["demand"].sum() / 1000
    factors = np.array([0.72, 0.66, 0.76, 0.88, 0.96, 1.04])
    months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"]
    out = pd.DataFrame(
        {
            "month": months,
            "solar_mwh": base_solar * factors,
            "grid_mwh": base_grid * factors[::-1],
            "load_mwh": base_load * (0.92 + factors / 10),
        }
    )
    out["self_suff"] = out["solar_mwh"] / out["load_mwh"].clip(lower=1) * 100
    out["co2_t"] = out["solar_mwh"] * cfg["co2_factor"]
    out["grid_cost"] = out["grid_mwh"] * 1000 * cfg["tariff"]
    return out


def forecast_view(cfg, controls):
    st.markdown('<div class="page-pad"></div>', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Weather-Aware Forecast</div>', unsafe_allow_html=True)

    forecast_controls = dict(controls)
    forecast_controls["seed"] = int(controls["seed"]) + 1
    with st.spinner("Fetching weather forecast and recalculating dispatch..."):
        weather = fetch_weather_forecast(controls["weather_lat"], controls["weather_lon"])
        df = weather_adjusted_frame(cfg, forecast_controls, weather)

    summary = summarize(df, cfg)
    kpis = "".join(
        [
            kpi("Forecast Solar", summary["solar"], "kWh", "tomorrow"),
            kpi("Forecast Demand", summary["demand"], "kWh", f"self-suff {summary['self_suff']:.0f}%", "neg"),
            kpi("Grid Exposure", summary["grid"], "kWh", f"Rs {summary['cost']/1000:.1f}K"),
            kpi("Final SOC", summary["soc"], "%", "after 24h"),
            kpi("CO2 Avoided", summary["co2"] / 1000, "t", "projected"),
        ]
    )
    st.markdown(f'<div class="kpi-grid">{kpis}</div>', unsafe_allow_html=True)

    weather_panel(weather)

    fig = dispatch_chart(df)
    st.markdown('<div class="panel-head solo-head"><span class="panel-title">Weather-Adjusted Dispatch Forecast</span></div>', unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    recommendation_panel(df, cfg, summary)


def weather_panel(weather):
    hours = weather.get("hours", [])
    if not hours:
        rows_panel("Weather API", [("Status", weather.get("status", "offline")), ("Source", weather.get("source", "unknown"))])
        return

    cloud = np.mean([float(item.get("cloud_cover_pct", 0)) for item in hours])
    rain = max(float(item.get("precipitation_probability_pct", 0)) for item in hours)
    temp = np.mean([float(item.get("temperature_c", 0)) for item in hours])
    rows_panel("Weather API", [
        ("Status", weather.get("status", "unknown")),
        ("Source", weather.get("source", "unknown")),
        ("Average Temperature", f"{temp:.1f} C"),
        ("Average Cloud Cover", f"{cloud:.0f}%"),
        ("Peak Rain Probability", f"{rain:.0f}%"),
    ])


def admin_view(role):
    st.markdown('<div class="page-pad"></div>', unsafe_allow_html=True)
    st.markdown('<div class="slabel">Admin Console</div>', unsafe_allow_html=True)
    if role != "Admin":
        st.warning("Admin role required to view registered users and saved run history.")
        return

    col1, col2 = st.columns(2)
    with col1:
        try:
            with st.spinner("Loading registered users..."):
                users = requests.get(f"{API}/users", headers=auth_headers(), timeout=4).json()
            if not isinstance(users, list):
                st.error(users.get("detail", "Could not load users."))
                users = []
            rows = "".join(
                f'<div class="drow"><span class="drow-label">{u["username"]}</span><span class="tag tag-on">{u["role"]}</span></div>'
                for u in users
            )
            st.markdown(f'<div class="panel"><div class="panel-head"><span class="panel-title">Registered Users</span></div>{rows}</div>', unsafe_allow_html=True)
        except Exception:
            st.error("Backend not available.")

    with col2:
        try:
            with st.spinner("Loading saved simulation runs..."):
                runs = requests.get(f"{API}/runs?limit=12", headers=auth_headers(), timeout=4).json()
            if not isinstance(runs, list):
                st.error(runs.get("detail", "Could not load saved runs."))
                runs = []
            rows = "".join(
                f'<div class="drow"><span class="drow-label">{r["entity_type"]}<br><span class="drow-val">{r["username"]} | {r["created_at"][:16]}</span></span><span class="drow-val">Rs {r["cost_rs"]:,.0f}</span></div>'
                for r in runs
            )
            st.markdown(f'<div class="panel"><div class="panel-head"><span class="panel-title">Saved Simulation Runs</span></div>{rows or "<div class=\"drow-val\">No saved runs yet.</div>"}</div>', unsafe_allow_html=True)
        except Exception:
            st.error("Backend not available.")


def account_view(username, role, cfg, entity_type):
    st.markdown('<div class="page-pad"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="panel" style="border-top:3px solid #C87000;">
            <div class="panel-title" style="font-size:20px;">{username or "Chandrakanti Devi"}</div>
            <div class="drow-val" style="text-align:left;margin-top:4px;">{entity_type} {role} | PSIT Kanpur</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        rows_panel("Plant Registration", [
            ("Plant ID", "IND-KNP-0042"),
            ("Registered Name", username or "Chandrakanti Devi"),
            ("Role", role),
            ("Organisation", "PSIT Kanpur"),
            ("Entity Type", entity_type),
            ("Commissioning Date", "12 Jan 2024"),
            ("Grid Connection", cfg["grid_conn"]),
            ("Tariff Zone", "UP - Zone B"),
            ("Applicable Tariff", f"Rs {cfg['tariff']:.2f}/kWh"),
        ])
    with c2:
        rows_panel("Technical Specifications", [
            ("Installed Solar Capacity", f"{cfg['capacity_kw']:.0f} kW"),
            ("Solar Array", cfg["solar_label"]),
            ("Battery System", cfg["battery_label"]),
            ("Battery Capacity", f"{cfg['battery_capacity']:.0f} kWh"),
            ("No. of Transformers", str(cfg["transformers"])),
            ("No. of Feeders", str(cfg["feeders"])),
            ("Grid System", cfg["grid_label"]),
            ("Monitoring Protocol", "IEC 61850 / ModBus TCP"),
        ])

def rows_panel(title, rows):
    rows_html = ""
    for label, value in rows:
        rows_html += f'<div class="drow"><span class="drow-label">{label}</span><span class="drow-val">{value}</span></div>'
    st.markdown(
        f'<div class="panel"><div class="panel-head"><span class="panel-title">{title}</span></div>{rows_html}</div>',
        unsafe_allow_html=True,
    )


def pct(numerator, denominator):
    return f"{0 if denominator == 0 else numerator / denominator * 100:.1f}%"


def bottom_bar(view):
    items = [("Live Simulator", "Live"), ("Energy Flow", "Flow"), ("Account", "Account")]
    html = "".join(f'<div class="bb-item {"bb-active" if name == view else ""}">{label}</div>' for name, label in items)
    st.markdown(f'<div class="bottom-bar">{html}</div>', unsafe_allow_html=True)
