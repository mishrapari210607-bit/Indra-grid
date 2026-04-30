import os
from pathlib import Path
import subprocess
import sys

from data.simulator import EnergySimulator


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

print("Generating simulation data...")
df = EnergySimulator(hours=48).generate()

DATA_DIR.mkdir(exist_ok=True)
df.to_csv(DATA_DIR / "scenarios.csv", index=False)

print("Data ready -> starting dashboard...")

backend = subprocess.Popen(
    [
        str(ROOT / "venv" / "Scripts" / "uvicorn.exe"),
        "backend.api:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
    ],
    cwd=ROOT,
)

try:
    os.system(f'streamlit run "{ROOT / "dashboard" / "app.py"}"')
finally:
    backend.terminate()
