from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import FacilitySettings
from ..schemas import SettingsBase, SettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])


def get_facility(db: Session) -> FacilitySettings:
    row = db.get(FacilitySettings, 1)
    if row is None:
        row = FacilitySettings(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db)):
    return get_facility(db)


@router.put("", response_model=SettingsOut)
def update_settings(body: SettingsBase, db: Session = Depends(get_db)):
    if body.logo_data_url and not body.logo_data_url.startswith("data:image/"):
        raise HTTPException(422, "logo_data_url must be an image data URL (data:image/...).")
    row = get_facility(db)
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row
