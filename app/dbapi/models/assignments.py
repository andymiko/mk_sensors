import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed')", name="ck_assignments_status"),
        UniqueConstraint("object_id", "scheduled_date", name="uq_assignments_object_date"),
        Index("ix_assignments_technician_status", "technician_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    object_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("objects.id", ondelete="RESTRICT"), nullable=False)
    channel_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="RESTRICT"))
    technician_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    dispatcher_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AssignmentItem(Base):
    __tablename__ = "assignment_items"
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed')", name="ck_assignment_items_status"),
        ForeignKeyConstraint(["assignment_id"], ["assignments.id"], ondelete="CASCADE"),
    )

    assignment_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id", ondelete="RESTRICT"), primary_key=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
