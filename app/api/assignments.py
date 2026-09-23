from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models import Assignment, AssignmentItem, Channel, Object, Role, User
from app.dbapi.models.access import division_objects, user_divisions
from app.dbapi.models.associations import user_roles
from app.rbac import accessible_objects
from app.schemas.assignments import AssignmentCreate, AssignmentRead, TechnicianOption


router = APIRouter(prefix="/assignments", tags=["assignments"])
Db = Annotated[AsyncSession, Depends(get_async_session)]
AssignmentViewer = Annotated[User, Depends(require_permission("assignment.view"))]
AssignmentCreator = Annotated[User, Depends(require_permission("assignment.create"))]
AssignmentCompleter = Annotated[User, Depends(require_permission("assignment.complete"))]


def _assignment_rows():
    technician = aliased(User)
    dispatcher = aliased(User)
    return (
        select(
            Assignment.id,
            Assignment.object_id,
            Object.dispatch_name.label("object_name"),
            Assignment.channel_id,
            Channel.sensor_name,
            Channel.sensor_type,
            Assignment.technician_id,
            technician.name.label("technician_name"),
            Assignment.dispatcher_id,
            dispatcher.name.label("dispatcher_name"),
            Assignment.scheduled_date,
            Assignment.status,
            Assignment.completed_at,
            Assignment.created_at,
        )
        .join(Object, Object.id == Assignment.object_id)
        .outerjoin(Channel, Channel.id == Assignment.channel_id)
        .join(technician, technician.id == Assignment.technician_id)
        .join(dispatcher, dispatcher.id == Assignment.dispatcher_id)
    )


async def _read_assignment(db: AsyncSession, assignment_id: str):
    row = (await db.execute(
        _assignment_rows().where(Assignment.id == assignment_id)
    )).mappings().one()
    return (await _with_sensors(db, [row]))[0]


async def _with_sensors(db: AsyncSession, rows) -> list[dict]:
    items = [dict(row) for row in rows]
    sensors_by_assignment: dict[str, list[dict]] = {
        item["id"]: [] for item in items
    }
    if items:
        channels = await db.execute(
            select(
                AssignmentItem.assignment_id,
                Channel.id,
                Channel.sensor_name,
                Channel.sensor_type,
                AssignmentItem.status,
                AssignmentItem.completed_at,
            )
            .join(Channel, Channel.id == AssignmentItem.channel_id)
            .where(AssignmentItem.assignment_id.in_(sensors_by_assignment))
            .order_by(AssignmentItem.assignment_id, Channel.sensor_name, Channel.id)
        )
        for assignment_id, channel_id, sensor_name, sensor_type, item_status, completed_at in channels:
            sensors_by_assignment[assignment_id].append({
                "id": channel_id,
                "name": sensor_name,
                "type": sensor_type,
                "status": item_status,
                "completed_at": completed_at,
            })
    for item in items:
        item["sensors"] = sensors_by_assignment[item["id"]]
    return items


@router.get("", response_model=list[AssignmentRead])
async def list_assignments(db: Db, user: AssignmentViewer):
    object_ids = accessible_objects(user.id).with_only_columns(Object.id)
    query = _assignment_rows().where(Assignment.object_id.in_(object_ids))
    if (
        not user.is_admin()
        and user.has_permission("assignment.complete")
        and not user.has_permission("assignment.create")
    ):
        query = query.where(Assignment.technician_id == user.id)
    rows = (await db.execute(
        query.order_by(Assignment.scheduled_date.desc(), Assignment.created_at.desc())
    )).mappings().all()
    return await _with_sensors(db, rows)


@router.get("/technicians", response_model=list[TechnicianOption])
async def list_technicians(object_id: int, db: Db, user: AssignmentCreator):
    visible = await db.scalar(
        accessible_objects(user.id).with_only_columns(Object.id).where(Object.id == object_id)
    )
    if visible is None:
        raise HTTPException(404, "Объект не найден")
    object_divisions = select(division_objects.c.division_id).where(
        division_objects.c.object_id == object_id
    )
    return (await db.execute(
        select(User.id, User.name, User.email)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .join(user_divisions, user_divisions.c.user_id == User.id)
        .where(
            User.is_active.is_(True),
            Role.code == "technician",
            user_divisions.c.division_id.in_(object_divisions),
        )
        .distinct()
        .order_by(User.name, User.id)
    )).mappings().all()


@router.post("", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(payload: AssignmentCreate, db: Db, user: AssignmentCreator):
    visible = await db.scalar(
        accessible_objects(user.id).with_only_columns(Object.id).where(Object.id == payload.object_id)
    )
    if visible is None:
        raise HTTPException(404, "Объект не найден")
    if payload.channel_id is not None:
        channel = await db.scalar(select(Channel).where(
            Channel.id == payload.channel_id,
            Channel.object_id == payload.object_id,
        ))
        if channel is None:
            raise HTTPException(422, "Датчик не относится к выбранному объекту")
        channel_ids = [channel.id]
    else:
        channel_ids = list(await db.scalars(
            select(Channel.id)
            .where(Channel.object_id == payload.object_id)
            .order_by(Channel.id)
        ))
        if not channel_ids:
            raise HTTPException(422, "На выбранном объекте нет датчиков")
    eligible = await db.scalar(
        select(User.id)
        .join(user_roles, user_roles.c.user_id == User.id)
        .join(Role, Role.id == user_roles.c.role_id)
        .join(user_divisions, user_divisions.c.user_id == User.id)
        .join(
            division_objects,
            and_(
                division_objects.c.division_id == user_divisions.c.division_id,
                division_objects.c.object_id == payload.object_id,
            ),
        )
        .where(
            User.id == payload.technician_id,
            User.is_active.is_(True),
            Role.code == "technician",
        )
        .limit(1)
    )
    if eligible is None:
        raise HTTPException(422, "Техник не обслуживает выбранный объект")
    assignment = Assignment(**payload.model_dump(), dispatcher_id=user.id)
    db.add(assignment)
    try:
        await db.flush()
        db.add_all([
            AssignmentItem(assignment_id=assignment.id, channel_id=channel_id)
            for channel_id in channel_ids
        ])
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "На выбранную дату для объекта уже создано задание") from None
    return await _read_assignment(db, assignment.id)


@router.patch("/{assignment_id}/complete", response_model=AssignmentRead)
async def complete_assignment(assignment_id: str, db: Db, user: AssignmentCompleter):
    assignment = await db.scalar(
        select(Assignment).where(Assignment.id == assignment_id).with_for_update()
    )
    if assignment is None:
        raise HTTPException(404, "Задание не найдено")
    if not user.is_admin() and assignment.technician_id != user.id:
        raise HTTPException(403, "Завершить задание может только назначенный техник")
    if assignment.status != "completed":
        completed_at = datetime.now(timezone.utc)
        items = list(await db.scalars(
            select(AssignmentItem)
            .where(AssignmentItem.assignment_id == assignment_id)
            .with_for_update()
        ))
        for item in items:
            item.status = "completed"
            item.completed_at = completed_at
        assignment.status = "completed"
        assignment.completed_at = completed_at
        await db.commit()
    return await _read_assignment(db, assignment.id)


@router.patch("/{assignment_id}/items/{channel_id}/complete", response_model=AssignmentRead)
async def complete_assignment_item(
    assignment_id: str,
    channel_id: int,
    db: Db,
    user: AssignmentCompleter,
):
    assignment = await db.scalar(
        select(Assignment).where(Assignment.id == assignment_id).with_for_update()
    )
    if assignment is None:
        raise HTTPException(404, "Задание не найдено")
    if not user.is_admin() and assignment.technician_id != user.id:
        raise HTTPException(403, "Завершить проверку может только назначенный техник")
    items = list(await db.scalars(
        select(AssignmentItem)
        .where(AssignmentItem.assignment_id == assignment_id)
        .with_for_update()
    ))
    item = next((row for row in items if row.channel_id == channel_id), None)
    if item is None:
        raise HTTPException(404, "Датчик не входит в задание")
    if item.status != "completed":
        item.status = "completed"
        item.completed_at = datetime.now(timezone.utc)
    if items and all(row.status == "completed" for row in items):
        assignment.status = "completed"
        assignment.completed_at = max(row.completed_at for row in items)
    await db.commit()
    return await _read_assignment(db, assignment.id)
