from app.models.database import SessionLocal, AILog, EvalRecord
from app.services.llm import validate_numbers_in_response
from app.core.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

def evaluate_ai_output(ai_log_id: int, source_data: dict) -> dict:
    db = SessionLocal()
    try:
        ai_log = db.query(AILog).filter(AILog.id == ai_log_id).first()
        if not ai_log:
            return {"error": "AI log not found"}
        validation = validate_numbers_in_response(
            ai_log.ai_output, source_data
        )
        relevance_score = 0.9 if validation["passed"] else 0.6
        accuracy_score = (
            validation["numbers_validated"] /
            max(validation["numbers_checked"], 1)
        )
        eval_record = EvalRecord(
            eval_type="output_validation",
            ai_log_id=ai_log_id,
            hallucination_detected=not validation["passed"],
            relevance_score=relevance_score,
            accuracy_score=accuracy_score,
            numbers_validated=validation["passed"],
            eval_notes=str(validation["issues"]) if validation["issues"] else "All checks passed"
        )
        db.add(eval_record)
        ai_log.validation_passed = validation["passed"]
        db.commit()
        logger.info(
            f"Eval complete for log {ai_log_id} — "
            f"passed: {validation['passed']}, "
            f"accuracy: {accuracy_score:.2f}"
        )
        return {
            "ai_log_id": ai_log_id,
            "validation_passed": validation["passed"],
            "hallucination_detected": not validation["passed"],
            "relevance_score": relevance_score,
            "accuracy_score": round(accuracy_score, 4),
            "numbers_checked": validation["numbers_checked"],
            "numbers_validated": validation["numbers_validated"],
            "issues": validation["issues"]
        }
    finally:
        db.close()