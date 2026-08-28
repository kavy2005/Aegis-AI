import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Text, JSON
)
from sqlalchemy.orm import relationship

from app.database.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient_profile = relationship("Patient", back_populates="user", uselist=False)


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)  # "male" | "female" | "other" | None
    pregnant = Column(Boolean, default=False)
    known_conditions = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    lifestyle_notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="patient_profile")
    reports = relationship("Report", back_populates="patient")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    filename = Column(String, nullable=False)
    language = Column(String, default="en")
    raw_text = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_demo = Column(Boolean, default=False)

    patient = relationship("Patient", back_populates="reports")
    parameters = relationship("ExtractedParameter", back_populates="report", cascade="all, delete-orphan")
    assessment = relationship("RiskAssessment", back_populates="report", uselist=False, cascade="all, delete-orphan")


class ExtractedParameter(Base):
    __tablename__ = "extracted_parameters"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    raw_label = Column(String, nullable=False)
    canonical_parameter = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)
    reference_source = Column(String, nullable=True)
    flag = Column(String, nullable=True)  # normal | high | low | unrecognized
    severity = Column(Integer, nullable=True)
    user_corrected = Column(Boolean, default=False)

    report = relationship("Report", back_populates="parameters")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    score = Column(Integer, nullable=False)
    level = Column(Integer, nullable=False)
    label = Column(String, nullable=False)
    abnormal_count = Column(Integer, default=0)
    critical_breach = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    explanation_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    report = relationship("Report", back_populates="assessment")
