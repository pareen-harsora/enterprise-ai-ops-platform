import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fake = Faker('en_CA')
random.seed(42)
np.random.seed(42)

LOCATIONS = [
    "Seneca King Campus",
    "Seneca Newnham Campus",
    "Seneca Markham Campus"
]

MENU_ITEMS = {
    "Hot Entrees": [
        ("Grilled Chicken Sandwich", 9.99),
        ("Beef Burger", 10.99),
        ("Veggie Wrap", 8.99),
        ("Mac and Cheese", 7.99),
        ("Butter Chicken Bowl", 11.99),
        ("Fish and Chips", 12.99),
        ("Pasta Primavera", 9.49),
        ("BBQ Pulled Pork", 11.49),
    ],
    "Cold Items": [
        ("Caesar Salad", 8.49),
        ("Garden Salad", 7.49),
        ("Club Sandwich", 9.99),
        ("Tuna Wrap", 8.99),
        ("Fruit Cup", 4.99),
        ("Greek Salad", 8.99),
    ],
    "Beverages": [
        ("Coffee", 2.49),
        ("Tea", 1.99),
        ("Orange Juice", 3.49),
        ("Bottled Water", 1.99),
        ("Energy Drink", 3.99),
        ("Smoothie", 5.99),
        ("Soft Drink", 2.49),
    ],
    "Snacks": [
        ("Muffin", 2.99),
        ("Cookie", 1.99),
        ("Granola Bar", 2.49),
        ("Chips", 1.99),
        ("Yogurt Parfait", 4.99),
        ("Banana", 0.99),
        ("Bagel with Cream Cheese", 3.99),
    ],
    "Breakfast": [
        ("Breakfast Sandwich", 6.99),
        ("Pancakes", 7.99),
        ("Oatmeal", 4.99),
        ("Scrambled Eggs", 5.99),
        ("French Toast", 6.49),
    ]
}

WEATHER_CONDITIONS = ["sunny", "cloudy", "rainy", "snowy", "windy"]

TORONTO_EVENTS = [
    "Fall Orientation Week",
    "Winter Exam Period",
    "Spring Convocation",
    "Campus Open House",
    "Sports Tournament",
    "Cultural Festival",
    "Career Fair",
    "Summer Orientation",
]

def is_school_day(date):
    if date.weekday() >= 5:
        return False
    if date.month == 7 or (date.month == 8 and date.day > 15):
        return False
    return True

def get_season(date):
    month = date.month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"

def get_weather(date):
    season = get_season(date)
    if season == "winter":
        weights = [0.1, 0.3, 0.1, 0.4, 0.1]
    elif season == "spring":
        weights = [0.3, 0.3, 0.3, 0.0, 0.1]
    elif season == "summer":
        weights = [0.6, 0.2, 0.2, 0.0, 0.0]
    else:
        weights = [0.3, 0.3, 0.2, 0.1, 0.1]
    return random.choices(WEATHER_CONDITIONS, weights=weights)[0]

def is_event_day(date):
    month_day = (date.month, date.day)
    event_dates = [
        (9, 5), (9, 6), (9, 7), (9, 8),
        (12, 10), (12, 11), (12, 12), (12, 13),
        (4, 20), (4, 21), (4, 22),
        (6, 15), (6, 16),
        (10, 15), (10, 16),
        (2, 10), (2, 11),
        (3, 20), (3, 21),
        (1, 15), (1, 16),
    ]
    return month_day in event_dates

def get_demand_multiplier(date, weather, location):
    multiplier = 1.0
    if not is_school_day(date):
        multiplier *= 0.3
    season = get_season(date)
    if season == "summer":
        multiplier *= 0.4
    elif season == "fall":
        multiplier *= 1.2
    elif season == "winter":
        multiplier *= 0.9
    if weather == "rainy":
        multiplier *= 1.15
    elif weather == "snowy":
        multiplier *= 0.7
    elif weather == "sunny":
        multiplier *= 1.05
    if is_event_day(date):
        multiplier *= 1.4
    if date.weekday() == 0:
        multiplier *= 0.9
    elif date.weekday() == 4:
        multiplier *= 0.85
    location_multipliers = {
        "Seneca King Campus": 1.2,
        "Seneca Newnham Campus": 1.0,
        "Seneca Markham Campus": 0.8,
    }
    multiplier *= location_multipliers.get(location, 1.0)
    return multiplier

def generate_sales_data(start_date, end_date):
    records = []
    current_date = start_date

    print(f"Generating sales data from {start_date.date()} to {end_date.date()}")

    while current_date <= end_date:
        weather = get_weather(current_date)
        event_day = is_event_day(current_date)

        for location in LOCATIONS:
            multiplier = get_demand_multiplier(
                current_date, weather, location
            )

            for category, items in MENU_ITEMS.items():
                if category == "Breakfast" and current_date.weekday() >= 5:
                    continue

                for item_name, base_price in items:
                    if category == "Hot Entrees":
                        base_qty = random.randint(20, 60)
                    elif category == "Beverages":
                        base_qty = random.randint(40, 100)
                    elif category == "Snacks":
                        base_qty = random.randint(15, 45)
                    elif category == "Cold Items":
                        base_qty = random.randint(10, 35)
                    else:
                        base_qty = random.randint(10, 30)

                    qty = max(0, int(base_qty * multiplier * random.uniform(0.8, 1.2)))

                    if qty == 0:
                        continue

                    price_variation = random.uniform(0.95, 1.05)
                    unit_price = round(base_price * price_variation, 2)
                    total_revenue = round(qty * unit_price, 2)

                    noise = np.random.normal(0, 0.05)
                    total_revenue = round(total_revenue * (1 + noise), 2)

                    records.append({
                        "date": current_date,
                        "location": location,
                        "category": category,
                        "item_name": item_name,
                        "quantity_sold": qty,
                        "unit_price": unit_price,
                        "total_revenue": total_revenue,
                        "weather": weather,
                        "is_event_day": event_day,
                    })

        current_date += timedelta(days=1)

        if current_date.day == 1:
            print(f"  Generated through {current_date.strftime('%B %Y')}")

    print(f"Total sales records generated: {len(records)}")
    return pd.DataFrame(records)

def generate_inventory_data(sales_df):
    records = []
    print("Generating inventory data")

    all_items = []
    for category, items in MENU_ITEMS.items():
        for item_name, _ in items:
            all_items.append((item_name, category))

    stock_levels = {}
    for item_name, category in all_items:
        for location in LOCATIONS:
            key = (item_name, location)
            if category == "Beverages":
                stock_levels[key] = random.randint(150, 200)
            elif category == "Hot Entrees":
                stock_levels[key] = random.randint(80, 120)
            elif category == "Snacks":
                stock_levels[key] = random.randint(60, 100)
            else:
                stock_levels[key] = random.randint(50, 80)

    for date in sorted(sales_df['date'].unique()):
        date_sales = sales_df[sales_df['date'] == date]

        for location in LOCATIONS:
            location_sales = date_sales[date_sales['location'] == location]

            for item_name, category in all_items:
                key = (item_name, location)
                opening_stock = stock_levels[key]

                item_sales = location_sales[
                    location_sales['item_name'] == item_name
                ]['quantity_sold'].sum()
                units_sold = int(item_sales)

                if category in ["Beverages", "Snacks"]:
                    reorder_point = 30
                    max_stock = 200
                    waste_rate = 0.02
                elif category == "Hot Entrees":
                    reorder_point = 20
                    max_stock = 120
                    waste_rate = 0.05
                else:
                    reorder_point = 15
                    max_stock = 80
                    waste_rate = 0.03

                waste_units = max(0, int(
                    opening_stock * waste_rate * random.uniform(0.5, 1.5)
                ))
                closing_stock = max(0, opening_stock - units_sold - waste_units)

                units_received = 0
                if closing_stock <= reorder_point:
                    units_received = random.randint(
                        int(max_stock * 0.5),
                        max_stock
                    )
                    closing_stock += units_received

                stock_levels[key] = closing_stock

                records.append({
                    "date": date,
                    "item_name": item_name,
                    "category": category,
                    "location": location,
                    "opening_stock": opening_stock,
                    "units_received": units_received,
                    "units_sold": units_sold,
                    "closing_stock": closing_stock,
                    "waste_units": waste_units,
                    "reorder_point": reorder_point,
                })

    print(f"Total inventory records generated: {len(records)}")
    return pd.DataFrame(records)

def save_to_csv(sales_df, inventory_df):
    os.makedirs("../data/raw", exist_ok=True)
    sales_path = "../data/raw/sales_data.csv"
    inventory_path = "../data/raw/inventory_data.csv"
    sales_df.to_csv(sales_path, index=False)
    inventory_df.to_csv(inventory_path, index=False)
    print(f"Sales data saved to {sales_path}")
    print(f"Inventory data saved to {inventory_path}")
    print(f"Sales records: {len(sales_df)}")
    print(f"Inventory records: {len(inventory_df)}")

if __name__ == "__main__":
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)

    print("=" * 50)
    print("Enterprise AI Ops Platform")
    print("Data Generator v1.0")
    print("=" * 50)

    sales_df = generate_sales_data(start_date, end_date)
    inventory_df = generate_inventory_data(sales_df)
    save_to_csv(sales_df, inventory_df)

    print("=" * 50)
    print("Data generation complete")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    print(f"Locations: {len(LOCATIONS)}")
    print(f"Menu categories: {len(MENU_ITEMS)}")
    print(f"Total menu items: {sum(len(v) for v in MENU_ITEMS.values())}")
    print("=" * 50)