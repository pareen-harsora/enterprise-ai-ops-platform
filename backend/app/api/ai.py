from fastapi import APIRouter, HTTPException
from app.services.llm import call_claude, build_system_prompt, validate_numbers_in_response
from app.services.rag import retrieve_context
from app.services.evaluator import evaluate_ai_output
from app.models.database import SessionLocal, SalesRecord, InventoryRecord, ForecastRecord, AILog
from app.core.logger import get_logger
from sqlalchemy import func
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
from app.agents.graph import run_ops_agent
from app.agents.mcp_server import mcp_claude_query, get_mcp_tools_list

router = APIRouter()
logger = get_logger(__name__)

class SearchQuery(BaseModel):
    query: str

@router.get("/ai/daily-brief")
def generate_daily_brief():
    logger.info("Generating daily operations brief")
    db = SessionLocal()
    try:
        yesterday = datetime.utcnow() - timedelta(days=1)
        since_30 = datetime.utcnow() - timedelta(days=30)
        sales_by_category = db.query(
            SalesRecord.category,
            func.sum(SalesRecord.total_revenue).label("revenue"),
            func.sum(SalesRecord.quantity_sold).label("units")
        ).filter(
            SalesRecord.date >= yesterday
        ).group_by(SalesRecord.category).all()
        monthly_revenue = db.query(
            func.sum(SalesRecord.total_revenue)
        ).filter(
            SalesRecord.date >= since_30
        ).scalar() or 0
        low_stock = db.query(InventoryRecord).filter(
            InventoryRecord.date >= datetime.utcnow() - timedelta(days=1),
            InventoryRecord.closing_stock <= InventoryRecord.reorder_point
        ).count()
        latest_forecast = db.query(ForecastRecord).order_by(
            ForecastRecord.created_at.desc()
        ).limit(5).all()
        sales_data = {
            "date": yesterday.strftime("%Y-%m-%d"),
            "categories": [
                {
                    "category": r.category,
                    "revenue": round(r.revenue, 2),
                    "units": r.units
                }
                for r in sales_by_category
            ],
            "monthly_revenue": round(monthly_revenue, 2),
            "low_stock_alerts": low_stock,
            "recent_forecasts": [
                {
                    "category": f.category,
                    "location": f.location,
                    "predicted": f.predicted_demand
                }
                for f in latest_forecast
            ]
        }
        rag_context = retrieve_context(
            "daily operations inventory management demand forecasting"
        )
        total_yesterday = sum(
            r.revenue for r in sales_by_category
        )
        prompt = f"""Generate a daily operations brief for our campus food service operations.

DATE: {yesterday.strftime("%B %d, %Y")}

YESTERDAY'S PERFORMANCE:
Total Revenue: ${total_yesterday:.2f}
30-Day Revenue: ${monthly_revenue:.2f}
Low Stock Alerts: {low_stock} items below reorder point

SALES BY CATEGORY:
{chr(10).join([f"- {r.category}: ${r.revenue:.2f} revenue, {r.units} units" for r in sales_by_category])}

UPCOMING FORECASTS:
{chr(10).join([f"- {f.category} at {f.location}: {f.predicted_demand} units predicted" for f in latest_forecast])}

RELEVANT POLICIES:
{rag_context if rag_context else "Standard operating procedures apply."}

Generate a professional operations brief with these sections:
1. PERFORMANCE SUMMARY (2-3 sentences on yesterday)
2. KEY ALERTS (bullet points — stock issues, anomalies)
3. TODAY'S PRIORITIES (3 specific actions for managers)
4. FORECAST OUTLOOK (what to prepare for based on predictions)

Be specific, use the actual numbers provided, and keep it under 300 words."""
        result = call_claude(
            prompt=prompt,
            system_prompt=build_system_prompt(),
            max_tokens=600
        )
        validation = validate_numbers_in_response(
            result["content"], sales_data
        )
        db2 = SessionLocal()
        try:
            ai_log = AILog(
                log_type="daily_brief",
                input_data=sales_data,
                prompt_used=prompt,
                ai_output=result["content"],
                tokens_used=result["total_tokens"],
                cost_usd=result["cost_usd"],
                validation_passed=validation["passed"],
            )
            db2.add(ai_log)
            db2.commit()
            db2.refresh(ai_log)
            log_id = ai_log.id
        finally:
            db2.close()
        return {
            "date": yesterday.strftime("%Y-%m-%d"),
            "brief": result["content"],
            "validation": validation,
            "tokens_used": result["total_tokens"],
            "cost_usd": result["cost_usd"],
            "ai_log_id": log_id,
            "data_used": sales_data
        }
    except Exception as e:
        logger.error(f"Daily brief generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.post("/ai/search")
def semantic_search_endpoint(request: SearchQuery):
    try:
        from app.services.semantic_search import semantic_search
        result = semantic_search(request.query)
        return result
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai/logs")
def get_ai_logs(limit: int = 10):
    db = SessionLocal()
    try:
        logs = db.query(AILog).order_by(
            AILog.created_at.desc()
        ).limit(limit).all()
        return {
            "logs": [
                {
                    "id": l.id,
                    "log_type": l.log_type,
                    "tokens_used": l.tokens_used,
                    "cost_usd": l.cost_usd,
                    "validation_passed": l.validation_passed,
                    "created_at": l.created_at.isoformat()
                }
                for l in logs
            ]
        }
    finally:
        db.close()

@router.get("/ai/eval/{log_id}")
def evaluate_log(log_id: int):
    db = SessionLocal()
    try:
        log = db.query(AILog).filter(AILog.id == log_id).first()
        if not log:
            raise HTTPException(status_code=404, detail="Log not found")
        source_data = log.input_data or {}
    finally:
        db.close()
    result = evaluate_ai_output(log_id, source_data)
    return result

@router.get("/ai/agent/run")
def run_agent():
    try:
        result = run_ops_agent()
        return result
    except Exception as e:
        logger.error(f"Agent run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai/mcp/tools")
def list_mcp_tools():
    return {"tools": get_mcp_tools_list()}

class MCPQuery(BaseModel):
    query: str

@router.post("/ai/mcp/query")
def mcp_query(request: MCPQuery):
    try:
        result = mcp_claude_query(request.query)
        return result
    except Exception as e:
        logger.error(f"MCP query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))