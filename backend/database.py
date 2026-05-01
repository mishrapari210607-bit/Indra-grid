from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database file lives at the repo root so backend and dashboard share one SQLite DB.
ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL = f"sqlite:///{ROOT / 'users.db'}"

# check_same_thread=False allows FastAPI request handlers to reuse SQLite safely enough for this demo.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
