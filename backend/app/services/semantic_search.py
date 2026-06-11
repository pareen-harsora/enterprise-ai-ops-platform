from app.services.rag import get_vector_store, retrieve_context
from app.services.llm import call_claude, build_system_prompt
from app.models.database import SessionLocal, SalesRecord, AILog
from app.core.logger import get_logger
from sqlalchemy import func, text
from datetime import datetime, timedelta

logger = get_logger(__name__)

def semantic_search(query: str) -> dict:
    logger.info(f"Semantic search query: {query}")
    context = retrieve_context(query, k=3)
    db = SessionLocal()
    try:
        recent_sales = db.query(
            SalesRecord.category,
            func.sum(SalesRecord.total_revenue).label("revenue"),
            func.sum(SalesRecord.quantity_sold).label("units")
        ).filter(
            SalesRecord.date >= datetime.utcnow() - timedelta(days=30)
        ).group_by(SalesRecord.category).all()
        data_context = "\n".join([
            f"{r.category}: ${r.revenue:.2f} revenue, {r.units} units (last 30 days)"
            for r in recent_sales
        ])
    finally:
        db.close()
    prompt = f"""Answer this question about our food service operations:

QUESTION: {query}

RECENT OPERATIONS DATA (last 30 days):
{data_context}

RELEVANT POLICIES AND RUNBOOKS:
{context if context else "No specific runbook found for this query."}

Provide a specific, actionable answer based on the data and policies above.
If the question requires data not provided, say so clearly."""
    result = call_claude(
        prompt=prompt,
        system_prompt=build_system_prompt(),
        max_tokens=500
    )
    db = SessionLocal()
    try:
        ai_log = AILog(
            log_type="semantic_search",
            input_data={"query": query},
            prompt_used=prompt,
            ai_output=result["content"],
            tokens_used=result["total_tokens"],
            cost_usd=result["cost_usd"],
            validation_passed=True,
        )
        db.add(ai_log)
        db.commit()
    finally:
        db.close()
    return {
        "query": query,
        "answer": result["content"],
        "sources_used": len(context.split("[Runbook:")) - 1 if context else 0,
        "tokens_used": result["total_tokens"],
        "cost_usd": result["cost_usd"],
    }