from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Sequence, Text, TIMESTAMP, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base
from app.dbapi.models.crud import UNSET, CrudTable, UnsetType


EVENT_ID_SEQUENCE = Sequence("events_ingest_id_seq")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, EVENT_ID_SEQUENCE, primary_key=True)
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


class EventsTable(CrudTable[Event]):
    model = Event

    async def insert_new_event(
        self,
        *,
        id: int,
        channel_id: int,
        event_at: datetime,
        is_alarm: bool,
        sensor_value: str | None = None,
        db: AsyncSession | None = None,
    ) -> Event:
        return await self._insert(Event(
            id=id,
            channel_id=channel_id,
            event_at=event_at,
            is_alarm=is_alarm,
            sensor_value=sensor_value,
        ), db)

    async def get_event_by_id(self, id: int, db: AsyncSession | None = None) -> Event | None:
        return await self._get_by_id(id, db)

    async def get_events_page(
        self, *, offset: int = 0, limit: int = 100, db: AsyncSession | None = None,
    ) -> tuple[list[Event], int]:
        return await self._get_page(offset=offset, limit=limit, db=db)

    async def update_event_by_id(
        self,
        id: int,
        *,
        channel_id: int | UnsetType = UNSET,
        event_at: datetime | UnsetType = UNSET,
        is_alarm: bool | UnsetType = UNSET,
        sensor_value: str | None | UnsetType = UNSET,
        db: AsyncSession | None = None,
    ) -> Event | None:
        return await self._update_by_id(id, {
            "channel_id": channel_id,
            "event_at": event_at,
            "is_alarm": is_alarm,
            "sensor_value": sensor_value,
        }, db)

    async def delete_event_by_id(self, id: int, db: AsyncSession | None = None) -> bool:
        return await self._delete_by_id(id, db)


Events = EventsTable()
