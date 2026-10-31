from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..analysis import aggregate, template_summary
from ..auth import current_user
from ..config import get_settings
from ..database import get_db
from ..models import AnalysisSession, User
from ..schemas import Aggregate, Finding, PredictionOut

router = APIRouter(tags=["predict"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff", "application/pdf"}


def get_session_or_404(db: Session, session_id: str, user: User) -> AnalysisSession:
    sess = db.get(AnalysisSession, session_id)
    if sess is None or sess.user_id != user.id:
        raise HTTPException(404, "Analysis session not found (it may have expired). Start a new session.")
    return sess


def session_aggregate(sess: AnalysisSession, with_template: bool = True) -> Aggregate:
    s = get_settings()
    agg = aggregate(sess.findings, s)
    summary = sess.summary or (template_summary(agg, s) if with_template else "")
    return Aggregate(**agg, summary=summary, summary_source=sess.summary_source or ("template" if summary else ""))


@router.post("/predict", response_model=PredictionOut)
def predict(
    request: Request,
    files: list[UploadFile] = File(..., description="Blood smear images (JPEG/PNG/WEBP/BMP/TIFF) or PDFs"),
    session_id: str | None = Form(None, description="Add these samples to an existing analysis session"),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Analyse samples and keep the results in a server-side session. Nothing is saved as a report until
    the user reviews the results and calls POST /api/reports (the 'Save Results' step)."""
    s = get_settings()
    ml = request.app.state.ml
    if not ml.ready:
        raise HTTPException(503, f"Model is not loaded: {ml.error}")
    if not files:
        raise HTTPException(400, "No files uploaded")
    if len(files) > s.max_files_per_request:
        raise HTTPException(413, f"A maximum of {s.max_files_per_request} files is allowed per request")

    # drop abandoned drafts
    cutoff = datetime.now(timezone.utc) - timedelta(hours=s.session_ttl_hours)
    db.execute(delete(AnalysisSession).where(AnalysisSession.created_at < cutoff))
    db.commit()

    sess = get_session_or_404(db, session_id, user) if session_id else None
    existing = len(sess.findings) if sess else 0

    limit = s.max_upload_mb * 1024 * 1024
    analyses = []
    for f in files:
        if f.content_type not in ALLOWED_TYPES:
            raise HTTPException(415, f"'{f.filename}': unsupported type {f.content_type}. Use JPEG, PNG, WEBP, BMP, TIFF or PDF.")
        raw = f.file.read(limit + 1)
        if len(raw) > limit:
            raise HTTPException(413, f"'{f.filename}' exceeds {s.max_upload_mb} MB")
        for name, img, err in ml.expand_upload(f.filename or "sample", raw, f.content_type):
            analyses.append(ml.analyze_image(name, img, err))
    if existing + len(analyses) > s.max_samples_per_session:
        raise HTTPException(413, f"A session can hold at most {s.max_samples_per_session} samples")

    findings = [Finding(**a.__dict__) for a in analyses]
    stored = [f.model_dump(exclude={"original_image"}) for f in findings]  # previews are not persisted

    if sess is None:
        sess = AnalysisSession(user_id=user.id, findings=stored)
        db.add(sess)
    else:
        sess.findings = [*sess.findings, *stored]  # reassign so SQLAlchemy sees the change
        sess.summary, sess.summary_source = "", ""  # any earlier summary is now stale
    db.commit()
    db.refresh(sess)

    return PredictionOut(session_id=sess.id, findings=findings, aggregate=session_aggregate(sess), model_info=ml.info)
