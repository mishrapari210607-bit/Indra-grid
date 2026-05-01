from pathlib import Path

import numpy as np
import pandas as pd


class EnergySimulator:
    # Generates repeatable demo profiles for solar, demand, and grid price.
    def __init__(self, hours=24, seed=42):
        self.hours = hours
        self.seed = seed

    def generate(self):
        # Seeded random generator keeps the same scenario repeatable for demos/tests.
        rng = np.random.default_rng(self.seed)
        data = []

        for t in range(self.hours):
            hour = t % 24
            # Solar follows a simple daytime curve: zero at night, highest near noon.
            solar = max(0.0, 50 * np.sin((hour - 6) * np.pi / 12))

            # Morning/evening hours carry higher demand than the rest of the day.
            if 6 <= hour <= 9:
                demand = rng.uniform(40, 60)
            elif 18 <= hour <= 22:
                demand = rng.uniform(50, 70)
            else:
                demand = rng.uniform(20, 40)

            # Evening peak hours are priced higher to test peak-shaving behavior.
            if 18 <= hour <= 22:
                grid_price = rng.uniform(10, 15)
            else:
                grid_price = rng.uniform(5, 9)

            data.append(
                {
                    "step": t,
                    "hour": hour,
                    "time": f"{hour:02d}:00",
                    "solar": round(solar, 2),
                    "demand": round(demand, 2),
                    "grid_price": round(grid_price, 2),
                }
            )

        return pd.DataFrame(data)


if __name__ == "__main__":
    # Manual utility: generate a CSV scenario file from the simulator.
    output_path = Path(__file__).resolve().parent / "scenarios.csv"
    df = EnergySimulator(hours=48).generate()
    df.to_csv(output_path, index=False)
    print(f"scenarios.csv generated at {output_path}")
