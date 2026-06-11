from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
import time
from app.core.logger import get_logger

logger = get_logger(__name__)

# ── Counters ──────────────────────────────────────────────────────────────────
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

ai_calls_total = Counter(
    'ai_calls_total',
    'Total Claude API calls',
    ['call_type']
)

hallucinations_total = Counter(
    'hallucinations_total',
    'Total hallucinations detected'
)

approvals_total = Counter(
    'approvals_total',
    'Total AI recommendation approvals',
    ['action']
)

etl_runs_total = Counter(
    'etl_runs_total',
    'Total ETL pipeline runs',
    ['status']
)

# ── Histograms ────────────────────────────────────────────────────────────────
api_latency_seconds = Histogram(
    'api_latency_seconds',
    'API endpoint latency',
    ['endpoint']
)

ai_tokens_used = Histogram(
    'ai_tokens_used',
    'Tokens used per Claude API call',
    ['call_type'],
    buckets=[100, 250, 500, 750, 1000, 1500, 2000, 3000, 5000]
)

ai_cost_usd = Histogram(
    'ai_cost_usd',
    'Cost per Claude API call in USD',
    ['call_type'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

forecast_accuracy = Histogram(
    'forecast_accuracy_pct',
    'ML forecast accuracy percentage',
    buckets=[50, 60, 70, 75, 80, 85, 90, 95, 100]
)

# ── Gauges ────────────────────────────────────────────────────────────────────
active_inventory_alerts = Gauge(
    'active_inventory_alerts',
    'Current number of inventory alerts'
)

model_accuracy_gauge = Gauge(
    'model_accuracy_pct',
    'Current ML model accuracy percentage'
)

pending_approvals_gauge = Gauge(
    'pending_approvals',
    'Number of AI recommendations pending approval'
)

total_ai_cost_gauge = Gauge(
    'total_ai_cost_usd',
    'Total AI API cost in USD'
)

def track_ai_call(call_type: str, tokens: int, cost: float):
    ai_calls_total.labels(call_type=call_type).inc()
    ai_tokens_used.labels(call_type=call_type).observe(tokens)
    ai_cost_usd.labels(call_type=call_type).observe(cost)
    total_ai_cost_gauge.inc(cost)

def track_hallucination():
    hallucinations_total.inc()

def track_approval(action: str):
    approvals_total.labels(action=action).inc()
    if action == "approve":
        pending_approvals_gauge.dec()
    elif action == "pending":
        pending_approvals_gauge.inc()

def get_metrics():
    return generate_latest()