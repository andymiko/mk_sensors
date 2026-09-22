from datetime import datetime, time, timedelta
from functools import partial
from typing import Annotated
from zoneinfo import ZoneInfo

from anyio import to_thread
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models import Channel, Event, Forecast, Object, User
from app.ml_models.inference import (
    load_bundle, model_for_channel, predict_failure, registered_object_id,
    supported_channels,
)
from app.rbac import accessible_channels, accessible_objects
from app.schemas.forecasts import ForecastChannelOption, ForecastCreate, ForecastRead


router = APIRouter(prefix="/forecasts", tags=["forecasts"])
Db = Annotated[AsyncSession, Depends(get_async_session)]
ForecastViewer = Annotated[User, Depends(require_permission("forecast.view"))]
ForecastCreator = Annotated[User, Depends(require_permission("forecast.create"))]
MOSCOW = ZoneInfo("Europe/Moscow")


def _moscow_naive(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(MOSCOW).replace(tzinfo=None)
    return value


def _forecast_rows():
    return (
        select(
            Forecast.id,
            Forecast.event_id,
            Event.event_at,
            Event.is_alarm,
            Event.sensor_value,
            Forecast.channel_id,
            Channel.sensor_name,
            Channel.sensor_type,
            Forecast.object_id,
            Object.dispatch_name.label("object_name"),
            Forecast.model_key,
            Forecast.model_version,
            Forecast.forecast_at,
            Forecast.target_from,
            Forecast.target_until,
            Forecast.status,
            Forecast.risk_score,
            Forecast.threshold,
            Forecast.warning,
            Forecast.created_at,
        )
        .join(Event, Event.id == Forecast.event_id)
        .join(Channel, Channel.id == Forecast.channel_id)
        .join(Object, Object.id == Forecast.object_id)
    )


@router.get("", response_model=list[ForecastRead])
async def list_forecasts(db: Db, user: ForecastViewer):
    object_ids = accessible_objects(user.id, "forecast.view").with_only_columns(Object.id)
    return (await db.execute(
        _forecast_rows()
        .where(Forecast.object_id.in_(object_ids))
        .order_by(Forecast.created_at.desc(), Forecast.id.desc())
    )).mappings().all()


@router.get("/channels", response_model=list[ForecastChannelOption])
async def list_forecast_channels(db: Db, user: ForecastCreator):
    models = await to_thread.run_sync(supported_channels)
    visible_ids = accessible_channels(user.id, "forecast.create").with_only_columns(Channel.id)
    rows = (await db.execute(
        select(
            Channel.id,
            Channel.sensor_name,
            Channel.sensor_type,
            Channel.object_id,
            Object.dispatch_name.label("object_name"),
        )
        .join(Object, Object.id == Channel.object_id)
        .where(Channel.id.in_(visible_ids), Channel.id.in_(models))
        .order_by(Object.dispatch_name, Channel.sensor_name, Channel.id)
    )).mappings().all()
    return [{**row, "model_key": models[row["id"]]} for row in rows]


@router.post("", response_model=ForecastRead, status_code=status.HTTP_201_CREATED)
async def create_forecast(payload: ForecastCreate, db: Db, user: ForecastCreator):
    channel = await db.scalar(
        accessible_channels(user.id, "forecast.create").where(Channel.id == payload.channel_id)
    )
    if channel is None or channel.object_id is None:
        raise HTTPException(404, "Доступный канал с привязанным объектом не найден")

    model_key = await to_thread.run_sync(model_for_channel, channel.id)
    if model_key is None:
        raise HTTPException(422, "Канал не поддерживается моделями насосов или вентиляции")
    bundle = await to_thread.run_sync(load_bundle, model_key)
    if registered_object_id(bundle, channel.id) != channel.object_id:
        raise HTTPException(422, "Привязка канала к объекту не соответствует версии модели")

    event_at = _moscow_naive(payload.event_at)
    forecast_at = datetime.combine(event_at.date() + timedelta(days=1), time.min)
    event = Event(
        channel_id=channel.id,
        event_at=event_at,
        is_alarm=payload.is_alarm,
        sensor_value=payload.sensor_value,
    )
    db.add(event)
    await db.flush()

    fault_times = list(await db.scalars(
        select(Event.event_at)
        .where(
            Event.channel_id == channel.id,
            Event.event_at < forecast_at,
            Event.is_alarm.is_(True),
            Event.sensor_value == "Неисправен",
        )
        .order_by(Event.event_at)
    ))
    activity_from = forecast_at - timedelta(days=bundle["activity_days"])
    has_recent_data = bool(await db.scalar(
        select(exists().where(
            Event.channel_id.in_(
                select(Channel.id).where(Channel.object_id == channel.object_id)
            ),
            Event.event_at >= activity_from,
            Event.event_at < forecast_at,
        ))
    ))
    prediction = await to_thread.run_sync(partial(
        predict_failure,
        bundle,
        channel.id,
        forecast_at,
        fault_times,
        has_recent_data,
    ))
    forecast = Forecast(
        event_id=event.id,
        channel_id=channel.id,
        object_id=channel.object_id,
        created_by=user.id,
        model_key=model_key,
        **prediction,
    )
    db.add(forecast)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Событие или прогноз уже существует") from None
    return (await db.execute(
        _forecast_rows().where(Forecast.id == forecast.id)
    )).mappings().one()
