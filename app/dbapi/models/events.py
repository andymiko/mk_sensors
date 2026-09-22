from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Text, TIMESTAMP, true
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id", name="fk_events_channel"), nullable=False
    )
    event_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=False), nullable=False)
    is_alarm: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sensor_value: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("idx_events_channel_time", "channel_id", "event_at"),
        Index("idx_events_event_at", "event_at"),
        Index("idx_events_alarm_time", "event_at", postgresql_where=is_alarm == true()),
    )
