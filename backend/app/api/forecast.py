from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.database import get_db, ForecastRecord
from app.ml.forecaster import predict_demand, save_forecast_to_db, load_model
from app.core.logger import get_logger
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

router = APIRouter()
logger = get_logger(__name__)

LOCATIONS = [
    "Seneca King Campus",
    "Seneca Newnham Campus",
    "Seneca Markham Campus"
]

CATEGORIES = [
    "Hot Entrees",
    "Beverages",
    "Cold Items",
    "Snacks",
    "Breakfast"
]

class PredictionRequest(BaseModel):
    location: str
    category: str
    date: str
    weather: Optional[str] = "sunny"
    is_event_day: Optional[bool] = False

@router.get("/forecast/model-info")
def get_model_info():
    try:
        _, _, metrics = load_model()
        return {
            "status": "loaded",
            "metrics": metrics
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Model not trained yet. Run train_model.py first."
        )

@router.post("/forecast/predict")
def predict(request: PredictionRequest):
    try:
        result = predict_demand(
            location=request.location,
            category=request.category,
            date=request.date,
            weather=request.weather,
            is_event_day=request.is_event_day
        )
        if result:
            save_forecast_to_db(result)
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/forecast/tomorrow")
def forecast_tomorrow(
    weather: Optional[str] = "sunny",
    is_event_day: Optional[bool] = False
):
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    predictions = []
    for location in LOCATIONS:
        for category in CATEGORIES:
            try:
                result = predict_demand(
                    location=location,
                    category=category,
                    date=tomorrow,
                    weather=weather,
                    is_event_day=is_event_day
                )
                if result:
                    predictions.append(result)
                    save_forecast_to_db(result)
            except Exception as e:
                logger.error(
                    f"Prediction failed for {location} {category}: {e}"
                )
    total_demand = sum(p['predicted_demand'] for p in predictions)
    return {
        "forecast_date": tomorrow,
        "weather": weather,
        "is_event_day": is_event_day,
        "total_predicted_demand": total_demand,
        "predictions": predictions
    }

@router.get("/forecast/history")
def get_forecast_history(
    days: int = 7,
    db: Session = Depends(get_db)
):
    since = datetime.utcnow() - timedelta(days=days)
    records = db.query(ForecastRecord)\
        .filter(ForecastRecord.forecast_date >= since)\
        .order_by(ForecastRecord.forecast_date.desc())\
        .limit(100)\
        .all()
    return {
        "forecasts": [
            {
                "date": r.forecast_date.isoformat(),
                "location": r.location,
                "category": r.category,
                "predicted_demand": r.predicted_demand,
                "actual_demand": r.actual_demand,
                "accuracy_pct": r.accuracy_pct,
                "model_version": r.model_version,
            }
            for r in records
        ],
        "total": len(records)
    }