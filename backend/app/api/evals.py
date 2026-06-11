from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import get_db, EvalRecord, AILog, ForecastRecord
from app.services.evaluator import evaluate_ai_output
from app.core.logger import get_logger
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter()
logger = get_logger(__name__)

@router.get("/evals/summary")
def get_eval_summary(
    days: int = 7,
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    total_evals = db.query(EvalRecord).filter(
        EvalRecord.created_at >= since
    ).count()
    hallucinations = db.query(EvalRecord).filter(
        EvalRecord.created_at >= since,
        EvalRecord.hallucination_detected == True
    ).count()
    avg_accuracy = db.query(
        func.avg(EvalRecord.accuracy_score)
    ).filter(
        EvalRecord.created_at >= since
    ).scalar() or 0
    avg_relevance = db.query(
        func.avg(EvalRecord.relevance_score)
    ).filter(
        EvalRecord.created_at >= since
    ).scalar() or 0
    hallucination_rate = (
        hallucinations / total_evals * 100
        if total_evals > 0 else 0
    )
    return {
        "period_days": days,
        "total_evaluations": total_evals,
        "hallucinations_detected": hallucinations,
        "hallucination_rate_pct": round(hallucination_rate, 2),
        "avg_accuracy_score": round(float(avg_accuracy), 4),
        "avg_relevance_score": round(float(avg_relevance), 4),
        "quality_grade": (
            "A" if avg_accuracy > 0.9 else
            "B" if avg_accuracy > 0.8 else
            "C" if avg_accuracy > 0.7 else "D"
        )
    }

@router.get("/evals/forecast-accuracy")
def get_forecast_eval(
    days: int = 30,
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    total = db.query(ForecastRecord).filter(
        ForecastRecord.forecast_date >= since
    ).count()
    with_actual = db.query(ForecastRecord).filter(
        ForecastRecord.forecast_date >= since,
        ForecastRecord.actual_demand.isnot(None)
    ).count()
    avg_accuracy = db.query(
        func.avg(ForecastRecord.accuracy_pct)
    ).filter(
        ForecastRecord.forecast_date >= since,
        ForecastRecord.accuracy_pct.isnot(None)
    ).scalar()
    return {
        "period_days": days,
        "total_forecasts": total,
        "forecasts_evaluated": with_actual,
        "avg_accuracy_pct": round(float(avg_accuracy), 2) if avg_accuracy else None,
        "model_status": (
            "healthy" if avg_accuracy and avg_accuracy > 80
            else "needs_review" if avg_accuracy
            else "insufficient_data"
        )
    }

@router.get("/evals/ai-cost")
def get_ai_cost_summary(
    days: int = 7,
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    logs = db.query(
        AILog.log_type,
        func.count(AILog.id).label("calls"),
        func.sum(AILog.tokens_used).label("total_tokens"),
        func.sum(AILog.cost_usd).label("total_cost"),
        func.avg(AILog.tokens_used).label("avg_tokens"),
    ).filter(
        AILog.created_at >= since
    ).group_by(AILog.log_type).all()
    total_cost = sum(l.total_cost or 0 for l in logs)
    total_calls = sum(l.calls for l in logs)
    return {
        "period_days": days,
        "total_cost_usd": round(total_cost, 6),
        "total_api_calls": total_calls,
        "cost_per_call_usd": round(
            total_cost / total_calls, 6
        ) if total_calls > 0 else 0,
        "by_type": [
            {
                "log_type": l.log_type,
                "calls": l.calls,
                "total_tokens": l.total_tokens,
                "total_cost_usd": round(l.total_cost or 0, 6),
                "avg_tokens_per_call": round(l.avg_tokens or 0, 0)
            }
            for l in logs
        ]
    }

@router.post("/evals/run/{log_id}")
def run_eval(log_id: int, db: Session = Depends(get_db)):
    log = db.query(AILog).filter(AILog.id == log_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="AI log not found")
    source_data = log.input_data or {}
    result = evaluate_ai_output(log_id, source_data)
    return result