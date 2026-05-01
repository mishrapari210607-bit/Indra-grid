from dataclasses import dataclass


@dataclass
class EnergyState:
    # One optimizer input row for a single hour/time step.
    solar: float
    demand: float
    battery_level: float
    battery_capacity: float
    grid_available: bool
    grid_price: float
    peak_hour: bool


@dataclass
class EnergyUsage:
    # Output split showing which energy source served the load.
    solar_used: float = 0.0
    battery_used: float = 0.0
    grid_used: float = 0.0
    battery_charged: float = 0.0
    unmet_demand: float = 0.0
    decision: str = ""


class EnergyOptimizer:
    # Fixed demo assumptions for charging loss, discharge loss, reserve, and high tariff.
    charge_efficiency = 0.90
    discharge_efficiency = 0.90
    reserve_fraction = 0.20
    high_price_threshold = 8.0

    def optimize(self, s: EnergyState):
        # Clamp battery and input values so dispatch math stays within physical bounds.
        usage = EnergyUsage()
        battery = max(0.0, min(s.battery_level, s.battery_capacity))
        remaining_demand = max(s.demand, 0.0)
        solar_available = max(s.solar, 0.0)

        # Solar is used first because it is free and renewable.
        usage.solar_used = min(solar_available, remaining_demand)
        remaining_demand -= usage.solar_used

        # Extra solar charges the battery after load is served.
        excess_solar = max(solar_available - usage.solar_used, 0.0)
        if excess_solar > 0:
            available_space = max(s.battery_capacity - battery, 0.0)
            usage.battery_charged = min(excess_solar * self.charge_efficiency, available_space)
            battery += usage.battery_charged

        # Battery is preferred during peak, outage, or expensive-grid conditions.
        use_battery = (
            s.peak_hour
            or not s.grid_available
            or s.grid_price > self.high_price_threshold
        )

        if use_battery and remaining_demand > 0:
            # Keep a 20% battery reserve for reliability and emergency backup.
            reserve = self.reserve_fraction * s.battery_capacity
            usable_battery = max(0.0, battery - reserve)
            deliverable_energy = usable_battery * self.discharge_efficiency

            usage.battery_used = min(remaining_demand, deliverable_energy)
            battery_draw = usage.battery_used / self.discharge_efficiency if usage.battery_used else 0.0
            battery -= battery_draw
            remaining_demand -= usage.battery_used

        if remaining_demand > 0 and s.grid_available:
            # Grid supplies whatever load remains when it is available.
            usage.grid_used = remaining_demand
            remaining_demand = 0.0

        # Any remaining load is unmet, usually because grid is unavailable and reserve is protected.
        usage.unmet_demand = max(remaining_demand, 0.0)
        battery = max(0.0, min(battery, s.battery_capacity))
        usage.decision = self._decision_for(usage, use_battery, s.grid_available)

        return usage, battery

    def _decision_for(self, usage: EnergyUsage, use_battery: bool, grid_available: bool) -> str:
        # Human-readable explanation shown by the dashboard/API.
        if usage.unmet_demand > 0:
            return "Power deficit - no grid available"
        if usage.battery_used > 0 and usage.grid_used > 0:
            return "Battery + grid used for peak deficit"
        if usage.battery_used > 0:
            return "Battery used with 20% safety reserve"
        if usage.grid_used > 0:
            return "Grid used for remaining demand"
        if usage.battery_charged > 0:
            return "Solar surplus charging battery"
        if use_battery and not grid_available:
            return "Solar handled demand while islanded"
        return "Solar handled demand"
