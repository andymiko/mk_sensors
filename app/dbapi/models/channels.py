from sqlalchemy import BigInteger, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.dbapi.base import Base


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
