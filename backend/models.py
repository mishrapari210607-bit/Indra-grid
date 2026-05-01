from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# Base class used by SQLAlchemy to create all database tables.
Base = declarative_base()

class User(Base):
    # Registered dashboard users and their role.
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    password = Column(String)
    role = Column(String, default="Operator")


class SimulationRun(Base):
    # Saved simulation summaries shown later in the admin/history view.
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    entity_type = Column(String)
    range_sel = Column(String)
    solar_kwh = Column(Float)
    demand_kwh = Column(Float)
    grid_kwh = Column(Float)
    battery_kwh = Column(Float)
    co2_kg = Column(Float)
    cost_rs = Column(Float)
    self_sufficiency = Column(Float)
    final_soc = Column(Float)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class FaultEvent(Base):
    # Operational event log used for active/resolved plant issues.
    __tablename__ = "fault_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    location = Column(String)
    status = Column(String, default="active")
    priority = Column(String, default="P3")
    created_at = Column(DateTime, default=datetime.utcnow)
