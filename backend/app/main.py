from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models.database import create_tables
from app.api import health, data, forecast, ai, search, graph, evals
from app.core.logger import get_logger
from app.core.metrics import get_metrics, CONTENT_TYPE_LATEST

logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Enterprise AI Ops Platform",
    version="1.0.0",
    debug=settings.debug
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    logger.info("Starting Enterprise AI Ops Platform")
    create_tables()
    logger.info("All systems ready")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down")

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(data.router, prefix="/api/v1", tags=["Data"])
app.include_router(forecast.router, prefix="/api/v1", tags=["Forecast"])
app.include_router(ai.router, prefix="/api/v1", tags=["AI"])
app.include_router(search.router, prefix="/api/v1", tags=["Search"])
app.include_router(graph.router, prefix="/api/v1", tags=["Graph"])
app.include_router(evals.router, prefix="/api/v1", tags=["Evals"])

@app.get("/metrics")
def metrics():
    return Response(
        content=get_metrics(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "metrics": "/metrics"
    }