from sqlite3 import OperationalError

import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from backend.auth import create_token, hash_password, verify_password, verify_token
from backend.database import SessionLocal, engine
from backend.models import Base, FaultEvent, SimulationRun, User as UserModel
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


class FaultPayload(BaseModel):
    title: str
    location: str
    status: str = "active"
    priority: str = "P3"


def clean_username(username: str) -> str:
    return username.strip().lower()


def clean_role(role: str) -> str:
    role = role.strip()
    return role if role in VALID_ROLES else "Operator"


def bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


def current_user(authorization: str | None = Header(default=None)):
    username = verify_token(bearer_token(authorization))
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    db = SessionLocal()
    try:
        user = db.query(UserModel).filter(UserModel.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return {"username": user.username, "role": user.role or "Operator"}
    finally:
        db.close()


def require_admin(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if user["role"] != "Admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def migrate_sqlite_schema():
    with engine.begin() as conn:
        try:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()]
            if "role" not in cols:
                conn.exec_driver_sql("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'Operator'")
        except OperationalError:
            pass

        try:
            fault_cols = conn.exec_driver_sql("PRAGMA table_info(fault_events)").fetchall()
            if not fault_cols:
                Base.metadata.create_all(bind=engine)
        except OperationalError:
            pass


migrate_sqlite_schema()


def seed_default_faults():
    db = SessionLocal()
    try:
        if db.query(FaultEvent).count() == 0:
            db.add_all(
                [
                    FaultEvent(title="Battery Cell Over-Temp", location="Li-Ion Battery Bank", status="active", priority="P1"),
                    FaultEvent(title="Grid Communication Loss", location="DISCOM HT Grid 33 kV", status="active", priority="P2"),
                    FaultEvent(title="Solar MPPT Deviation >5%", location="Rooftop Solar Array", status="resolved", priority="P3"),
                    FaultEvent(title="Peak Demand Threshold Hit", location="Factory Load Panel", status="resolved", priority="P3"),
                ]
            )
            db.commit()
    finally:
        db.close()


seed_default_faults()


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
    requested_role = clean_role(user.role or "Operator")

    db = SessionLocal()
    try:
        existing = db.query(UserModel).filter(UserModel.username == username).first()
        if existing and verify_password(password, existing.password):
            if not existing.password.startswith("pbkdf2_sha256$"):
                existing.password = hash_password(password)
            if requested_role in {"Owner", "Operator"} and existing.role != requested_role:
                existing.role = requested_role
            if db.is_modified(existing):
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
def users(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    db = SessionLocal()
    try:
        return [
            {"id": user.id, "username": user.username, "role": user.role or "Operator"}
            for user in db.query(UserModel).order_by(UserModel.id.desc()).all()
        ]
    finally:
        db.close()


@app.post("/runs")
def save_run(run: RunPayload, authorization: str | None = Header(default=None)):
    current_user(authorization)
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
def runs(limit: int = 20, authorization: str | None = Header(default=None)):
    require_admin(authorization)
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


@app.get("/faults")
def faults(authorization: str | None = Header(default=None)):
    require_admin(authorization)
    db = SessionLocal()
    try:
        items = db.query(FaultEvent).order_by(FaultEvent.id.desc()).all()
        return [
            {
                "id": item.id,
                "title": item.title,
                "location": item.location,
                "status": item.status,
                "priority": item.priority,
                "created_at": item.created_at.isoformat() if item.created_at else "",
            }
            for item in items
        ]
    finally:
        db.close()


@app.post("/faults")
def create_fault(fault: FaultPayload, authorization: str | None = Header(default=None)):
    require_admin(authorization)
    status = fault.status.strip().lower()
    priority = fault.priority.strip().upper()
    if status not in {"active", "resolved"}:
        status = "active"
    if priority not in {"P1", "P2", "P3"}:
        priority = "P3"

    db = SessionLocal()
    try:
        item = FaultEvent(
            title=fault.title.strip(),
            location=fault.location.strip(),
            status=status,
            priority=priority,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return {"status": "success", "id": item.id}
    finally:
        db.close()


@app.get("/weather/forecast")
def weather_forecast(latitude: float = 26.4499, longitude: float = 80.3319):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "temperature_2m,cloud_cover,precipitation_probability",
        "forecast_days": 1,
        "timezone": "Asia/Kolkata",
    }
    try:
        response = requests.get(url, params=params, timeout=6)
        response.raise_for_status()
        data = response.json()
        hourly = data.get("hourly", {})
        times = hourly.get("time", [])[:24]
        temps = hourly.get("temperature_2m", [])[:24]
        clouds = hourly.get("cloud_cover", [])[:24]
        rain = hourly.get("precipitation_probability", [])[:24]
        rows = [
            {
                "time": times[i],
                "temperature_c": temps[i],
                "cloud_cover_pct": clouds[i],
                "precipitation_probability_pct": rain[i],
            }
            for i in range(min(len(times), len(temps), len(clouds), len(rain)))
        ]
        return {
            "status": "success",
            "source": "open-meteo",
            "latitude": latitude,
            "longitude": longitude,
            "hours": rows,
        }
    except Exception:
        rows = [
            {
                "time": f"{hour:02d}:00",
                "temperature_c": 31 if 10 <= hour <= 17 else 24,
                "cloud_cover_pct": 35 if 9 <= hour <= 16 else 55,
                "precipitation_probability_pct": 10,
            }
            for hour in range(24)
        ]
        return {
            "status": "fallback",
            "source": "synthetic-kanpur",
            "latitude": latitude,
            "longitude": longitude,
            "hours": rows,
        }


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
