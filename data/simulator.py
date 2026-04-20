# data/simulator.py

import csv
import random

def generate_data(filename="data/scenarios.csv"):

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)

        # HEADER (DO NOT CHANGE)
        writer.writerow(["time", "solar", "demand", "grid_price", "grid_available"])

        for i in range(24):

            # ☀️ Solar pattern (peak at noon)
            solar = max(0, int(100 * (1 - abs(i - 12) / 12)) + random.randint(-5, 5))

            # 🏭 Demand pattern
            if 8 <= i <= 18:
                demand = random.randint(80, 140)   # working hours
            else:
                demand = random.randint(30, 60)    # low usage

            # 💰 Grid pricing (peak hours expensive)
            if 18 <= i <= 21:
                grid_price = random.randint(20, 30)   # peak
            else:
                grid_price = random.randint(5, 12)    # normal

            # 🔌 Power cut simulation (7–9 PM)
            grid_available = 0 if i in [19, 20] else 1

            writer.writerow([i, solar, demand, grid_price, grid_available])

    print("✅ scenarios.csv created successfully!")


# Run file directly
if __name__ == "__main__":
    generate_data()