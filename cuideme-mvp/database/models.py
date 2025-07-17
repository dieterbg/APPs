from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Professional(Base):
    __tablename__ = "professionals"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    status = Column(String, default="automatico", nullable=False)
    
    # NOVAS COLUNAS ADICIONADAS
    altura_cm = Column(Numeric(5, 2), nullable=True)
    peso_inicial = Column(Numeric(5, 2), nullable=True)
    peso_meta = Column(Numeric(5, 2), nullable=True)
    
    messages = relationship("Message", back_populates="patient")
    metrics = relationship("Metric", back_populates="patient")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    text = Column(String, nullable=False)
    sender = Column(String, default="patient") 
    has_alert = Column(Boolean, default=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    ai_suggestion = Column(Text, nullable=True)

    patient = relationship("Patient", back_populates="messages")

class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    metric_type = Column(String, nullable=False)
    value = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("Patient", back_populates="metrics")