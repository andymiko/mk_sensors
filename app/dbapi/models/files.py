import uuid

from sqlalchemy import BigInteger, ForeignKey, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.dbapi.base import Base, get_async_db_context
from app.schemas.files import FileModel


class File(Base):
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    path: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_type: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="stored", nullable=False)
    user = relationship("User", back_populates="files")


class FileRepository:
    async def page(self, *, page: int, page_size: int, user_id: str | None = None, search: str | None = None, db: AsyncSession | None = None) -> tuple[list[FileModel], int]:
        async with get_async_db_context(db) as session:
            filters = []
            if user_id:
                filters.append(File.user_id == user_id)
            if search:
                filters.append(File.original_name.ilike(f"%{search.strip()}%"))
            total = await session.scalar(select(func.count()).select_from(File).where(*filters))
            rows = (await session.scalars(select(File).where(*filters).order_by(File.created_at.desc()).offset((page - 1) * page_size).limit(page_size))).all()
            return [FileModel.model_validate(row) for row in rows], int(total or 0)


Files = FileRepository()
