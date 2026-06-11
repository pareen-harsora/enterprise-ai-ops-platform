from sqlalchemy import (
    create_engine, Column, Integer, String,
    Float, DateTime, Boolean, Text, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class SalesRecord(Base):
    __tablename__ = "sales_records"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    location = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    item_name = Column(String(100), nullable=False)
    quantity_sold = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_revenue = Column(Float, nullable=False)
    weather = Column(String(20))
    is_event_day = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class InventoryRecord(Base):
    __tablename__ = "inventory_records"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    item_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    location = Column(String(100), nullable=True)
    opening_stock = Column(Integer, nullable=False)
    units_received = Column(Integer, default=0)
    units_sold = Column(Integer, nullable=False)
    closing_stock = Column(Integer, nullable=False)
    waste_units = Column(Integer, default=0)
    reorder_point = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ForecastRecord(Base):
    __tablename__ = "forecast_records"
    id = Column(Integer, primary_key=True, index=True)
    forecast_date = Column(DateTime, nullable=False, index=True)
    location = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    predicted_demand = Column(Float, nullable=False)
    actual_demand = Column(Float, nullable=True)
    accuracy_pct = Column(Float, nullable=True)
    model_version = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class AILog(Base):
    __tablename__ = "ai_logs"
    id = Column(Integer, primary_key=True, index=True)
    log_type = Column(String(50), nullable=False)
    input_data = Column(JSON)
    prompt_used = Column(Text)
    ai_output = Column(Text)
    tokens_used = Column(Integer)
    cost_usd = Column(Float)
    validation_passed = Column(Boolean, default=True)
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class DataQualityLog(Base):
    __tablename__ = "data_quality_logs"
    id = Column(Integer, primary_key=True, index=True)
    pipeline_run = Column(String(50), nullable=False)
    total_records = Column(Integer)
    passed_records = Column(Integer)
    failed_records = Column(Integer)
    quality_score = Column(Float)
    issues_found = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class EvalRecord(Base):
    __tablename__ = "eval_records"
    id = Column(Integer, primary_key=True, index=True)
    eval_type = Column(String(50), nullable=False)
    ai_log_id = Column(Integer, nullable=True)
    hallucination_detected = Column(Boolean, default=False)
    relevance_score = Column(Float)
    accuracy_score = Column(Float)
    numbers_validated = Column(Boolean, default=True)
    eval_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully")

def drop_and_recreate_tables():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("All tables dropped and recreated successfully")