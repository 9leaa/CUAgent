from datetime import datetime, timezone
import uuid
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = 'tasks'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    request_sha256: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(24), default='QUEUED', index=True)
    error_code: Mapped[str | None] = mapped_column(String(80))
    session_id: Mapped[str | None] = mapped_column(String(160))
    run_dir: Mapped[str | None] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(36))
    epoch: Mapped[int] = mapped_column(Integer, default=0)
    calls: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Attempt(Base):
    __tablename__ = 'attempts'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), index=True)
    owner: Mapped[str] = mapped_column(String(36))
    epoch: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Event(Base):
    __tablename__ = 'events'
    __table_args__ = (UniqueConstraint('task_id', 'external_id'),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    external_id: Mapped[str | None] = mapped_column(String(160))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Artifact(Base):
    __tablename__ = 'artifacts'
    __table_args__ = (UniqueConstraint('task_id', 'name'),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), index=True)
    name: Mapped[str] = mapped_column(String(40))
    sha256: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(Integer)


class Usage(Base):
    __tablename__ = 'usage'
    task_id: Mapped[str] = mapped_column(ForeignKey('tasks.id'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)


class Resource(Base):
    __tablename__ = 'resources'
    name: Mapped[str] = mapped_column(String(80), primary_key=True)
    owner: Mapped[str | None] = mapped_column(String(36))
    task_id: Mapped[str | None] = mapped_column(ForeignKey('tasks.id'))
    epoch: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
