from collections.abc import Sequence
import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Table,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base, get_async_db_context
from app.dbapi.models.crud import UNSET, CrudTable, UnsetType


district_divisions = Table(
    "district_divisions",
    Base.metadata,
    Column("district_id", String(36), ForeignKey("districts.id", ondelete="CASCADE"), primary_key=True),
    Column("division_id", String(36), ForeignKey("divisions.id", ondelete="RESTRICT"), primary_key=True),
)

division_objects = Table(
    "division_objects",
    Base.metadata,
    Column("division_id", String(36), ForeignKey("divisions.id", ondelete="CASCADE"), primary_key=True),
    Column("object_id", BigInteger, ForeignKey("objects.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_division_objects_object_id", "object_id"),
)

user_divisions = Table(
    "user_divisions",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("division_id", String(36), ForeignKey("divisions.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_user_divisions_division_id", "division_id"),
)


class Division(Base):
    __tablename__ = "divisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))


class District(Base):
    __tablename__ = "districts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    division_id: Mapped[str] = mapped_column(ForeignKey("divisions.id", ondelete="RESTRICT"), index=True)


class DivisionsTable(CrudTable[Division]):
    model = Division

    async def insert_new_division(
        self,
        code: str,
        name: str,
        db: AsyncSession | None = None,
    ) -> Division:
        """Create and commit a division; database conflicts are propagated."""
        return await self._insert(Division(code=code, name=name), db)

    async def get_division_by_id(self, id: str, db: AsyncSession | None = None) -> Division | None:
        return await self._get_by_id(id, db)

    async def get_division_by_code(self, code: str, db: AsyncSession | None = None) -> Division | None:
        async with get_async_db_context(db) as session:
            return await session.scalar(select(Division).where(Division.code == code))

    async def get_divisions_page(
        self, *, offset: int = 0, limit: int = 100, db: AsyncSession | None = None,
    ) -> tuple[list[Division], int]:
        return await self._get_page(offset=offset, limit=limit, db=db)

    async def update_division_by_id(
        self,
        id: str,
        *,
        code: str | UnsetType = UNSET,
        name: str | UnsetType = UNSET,
        db: AsyncSession | None = None,
    ) -> Division | None:
        return await self._update_by_id(id, {"code": code, "name": name}, db)

    async def delete_division_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        return await self._delete_by_id(id, db)


class DistrictsTable(CrudTable[District]):
    model = District

    async def insert_new_district(
        self,
        code: str,
        name: str,
        division_ids: Sequence[str],
        primary_division_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> District:

        unique_division_ids = tuple(dict.fromkeys(division_ids))
        if not unique_division_ids:
            raise ValueError("Укажите хотя бы одно подразделение")
        if primary_division_id is not None and primary_division_id not in unique_division_ids:
            raise ValueError("Основное подразделение должно входить в division_ids")

        async with get_async_db_context(db) as session:
            existing_ids = set(await session.scalars(
                select(Division.id).where(Division.id.in_(unique_division_ids))
            ))
            missing_ids = sorted(set(unique_division_ids) - existing_ids)
            if missing_ids:
                raise ValueError(f"Неизвестные подразделения: {', '.join(missing_ids)}")

            district = District(
                code=code,
                name=name,
                division_id=primary_division_id or unique_division_ids[0],
            )
            session.add(district)
            try:
                await session.flush()
                await session.execute(insert(district_divisions), [
                    {"district_id": district.id, "division_id": division_id}
                    for division_id in unique_division_ids
                ])
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return district

    async def get_district_by_id(self, id: str, db: AsyncSession | None = None) -> District | None:
        return await self._get_by_id(id, db)

    async def get_district_by_code(self, code: str, db: AsyncSession | None = None) -> District | None:
        async with get_async_db_context(db) as session:
            return await session.scalar(select(District).where(District.code == code))

    async def get_districts_page(
        self, *, offset: int = 0, limit: int = 100, db: AsyncSession | None = None,
    ) -> tuple[list[District], int]:
        return await self._get_page(offset=offset, limit=limit, db=db)

    async def update_district_by_id(
        self,
        id: str,
        *,
        code: str | UnsetType = UNSET,
        name: str | UnsetType = UNSET,
        division_ids: Sequence[str] | UnsetType = UNSET,
        primary_division_id: str | UnsetType = UNSET,
        db: AsyncSession | None = None,
    ) -> District | None:
        async with get_async_db_context(db) as session:
            district = await session.get(District, id)
            if district is None:
                return None
            try:
                if code is not UNSET:
                    district.code = code
                if name is not UNSET:
                    district.name = name

                if division_ids is not UNSET:
                    unique_ids = tuple(dict.fromkeys(division_ids))
                    if not unique_ids:
                        raise ValueError("Укажите хотя бы одно подразделение")
                    await self._validate_division_ids(session, unique_ids)
                    if primary_division_id is not UNSET and primary_division_id not in unique_ids:
                        raise ValueError("Основное подразделение должно входить в division_ids")
                    district.division_id = (
                        primary_division_id
                        if primary_division_id is not UNSET
                        else district.division_id if district.division_id in unique_ids else unique_ids[0]
                    )
                    await session.execute(
                        district_divisions.delete().where(district_divisions.c.district_id == id)
                    )
                    await session.execute(insert(district_divisions), [
                        {"district_id": id, "division_id": division_id}
                        for division_id in unique_ids
                    ])
                elif primary_division_id is not UNSET:
                    linked_ids = set(await session.scalars(
                        select(district_divisions.c.division_id)
                        .where(district_divisions.c.district_id == id)
                    ))
                    if primary_division_id not in linked_ids:
                        raise ValueError("Основное подразделение должно быть связано с районом")
                    district.division_id = primary_division_id

                await session.commit()
            except Exception:
                await session.rollback()
                session.expire_all()
                raise
            return district

    async def delete_district_by_id(self, id: str, db: AsyncSession | None = None) -> bool:
        return await self._delete_by_id(id, db)

    @staticmethod
    async def _validate_division_ids(session: AsyncSession, division_ids: Sequence[str]) -> None:
        existing_ids = set(await session.scalars(
            select(Division.id).where(Division.id.in_(division_ids))
        ))
        missing_ids = sorted(set(division_ids) - existing_ids)
        if missing_ids:
            raise ValueError(f"Неизвестные подразделения: {', '.join(missing_ids)}")


def _assignment_table(name, resource_column, resource_type, target):
    return Table(
        name,
        Base.metadata,
        Column("user_id", String(36), primary_key=True),
        Column("role_id", String(36), primary_key=True),
        Column(resource_column, resource_type, ForeignKey(target, ondelete="CASCADE"), primary_key=True),
        ForeignKeyConstraint(
            ["user_id", "role_id"], ["user_roles.user_id", "user_roles.role_id"],
            ondelete="CASCADE",
        ),
    )


user_role_divisions = _assignment_table("user_role_divisions", "division_id", String(36), "divisions.id")
user_role_districts = _assignment_table("user_role_districts", "district_id", String(36), "districts.id")
user_role_objects = _assignment_table("user_role_objects", "object_id", BigInteger, "objects.id")


Divisions = DivisionsTable()
Districts = DistrictsTable()
