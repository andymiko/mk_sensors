from datetime import datetime, timezone
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import BigInteger, create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncAttrs,
)
from sqlalchemy.orm import (
    sessionmaker,
    DeclarativeBase,
    Mapped,
    mapped_column,
    class_mapper,
)

from app.config import settings


SYNC_DB_URL = settings.sync_db_url
ASYNC_DB_URL = settings.async_db_url

async_engine = create_async_engine(ASYNC_DB_URL)
async_session = async_sessionmaker(async_engine, expire_on_commit=False)

sync_engine = create_engine(SYNC_DB_URL, pool_pre_ping=True)
sync_session = sessionmaker(sync_engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    created_at: Mapped[int] = mapped_column(
        BigInteger,
        default=lambda: int(datetime.now(timezone.utc).timestamp()),
        server_default=text("EXTRACT(EPOCH FROM now())::bigint"),
    )

    updated_at: Mapped[int] = mapped_column(
        BigInteger,
        default=lambda: int(datetime.now(timezone.utc).timestamp()),
        onupdate=lambda: int(datetime.now(timezone.utc).timestamp()),
        server_default=text("EXTRACT(EPOCH FROM now())::bigint"),
    )

    def to_dict(self) -> dict:
        columns = class_mapper(self.__class__).columns
        result = {}

        for column in columns:
            key = column.key
            value = getattr(self, key)

            attr = getattr(self.__class__, key, None)
            if isinstance(attr, property):
                continue

            result[key] = value

        if hasattr(self, 'role_codes'):
            result['role_codes'] = self.role_codes

        if hasattr(self, 'permission_codes'):
            result['permission_codes'] = self.permission_codes

        return result

    def __repr__(self):
        attrs = ', '.join(
            f"{key}={value}"
            for key, value in self.to_dict().items()
        )

        return f"<{self.__class__.__name__}({attrs})>"


def get_session():
    db = sync_session()
    try:
        yield db
    finally:
        db.close()

get_db = contextmanager(get_session)

async def get_async_session():
    async with async_session() as db:
        try:
            yield db
        finally:
            await db.close()

@asynccontextmanager
async def get_async_db():
    async with async_session() as db:
        try:
            yield db
        finally:
            await db.close()

@asynccontextmanager
async def get_async_db_context(db: AsyncSession | None = None):
    if isinstance(db, AsyncSession):
        yield db
    else:
        async with get_async_db() as session:
            yield session
