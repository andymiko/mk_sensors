from sqlalchemy import BigInteger, ForeignKey, Index, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base
from app.dbapi.models.crud import UNSET, CrudTable, UnsetType


class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (
        Index("idx_channels_system_type", "engineering_system_type"),
        Index("idx_channels_sensor_type", "sensor_type"),
        Index("idx_channels_tag", "engineering_system_tag"),
        Index("idx_channels_object_id", "object_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    engineering_system_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensor_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    engineering_system_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensor_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    object_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("objects.id", name="fk_channels_object"), nullable=True
    )


class ChannelsTable(CrudTable[Channel]):
    model = Channel

    async def insert_new_channel(
        self,
        *,
        id: int,
        engineering_system_type: str | None = None,
        sensor_type: str | None = None,
        engineering_system_tag: str | None = None,
        sensor_name: str | None = None,
        object_id: int | None = None,
        db: AsyncSession | None = None,
    ) -> Channel:
        return await self._insert(Channel(
            id=id,
            engineering_system_type=engineering_system_type,
            sensor_type=sensor_type,
            engineering_system_tag=engineering_system_tag,
            sensor_name=sensor_name,
            object_id=object_id,
        ), db)

    async def get_channel_by_id(self, id: int, db: AsyncSession | None = None) -> Channel | None:
        return await self._get_by_id(id, db)

    async def get_channels_page(
        self, *, offset: int = 0, limit: int = 100, db: AsyncSession | None = None,
    ) -> tuple[list[Channel], int]:
        return await self._get_page(offset=offset, limit=limit, db=db)

    async def update_channel_by_id(
        self,
        id: int,
        *,
        engineering_system_type: str | None | UnsetType = UNSET,
        sensor_type: str | None | UnsetType = UNSET,
        engineering_system_tag: str | None | UnsetType = UNSET,
        sensor_name: str | None | UnsetType = UNSET,
        object_id: int | None | UnsetType = UNSET,
        db: AsyncSession | None = None,
    ) -> Channel | None:
        return await self._update_by_id(id, {
            "engineering_system_type": engineering_system_type,
            "sensor_type": sensor_type,
            "engineering_system_tag": engineering_system_tag,
            "sensor_name": sensor_name,
            "object_id": object_id,
        }, db)

    async def delete_channel_by_id(self, id: int, db: AsyncSession | None = None) -> bool:
        return await self._delete_by_id(id, db)


Channels = ChannelsTable()
