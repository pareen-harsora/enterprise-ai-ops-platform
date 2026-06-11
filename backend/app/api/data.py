from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import get_db, SalesRecord, InventoryRecord, DataQualityLog
from app.core.logger import get_logger
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter()
logger = get_logger(__name__)

@router.get("/sales/summary")
def get_sales_summary(
    days: int = 30,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    query = db.query(
        func.sum(SalesRecord.total_revenue).label("total_revenue"),
        func.sum(SalesRecord.quantity_sold).label("total_units"),
        func.count(SalesRecord.id).label("total_transactions"),
        func.avg(SalesRecord.total_revenue).label("avg_transaction")
    ).filter(SalesRecord.date >= since)
    if location:
        query = query.filter(SalesRecord.location == location)
    result = query.first()
    return {
        "period_days": days,
        "total_revenue": round(result.total_revenue or 0, 2),
        "total_units_sold": result.total_units or 0,
        "total_transactions": result.total_transactions or 0,
        "avg_transaction_value": round(result.avg_transaction or 0, 2)
    }

@router.get("/sales/by-category")
def get_sales_by_category(
    days: int = 30,
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    results = db.query(
        SalesRecord.category,
        func.sum(SalesRecord.total_revenue).label("revenue"),
        func.sum(SalesRecord.quantity_sold).label("units")
    ).filter(SalesRecord.date >= since)\
     .group_by(SalesRecord.category)\
     .order_by(func.sum(SalesRecord.total_revenue).desc())\
     .all()
    return [
        {
            "category": r.category,
            "revenue": round(r.revenue, 2),
            "units_sold": r.units
        }
        for r in results
    ]

@router.get("/inventory/alerts")
def get_inventory_alerts(db: Session = Depends(get_db)):
    latest_date = db.query(func.max(InventoryRecord.date)).scalar()
    if not latest_date:
        return {"alerts": []}
    alerts = db.query(InventoryRecord).filter(
        InventoryRecord.date >= latest_date - timedelta(days=1),
        InventoryRecord.closing_stock <= InventoryRecord.reorder_point
    ).all()
    return {
        "alerts": [
            {
                "item": a.item_name,
                "category": a.category,
                "current_stock": a.closing_stock,
                "reorder_point": a.reorder_point,
                "urgency": "critical" if a.closing_stock == 0 else "warning"
            }
            for a in alerts
        ],
        "total_alerts": len(alerts)
    }

@router.get("/quality/latest")
def get_latest_quality_report(db: Session = Depends(get_db)):
    latest = db.query(DataQualityLog)\
               .order_by(DataQualityLog.created_at.desc())\
               .first()
    if not latest:
        raise HTTPException(status_code=404, detail="No quality reports found")
    return {
        "pipeline_run": latest.pipeline_run,
        "total_records": latest.total_records,
        "passed_records": latest.passed_records,
        "failed_records": latest.failed_records,
        "quality_score": latest.quality_score,
        "issues_found": latest.issues_found,
        "run_at": latest.created_at.isoformat()
    }

from app.models.database import AILog
from datetime import datetime

@router.get("/approvals/pending")
def get_pending_approvals(db: Session = Depends(get_db)):
    pending = db.query(AILog).filter(
        AILog.approved_by.is_(None),
        AILog.log_type.in_(["daily_brief", "agent_report"])
    ).order_by(AILog.created_at.desc()).limit(20).all()
    return {
        "pending": [
            {
                "id": l.id,
                "log_type": l.log_type,
                "ai_output_preview": l.ai_output[:200] if l.ai_output else "",
                "validation_passed": l.validation_passed,
                "cost_usd": l.cost_usd,
                "created_at": l.created_at.isoformat()
            }
            for l in pending
        ],
        "total_pending": len(pending)
    }

@router.post("/approvals/{log_id}/approve")
def approve_recommendation(
    log_id: int,
    manager_name: str,
    db: Session = Depends(get_db)
):
    log = db.query(AILog).filter(AILog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    log.approved_by = manager_name
    log.approved_at = datetime.utcnow()
    db.commit()
    logger.info(
        f"AI recommendation {log_id} approved by {manager_name}"
    )
    return {
        "log_id": log_id,
        "approved_by": manager_name,
        "approved_at": log.approved_at.isoformat(),
        "status": "approved"
    }

@router.post("/approvals/{log_id}/reject")
def reject_recommendation(
    log_id: int,
    manager_name: str,
    reason: str,
    db: Session = Depends(get_db)
):
    log = db.query(AILog).filter(AILog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    log.approved_by = f"REJECTED by {manager_name}: {reason}"
    log.approved_at = datetime.utcnow()
    db.commit()
    logger.info(
        f"AI recommendation {log_id} rejected by {manager_name}"
    )
    return {
        "log_id": log_id,
        "rejected_by": manager_name,
        "reason": reason,
        "status": "rejected"
    }