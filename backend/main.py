
"""
LeukNet API entry point.

Run locally:
    uvicorn main:app --reload --port 8000

Documentation:
    http://localhost:8000/docs

Health:
    http://localhost:8000/api/health
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


# --------------------------------------------------
# Logging and configuration
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

logger = logging.getLogger("leuknet")

cfg = get_settings()


# --------------------------------------------------
# Application lifespan
# --------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting LeukNet API...")

    # Initialize model state immediately
    app.state.ml = None

    # Initialize database
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized.")

    except Exception:
        logger.exception("Database initialization failed.")

    # Initialize administrator account
    if cfg.admin_email and cfg.admin_password:
        try:
            with SessionLocal() as db:
                ensure_user(db, cfg.admin_email, cfg.admin_password)

            logger.info("Administrator account initialized.")

        except Exception:
            logger.exception("Administrator initialization failed.")

    # Check production secret
    if cfg.secret_key == "change-me-in-production":
        logger.warning(
            "Default SECRET_KEY detected. Configure a secure SECRET_KEY in Render."
        )

    # Initialize machine learning service
    try:
        logger.info("Initializing LeukNet model...")

        app.state.ml = ModelService(cfg)
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

        if app.state.ml is not None:
            app.state.ml.error = str(exc)

    # Update report model information
    try:
        if app.state.ml is not None:
            reports.set_model_info(app.state.ml.info)

    except Exception:
        logger.exception("Could not update report model information.")

    logger.info("LeukNet API startup complete.")

    yield

    logger.info("LeukNet API shutting down.")


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="LeukNet API",
    description="LeukNet blood-cell classification API",
    version="2.1.0",
    lifespan=lifespan,
)


# --------------------------------------------------
# CORS configuration
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://main-6x0.pages.dev",
    ],
    allow_origin_regex=r"^https://([a-zA-Z0-9-]+\.)?main-6x0\.pages\.dev$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Public routers
# --------------------------------------------------

app.include_router(auth.router, prefix="/api")
app.include_router(verify.router, prefix="/api")


# --------------------------------------------------
# Protected routers
# --------------------------------------------------

protected_routers = [
    predict.router,
    sessions.router,
    patients.router,
    reports.router,
    settings_router.router,
]

for router in protected_routers:
    app.include_router(
        router,
        prefix="/api",
        dependencies=[Depends(current_user)],
    )


# --------------------------------------------------
# Health checks
# --------------------------------------------------

@app.get("/api/health", tags=["meta"])
@app.get("/health", tags=["meta"])
@app.get("/healthz", tags=["meta"])
def health():

    ml = getattr(app.state, "ml", None)

    if ml is None:
        return {
            "service": "LeukNet API",
            "status": "degraded",
            "model_loaded": False,
            "error": "Model service has not initialized.",
            "model": {},
        }

    model_ready = bool(ml.ready)

    return {
        "service": "LeukNet API",
        "status": "ok" if model_ready else "degraded",
        "model_loaded": model_ready,
        "error": ml.error,
        "model": ml.info,
    }


# --------------------------------------------------
# Root endpoint
# --------------------------------------------------

@app.get("/", tags=["meta"])
def root():

    return {
        "service": "LeukNet API",
        "version": "2.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health",
        "health_alternative": "/health",
    }
