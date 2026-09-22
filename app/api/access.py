from collections import defaultdict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_permission
from app.dbapi.base import get_async_session
from app.dbapi.models import Object, Role, User
from app.dbapi.models.access import (
    District, Districts, Division, Divisions, district_divisions, division_objects,
    user_divisions, user_role_districts, user_role_divisions, user_role_objects,
)
from app.dbapi.models.associations import user_roles
from app.schemas.access import (
    DistrictCreate, DistrictRead, DivisionDetails, DivisionMember, IdsUpdate,
    ObjectDistrictUpdate, ObjectRead, RoleScope, TerritoryCreate, TerritoryRead,
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


@router.get("/divisions/details", response_model=list[DivisionDetails])
async def list_division_details(db: Db):
    divisions = (await db.scalars(select(Division).order_by(Division.name))).all()
    object_ids = defaultdict(list)
    members = defaultdict(list)
    for division_id, object_id in await db.execute(
        select(division_objects.c.division_id, division_objects.c.object_id)
        .order_by(division_objects.c.object_id)
    ):
        object_ids[division_id].append(object_id)
    for division_id, user_id, name, email in await db.execute(
        select(user_divisions.c.division_id, User.id, User.name, User.email)
        .join(User, User.id == user_divisions.c.user_id)
        .order_by(User.name, User.id)
    ):
        members[division_id].append(DivisionMember(id=user_id, name=name, email=email))
    return [DivisionDetails(
        id=division.id, code=division.code, name=division.name,
        object_ids=object_ids[division.id], users=members[division.id],
    ) for division in divisions]


@router.put("/divisions/{division_id}/objects", response_model=DivisionDetails)
async def replace_division_objects(division_id: str, payload: IdsUpdate, db: Db):
    division = await db.get(Division, division_id)
    if division is None:
        raise HTTPException(404, "Подразделение не найдено")
    object_ids = set(payload.ids)
    if object_ids and set(await db.scalars(select(Object.id).where(Object.id.in_(object_ids)))) != object_ids:
        raise HTTPException(422, "Переданы неизвестные объекты")
    await db.execute(delete(division_objects).where(division_objects.c.division_id == division_id))
    if object_ids:
        await db.execute(division_objects.insert(), [
            {"division_id": division_id, "object_id": object_id}
            for object_id in sorted(object_ids)
        ])
    await _commit(db)
    users = [DivisionMember(id=user_id, name=name, email=email) for user_id, name, email in await db.execute(
        select(User.id, User.name, User.email)
        .join(user_divisions, user_divisions.c.user_id == User.id)
        .where(user_divisions.c.division_id == division_id)
        .order_by(User.name, User.id)
    )]
    return DivisionDetails(
        id=division.id, code=division.code, name=division.name,
        object_ids=sorted(object_ids), users=users,
    )


@router.post("/divisions", response_model=TerritoryRead, status_code=201)
async def create_division(payload: TerritoryCreate, db: Db):
    try:
        return await Divisions.insert_new_division(**payload.model_dump(), db=db)
    except IntegrityError:
        raise HTTPException(409, "Подразделение с таким кодом уже существует") from None


@router.get("/districts", response_model=list[DistrictRead])
async def list_districts(db: Db):
    districts = (await db.scalars(select(District).order_by(District.name))).all()
    linked_divisions = defaultdict(list)
    if districts:
        rows = await db.execute(
            select(district_divisions.c.district_id, district_divisions.c.division_id)
            .where(district_divisions.c.district_id.in_([district.id for district in districts]))
            .order_by(district_divisions.c.division_id)
        )
        for district_id, division_id in rows:
            linked_divisions[district_id].append(division_id)
    return [
        _district_read(district, linked_divisions[district.id])
        for district in districts
    ]


@router.post("/districts", response_model=DistrictRead, status_code=201)
async def create_district(payload: DistrictCreate, db: Db):
    division_ids = set(payload.division_ids)
    if payload.division_id:
        division_ids.add(payload.division_id)
    try:
        district = await Districts.insert_new_district(
            code=payload.code,
            name=payload.name,
            division_ids=sorted(division_ids),
            primary_division_id=(
                payload.division_id
                or (payload.division_ids[0] if payload.division_ids else None)
            ),
            db=db,
        )
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except IntegrityError:
        raise HTTPException(409, "Район с таким кодом уже существует") from None
    return _district_read(district, sorted(division_ids))


def _district_read(district: District, division_ids: list[str]) -> DistrictRead:
    return DistrictRead.model_validate({
        "id": district.id,
        "code": district.code,
        "name": district.name,
        "division_id": district.division_id,
        "division_ids": division_ids,
    })


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
