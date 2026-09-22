from sqlalchemy import BigInteger, CheckConstraint, Double, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base
from app.dbapi.models.crud import UNSET, CrudTable, UnsetType


class Object(Base):
    __tablename__ = "objects"
    __table_args__ = (
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_objects_longitude"),
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_objects_latitude"),
        Index("idx_objects_parent_id", "parent_id"),
        Index("idx_objects_type", "object_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    hierarchy_level: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    district_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("districts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    object_type: Mapped[str] = mapped_column(String(100), nullable=False)
    dispatch_name: Mapped[str] = mapped_column(Text, nullable=False)

    longitude: Mapped[float | None] = mapped_column(Double, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Double, nullable=True)


class ObjectsTable(CrudTable[Object]):
    model = Object

    async def insert_new_object(
        self,
        *,
        id: int,
        hierarchy_level: int,
        object_type: str,
        dispatch_name: str,
        parent_id: int | None = None,
        district_id: str | None = None,
        longitude: float | None = None,
        latitude: float | None = None,
        db: AsyncSession | None = None,
    ) -> Object:
        return await self._insert(Object(
            id=id,
            hierarchy_level=hierarchy_level,
            parent_id=parent_id,
            district_id=district_id,
            object_type=object_type,
            dispatch_name=dispatch_name,
            longitude=longitude,
            latitude=latitude,
        ), db)

    async def get_object_by_id(self, id: int, db: AsyncSession | None = None) -> Object | None:
        return await self._get_by_id(id, db)

    async def get_objects_page(
        self, *, offset: int = 0, limit: int = 100, db: AsyncSession | None = None,
    ) -> tuple[list[Object], int]:
        return await self._get_page(offset=offset, limit=limit, db=db)

    async def update_object_by_id(
        self,
        id: int,
        *,
        hierarchy_level: int | UnsetType = UNSET,
        parent_id: int | None | UnsetType = UNSET,
        district_id: str | None | UnsetType = UNSET,
        object_type: str | UnsetType = UNSET,
        dispatch_name: str | UnsetType = UNSET,
        longitude: float | None | UnsetType = UNSET,
        latitude: float | None | UnsetType = UNSET,
        db: AsyncSession | None = None,
    ) -> Object | None:
        return await self._update_by_id(id, {
            "hierarchy_level": hierarchy_level,
            "parent_id": parent_id,
            "district_id": district_id,
            "object_type": object_type,
            "dispatch_name": dispatch_name,
            "longitude": longitude,
            "latitude": latitude,
        }, db)

    async def delete_object_by_id(self, id: int, db: AsyncSession | None = None) -> bool:
        return await self._delete_by_id(id, db)


Objects = ObjectsTable()
