"""LeukNet API entry point.

Run locally:   uvicorn main:app --reload --port 8000
Docs:          http://localhost:8000/docs
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
cfg = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if cfg.secret_key == "change-me-in-production":
        logging.warning("SECRET_KEY is the default value - set a long random SECRET_KEY before deploying!")
    if cfg.admin_email and cfg.admin_password:
        with SessionLocal() as db:
            ensure_user(db, cfg.admin_email, cfg.admin_password)
    app.state.ml = ModelService(cfg)
    app.state.ml.load()  # sets .error instead of crashing if files are missing
    reports.set_model_info(app.state.ml.info)
    yield


app = FastAPI(title="LeukNet API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.origins,
    # also allow every Vercel preview URL of your project, e.g. https://leuknet-git-main-you.vercel.app
    allow_origin_regex=r"https://.*\.vercel\.app" if any("vercel.app" in o for o in cfg.origins) else None,
    allow_credentials=False,  # we use a bearer token header, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public: login, QR verification, health.  Everything else needs a valid bearer token.
app.include_router(auth.router, prefix="/api")
app.include_router(verify.router, prefix="/api")
for r in (predict.router, sessions.router, patients.router, reports.router, settings_router.router):
    app.include_router(r, prefix="/api", dependencies=[Depends(current_user)])


@app.get("/api/health", tags=["meta"])
def health():
    ml = app.state.ml
    return {"status": "ok" if ml.ready else "degraded", "model_loaded": ml.ready, "error": ml.error, "model": ml.info}


@app.get("/", include_in_schema=False)
def root():
    return {"service": "LeukNet API", "docs": "/docs", "health": "/api/health"}
