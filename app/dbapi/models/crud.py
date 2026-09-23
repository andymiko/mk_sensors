from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dbapi.base import Base, get_async_db_context


ModelT = TypeVar("ModelT", bound=Base)


class UnsetType:
    """Marker that distinguishes an omitted update from an explicit NULL."""


UNSET = UnsetType()


class CrudTable(Generic[ModelT]):
    model: type[ModelT]

    async def _get_by_id(self, row_id, db: AsyncSession | None = None) -> ModelT | None:
        async with get_async_db_context(db) as session:
            return await session.get(self.model, row_id)

    async def _get_page(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        db: AsyncSession | None = None,
    ) -> tuple[list[ModelT], int]:
        if offset < 0:
            raise ValueError("offset не может быть отрицательным")
        if not 1 <= limit <= 1000:
            raise ValueError("limit должен быть от 1 до 1000")
        async with get_async_db_context(db) as session:
            total = await session.scalar(select(func.count()).select_from(self.model))
            items = list(await session.scalars(
                select(self.model)
                .order_by(self.model.id)
                .offset(offset)
                .limit(limit)
            ))
            return items, int(total or 0)

    async def _insert(self, row: ModelT, db: AsyncSession | None = None) -> ModelT:
        async with get_async_db_context(db) as session:
            session.add(row)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            return row

    async def _update_by_id(
        self,
        row_id,
        values: dict,
        db: AsyncSession | None = None,
    ) -> ModelT | None:
        async with get_async_db_context(db) as session:
            row = await session.get(self.model, row_id)
            if row is None:
                return None
            try:
                for field, value in values.items():
                    if value is not UNSET:
                        setattr(row, field, value)
                await session.commit()
            except Exception:
                await session.rollback()
                session.expire_all()
                raise
            return row

    async def _delete_by_id(self, row_id, db: AsyncSession | None = None) -> bool:
        async with get_async_db_context(db) as session:
            row = await session.get(self.model, row_id)
            if row is None:
                return False
            await session.delete(row)
            try:
                await session.commit()
            except Exception:
                await session.rollback()
                session.expire_all()
                raise
            return True
