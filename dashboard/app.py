import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys, os
from logic.simulator import EnergySimulator
from logic.optimizer import EnergyOptimizer, EnergyState

# ─── Import Optimizer ───────────────────────────────
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logic.optimizer import EnergyOptimizer, EnergyState

st.set_page_config(page_title="Indra-Grid", page_icon="⚡", layout="wide")

# ─── Sidebar (FULL CONTROL PANEL) ───────────────────
with st.sidebar:
    st.header("⚙️ Scenario Control Panel")

    st.subheader("🔋 Energy Settings")
    demand_multiplier = st.slider("Demand Multiplier", 0.5, 2.0, 1.0, step=0.1)
    battery_capacity  = st.slider("Battery Capacity (kWh)", 10, 100, 40)
    battery_soc       = st.slider("Battery SoC (%)", 0, 100, 70)

    st.divider()

    st.subheader("⚡ Grid Controls")
    grid_available = st.toggle("Grid Available", True)
    island_mode = not grid_available
    grid_price = st.slider("Electricity Price (₹/kWh)", 1, 15, 8)

    st.divider()

    st.subheader("🧠 AI Behavior")
    peak_override = st.toggle("Force Peak Hour Mode", False)
    st.caption("Forces battery usage even if grid is available.")

    st.divider()

    st.subheader("📊 Simulation")
    speed = st.selectbox("Simulation Speed", ["Slow", "Normal", "Fast"])

    st.markdown("### 🔍 System Status")
    st.write(f"Battery: {battery_soc}%")
    st.write(f"Grid: {'ON' if grid_available else 'OFF'}")
    st.write(f"Price: ₹{grid_price}/kWh")

# ─── Load Data ─────────────────────────────────────
use_simulator = st.sidebar.toggle("Use Live Simulator", True)

if use_simulator:
    sim = EnergySimulator(hours=48)
    df = sim.generate()
else:
    df = pd.read_csv("../data/scenarios.csv")
df["demand"] = df["demand"] * demand_multiplier

# ─── Header ────────────────────────────────────────
st.title("⚡ Indra-Grid")
st.caption("AI-driven energy optimizer · Smart Energy Dashboard")

# ─── System Alerts ─────────────────────────────────
if island_mode:
    st.error("🔴 Island Mode Active — Running on Battery + Solar only")
elif grid_price > 10:
    st.warning("⚠️ High electricity price — AI minimizing grid usage")
else:
    st.success("✅ Grid operating normally")

# ─── Run Optimizer ─────────────────────────────────
optimizer = EnergyOptimizer()
battery_level = battery_capacity * battery_soc / 100

results = []

for i, row in df.iterrows():

    peak_hour = peak_override or (i % 24 >= 18 or i % 24 <= 6)

    state = EnergyState(
    solar=row["solar"],
    demand=row["demand"],
    battery_level=battery_level,
    battery_capacity=battery_capacity,
    grid_available=grid_available,
    grid_price=row["grid_price"],  # ✅ dynamic now
    peak_hour=peak_hour
)
    

    usage, battery_level = optimizer.optimize(state)

    results.append({
        "solar": row["solar"],
        "demand": row["demand"],
        "solar_used": usage.solar_used,
        "battery_used": usage.battery_used,
        "grid": usage.grid_used,
        "battery_level": battery_level
    })

df = pd.DataFrame(results)
df["gap"] = df["demand"] - df["solar"]

# ─── KPI Metrics ───────────────────────────────────
solar_pct = round((df["solar_used"].sum() / df["demand"].sum()) * 100)
grid_draw = round(df["grid"].sum(), 1)
money_saved = round(grid_draw * 8.5)
co2_offset = round(df["solar_used"].sum() * 0.82, 1)

c1, c2, c3, c4 = st.columns(4)
c1.metric("🌱 Green Score", f"{solar_pct}%")
c2.metric("💰 Money Saved", f"₹{money_saved:,}")
c3.metric("🌍 CO₂ Offset", f"{co2_offset} kg")
c4.metric("🔋 Battery Left", f"{battery_level:.1f} kWh")

st.divider()

# ─── Charts ────────────────────────────────────────
col1, col2 = st.columns([2,1])

with col1:
    st.subheader("⚡ Energy Flow Over Time")
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index, y=df["solar_used"],
        name="Solar", fill="tozeroy",
        line=dict(color="#3B6D11")
    ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df["demand"],
        name="Demand",
        line=dict(color="#D85A30", dash="dash")
    ))

    fig.add_trace(go.Bar(
        x=df.index, y=df["grid"],
        name="Grid",
        marker_color="rgba(136,135,128,0.4)"
    ))

    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("🔋 Energy Mix")

    total = df["solar_used"].sum() + df["battery_used"].sum() + df["grid"].sum()

    fig2 = go.Figure(go.Pie(
        labels=["Solar", "Battery", "Grid"],
        values=[
            df["solar_used"].sum(),
            df["battery_used"].sum(),
            df["grid"].sum()
        ],
        hole=0.5
    ))

    fig2.update_layout(height=250)
    st.plotly_chart(fig2, use_container_width=True)

# ─── Live Simulation ───────────────────────────────
st.subheader("⚡ Live Simulation")

time_step = st.slider("Select Hour", 0, len(df)-1, 0)
current = df.iloc[time_step]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Solar", f"{current['solar']:.1f}")
c2.metric("Demand", f"{current['demand']:.1f}")
c3.metric("Grid", f"{current['grid']:.1f}")
c4.metric("Battery", f"{current['battery_level']:.1f}")

# ─── AI Decision ───────────────────────────────────
if island_mode:
    st.success("🧠 AI: Grid OFF → Running on Battery + Solar")
elif current["grid"] > 0:
    st.warning("🧠 AI: Grid used due to high demand")
elif current["battery_used"] > 0:
    st.info("🧠 AI: Battery supplying energy")
else:
    st.success("🧠 AI: Solar sufficient")
