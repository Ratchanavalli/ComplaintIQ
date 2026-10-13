"""
Database models for the Customer Complaint Intelligence System.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Boolean, create_engine
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/complaints.db")


class Base(DeclarativeBase):
    pass


class User(Base):
    """Application user — customer or manager."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), nullable=False, default="customer")
    full_name = Column(String(150))
    email = Column(String(150))

    # Relationship back-populated by Complaint.assignee
    managed_complaints = relationship(
        "Complaint",
        foreign_keys="Complaint.assigned_to",
        back_populates="assignee",
    )


class Complaint(Base):
    """Core complaint record."""
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(String(50), nullable=False)
    customer_name = Column(String(100))
    email = Column(String(150))
    complaint_text = Column(Text, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    channel = Column(String(50))          # email, chat, phone, web
    product_id = Column(String(50))
    order_id = Column(String(50))

    # Analysis results (populated after processing)
    category = Column(String(50))         # delivery, refund, quality, service, other
    sentiment = Column(String(20))        # positive, neutral, negative
    sentiment_score = Column(Float)       # -1.0 to +1.0
    priority_level = Column(String(20))   # critical, high, medium, low
    priority_score = Column(Float)        # 0–100
    cluster_id = Column(Integer, ForeignKey("clusters.id"), nullable=True)
    is_processed = Column(Boolean, default=False)

    # Status & assignment (FEAT-001 additions)
    status = Column(String(30), default="open", nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    cluster = relationship("Cluster", back_populates="complaints")
    assignee = relationship(
        "User",
        foreign_keys=[assigned_to],
        back_populates="managed_complaints",
    )
    responses = relationship("ComplaintResponse", backref="complaint", lazy="dynamic")
    notes = relationship("InternalNote", backref="complaint", lazy="dynamic")


class ComplaintResponse(Base):
    """Visible response from a manager to a customer complaint."""
    __tablename__ = "complaint_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    manager_id = Column(Integer, ForeignKey("users.id"))
    response_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_visible_to_customer = Column(Boolean, default=True)


class InternalNote(Base):
    """Private internal note on a complaint — not visible to customers."""
    __tablename__ = "internal_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    manager_id = Column(Integer, ForeignKey("users.id"))
    note_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Cluster(Base):
    """Groups of similar complaints."""
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(200))           # auto-generated theme label
    category = Column(String(50))
    complaint_count = Column(Integer, default=0)
    avg_sentiment_score = Column(Float)
    avg_priority_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    complaints = relationship("Complaint", back_populates="cluster")


class ProcessingLog(Base):
    """Audit trail for every analysis run."""
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    step = Column(String(50))             # categorization, sentiment, grouping, priority
    status = Column(String(20))           # success, error
    detail = Column(Text)
    processed_at = Column(DateTime, default=datetime.utcnow)


# ── Engine & session factory ──────────────────────────────────────────────────

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Yield a database session (use as a context manager or dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    # Ensure the data directory exists
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)
    print("Database initialised.")
