from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Patient
from ..schemas import PatientCreate, PatientOut, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


def _get_or_404(db: Session, patient_id: str) -> Patient:
    p = db.get(Patient, patient_id)
    if p is None:
        raise HTTPException(404, "Patient not found")
    return p


@router.get("", response_model=list[PatientOut])
def list_patients(
    q: str | None = Query(None, description="Search by name or contact"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    stmt = select(Patient).order_by(Patient.created_at.desc()).limit(limit).offset(offset)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Patient.name.ilike(like), Patient.contact.ilike(like)))
    return db.scalars(stmt).all()


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(body: PatientCreate, db: Session = Depends(get_db)):
    p = Patient(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    return _get_or_404(db, patient_id)


@router.put("/{patient_id}", response_model=PatientOut)
def update_patient(patient_id: str, body: PatientUpdate, db: Session = Depends(get_db)):
    p = _get_or_404(db, patient_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{patient_id}", status_code=204)
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    p = _get_or_404(db, patient_id)
    db.delete(p)  # cascades to the patient's reports
    db.commit()
    return Response(status_code=204)
