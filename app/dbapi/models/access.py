"""Territories and role-specific resource assignments."""
import uuid

from collections.abc import Sequence

from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    Table,
    insert,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base, get_async_db_context


district_divisions = Table(
    "district_divisions",
    Base.metadata,
    Column("district_id", String(36), ForeignKey("districts.id", ondelete="CASCADE"), primary_key=True),
    Column("division_id", String(36), ForeignKey("divisions.id", ondelete="RESTRICT"), primary_key=True),
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


class DivisionsTable:
    async def insert_new_division(
        self,
        code: str,
        name: str,
        db: AsyncSession | None = None,
    ) -> Division:
        """Create and commit a division; database conflicts are propagated."""
        async with get_async_db_context(db) as session:
            division = Division(code=code, name=name)
            session.add(division)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return division


class DistrictsTable:
    async def insert_new_district(
        self,
        code: str,
        name: str,
        division_ids: Sequence[str],
        primary_division_id: str | None = None,
        db: AsyncSession | None = None,
    ) -> District:
        """Create a district and all its division links in one transaction."""
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
