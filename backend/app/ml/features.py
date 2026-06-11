import pandas as pd
import numpy as np
from datetime import datetime
from app.core.logger import get_logger

logger = get_logger(__name__)

def add_time_features(df, date_col='date'):
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df['day_of_week'] = df[date_col].dt.dayofweek
    df['day_of_month'] = df[date_col].dt.day
    df['month'] = df[date_col].dt.month
    df['quarter'] = df[date_col].dt.quarter
    df['week_of_year'] = df[date_col].dt.isocalendar().week.astype(int)
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    df['is_month_start'] = df[date_col].dt.is_month_start.astype(int)
    df['is_month_end'] = df[date_col].dt.is_month_end.astype(int)
    df['season'] = df['month'].map({
        12: 0, 1: 0, 2: 0,
        3: 1, 4: 1, 5: 1,
        6: 2, 7: 2, 8: 2,
        9: 3, 10: 3, 11: 3
    })
    return df

def add_weather_features(df, weather_col='weather'):
    weather_map = {
        'sunny': 0,
        'cloudy': 1,
        'rainy': 2,
        'snowy': 3,
        'windy': 4
    }
    df['weather_encoded'] = df[weather_col].map(weather_map).fillna(1)
    df['is_bad_weather'] = df[weather_col].isin(['rainy', 'snowy']).astype(int)
    df['is_good_weather'] = df[weather_col].isin(['sunny']).astype(int)
    return df

def add_location_features(df, location_col='location'):
    location_map = {
        'Seneca King Campus': 0,
        'Seneca Newnham Campus': 1,
        'Seneca Markham Campus': 2
    }
    df['location_encoded'] = df[location_col].map(location_map).fillna(0)
    return df

def add_category_features(df, category_col='category'):
    category_map = {
        'Hot Entrees': 0,
        'Beverages': 1,
        'Cold Items': 2,
        'Snacks': 3,
        'Breakfast': 4
    }
    df['category_encoded'] = df[category_col].map(category_map).fillna(0)
    return df

def add_lag_features(df, target_col='quantity_sold', lags=[1, 7, 14, 30]):
    df = df.sort_values('date')
    for lag in lags:
        df[f'lag_{lag}'] = df.groupby(
            ['location', 'category']
        )[target_col].shift(lag)
    return df

def add_rolling_features(df, target_col='quantity_sold', windows=[7, 14, 30]):
    df = df.sort_values('date')
    for window in windows:
        df[f'rolling_mean_{window}'] = df.groupby(
            ['location', 'category']
        )[target_col].transform(
            lambda x: x.shift(1).rolling(window=window, min_periods=1).mean()
        )
        df[f'rolling_std_{window}'] = df.groupby(
            ['location', 'category']
        )[target_col].transform(
            lambda x: x.shift(1).rolling(window=window, min_periods=1).std()
        )
    return df

def build_features(df):
    logger.info("Building feature set")
    df = add_time_features(df)
    df = add_weather_features(df)
    df = add_location_features(df)
    df = add_category_features(df)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = df.dropna()
    logger.info(f"Feature set built: {len(df)} rows, {len(df.columns)} columns")
    return df

FEATURE_COLUMNS = [
    'day_of_week', 'day_of_month', 'month', 'quarter',
    'week_of_year', 'is_weekend', 'is_month_start', 'is_month_end',
    'season', 'weather_encoded', 'is_bad_weather', 'is_good_weather',
    'location_encoded', 'category_encoded', 'is_event_day',
    'lag_1', 'lag_7', 'lag_14', 'lag_30',
    'rolling_mean_7', 'rolling_mean_14', 'rolling_mean_30',
    'rolling_std_7', 'rolling_std_14', 'rolling_std_30',
]

TARGET_COLUMN = 'quantity_sold'