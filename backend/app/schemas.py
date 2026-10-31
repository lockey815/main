from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- Patients ----------
class PatientBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    gender: Literal["Male", "Female", "Other"]
    age: int = Field(ge=0, le=130)
    contact: str = Field(default="", max_length=100)
    address: str = Field(default="", max_length=300)


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    gender: Optional[Literal["Male", "Female", "Other"]] = None
    age: Optional[int] = Field(default=None, ge=0, le=130)
    contact: Optional[str] = Field(default=None, max_length=100)
    address: Optional[str] = Field(default=None, max_length=300)


class PatientOut(PatientBase, ORM):
    id: str
    created_at: datetime


# ---------- Auth ----------
class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str


# ---------- Predictions / sessions / reports ----------
Status = Literal["normal", "blast_detected", "unknown"]


class Finding(BaseModel):
    filename: str
    blast_count: int
    tiles_analyzed: int
    max_blast_probability: float
    mean_blast_probability: float
    foreign_objects: int = 0
    status: Status
    note: str = ""
    annotated_image: str = ""  # data URI (JPEG)
    original_image: str = ""   # small preview, present only while reviewing


class Aggregate(BaseModel):
    result: Status
    indication: str = ""  # acute | chronic | ""
    sample_size: int
    images_analyzed: int
    total_blasts: int
    foreign_objects: int
    max_blast_probability: float
    summary: str = ""
    summary_source: str = ""


class PredictionOut(BaseModel):
    session_id: str
    findings: list[Finding]  # findings of THIS request
    aggregate: Aggregate     # running totals of the whole session
    model_info: dict


class ReportCreate(BaseModel):
    patient_id: str
    session_id: str


class ReportListItem(BaseModel):
    id: str
    token: str
    patient_id: str
    patient_name: str
    result: str
    indication: str
    total_blasts: int
    foreign_objects: int
    images_analyzed: int
    created_at: datetime


class ReportOut(BaseModel):
    id: str
    token: str
    patient: PatientOut
    result: str
    indication: str
    test_name: str
    sample_size: int
    images_analyzed: int
    total_blasts: int
    foreign_objects: int
    max_blast_probability: float
    summary: str
    summary_source: str
    findings: list[Finding]
    model_info: dict
    created_at: datetime
    verify_url: str
    qr_code: str  # data URI (PNG)


class VerifyOut(BaseModel):
    valid: bool
    report_id: Optional[str] = None
    patient_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    test_name: Optional[str] = None
    result: Optional[str] = None
    indication: Optional[str] = None
    total_blasts: Optional[int] = None
    foreign_objects: Optional[int] = None
    images_analyzed: Optional[int] = None
    summary: Optional[str] = None
    issued_at: Optional[datetime] = None
    facility_name: Optional[str] = None


# ---------- Settings ----------
class SettingsBase(BaseModel):
    facility_name: str = Field(default="Your Facility Name", max_length=200)
    address: str = Field(default="", max_length=300)
    contact: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=200)
    logo_data_url: str = Field(default="", max_length=700_000)
    report_footer: str = Field(default="", max_length=500)


class SettingsOut(SettingsBase, ORM):
    pass
