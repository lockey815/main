from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, defer, joinedload

from ..analysis import TEST_NAME, aggregate, make_summary
from ..auth import current_user
from ..config import get_settings
from ..database import get_db
from ..models import Patient, Report, User
from ..pdf import build_report_pdf
from ..qr import qr_data_uri, qr_png_bytes
from ..schemas import ReportCreate, ReportListItem, ReportOut
from .predict import get_session_or_404
from .settings import get_facility

router = APIRouter(prefix="/reports", tags=["reports"])


def verify_url_for(token: str) -> str:
    return f"{get_settings().frontend_url.rstrip('/')}/verify/{token}"


def _get_or_404(db: Session, report_id: str) -> Report:
    r = db.scalar(select(Report).options(joinedload(Report.patient)).where(Report.id == report_id))
    if r is None:
        raise HTTPException(404, "Report not found")
    return r


def to_report_out(r: Report) -> ReportOut:
    url = verify_url_for(r.token)
    return ReportOut(
        id=r.id, token=r.token, patient=r.patient, result=r.result, indication=r.indication,
        test_name=TEST_NAME, sample_size=r.sample_size, images_analyzed=r.images_analyzed,
        total_blasts=r.total_blasts, foreign_objects=r.foreign_objects,
        max_blast_probability=r.max_blast_probability, summary=r.summary, summary_source=r.summary_source,
        findings=r.findings, model_info=r.model_info, created_at=r.created_at,
        verify_url=url, qr_code=qr_data_uri(url),
    )


@router.post("", response_model=ReportOut, status_code=201)
def create_report(body: ReportCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """'Save Results': turn a reviewed analysis session into a saved report (UUID + QR token)."""
    s = get_settings()
    patient = db.get(Patient, body.patient_id)
    if patient is None:
        raise HTTPException(404, "Patient not found")
    sess = get_session_or_404(db, body.session_id, user)
    if not sess.findings:
        raise HTTPException(400, "This session has no analysed samples")

    agg = aggregate(sess.findings, s)  # recomputed server-side: never trust client numbers
    summary, source = (sess.summary, sess.summary_source) if sess.summary else make_summary(agg, s)

    report = Report(
        patient_id=patient.id, summary=summary, summary_source=source or "template",
        findings=sess.findings, model_info=request_model_info(), **agg,
    )
    db.add(report)
    db.delete(sess)
    db.commit()
    db.refresh(report)
    return to_report_out(_get_or_404(db, report.id))


_model_info: dict = {}


def request_model_info() -> dict:
    return dict(_model_info)


def set_model_info(info: dict) -> None:
    _model_info.clear()
    _model_info.update(info)


@router.get("", response_model=list[ReportListItem])
def list_reports(
    patient_id: str | None = None,
    limit: int = Query(500, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    # findings (heavy base64 images) are not loaded for the list view
    stmt = (
        select(Report)
        .options(joinedload(Report.patient), defer(Report.findings))
        .order_by(Report.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if patient_id:
        stmt = stmt.where(Report.patient_id == patient_id)
    rows = db.scalars(stmt).unique().all()
    return [
        ReportListItem(
            id=r.id, token=r.token, patient_id=r.patient_id, patient_name=r.patient.name, result=r.result,
            indication=r.indication, total_blasts=r.total_blasts, foreign_objects=r.foreign_objects,
            images_analyzed=r.images_analyzed, created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: str, db: Session = Depends(get_db)):
    return to_report_out(_get_or_404(db, report_id))


@router.get("/{report_id}/qr.png")
def get_report_qr(report_id: str, db: Session = Depends(get_db)):
    r = _get_or_404(db, report_id)
    return Response(qr_png_bytes(verify_url_for(r.token)), media_type="image/png")


@router.get("/{report_id}/pdf")
def get_report_pdf(report_id: str, db: Session = Depends(get_db)):
    r = _get_or_404(db, report_id)
    pdf = build_report_pdf(r, get_facility(db), verify_url_for(r.token))
    name = "".join(c if c.isalnum() else "_" for c in r.patient.name)[:40]
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="LeukNet_Report_{name}_{r.created_at:%Y%m%d}.pdf"'})


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: str, db: Session = Depends(get_db)):
    db.delete(_get_or_404(db, report_id))
    db.commit()
    return Response(status_code=204)
