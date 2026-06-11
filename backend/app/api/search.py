from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.semantic_search import semantic_search
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)

class SearchRequest(BaseModel):
    query: str

@router.post("/search")
def search(request: SearchRequest):
    try:
        result = semantic_search(request.query)
        return result
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))