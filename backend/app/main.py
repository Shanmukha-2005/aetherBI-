import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import engine, Base
import app.models  # Ensures all models are registered with Base.metadata
from app.api.auth import router as auth_router
from app.api.datasets import router as datasets_router
from app.api.dashboard import router as dashboard_router
from app.api.sql_studio import router as sql_studio_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_business_agent")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("SQLite database tables initialized successfully.")
    yield
    logger.info("Shutting down application...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Autonomous AI Business Intelligence Agent backend powered by SQLite & Gemini",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth_router, prefix="/api")
app.include_router(datasets_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(sql_studio_router, prefix="/api")

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "database": "SQLite",
        "llm": "Gemini-Ready" if settings.GEMINI_API_KEY else "Heuristic-Fallback"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
