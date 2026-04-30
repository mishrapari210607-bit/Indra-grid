from sqlite3 import OperationalError

from fastapi import FastAPI
from pydantic import BaseModel

from backend.auth import create_token, hash_password, verify_password
from backend.database import SessionLocal, engine
from backend.models import Base, SimulationRun, User as UserModel
from logic.optimizer import EnergyOptimizer, EnergyState


app = FastAPI()
Base.metadata.create_all(bind=engine)

VALID_ROLES = {"Owner", "Operator", "Admin"}


class UserPayload(BaseModel):
    username: str
    password: str
    role: str = "Operator"


class RunPayload(BaseModel):
    username: str
    entity_type: str
    range_sel: str
    solar_kwh: float
    demand_kwh: float
    grid_kwh: float
    battery_kwh: float
    co2_kg: float
    cost_rs: float
    self_sufficiency: float
    final_soc: float
    notes: str = ""


class OptimizerPayload(BaseModel):
    solar: float
    demand: float
    battery_level: float
    battery_capacity: float
    grid_available: bool
    grid_price: float
    peak_hour: bool


def clean_username(username: str) -> str:
    return username.strip().lower()


def clean_role(role: str) -> str:
    role = role.strip()
    return role if role in VALID_ROLES else "Operator"


def migrate_sqlite_schema():
    with engine.begin() as conn:
        try:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()]
            if "role" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'Operator'")
        except OperationalError:
            pass


migrate_sqlite_schema()


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Indra-Grid API",
        "optimizer": "online",
    }


@app.post("/register")
def register(user: UserPayload):
    username = clean_username(user.username)
    password = user.password.strip()
    role = clean_role(user.role or "Operator")

    if not username or not password:
        return {"status": "error", "message": "Username and password are required"}

    db = SessionLocal()
    try:
        existing = db.query(UserModel).filter(UserModel.username == username).first()
        if existing:
            return {"status": "error", "message": "User exists"}

        db.add(UserModel(username=username, password=hash_password(password), role=role))
        db.commit()
        return {"status": "success", "message": "User created"}
    finally:
        db.close()


@app.post("/login")
def login(user: UserPayload):
    username = clean_username(user.username)
    password = user.password.strip()

    db = SessionLocal()
    try:
        existing = db.query(UserModel).filter(UserModel.username == username).first()
        if existing and verify_password(password, existing.password):
            if not existing.password.startswith("pbkdf2_sha256$"):
                existing.password = hash_password(password)
                db.commit()
            return {
                "status": "success",
                "token": create_token(username),
                "role": existing.role or "Operator",
            }

        return {"status": "error", "message": "Invalid credentials"}
    finally:
        db.close()


@app.get("/users")
def users():
    db = SessionLocal()
    try:
        return [
            {"id": user.id, "username": user.username, "role": user.role or "Operator"}
            for user in db.query(UserModel).order_by(UserModel.id.desc()).all()
        ]
    finally:
        db.close()


@app.post("/runs")
def save_run(run: RunPayload):
    db = SessionLocal()
    try:
        data = run.model_dump() if hasattr(run, "model_dump") else run.dict()
        item = SimulationRun(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"status": "success", "id": item.id}
    finally:
        db.close()


@app.get("/runs")
def runs(limit: int = 20):
    db = SessionLocal()
    try:
        items = db.query(SimulationRun).order_by(SimulationRun.id.desc()).limit(limit).all()
        return [
            {
                "id": item.id,
                "username": item.username,
                "entity_type": item.entity_type,
                "range_sel": item.range_sel,
                "solar_kwh": item.solar_kwh,
                "demand_kwh": item.demand_kwh,
                "grid_kwh": item.grid_kwh,
                "battery_kwh": item.battery_kwh,
                "co2_kg": item.co2_kg,
                "cost_rs": item.cost_rs,
                "self_sufficiency": item.self_sufficiency,
                "final_soc": item.final_soc,
                "notes": item.notes,
                "created_at": item.created_at.isoformat() if item.created_at else "",
            }
            for item in items
        ]
    finally:
        db.close()


@app.post("/optimize")
def optimize(payload: OptimizerPayload):
    usage, battery = EnergyOptimizer().optimize(EnergyState(**payload.dict()))
    return {
        "solar_used": usage.solar_used,
        "battery_used": usage.battery_used,
        "grid_used": usage.grid_used,
        "battery_charged": usage.battery_charged,
        "unmet_demand": usage.unmet_demand,
        "battery_level": battery,
        "decision": usage.decision,
    }
