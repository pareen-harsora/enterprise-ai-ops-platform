import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from app.ml.features import build_features, FEATURE_COLUMNS, TARGET_COLUMN
from app.models.database import SessionLocal, SalesRecord, ForecastRecord
from app.core.logger import get_logger
import warnings
warnings.filterwarnings('ignore')

logger = get_logger(__name__)

MODEL_DIR = "models/saved"
MODEL_PATH = f"{MODEL_DIR}/forecaster.joblib"
SCALER_PATH = f"{MODEL_DIR}/scaler.joblib"
METRICS_PATH = f"{MODEL_DIR}/metrics.joblib"
MODEL_VERSION = "1.0.0"

def load_training_data():
    logger.info("Loading training data from PostgreSQL")
    db = SessionLocal()
    try:
        records = db.query(SalesRecord).all()
        data = []
        for r in records:
            data.append({
                'date': r.date,
                'location': r.location,
                'category': r.category,
                'item_name': r.item_name,
                'quantity_sold': r.quantity_sold,
                'unit_price': r.unit_price,
                'total_revenue': r.total_revenue,
                'weather': r.weather,
                'is_event_day': r.is_event_day,
            })
        df = pd.DataFrame(data)
        logger.info(f"Loaded {len(df)} records from database")
        return df
    finally:
        db.close()

def aggregate_daily(df):
    logger.info("Aggregating data to daily level")
    daily = df.groupby(
        ['date', 'location', 'category', 'weather', 'is_event_day']
    ).agg(
        quantity_sold=('quantity_sold', 'sum'),
        total_revenue=('total_revenue', 'sum'),
        avg_unit_price=('unit_price', 'mean')
    ).reset_index()
    logger.info(f"Daily aggregated records: {len(daily)}")
    return daily

def train_model(df):
    logger.info("Starting model training")
    features_df = build_features(df)
    X = features_df[FEATURE_COLUMNS]
    y = features_df[TARGET_COLUMN]
    logger.info(f"Training with {len(X)} samples and {len(X.columns)} features")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    logger.info("Training Random Forest model")
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=15,
        min_samples_split=5,
        min_samples_leaf=2,
        max_features='sqrt',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    accuracy = max(0, 1 - (mae / y_test.mean())) * 100
    metrics = {
        'mae': round(mae, 4),
        'rmse': round(rmse, 4),
        'r2': round(r2, 4),
        'accuracy_pct': round(accuracy, 2),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': len(FEATURE_COLUMNS),
        'model_version': MODEL_VERSION,
        'trained_at': datetime.utcnow().isoformat()
    }
    logger.info(f"Model Performance:")
    logger.info(f"  MAE:      {mae:.4f}")
    logger.info(f"  RMSE:     {rmse:.4f}")
    logger.info(f"  R2 Score: {r2:.4f}")
    logger.info(f"  Accuracy: {accuracy:.2f}%")
    feature_importance = pd.DataFrame({
        'feature': FEATURE_COLUMNS,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    logger.info("Top 10 most important features:")
    for _, row in feature_importance.head(10).iterrows():
        logger.info(f"  {row['feature']}: {row['importance']:.4f}")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(metrics, METRICS_PATH)
    logger.info(f"Model saved to {MODEL_PATH}")
    return model, scaler, metrics

def load_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Model not found. Run train_model first."
        )
    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)
    metrics = joblib.load(METRICS_PATH)
    return model, scaler, metrics

def predict_demand(
    location, category, date, weather='sunny', is_event_day=False
):
    model, scaler, metrics = load_model()
    input_data = pd.DataFrame([{
        'date': pd.to_datetime(date),
        'location': location,
        'category': category,
        'weather': weather,
        'is_event_day': is_event_day,
        'quantity_sold': 0,
    }])
    db = SessionLocal()
    try:
        history = db.query(SalesRecord).filter(
            SalesRecord.location == location,
            SalesRecord.category == category,
            SalesRecord.date < date
        ).order_by(SalesRecord.date.desc()).limit(100).all()
        if len(history) < 30:
            logger.warning("Insufficient history for reliable prediction")
        hist_data = [{
            'date': r.date,
            'location': r.location,
            'category': r.category,
            'weather': r.weather,
            'is_event_day': r.is_event_day,
            'quantity_sold': r.quantity_sold,
        } for r in history]
        hist_df = pd.DataFrame(hist_data)
        combined = pd.concat(
            [hist_df, input_data], ignore_index=True
        ).sort_values('date')
        features_df = build_features(combined)
        if len(features_df) == 0:
            return None
        last_row = features_df.iloc[[-1]][FEATURE_COLUMNS]
        last_scaled = scaler.transform(last_row)
        prediction = model.predict(last_scaled)[0]
        prediction = max(0, round(prediction))
        return {
            'location': location,
            'category': category,
            'date': str(date),
            'predicted_demand': prediction,
            'weather': weather,
            'is_event_day': is_event_day,
            'model_version': MODEL_VERSION,
            'model_accuracy': metrics['accuracy_pct']
        }
    finally:
        db.close()

def save_forecast_to_db(prediction):
    db = SessionLocal()
    try:
        record = ForecastRecord(
            forecast_date=pd.to_datetime(prediction['date']),
            location=prediction['location'],
            category=prediction['category'],
            predicted_demand=prediction['predicted_demand'],
            model_version=prediction['model_version'],
        )
        db.add(record)
        db.commit()
        logger.info(
            f"Forecast saved: {prediction['category']} "
            f"at {prediction['location']} = "
            f"{prediction['predicted_demand']} units"
        )
    finally:
        db.close()