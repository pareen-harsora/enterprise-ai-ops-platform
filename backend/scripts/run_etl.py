import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import (
    SessionLocal, SalesRecord, InventoryRecord,
    DataQualityLog, drop_and_recreate_tables
)
from app.core.logger import get_logger

logger = get_logger(__name__)

class DataQualityChecker:
    def __init__(self, df, dataset_name):
        self.df = df
        self.dataset_name = dataset_name
        self.issues = []
        self.passed = 0
        self.failed = 0

    def check_missing_values(self):
        missing = self.df.isnull().sum()
        missing_cols = missing[missing > 0]
        if len(missing_cols) > 0:
            for col, count in missing_cols.items():
                self.issues.append({
                    "type": "missing_values",
                    "column": col,
                    "count": int(count)
                })
                self.failed += count
        else:
            self.passed += len(self.df)
        return self

    def check_negative_values(self, numeric_cols):
        for col in numeric_cols:
            if col in self.df.columns:
                neg_count = (self.df[col] < 0).sum()
                if neg_count > 0:
                    self.issues.append({
                        "type": "negative_values",
                        "column": col,
                        "count": int(neg_count)
                    })
                    self.failed += neg_count
                    self.df = self.df[self.df[col] >= 0]
        return self

    def check_duplicates(self):
        dup_count = self.df.duplicated().sum()
        if dup_count > 0:
            self.issues.append({
                "type": "duplicates",
                "count": int(dup_count)
            })
            self.failed += dup_count
            self.df = self.df.drop_duplicates()
        return self

    def check_date_range(self, date_col):
        if date_col in self.df.columns:
            future_dates = (
                pd.to_datetime(self.df[date_col]) > datetime.now()
            ).sum()
            if future_dates > 0:
                self.issues.append({
                    "type": "future_dates",
                    "column": date_col,
                    "count": int(future_dates)
                })
                self.failed += future_dates
        return self

    def check_outliers(self, col, threshold=3):
        if col in self.df.columns:
            mean = self.df[col].mean()
            std = self.df[col].std()
            outliers = (
                (self.df[col] - mean).abs() > threshold * std
            ).sum()
            if outliers > 0:
                self.issues.append({
                    "type": "outliers",
                    "column": col,
                    "count": int(outliers),
                    "threshold": f"{threshold} standard deviations"
                })
        return self

    def get_quality_score(self):
        total = self.passed + self.failed
        if total == 0:
            return 100.0
        score = (self.passed / total) * 100
        issue_penalty = min(len(self.issues) * 2, 20)
        return round(max(0, score - issue_penalty), 2)

    def get_clean_df(self):
        return self.df

def load_sales_data(db, sales_df):
    logger.info(f"Loading {len(sales_df)} sales records into PostgreSQL")
    batch_size = 1000
    loaded = 0

    for i in range(0, len(sales_df), batch_size):
        batch = sales_df.iloc[i:i + batch_size]
        records = []
        for _, row in batch.iterrows():
            record = SalesRecord(
                date=pd.to_datetime(row['date']),
                location=str(row['location']),
                category=str(row['category']),
                item_name=str(row['item_name']),
                quantity_sold=int(row['quantity_sold']),
                unit_price=float(row['unit_price']),
                total_revenue=float(row['total_revenue']),
                weather=str(row['weather']),
                is_event_day=bool(row['is_event_day']),
            )
            records.append(record)
        db.bulk_save_objects(records)
        db.commit()
        loaded += len(batch)
        logger.info(f"  Loaded {loaded}/{len(sales_df)} sales records")

    logger.info("Sales data loading complete")

def load_inventory_data(db, inventory_df):
    logger.info(f"Loading {len(inventory_df)} inventory records into PostgreSQL")
    batch_size = 1000
    loaded = 0

    for i in range(0, len(inventory_df), batch_size):
        batch = inventory_df.iloc[i:i + batch_size]
        records = []
        for _, row in batch.iterrows():
            record = InventoryRecord(
                date=pd.to_datetime(row['date']),
                item_name=str(row['item_name']),
                category=str(row['category']),
                location=str(row['location']),
                opening_stock=int(row['opening_stock']),
                units_received=int(row['units_received']),
                units_sold=int(row['units_sold']),
                closing_stock=int(row['closing_stock']),
                waste_units=int(row['waste_units']),
                reorder_point=int(row['reorder_point']),
            )
            records.append(record)
        db.bulk_save_objects(records)
        db.commit()
        loaded += len(batch)
        logger.info(f"  Loaded {loaded}/{len(inventory_df)} inventory records")

    logger.info("Inventory data loading complete")

def save_quality_log(db, checker, pipeline_run):
    quality_log = DataQualityLog(
        pipeline_run=pipeline_run,
        total_records=checker.passed + checker.failed,
        passed_records=checker.passed,
        failed_records=checker.failed,
        quality_score=checker.get_quality_score(),
        issues_found=checker.issues,
    )
    db.add(quality_log)
    db.commit()
    logger.info(
        f"Quality score for {pipeline_run}: "
        f"{checker.get_quality_score()}%"
    )

def run_etl():
    logger.info("=" * 50)
    logger.info("Starting ETL Pipeline")
    logger.info("=" * 50)

    drop_and_recreate_tables()

    sales_path = "../data/raw/sales_data.csv"
    inventory_path = "../data/raw/inventory_data.csv"

    if not os.path.exists(sales_path):
        logger.error("Sales data not found. Run generate_data.py first.")
        return

    logger.info("Loading raw data files")
    sales_df = pd.read_csv(sales_path)
    inventory_df = pd.read_csv(inventory_path)
    logger.info(f"Raw sales records: {len(sales_df)}")
    logger.info(f"Raw inventory records: {len(inventory_df)}")

    logger.info("Running data quality checks on sales data")
    sales_checker = DataQualityChecker(sales_df, "sales")
    sales_checker\
        .check_missing_values()\
        .check_negative_values(['quantity_sold', 'unit_price', 'total_revenue'])\
        .check_duplicates()\
        .check_date_range('date')\
        .check_outliers('total_revenue')

    logger.info("Running data quality checks on inventory data")
    inventory_checker = DataQualityChecker(inventory_df, "inventory")
    inventory_checker\
        .check_missing_values()\
        .check_negative_values(['opening_stock', 'closing_stock', 'units_sold'])\
        .check_duplicates()\
        .check_date_range('date')

    clean_sales = sales_checker.get_clean_df()
    clean_inventory = inventory_checker.get_clean_df()

    logger.info(f"Clean sales records: {len(clean_sales)}")
    logger.info(f"Clean inventory records: {len(clean_inventory)}")

    os.makedirs("../data/processed", exist_ok=True)
    clean_sales.to_csv("../data/processed/clean_sales.csv", index=False)
    clean_inventory.to_csv("../data/processed/clean_inventory.csv", index=False)

    db = SessionLocal()
    try:
        load_sales_data(db, clean_sales)
        load_inventory_data(db, clean_inventory)
        save_quality_log(db, sales_checker, "sales_etl")
        save_quality_log(db, inventory_checker, "inventory_etl")
    finally:
        db.close()

    logger.info("=" * 50)
    logger.info("ETL Pipeline Complete")
    logger.info(f"Sales quality score: {sales_checker.get_quality_score()}%")
    logger.info(f"Inventory quality score: {inventory_checker.get_quality_score()}%")
    logger.info(f"Issues found: {len(sales_checker.issues)}")
    logger.info("=" * 50)

if __name__ == "__main__":
    run_etl()