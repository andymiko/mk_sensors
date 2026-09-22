from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models import Channel, Event, Object, User
from app.dbapi.models.access import District
from app.rbac import accessible_channels, accessible_events, accessible_objects
from app.schemas.access import (
    ChannelRead, EventRead, ObjectDetails, ObjectRead, ObjectUpdate, Page,
    SensorState, TerritoryRead,
)

router = APIRouter(tags=["objects"])
Db = Annotated[AsyncSession, Depends(get_async_session)]
ObjectViewer = Annotated[User, Depends(require_permission("object.view"))]
ChannelViewer = Annotated[User, Depends(require_permission("channel.view"))]
EventViewer = Annotated[User, Depends(require_permission("event.view"))]
ObjectEditor = Annotated[User, Depends(require_permission("object.edit"))]


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
    sort_by: Literal["id", "dispatch_name", "object_type", "hierarchy_level", "district_name"] = "id",
    sort_order: Literal["asc", "desc"] = "asc",
    search: str | None = Query(default=None, max_length=255),
    district_id: str | None = Query(default=None, max_length=36),
):
    base_query = accessible_objects(user.id)
    if search and search.strip():
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        base_query = base_query.where(Object.dispatch_name.ilike(f"%{escaped}%", escape="\\"))
    if district_id:
        base_query = base_query.where(Object.district_id == district_id)
    base = base_query.subquery()
    sort_column = District.name if sort_by == "district_name" else getattr(base.c, sort_by)
    ordering = sort_column.desc() if sort_order == "desc" else sort_column.asc()
    query = (
        select(*[base.c[column.name] for column in Object.__table__.columns], District.name.label("district_name"))
        .outerjoin(District, District.id == base.c.district_id)
        .order_by(ordering.nullslast(), base.c.id)
    )
    total = await db.scalar(select(func.count()).select_from(base))
    rows = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).mappings().all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/objects/districts", response_model=list[TerritoryRead])
async def list_object_districts(db: Db, user: ObjectViewer):
    accessible_ids = accessible_objects(user.id).with_only_columns(Object.id)
    return (await db.execute(
        select(District.id, District.code, District.name)
        .join(Object, Object.district_id == District.id)
        .where(Object.id.in_(accessible_ids))
        .distinct()
        .order_by(District.name)
    )).mappings().all()


def _ranked_events():
    return select(
        Event.id,
        Event.channel_id,
        Event.event_at,
        Event.is_alarm,
        Event.sensor_value,
        func.row_number().over(
            partition_by=Event.channel_id,
            order_by=(Event.event_at.desc(), Event.id.desc()),
        ).label("position"),
    ).subquery()


async def _object_details(db: AsyncSession, object_ids: list[int]) -> list[ObjectDetails]:
    if not object_ids:
        return []
    latest = _ranked_events()
    rows = (await db.execute(
        select(
            *Object.__table__.columns,
            District.name.label("district_name"),
            Channel.id.label("channel_id"),
            Channel.sensor_name,
            Channel.sensor_type,
            latest.c.sensor_value,
            latest.c.is_alarm,
            latest.c.event_at,
        )
        .select_from(Object)
        .outerjoin(District, District.id == Object.district_id)
        .outerjoin(Channel, Channel.object_id == Object.id)
        .outerjoin(latest, and_(latest.c.channel_id == Channel.id, latest.c.position == 1))
        .where(Object.id.in_(object_ids))
        .order_by(Object.dispatch_name, Object.id, Channel.sensor_name, Channel.id)
    )).mappings().all()
    grouped = {}
    for row in rows:
        item = grouped.setdefault(row["id"], {
            **{column.name: row[column.name] for column in Object.__table__.columns},
            "district_name": row["district_name"],
            "sensors": [],
        })
        if row["channel_id"] is not None:
            status = "Нет данных" if row["is_alarm"] is None else "Тревога" if row["is_alarm"] else "Норма"
            item["sensors"].append(SensorState(
                channel_id=row["channel_id"], sensor_name=row["sensor_name"],
                sensor_type=row["sensor_type"], sensor_value=row["sensor_value"],
                is_alarm=row["is_alarm"], status=status, event_at=row["event_at"],
            ))
    result = []
    for item in grouped.values():
        non_normal = sum(sensor.is_alarm is not False for sensor in item["sensors"])
        total = len(item["sensors"])
        if non_normal == 0:
            status, color = "Норма", "green"
        elif total and non_normal / total > 0.3:
            status, color = "Критический", "red"
        else:
            status, color = "Внимание", "orange"
        result.append(ObjectDetails(**item, status=status, status_color=color))
    return result


@router.get("/objects/map", response_model=list[ObjectDetails])
async def list_map_objects(db: Db, user: ObjectViewer):
    object_ids = list(await db.scalars(accessible_objects(user.id).with_only_columns(Object.id)))
    return await _object_details(db, object_ids)


@router.get("/objects/{object_id}/details", response_model=ObjectDetails)
async def get_object_details(object_id: int, db: Db, user: ObjectViewer):
    visible_id = await db.scalar(accessible_objects(user.id).with_only_columns(Object.id).where(Object.id == object_id))
    if visible_id is None:
        raise HTTPException(404, "Объект не найден")
    return (await _object_details(db, [object_id]))[0]


@router.put("/objects/{object_id}", response_model=ObjectRead)
async def update_object(object_id: int, payload: ObjectUpdate, db: Db, user: ObjectEditor):
    obj = await db.scalar(accessible_objects(user.id, "object.edit").where(Object.id == object_id))
    if obj is None:
        raise HTTPException(404, "Объект не найден")
    if payload.district_id and await db.get(District, payload.district_id) is None:
        raise HTTPException(422, "Неизвестный район")
    for field, value in payload.model_dump().items():
        setattr(obj, field, value)
    await db.commit()
    district_name = await db.scalar(select(District.name).where(District.id == obj.district_id))
    return ObjectRead.model_validate({**payload.model_dump(), "id": obj.id, "parent_id": obj.parent_id, "district_name": district_name})


@router.get("/objects/{object_id}", response_model=ObjectRead)
async def get_object(object_id: int, db: Db, user: ObjectViewer):
    details = await get_object_details(object_id, db, user)
    if details is None:
        raise HTTPException(404, "Объект не найден")
    return details


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
            Object.dispatch_name.label("object_name"),
            Event.event_at,
            Event.is_alarm,
            Event.sensor_value,
            Channel.sensor_type,
            Channel.sensor_name,
        )
        .join(Channel, Channel.id == Event.channel_id)
        .join(Object, Object.id == Channel.object_id)
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
