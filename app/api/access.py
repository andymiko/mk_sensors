from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models import Object, Role, User
from app.dbapi.models.access import (
    District, Division, user_role_districts, user_role_divisions, user_role_objects,
)
from app.dbapi.models.associations import user_roles
from app.schemas.access import (
    DistrictCreate, DistrictRead, ObjectDistrictUpdate, ObjectRead,
    RoleScope, TerritoryCreate, TerritoryRead,
)

router = APIRouter(
    prefix="/admin", tags=["access"], dependencies=[Depends(require_permission("access.manage"))],
)
Db = Annotated[AsyncSession, Depends(get_async_session)]
SCOPE_TABLES = (
    ("division_ids", user_role_divisions, "division_id", Division),
    ("district_ids", user_role_districts, "district_id", District),
    ("object_ids", user_role_objects, "object_id", Object),
)


async def _commit(db: AsyncSession):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Конфликт данных: код уже занят или связанная запись изменилась") from None


@router.get("/divisions", response_model=list[TerritoryRead])
async def list_divisions(db: Db):
    return (await db.scalars(select(Division).order_by(Division.name))).all()


@router.post("/divisions", response_model=TerritoryRead, status_code=201)
async def create_division(payload: TerritoryCreate, db: Db):
    division = Division(**payload.model_dump())
    db.add(division)
    await _commit(db)
    return division


@router.get("/districts", response_model=list[DistrictRead])
async def list_districts(db: Db):
    return (await db.scalars(select(District).order_by(District.name))).all()


@router.post("/districts", response_model=DistrictRead, status_code=201)
async def create_district(payload: DistrictCreate, db: Db):
    if await db.get(Division, payload.division_id) is None:
        raise HTTPException(422, "Неизвестное подразделение")
    district = District(**payload.model_dump())
    db.add(district)
    await _commit(db)
    return district


@router.put("/objects/{object_id}/district", response_model=ObjectRead)
async def set_object_district(object_id: int, payload: ObjectDistrictUpdate, db: Db):
    obj = await db.get(Object, object_id)
    if obj is None:
        raise HTTPException(404, "Объект не найден")
    if payload.district_id is not None and await db.get(District, payload.district_id) is None:
        raise HTTPException(422, "Неизвестный район")
    obj.district_id = payload.district_id
    await _commit(db)
    return obj


async def _assigned_role(db, user_id, role_id, *, lock=False):
    query = select(User).where(User.id == user_id)
    if lock:
        query = query.with_for_update()
    if await db.scalar(query) is None:
        raise HTTPException(404, "Пользователь не найден")
    role = await db.scalar(
        select(Role).join(user_roles, user_roles.c.role_id == Role.id)
        .where(user_roles.c.user_id == user_id, Role.id == role_id)
    )
    if role is None:
        raise HTTPException(404, "Роль не назначена пользователю")
    return role


@router.get("/users/{user_id}/roles/{role_id}/scope", response_model=RoleScope)
async def get_role_scope(user_id: str, role_id: str, db: Db):
    await _assigned_role(db, user_id, role_id)
    result = {}
    for field, table, column, _model in SCOPE_TABLES:
        result[field] = list(await db.scalars(
            select(table.c[column]).where(table.c.user_id == user_id, table.c.role_id == role_id)
            .order_by(table.c[column])
        ))
    return RoleScope(**result)


@router.put("/users/{user_id}/roles/{role_id}/scope", response_model=RoleScope)
async def replace_role_scope(user_id: str, role_id: str, payload: RoleScope, db: Db):
    role = await _assigned_role(db, user_id, role_id, lock=True)
    if role.code not in {"dispatcher", "technician", "manager"}:
        raise HTTPException(422, "Область назначается диспетчеру, технику или руководителю")
    if role.code == "manager" and (payload.district_ids or payload.object_ids):
        raise HTTPException(422, "Руководителю назначаются подразделения")
    if role.code != "manager" and payload.division_ids:
        raise HTTPException(422, "Подразделения назначаются руководителю")
    for field, _table, _column, model in SCOPE_TABLES:
        ids = set(getattr(payload, field))
        if ids and set(await db.scalars(select(model.id).where(model.id.in_(ids)))) != ids:
            raise HTTPException(422, f"Неизвестные идентификаторы: {field}")
    if payload.object_ids:
        objects = (await db.scalars(select(Object).where(Object.id.in_(payload.object_ids)))).all()
        if any(obj.district_id is None for obj in objects):
            raise HTTPException(422, "Сначала назначьте объектам районы")
        if role.code == "technician" and any(obj.district_id not in payload.district_ids for obj in objects):
            raise HTTPException(422, "Объекты техника должны принадлежать назначенным районам")
    for field, table, column, _model in SCOPE_TABLES:
        await db.execute(delete(table).where(table.c.user_id == user_id, table.c.role_id == role_id))
        ids = set(getattr(payload, field))
        if ids:
            await db.execute(table.insert(), [
                {"user_id": user_id, "role_id": role_id, column: value} for value in sorted(ids)
            ])
    await _commit(db)
    return RoleScope(**{field: sorted(set(getattr(payload, field))) for field, *_ in SCOPE_TABLES})
