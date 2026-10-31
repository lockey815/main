from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ..analysis import aggregate, make_summary
from ..auth import current_user
from ..config import get_settings
from ..database import get_db
from ..models import User
from ..schemas import Aggregate
from .predict import get_session_or_404

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/{session_id}/summarize", response_model=Aggregate)
def summarize_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Final totals + the 'Results Report' text (Mistral if MISTRAL_API_KEY is set, otherwise a template)."""
    s = get_settings()
    sess = get_session_or_404(db, session_id, user)
    agg = aggregate(sess.findings, s)
    sess.summary, sess.summary_source = make_summary(agg, s)
    db.commit()
    return Aggregate(**agg, summary=sess.summary, summary_source=sess.summary_source)


@router.delete("/{session_id}", status_code=204)
def discard_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """'New Session' - throw the draft away."""
    db.delete(get_session_or_404(db, session_id, user))
    db.commit()
    return Response(status_code=204)
