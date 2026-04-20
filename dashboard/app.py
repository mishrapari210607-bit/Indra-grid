import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Indra-Grid",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
.metric-card {
    background: #f8f9fa;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    border-left: 4px solid;
}
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Scenario Settings")
    demand_multiplier = st.slider("Demand multiplier", 0.5, 2.0, 1.0, step=0.1)
    battery_capacity  = st.slider("Battery capacity (kWh)", 10, 100, 40)
    battery_soc       = st.slider("Current battery SoC (%)", 0, 100, 72)
    st.divider()
    island_mode = st.toggle("Simulate grid failure (Island Mode)", value=False)
    st.caption("Activates battery-only operation with solar priority.")

# ─── Load data ─────────────────────────────────────────────────────────────
df = pd.read_csv("data/scenarios.csv")
df["demand"] = df["demand"] * demand_multiplier
df["gap"]    = df["demand"] - df["solar"]

if island_mode:
    df["grid"] = 0
    df["battery_draw"] = df["gap"].clip(lower=0)
else:
    df["grid"]         = df["gap"].clip(lower=0) * 0.4
    df["battery_draw"] = df["gap"].clip(lower=0) * 0.6

avg_gap     = df["gap"].mean()
solar_pct   = round((df["solar"].sum() / df["demand"].sum()) * 100)
grid_draw   = round(df["grid"].sum(), 1)
money_saved = round(grid_draw * 8.5)        # ₹8.5/kWh peak rate
co2_offset  = round(df["solar"].sum() * 0.82, 1)  # 0.82 kg CO₂ per kWh

# ─── Header ────────────────────────────────────────────────────────────────
st.title("⚡ Indra-Grid")
st.caption("AI-driven energy optimizer · Real-time factory dashboard")

if island_mode:
    st.error("🔴 **Island Mode Active** — Grid disconnected. Running on Solar + Battery only.")

# ─── AI Insight banner ─────────────────────────────────────────────────────
st.subheader("AI System Analysis")
if avg_gap > 10:
    st.error(
        f"**High deficit detected** — Average gap: {avg_gap:.1f} kW. "
        f"Grid draw at {grid_draw} kWh. Recommend activating backup generators "
        f"and pre-charging battery to ≥80% SoC before next peak window."
    )
elif avg_gap > 0:
    st.warning(
        f"**Minor deficit** — Average gap: {avg_gap:.1f} kW. "
        f"Battery reserves sufficient for {round(battery_capacity * battery_soc / 100 / max(avg_gap, 0.1), 1)} hrs. "
        f"Optimize storage discharge schedule."
    )
else:
    st.success(
        f"**Grid stable** — Solar surplus of {abs(avg_gap):.1f} kW average. "
        f"Charging battery at current rate. No grid draw required."
    )

# ─── KPI Cards ─────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Green Score",      f"{solar_pct}%",      delta="+6% vs yesterday")
c2.metric("Money Saved",      f"₹{money_saved:,}",  delta="Peak shaving")
c3.metric("CO₂ Offset",       f"{co2_offset} kg",   delta=f"{round(co2_offset/3.67,2)} credits")
c4.metric("Battery SoC",      f"{battery_soc}%",    delta="Charging" if avg_gap < 0 else "Discharging")

st.divider()

# ─── Energy Mix Chart ──────────────────────────────────────────────────────
col_chart, col_mix = st.columns([2, 1])

with col_chart:
    st.subheader("Energy flow over time")
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index, y=df["solar"],
        name="Solar", fill="tozeroy",
        line=dict(color="#3B6D11", width=2),
        fillcolor="rgba(99,153,34,0.15)"
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["demand"],
        name="Demand",
        line=dict(color="#D85A30", width=2, dash="dash")
    ))
    if not island_mode:
        fig.add_trace(go.Bar(
            x=df.index, y=df["grid"],
            name="Grid draw", marker_color="rgba(136,135,128,0.4)"
        ))

    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis_title="kW",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

with col_mix:
    st.subheader("Source mix")
    total = df["solar"].sum() + df["battery_draw"].sum() + df["grid"].sum()
    labels = ["Solar", "Battery", "Grid"]
    values = [
        round(df["solar"].sum() / total * 100),
        round(df["battery_draw"].sum() / total * 100),
        round(df["grid"].sum() / total * 100)
    ]
    fig2 = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker_colors=["#639922", "#1D9E75", "#888780"],
        textinfo="label+percent",
        textfont_size=12
    ))
    fig2.update_layout(
        height=250,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True)

# ─── Data table (collapsible) ──────────────────────────────────────────────
with st.expander("View raw scenario data"):
    st.dataframe(
        df.style.format(precision=2)
               .background_gradient(subset=["gap"], cmap="RdYlGn_r"),
        use_container_width=True
    )
# ─── SideBar ──────────────────────────────────────────────
time_step = st.slider("⏱️ Select Hour (Simulation)", 0, len(df)-1, 0)
current = df.iloc[time_step]
st.subheader(f"⚡ Live Simulation — Hour {time_step}")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Solar", f"{current['solar']:.1f} kW")
col2.metric("Demand", f"{current['demand']:.1f} kW")
col3.metric("Grid Used", f"{current['grid']:.1f} kW")
col4.metric("Battery Used", f"{current['battery_draw']:.1f} kW")

if island_mode:
    st.success("🧠 Decision: Grid OFF → Running on Battery + Solar (Island Mode)")
elif current["grid"] > 0:
    st.warning("🧠 Decision: Grid used due to energy deficit")
elif current["solar"] > current["demand"]:
    st.success("🧠 Decision: Solar surplus → Charging battery")
else:
    st.info("🧠 Decision: Balanced usage")