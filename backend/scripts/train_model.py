import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.ml.forecaster import load_training_data, aggregate_daily, train_model
from app.core.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("Enterprise AI Ops Platform")
    logger.info("ML Model Training Pipeline")
    logger.info("=" * 50)

    df = load_training_data()
    daily_df = aggregate_daily(df)
    model, scaler, metrics = train_model(daily_df)

    logger.info("=" * 50)
    logger.info("Training Complete")
    logger.info(f"Accuracy:    {metrics['accuracy_pct']}%")
    logger.info(f"R2 Score:    {metrics['r2']}")
    logger.info(f"MAE:         {metrics['mae']}")
    logger.info(f"RMSE:        {metrics['rmse']}")
    logger.info(f"Train size:  {metrics['train_samples']} samples")
    logger.info(f"Test size:   {metrics['test_samples']} samples")
    logger.info(f"Features:    {metrics['features']}")
    logger.info("=" * 50)