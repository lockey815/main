import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), index=True)
    gender: Mapped[str] = mapped_column(String(20))
    age: Mapped[int] = mapped_column(Integer)
    contact: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    reports: Mapped[list["Report"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class AnalysisSession(Base):
    """Server-held draft of an analysis. Results are only turned into a saved report
    from here, so a client cannot forge findings in a report that carries a QR code."""

    __tablename__ = "analysis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    findings: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_source: Mapped[str] = mapped_column(String(20), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Random, unguessable token that goes into the QR code
    token: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(ForeignKey("patients.id", ondelete="CASCADE"), index=True)

    result: Mapped[str] = mapped_column(String(40))  # normal | blast_detected | unknown
    indication: Mapped[str] = mapped_column(String(20), default="")  # acute | chronic | ""
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    images_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    total_blasts: Mapped[int] = mapped_column(Integer, default=0)
    foreign_objects: Mapped[int] = mapped_column(Integer, default=0)
    max_blast_probability: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_source: Mapped[str] = mapped_column(String(20), default="template")
    findings: Mapped[list] = mapped_column(JSON, default=list)
    model_info: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    patient: Mapped[Patient] = relationship(back_populates="reports")


class FacilitySettings(Base):
    __tablename__ = "facility_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    facility_name: Mapped[str] = mapped_column(String(200), default="Your Facility Name")
    address: Mapped[str] = mapped_column(String(300), default="")
    contact: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    logo_data_url: Mapped[str] = mapped_column(Text, default="")
    report_footer: Mapped[str] = mapped_column(
        String(500),
        default="This report is AI-assisted and must be reviewed by a qualified pathologist or hematologist.",
    )
