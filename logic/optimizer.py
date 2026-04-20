from dataclasses import dataclass

# ─── INPUT STATE ─────────────────────────────────────
@dataclass
class EnergyState:
    solar: float
    demand: float
    battery_level: float
    battery_capacity: float
    grid_available: bool
    grid_price: float
    peak_hour: bool


# ─── OUTPUT ──────────────────────────────────────────
@dataclass
class EnergyUsage:
    solar_used: float = 0.0
    battery_used: float = 0.0
    grid_used: float = 0.0
    battery_charged: float = 0.0
    decision: str = ""   # 🔥 NEW (for dashboard insight)


# ─── OPTIMIZER ───────────────────────────────────────
class EnergyOptimizer:

    def optimize(self, s: EnergyState):
        usage = EnergyUsage()

        # ─── Safety ───────────────────────────────────
        battery = max(0, min(s.battery_level, s.battery_capacity))
        remaining_demand = max(s.demand, 0)

        CHARGE_EFF = 0.9
        DISCHARGE_EFF = 0.9

        # ─── 1. Solar First ───────────────────────────
        usage.solar_used = min(s.solar, remaining_demand)
        remaining_demand -= usage.solar_used

        # ─── 2. Store Excess Solar ────────────────────
        if s.solar > s.demand:
            excess = s.solar - s.demand
            available_space = max(s.battery_capacity - battery, 0)

            charge = min(excess * CHARGE_EFF, available_space)
            usage.battery_charged = charge
            battery += charge

        # ─── 3. Battery Decision ──────────────────────
        use_battery = (
            s.peak_hour or
            not s.grid_available or
            s.grid_price > 8
        )

        if use_battery and remaining_demand > 0:
            usable_energy = battery * DISCHARGE_EFF

            used = min(remaining_demand, usable_energy)
            usage.battery_used = used

            battery -= used
            remaining_demand -= used

            usage.decision = "Battery used (peak/grid expensive/off)"

        # ─── 4. Grid Fallback ─────────────────────────
        if remaining_demand > 0:
            if s.grid_available:
                usage.grid_used = remaining_demand
                usage.decision = "Grid used (deficit)"
                remaining_demand = 0
            else:
                usage.decision = "Power deficit (no grid)"

        # ─── 5. Final Clamp ───────────────────────────
        battery = max(0, min(battery, s.battery_capacity))

        # ─── Default decision if nothing triggered ────
        if usage.decision == "":
            if usage.battery_charged > 0:
                usage.decision = "Solar surplus → charging battery"
            else:
                usage.decision = "Solar handled demand"

        return usage, battery