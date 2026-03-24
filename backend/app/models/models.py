"""SQLAlchemy ORM Models for NexusSearch."""
import uuid
import enum
from typing import Optional, List
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.database import Base


class SearchType(str, enum.Enum):
    PSEUDO = "pseudo"
    EMAIL = "email"
    NAME = "name"
    DOMAIN = "domain"
    PHONE = "phone"
    IP = "ip"
    EXIF = "exif"


class SearchStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    searches: Mapped[List["SearchJob"]] = relationship("SearchJob", back_populates="user")


class SearchJob(Base):
    """Represents a single investigation task."""
    __tablename__ = "search_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    query: Mapped[str] = mapped_column(String(255))
    search_type: Mapped[SearchType] = mapped_column(SAEnum(SearchType))
    status: Mapped[SearchStatus] = mapped_column(SAEnum(SearchStatus), default=SearchStatus.PENDING)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="searches")
    results: Mapped[List["SearchResult"]] = relationship("SearchResult", back_populates="job")


class SearchResult(Base):
    """A single result item found for a search job."""
    __tablename__ = "search_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("search_jobs.id"))
    source: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    found_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped["SearchJob"] = relationship("SearchJob", back_populates="results")
