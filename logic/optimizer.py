from dataclasses import dataclass

@dataclass
class EnergyState:
    solar: float
    demand: float
    battery_level: float
    battery_capacity: float
    grid_available: bool
    grid_price: float
    peak_hour: bool

@dataclass
class EnergyUsage:
    solar_used: float = 0.0
    battery_used: float = 0.0
    grid_used: float = 0.0
    battery_charged: float = 0.0

class EnergyOptimizer:

    def optimize(self, s: EnergyState):
        usage = EnergyUsage()
        remaining_demand = s.demand
        battery = s.battery_level

        # --- 1. Use solar first ---
        usage.solar_used = min(s.solar, remaining_demand)
        remaining_demand -= usage.solar_used

        # --- 2. Store excess solar into battery ---
        if s.solar > s.demand:
            excess = s.solar - s.demand
            usage.battery_charged = min(excess, s.battery_capacity - battery)
            battery += usage.battery_charged

        # --- 3. Decide if we should use battery ---
        use_battery = (
            s.peak_hour or
            not s.grid_available or
            s.grid_price > 8
        )

        if use_battery and remaining_demand > 0:
            usage.battery_used = min(remaining_demand, battery)
            battery -= usage.battery_used
            remaining_demand -= usage.battery_used

        # --- 4. Fallback to grid if possible ---
        if remaining_demand > 0 and s.grid_available:
            usage.grid_used = remaining_demand
            remaining_demand = 0

        return usage, battery
