import pandas as pd
import numpy as np

class EnergySimulator:

    def __init__(self, hours=24):
        self.hours = hours

    def generate(self):
        data = []

        for t in range(self.hours):

            # ─── Solar Pattern (bell curve) ───────────
            solar = max(0, 50 * np.sin((t - 6) * np.pi / 12))

            # ─── Demand Pattern ──────────────────────
            if 6 <= t <= 9:          # morning peak
                demand = np.random.uniform(40, 60)
            elif 18 <= t <= 22:     # evening peak
                demand = np.random.uniform(50, 70)
            else:
                demand = np.random.uniform(20, 40)

            # ─── Grid Price ──────────────────────────
            if 18 <= t <= 22:
                grid_price = np.random.uniform(10, 15)
            else:
                grid_price = np.random.uniform(5, 9)

            data.append({
                "hour": t,
                "solar": round(solar, 2),
                "demand": round(demand, 2),
                "grid_price": round(grid_price, 2)
            })

        df = pd.DataFrame(data)
        return df


# ─── Save to CSV ─────────────────────────────────────
if __name__ == "__main__":
    sim = EnergySimulator(hours=48)
    df = sim.generate()
    df.to_csv("../data/scenarios.csv", index=False)
    print("✅ scenarios.csv generated!")