from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models import Channel, Event, Object, User
from app.rbac import accessible_channels, accessible_events, accessible_objects
from app.schemas.access import ChannelRead, EventRead, ObjectRead, Page

router = APIRouter(tags=["objects"])
Db = Annotated[AsyncSession, Depends(get_async_session)]
ObjectViewer = Annotated[User, Depends(require_permission("object.view"))]
ChannelViewer = Annotated[User, Depends(require_permission("channel.view"))]
EventViewer = Annotated[User, Depends(require_permission("event.view"))]


async def _page(db, query, page, page_size):
    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    items = (await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/objects", response_model=Page[ObjectRead])
async def list_objects(
    db: Db,
    user: ObjectViewer,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Literal["id", "dispatch_name", "object_type", "hierarchy_level"] = "id",
    sort_order: Literal["asc", "desc"] = "asc",
):
    column = getattr(Object, sort_by)
    ordering = column.desc() if sort_order == "desc" else column.asc()
    return await _page(db, accessible_objects(user.id).order_by(ordering, Object.id), page, page_size)


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


@router.get("/events", response_model=Page[EventRead])
async def list_events(
    db: Db,
    user: EventViewer,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    object_id: int | None = None,
    sensor_type: str | None = Query(None, max_length=255),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(422, "Начальная дата не может быть позже конечной")
    event_ids = accessible_events(user.id).with_only_columns(Event.id)
    query = (
        select(
            Event.id,
            Event.channel_id,
            Channel.object_id,
            Event.event_at,
            Event.is_alarm,
            Event.sensor_value,
            Channel.sensor_type,
            Channel.sensor_name,
        )
        .join(Channel, Channel.id == Event.channel_id)
        .where(Event.id.in_(event_ids))
    )
    if date_from is not None:
        query = query.where(Event.event_at >= date_from)
    if date_to is not None:
        query = query.where(Event.event_at <= date_to)
    if object_id is not None:
        query = query.where(Channel.object_id == object_id)
    if sensor_type:
        query = query.where(Channel.sensor_type == sensor_type)
    query = query.order_by(Event.event_at.desc(), Event.id.desc())
    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
    rows = (await db.execute(
        query.offset((page - 1) * page_size).limit(page_size)
    )).mappings().all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}
