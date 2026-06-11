from app.core.logger import get_logger

logger = get_logger(__name__)

ANOMALY_RULES = {
    "critical": {
        "revenue_drop_pct": 50,
        "stock_zero": True,
        "waste_pct": 10,
    },
    "high": {
        "revenue_drop_pct": 30,
        "stock_below_reorder": True,
        "waste_pct": 7,
    },
    "medium": {
        "revenue_drop_pct": 20,
        "waste_pct": 5,
    },
    "low": {
        "revenue_drop_pct": 10,
        "waste_pct": 3,
    }
}

def classify_anomaly_severity(change_pct: float) -> str:
    abs_change = abs(change_pct)
    if abs_change >= 50:
        return "critical"
    elif abs_change >= 30:
        return "high"
    elif abs_change >= 20:
        return "medium"
    else:
        return "low"

def classify_stock_urgency(
    current_stock: int,
    reorder_point: int
) -> str:
    if current_stock == 0:
        return "critical"
    elif current_stock <= reorder_point * 0.5:
        return "high"
    elif current_stock <= reorder_point:
        return "medium"
    else:
        return "low"

def classify_query_intent(query: str) -> str:
    query_lower = query.lower()
    if any(word in query_lower for word in [
        "stock", "inventory", "reorder", "supply", "order"
    ]):
        return "inventory"
    elif any(word in query_lower for word in [
        "revenue", "sales", "profit", "money", "performance"
    ]):
        return "sales"
    elif any(word in query_lower for word in [
        "forecast", "predict", "tomorrow", "next week", "demand"
    ]):
        return "forecast"
    elif any(word in query_lower for word in [
        "waste", "spoilage", "expired", "discard"
    ]):
        return "waste"
    elif any(word in query_lower for word in [
        "staff", "staffing", "employees", "workers", "schedule"
    ]):
        return "staffing"
    else:
        return "general"

def classify_brief_priority(brief_data: dict) -> str:
    low_stock = brief_data.get("low_stock_alerts", 0)
    categories = brief_data.get("categories", [])
    if low_stock > 5:
        return "critical"
    if low_stock > 2:
        return "high"
    revenues = [c.get("revenue", 0) for c in categories]
    if revenues and min(revenues) < 100:
        return "high"
    return "normal"

def route_to_model(query: str, complexity: str = "auto") -> str:
    if complexity == "simple":
        return "rule_based"
    if complexity == "complex":
        return "claude"
    query_lower = query.lower()
    simple_patterns = [
        "how many", "what is the", "list all",
        "show me", "count", "total"
    ]
    if any(p in query_lower for p in simple_patterns):
        return "rule_based"
    return "claude"