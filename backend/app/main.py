import sys
import os

# Ensure backend directory is on sys.path regardless of execution CWD
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import logger
from app.api.router import api_router
from app.session.session_manager import session_manager

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing in-memory session manager...")
    default_sess = session_manager.get_or_create_session()
    logger.info(f"{settings.APP_NAME} Backend API Server initialized successfully with active session {default_sess.session_id}.")
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="SORTOLOG IQ — Stateless AI-Powered Industrial Product Enrichment Engine API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Middleware Setup
frontend_clean = settings.FRONTEND_URL.rstrip("/").strip() if settings.FRONTEND_URL else ""
cors_origins = list(dict.fromkeys(settings.CORS_ORIGINS + ([frontend_clean] if frontend_clean else [])))
cors_origins = [o for o in cors_origins if o != "*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://.*\.vercel\.app|http://localhost:\d+|http://127\.0\.0\.1:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes.health import get_health

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["System"])
def root_health():
    return get_health()

@app.get("/", tags=["System"])
def root():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Server Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred.",
            "details": str(exc) if settings.DEBUG else {}
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
