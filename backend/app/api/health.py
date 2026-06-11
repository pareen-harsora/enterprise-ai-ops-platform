from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.database import get_db
from app.core.logger import get_logger
from datetime import datetime

router = APIRouter()
logger = get_logger(__name__)

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Enterprise AI Ops Platform"
    }

@router.get("/health/db")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@router.get("/health/full")
def full_health(db: Session = Depends(get_db)):
    checks = {}
    try:
        db.execute(text("SELECT 1"))
        checks["postgresql"] = "healthy"
    except Exception as e:
        checks["postgresql"] = f"unhealthy: {str(e)}"
    try:
        from neo4j import GraphDatabase
        from app.config import settings
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password)
        )
        driver.verify_connectivity()
        driver.close()
        checks["neo4j"] = "healthy"
    except Exception as e:
        checks["neo4j"] = f"unhealthy: {str(e)}"
    return {
        "status": "healthy" if all(
            v == "healthy" for v in checks.values()
        ) else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }