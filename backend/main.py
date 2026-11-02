
"""
LeukNet API entry point.

Run locally: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import current_user, ensure_user
from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.ml import ModelService
from app.routers import auth, patients, predict, reports, sessions, verify
from app.routers import settings as settings_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

cfg = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database
    Base.metadata.create_all(bind=engine)

    # Warn about insecure configuration
    if cfg.secret_key == "change-me-in-production":
        logger.warning(
            "SECRET_KEY is the default value. "
            "Configure a secure SECRET_KEY in Render."
        )

    # Initialize administrator account
    if cfg.admin_email and cfg.admin_password:
        with SessionLocal() as db:
            ensure_user(db, cfg.admin_email, cfg.admin_password)

    # Initialize machine learning service
    app.state.ml = ModelService(cfg)

    try:
        logger.info("Initializing LeukNet model...")
        app.state.ml.load()

        if app.state.ml.ready:
            logger.info("LeukNet model loaded successfully.")
        else:
            logger.error(
                "LeukNet model failed to load: %s",
                app.state.ml.error,
            )

    except Exception as exc:
        logger.exception("Model initialization failed.")
        app.state.ml.error = str(exc)

    # Update report model information
    reports.set_model_info(app.state.ml.info)

    yield

    logger.info("LeukNet API shutting down.")


app = FastAPI(
    title="LeukNet API",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://main-6x0.pages.dev",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes
app.include_router(auth.router, prefix="/api")
app.include_router(verify.router, prefix="/api")

# Protected routes
protected_routers = (
    predict.router,
    sessions.router,
    patients.router,
    reports.router,
    settings_router.router,
)

for router in protected_routers:
    app.include_router(
        router,
        prefix="/api",
        dependencies=[Depends(current_user)],
    )


@app.get("/api/health", tags=["meta"])
def health():
    ml = getattr(app.state, "ml", None)

    if ml is None:
        return {
            "status": "degraded",
            "model_loaded": False,
            "error": "Model service has not initialized.",
            "model": {},
        }

    return {
        "status": "ok" if ml.ready else "degraded",
        "model_loaded": ml.ready,
        "error": ml.error,
        "model": ml.info,
    }


@app.get("/", include_in_schema=False)
def root():
    return {
        "service": "LeukNet API",
        "docs": "/docs",
        "health": "/api/health",
    }
