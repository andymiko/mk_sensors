from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models import Channel, Object, User
from app.rbac import accessible_channels, accessible_objects
from app.schemas.access import ChannelRead, ObjectRead, Page

router = APIRouter(tags=["objects"])
Db = Annotated[AsyncSession, Depends(get_async_session)]
ObjectViewer = Annotated[User, Depends(require_permission("object.view"))]
ChannelViewer = Annotated[User, Depends(require_permission("channel.view"))]


async def _page(db, query, page, page_size):
    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = (await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/objects", response_model=Page[ObjectRead])
async def list_objects(db: Db, user: ObjectViewer, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    return await _page(db, accessible_objects(user.id).order_by(Object.id), page, page_size)


@router.get("/objects/{object_id}", response_model=ObjectRead)
async def get_object(object_id: int, db: Db, user: ObjectViewer):
    obj = await db.scalar(accessible_objects(user.id).where(Object.id == object_id))
    if obj is None:
        raise HTTPException(404, "Объект не найден")
    return obj


@router.get("/channels", response_model=Page[ChannelRead])
async def list_channels(db: Db, user: ChannelViewer, object_id: int | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    query = accessible_channels(user.id).order_by(Channel.id)
    if object_id is not None:
        query = query.where(Channel.object_id == object_id)
    return await _page(db, query, page, page_size)


@router.get("/channels/{channel_id}", response_model=ChannelRead)
async def get_channel(channel_id: int, db: Db, user: ChannelViewer):
    channel = await db.scalar(accessible_channels(user.id).where(Channel.id == channel_id))
    if channel is None:
        raise HTTPException(404, "Канал не найден")
    return channel
