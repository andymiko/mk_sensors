"""Territories and role-specific resource assignments."""
import uuid

from sqlalchemy import BigInteger, Column, ForeignKey, ForeignKeyConstraint, String, Table
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base


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
