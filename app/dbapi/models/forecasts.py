import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base


class Forecast(Base):
    __tablename__ = "forecasts"
    __table_args__ = (
        Index("ix_forecasts_object_created", "object_id", "created_at"),
        Index("ix_forecasts_channel_created", "channel_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("events.id", ondelete="RESTRICT"), unique=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("channels.id", ondelete="RESTRICT"), nullable=False)
    object_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("objects.id", ondelete="RESTRICT"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    model_key: Mapped[str] = mapped_column(String(30), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    forecast_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    target_from: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    target_until: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float)
    threshold: Mapped[float | None] = mapped_column(Float)
    warning: Mapped[bool | None] = mapped_column(Boolean)
