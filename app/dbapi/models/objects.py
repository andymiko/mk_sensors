from sqlalchemy import BigInteger, CheckConstraint, Double, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base


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
