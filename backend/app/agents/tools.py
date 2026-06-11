from app.models.database import SessionLocal, SalesRecord, InventoryRecord, ForecastRecord
from app.core.logger import get_logger
from sqlalchemy import func
from datetime import datetime, timedelta
import json

logger = get_logger(__name__)

def get_sales_summary(days: int = 7) -> dict:
    db = SessionLocal()
    try:
        since = datetime.utcnow() - timedelta(days=days)
        results = db.query(
            SalesRecord.category,
            func.sum(SalesRecord.total_revenue).label("revenue"),
            func.sum(SalesRecord.quantity_sold).label("units"),
            func.count(SalesRecord.id).label("transactions")
        ).filter(
            SalesRecord.date >= since
        ).group_by(SalesRecord.category).all()
        total_revenue = sum(r.revenue for r in results)
        return {
            "period_days": days,
            "total_revenue": round(total_revenue, 2),
            "by_category": [
                {
                    "category": r.category,
                    "revenue": round(r.revenue, 2),
                    "units": r.units,
                    "transactions": r.transactions
                }
                for r in results
            ]
        }
    finally:
        db.close()

def get_inventory_status() -> dict:
    db = SessionLocal()
    try:
        latest = db.query(
            func.max(InventoryRecord.date)
        ).scalar()
        if not latest:
            return {"alerts": [], "healthy_items": 0}
        alerts = db.query(InventoryRecord).filter(
            InventoryRecord.date >= latest - timedelta(days=1),
            InventoryRecord.closing_stock <= InventoryRecord.reorder_point
        ).all()
        healthy = db.query(InventoryRecord).filter(
            InventoryRecord.date >= latest - timedelta(days=1),
            InventoryRecord.closing_stock > InventoryRecord.reorder_point
        ).count()
        return {
            "alerts": [
                {
                    "item": a.item_name,
                    "category": a.category,
                    "location": a.location,
                    "current_stock": a.closing_stock,
                    "reorder_point": a.reorder_point,
                    "urgency": "critical" if a.closing_stock == 0 else "warning"
                }
                for a in alerts
            ],
            "total_alerts": len(alerts),
            "healthy_items": healthy
        }
    finally:
        db.close()

def detect_anomalies() -> dict:
    db = SessionLocal()
    try:
        recent = datetime.utcnow() - timedelta(days=7)
        older = datetime.utcnow() - timedelta(days=14)
        recent_avg = db.query(
            SalesRecord.category,
            func.avg(SalesRecord.total_revenue).label("avg_revenue")
        ).filter(
            SalesRecord.date >= recent
        ).group_by(SalesRecord.category).all()
        older_avg = db.query(
            SalesRecord.category,
            func.avg(SalesRecord.total_revenue).label("avg_revenue")
        ).filter(
            SalesRecord.date >= older,
            SalesRecord.date < recent
        ).group_by(SalesRecord.category).all()
        older_dict = {r.category: r.avg_revenue for r in older_avg}
        anomalies = []
        for r in recent_avg:
            if r.category in older_dict and older_dict[r.category] > 0:
                change_pct = (
                    (r.avg_revenue - older_dict[r.category]) /
                    older_dict[r.category] * 100
                )
                if abs(change_pct) > 20:
                    anomalies.append({
                        "category": r.category,
                        "recent_avg": round(r.avg_revenue, 2),
                        "previous_avg": round(older_dict[r.category], 2),
                        "change_pct": round(change_pct, 2),
                        "direction": "up" if change_pct > 0 else "down",
                        "severity": "high" if abs(change_pct) > 40 else "medium"
                    })
        return {
            "anomalies": anomalies,
            "total_anomalies": len(anomalies),
            "analysis_period": "last 7 days vs previous 7 days"
        }
    finally:
        db.close()

def get_forecast_accuracy() -> dict:
    db = SessionLocal()
    try:
        forecasts = db.query(ForecastRecord).filter(
            ForecastRecord.actual_demand.isnot(None)
        ).order_by(
            ForecastRecord.forecast_date.desc()
        ).limit(50).all()
        if not forecasts:
            return {
                "message": "No forecasts with actual data yet",
                "total_forecasts": db.query(ForecastRecord).count()
            }
        accuracies = [f.accuracy_pct for f in forecasts if f.accuracy_pct]
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        return {
            "avg_accuracy": round(avg_accuracy, 2),
            "total_evaluated": len(forecasts),
            "sample_forecasts": [
                {
                    "category": f.category,
                    "predicted": f.predicted_demand,
                    "actual": f.actual_demand,
                    "accuracy": f.accuracy_pct
                }
                for f in forecasts[:5]
            ]
        }
    finally:
        db.close()