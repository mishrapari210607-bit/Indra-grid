import os
from logic.simulator import EnergySimulator

print("⚡ Generating simulation data...")

sim = EnergySimulator(hours=48)
df = sim.generate()

os.makedirs("data", exist_ok=True)
df.to_csv("data/scenarios.csv", index=False)

print("✅ Data ready → Starting dashboard...")

os.system("streamlit run dashboard/app.py")