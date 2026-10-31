from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..analysis import TEST_NAME
from ..config import get_settings
from ..database import get_db
from ..models import Report
from ..schemas import VerifyOut
from .settings import get_facility

router = APIRouter(prefix="/verify", tags=["verify"])


def _initials(name: str) -> str:
    parts = [p for p in name.replace(".", " ").split() if p]
    return ". ".join(p[0].upper() for p in parts) + "." if parts else "-"


@router.get("/{token}", response_model=VerifyOut)
def verify(token: str, db: Session = Depends(get_db)):
    """Public endpoint opened by scanning the QR code. The token is an unguessable UUID printed only on the
    report itself. With VERIFY_SHOW_FULL_DETAILS=false only the patient's initials are returned."""
    r = db.scalar(select(Report).options(joinedload(Report.patient)).where(Report.token == token))
    if r is None:
        return VerifyOut(valid=False)
    full = get_settings().verify_show_full_details
    return VerifyOut(
        valid=True, report_id=r.id,
        patient_name=r.patient.name if full else _initials(r.patient.name),
        gender=r.patient.gender, age=r.patient.age, test_name=TEST_NAME,
        result=r.result, indication=r.indication, total_blasts=r.total_blasts,
        foreign_objects=r.foreign_objects, images_analyzed=r.images_analyzed,
        summary=r.summary, issued_at=r.created_at, facility_name=get_facility(db).facility_name,
    )
