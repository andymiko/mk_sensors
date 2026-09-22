"""Integration tests; TEST_DATABASE_URL must point to disposable PostgreSQL."""
import os
import uuid
import importlib.util
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.dbapi.base import Base
from app.dbapi.models import (
    Channel, Channels, Event, Events, Object, Objects, Permission, Role, User,
)
from app.dbapi.models.access import (
    District, Districts, Division, Divisions, district_divisions, user_role_districts,
    user_role_divisions, user_role_objects,
)
from app.dbapi.models.associations import role_permissions, user_roles
from app.rbac import accessible_channels, accessible_events, accessible_objects
from app.dbapi.base import get_async_session
from app.utils.security import create_access_token
from main import app
from scripts.seed_territories import (
    DISTRICTS, DIVISIONS, OBJECT_DISTRICTS, seed_territories,
)


@pytest.fixture
async def rbac_db():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to run PostgreSQL RBAC integration tests")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            schema = "rbac_test_" + uuid.uuid4().hex
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            await connection.run_sync(Base.metadata.create_all)
            async with AsyncSession(connection, expire_on_commit=False, join_transaction_mode="create_savepoint") as db:
                db.add_all([
                    Division(id="v1", code="v1", name="Первое"),
                    Division(id="v2", code="v2", name="Второе"),
                    User(id="u", email="test@example.com", name="Test", is_active=True),
                    Permission(id="view", code="object.view", name="View", description="View"),
                    Permission(id="edit", code="object.edit", name="Edit", description="Edit"),
                ])
                await db.flush()
                db.add_all([
                    District(id="d1", code="d1", name="Район 1", division_id="v1"),
                    District(id="d2", code="d2", name="Район 2", division_id="v2"),
                ])
                await db.flush()
                await db.execute(insert(district_divisions), [
                    {"district_id": "d1", "division_id": "v1"},
                    {"district_id": "d2", "division_id": "v2"},
                ])
                db.add_all([
                    Object(id=i, district_id=d, hierarchy_level=1, object_type="test", dispatch_name=str(i))
                    for i, d in [(1, "d1"), (2, "d1"), (3, "d2"), (4, None)]
                ])
                await db.flush()
                db.add_all([Channel(id=11, object_id=1), Channel(id=12, object_id=3), Channel(id=13)])
                await db.commit()
                yield db
            await transaction.rollback()
    finally:
        await engine.dispose()


async def grant(db, code, permissions=("view",), districts=(), objects=(), divisions=()):
    db.add(Role(id=code, code=code, name=code))
    await db.flush()
    await db.execute(insert(user_roles).values(user_id="u", role_id=code))
    for permission in permissions:
        await db.execute(insert(role_permissions).values(role_id=code, permission_id=permission))
    for table, column, values in [
        (user_role_districts, "district_id", districts),
        (user_role_objects, "object_id", objects),
        (user_role_divisions, "division_id", divisions),
    ]:
        for value in values:
            await db.execute(insert(table).values(user_id="u", role_id=code, **{column: value}))


async def visible(db, permission="object.view"):
    return set(await db.scalars(accessible_objects("u", permission).with_only_columns(Object.id)))


async def test_insert_new_division(rbac_db):
    division = await Divisions.insert_new_division(
        code="new-division",
        name="Новое подразделение",
        db=rbac_db,
    )

    assert division.id
    assert division.code == "new-division"
    assert division.name == "Новое подразделение"
    assert await rbac_db.get(Division, division.id) is division


async def test_insert_new_district_with_multiple_divisions(rbac_db):
    district = await Districts.insert_new_district(
        code="new-district",
        name="Новый район",
        division_ids=["v1", "v2", "v1"],
        primary_division_id="v2",
        db=rbac_db,
    )

    assert district.id
    assert district.division_id == "v2"
    linked_ids = set(await rbac_db.scalars(
        select(district_divisions.c.division_id)
        .where(district_divisions.c.district_id == district.id)
    ))
    assert linked_ids == {"v1", "v2"}


async def test_insert_new_district_rejects_unknown_divisions(rbac_db):
    with pytest.raises(ValueError, match="Неизвестные подразделения: missing"):
        await Districts.insert_new_district(
            code="invalid-district",
            name="Некорректный район",
            division_ids=["v1", "missing"],
            db=rbac_db,
        )

    assert await rbac_db.scalar(
        select(District).where(District.code == "invalid-district")
    ) is None


async def test_insert_new_district_requires_division(rbac_db):
    with pytest.raises(ValueError, match="Укажите хотя бы одно подразделение"):
        await Districts.insert_new_district(
            code="invalid-district",
            name="Некорректный район",
            division_ids=[],
            db=rbac_db,
        )


async def test_divisions_crud(rbac_db):
    division = await Divisions.insert_new_division("crud-division", "До", db=rbac_db)
    assert await Divisions.get_division_by_id(division.id, db=rbac_db) is division
    assert (await Divisions.get_division_by_code("crud-division", db=rbac_db)).id == division.id
    updated = await Divisions.update_division_by_id(
        division.id, code="crud-division-new", name="После", db=rbac_db,
    )
    assert (updated.code, updated.name) == ("crud-division-new", "После")
    items, total = await Divisions.get_divisions_page(offset=0, limit=100, db=rbac_db)
    assert updated in items and total >= 3
    assert await Divisions.delete_division_by_id(division.id, db=rbac_db)
    assert not await Divisions.delete_division_by_id(division.id, db=rbac_db)


async def test_districts_crud_updates_division_links(rbac_db):
    district = await Districts.insert_new_district(
        "crud-district", "До", ["v1"], db=rbac_db,
    )
    assert await Districts.get_district_by_id(district.id, db=rbac_db) is district
    assert (await Districts.get_district_by_code("crud-district", db=rbac_db)).id == district.id
    updated = await Districts.update_district_by_id(
        district.id,
        code="crud-district-new",
        name="После",
        division_ids=["v1", "v2"],
        primary_division_id="v2",
        db=rbac_db,
    )
    assert updated.division_id == "v2"
    linked_ids = set(await rbac_db.scalars(
        select(district_divisions.c.division_id)
        .where(district_divisions.c.district_id == district.id)
    ))
    assert linked_ids == {"v1", "v2"}
    items, total = await Districts.get_districts_page(offset=0, limit=100, db=rbac_db)
    assert updated in items and total >= 3
    assert await Districts.delete_district_by_id(district.id, db=rbac_db)


async def test_invalid_district_update_rolls_back_fields(rbac_db):
    with pytest.raises(ValueError, match="Неизвестные подразделения"):
        await Districts.update_district_by_id(
            "d1",
            code="must-not-persist",
            division_ids=["missing"],
            db=rbac_db,
        )
    district = await Districts.get_district_by_id("d1", db=rbac_db)
    assert district.code == "d1"


async def test_objects_crud(rbac_db):
    obj = await Objects.insert_new_object(
        id=100,
        hierarchy_level=2,
        parent_id=1,
        district_id="d1",
        object_type="equipment",
        dispatch_name="Объект",
        longitude=37.6,
        latitude=55.7,
        db=rbac_db,
    )
    assert await Objects.get_object_by_id(100, db=rbac_db) is obj
    updated = await Objects.update_object_by_id(
        100, parent_id=None, dispatch_name="Обновлён", longitude=None, db=rbac_db,
    )
    assert updated.parent_id is None and updated.longitude is None
    items, total = await Objects.get_objects_page(offset=0, limit=2, db=rbac_db)
    assert len(items) == 2 and total == 5
    assert await Objects.delete_object_by_id(100, db=rbac_db)


async def test_delete_parent_with_channels_is_rejected(rbac_db):
    with pytest.raises(IntegrityError):
        await Objects.delete_object_by_id(1, db=rbac_db)
    assert await Objects.get_object_by_id(1, db=rbac_db) is not None


async def test_channels_crud(rbac_db):
    channel = await Channels.insert_new_channel(
        id=100,
        object_id=1,
        engineering_system_type="heat",
        sensor_type="temperature",
        engineering_system_tag="T1",
        sensor_name="Датчик",
        db=rbac_db,
    )
    assert await Channels.get_channel_by_id(100, db=rbac_db) is channel
    updated = await Channels.update_channel_by_id(
        100, object_id=None, sensor_name="Обновлён", db=rbac_db,
    )
    assert updated.object_id is None and updated.sensor_name == "Обновлён"
    items, total = await Channels.get_channels_page(offset=0, limit=2, db=rbac_db)
    assert len(items) == 2 and total == 4
    assert await Channels.delete_channel_by_id(100, db=rbac_db)


async def test_events_crud(rbac_db):
    from datetime import datetime

    event = await Events.insert_new_event(
        id=100,
        channel_id=11,
        event_at=datetime(2026, 1, 2, 10, 0),
        is_alarm=False,
        sensor_value="10",
        db=rbac_db,
    )
    assert await Events.get_event_by_id(100, db=rbac_db) is event
    updated = await Events.update_event_by_id(
        100, is_alarm=True, sensor_value=None, db=rbac_db,
    )
    assert updated.is_alarm and updated.sensor_value is None
    items, total = await Events.get_events_page(offset=0, limit=100, db=rbac_db)
    assert updated in items and total == 1
    assert await Events.delete_event_by_id(100, db=rbac_db)


async def test_no_assignments_deny_access(rbac_db):
    await grant(rbac_db, "dispatcher")
    assert await visible(rbac_db) == set()


async def test_technician_requires_both_district_and_object(rbac_db):
    await grant(rbac_db, "technician", districts=["d1"], objects=[1, 3, 4])
    assert await visible(rbac_db) == {1}


async def test_dispatcher_districts_union_explicit_objects(rbac_db):
    await grant(rbac_db, "dispatcher", districts=["d1"], objects=[3])
    assert await visible(rbac_db) == {1, 2, 3}


async def test_manager_division(rbac_db):
    await grant(rbac_db, "manager", divisions=["v1"])
    assert await visible(rbac_db) == {1, 2}


async def test_manager_sees_district_linked_as_secondary_division(rbac_db):
    await rbac_db.execute(insert(district_divisions).values(district_id="d1", division_id="v2"))
    await grant(rbac_db, "manager", divisions=["v2"])
    assert await visible(rbac_db) == {1, 2, 3}


async def test_multiple_roles_do_not_multiply_permissions(rbac_db):
    await grant(rbac_db, "manager", permissions=["view", "edit"], divisions=["v1"])
    await grant(rbac_db, "technician", districts=["d2"], objects=[3])
    assert await visible(rbac_db) == {1, 2, 3}
    assert await visible(rbac_db, "object.edit") == {1, 2}


async def test_missing_permission_denies_even_assigned_object(rbac_db):
    await grant(rbac_db, "dispatcher", districts=["d1"])
    assert await visible(rbac_db, "object.edit") == set()


async def test_channels_inherit_object_access(rbac_db):
    await grant(rbac_db, "technician", districts=["d1"], objects=[1])
    query = accessible_channels("u", "object.view").with_only_columns(Channel.id)
    assert set(await rbac_db.scalars(query)) == {11}


async def test_admin_has_global_access_including_unassigned_channels(rbac_db):
    await grant(rbac_db, "admin", permissions=[])
    assert await visible(rbac_db, "object.edit") == {1, 2, 3, 4}
    query = accessible_channels("u", "channel.view").with_only_columns(Channel.id)
    assert set(await rbac_db.scalars(query)) == {11, 12, 13}


async def test_inactive_user_denied_even_if_admin(rbac_db):
    await grant(rbac_db, "admin", permissions=[])
    user = await rbac_db.get(User, "u")
    user.is_active = False
    await rbac_db.flush()
    assert await visible(rbac_db) == set()


@pytest.fixture
async def rbac_client(rbac_db):
    async def override_db():
        yield rbac_db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_async_session] = override_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test",
            headers={"Authorization": f"Bearer {create_access_token({'sub': 'u'})}"},
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


async def test_objects_api_filters_totals_and_detail(rbac_db, rbac_client):
    await grant(rbac_db, "technician", districts=["d1"], objects=[1])
    response = await rbac_client.get("/api/objects?page_size=1")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [1]
    assert (await rbac_client.get("/api/objects/3")).status_code == 404


async def test_objects_api_supports_sorting(rbac_db, rbac_client):
    await grant(rbac_db, "dispatcher", districts=["d1"])
    response = await rbac_client.get(
        "/api/objects?sort_by=dispatch_name&sort_order=desc&page_size=100"
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [2, 1]


async def test_scope_management_requires_permission(rbac_db, rbac_client):
    await grant(rbac_db, "technician", districts=["d1"], objects=[1])
    response = await rbac_client.put("/api/admin/users/u/roles/technician/scope", json={"district_ids": ["d2"], "object_ids": [3]})
    assert response.status_code == 403


async def test_scope_replacement_rejects_objects_outside_technician_districts(rbac_db, rbac_client):
    await grant(rbac_db, "admin", permissions=[])
    await grant(rbac_db, "technician", districts=["d1"], objects=[1])
    response = await rbac_client.put("/api/admin/users/u/roles/technician/scope", json={"district_ids": ["d1"], "object_ids": [3]})
    assert response.status_code == 422
    ids = await rbac_db.scalars(select(user_role_objects.c.object_id).where(user_role_objects.c.role_id == "technician"))
    assert set(ids) == {1}


async def test_replacing_roles_preserves_retained_scopes(rbac_db, rbac_client):
    await grant(rbac_db, "admin", permissions=[])
    await grant(rbac_db, "technician", districts=["d1"], objects=[1])
    await grant(rbac_db, "dispatcher", districts=["d2"])
    response = await rbac_client.put("/api/admin/users/u/roles", json={"role_ids": ["admin", "technician"]})
    assert response.status_code == 200
    assert set(response.json()["role_codes"]) == {"admin", "technician"}
    assert set(await rbac_db.scalars(select(user_role_objects.c.object_id))) == {1}
    assert set(await rbac_db.scalars(select(user_role_districts.c.role_id))) == {"technician"}


async def test_scope_roundtrip_and_clear(rbac_db, rbac_client):
    await grant(rbac_db, "admin", permissions=[])
    await grant(rbac_db, "technician")
    path = "/api/admin/users/u/roles/technician/scope"
    response = await rbac_client.put(path, json={"district_ids": ["d1", "d1"], "object_ids": [1, 2]})
    assert response.status_code == 200
    assert response.json() == {"division_ids": [], "district_ids": ["d1"], "object_ids": [1, 2]}
    assert (await rbac_client.get(path)).json() == response.json()
    assert (await rbac_client.put(path, json={})).status_code == 200
    assert (await rbac_client.get(path)).json() == {"division_ids": [], "district_ids": [], "object_ids": []}


@pytest.mark.parametrize("payload", [
    {"division_ids": ["v1"]},
    {"district_ids": ["missing"]},
    {"district_ids": ["d1"], "object_ids": [999]},
    {"district_ids": ["d1"], "object_ids": [4]},
])
async def test_invalid_scope_rejected(rbac_db, rbac_client, payload):
    await grant(rbac_db, "admin", permissions=[])
    await grant(rbac_db, "technician")
    response = await rbac_client.put("/api/admin/users/u/roles/technician/scope", json=payload)
    assert response.status_code == 422


async def test_cannot_assign_scope_without_user_role(rbac_db, rbac_client):
    await grant(rbac_db, "admin", permissions=[])
    rbac_db.add(Role(id="technician", code="technician", name="Техник"))
    await rbac_db.flush()
    response = await rbac_client.put("/api/admin/users/u/roles/technician/scope", json={"district_ids": ["d1"]})
    assert response.status_code == 404


async def test_territory_creation_and_object_assignment(rbac_db, rbac_client):
    await grant(rbac_db, "admin", permissions=[])
    division = await rbac_client.post("/api/admin/divisions", json={"code": "new", "name": "Новое"})
    assert division.status_code == 201
    district = await rbac_client.post("/api/admin/districts", json={
        "code": "new", "name": "Новый", "division_ids": ["v1", division.json()["id"]],
    })
    assert district.status_code == 201
    assert set(district.json()["division_ids"]) == {"v1", division.json()["id"]}
    response = await rbac_client.put("/api/admin/objects/4/district", json={"district_id": district.json()["id"]})
    assert response.status_code == 200
    assert response.json()["district_id"] == district.json()["id"]

    legacy = await rbac_client.post("/api/admin/districts", json={
        "code": "legacy", "name": "Совместимый", "division_id": "v1",
    })
    assert legacy.status_code == 201
    assert legacy.json()["division_ids"] == ["v1"]


async def test_channels_api_checks_scope_and_permission(rbac_db, rbac_client):
    rbac_db.add(Permission(id="channel", code="channel.view", name="Каналы", description="Каналы"))
    await rbac_db.flush()
    await grant(rbac_db, "technician", permissions=["channel"], districts=["d1"], objects=[1])
    response = await rbac_client.get("/api/channels")
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert [item["id"] for item in response.json()["items"]] == [11]
    assert (await rbac_client.get("/api/channels/12")).status_code == 404
    assert (await rbac_client.get("/api/channels?object_id=3")).json()["items"] == []
    assert (await rbac_client.get("/api/objects")).status_code == 403


async def test_events_api_filters_access_date_object_and_sensor(rbac_db, rbac_client):
    from datetime import datetime

    rbac_db.add(Permission(id="event", code="event.view", name="События", description="События"))
    await rbac_db.flush()
    await grant(rbac_db, "technician", permissions=["event"], districts=["d1"], objects=[1])
    channel = await rbac_db.get(Channel, 11)
    channel.sensor_type = "temperature"
    rbac_db.add_all([
        Event(id=201, channel_id=11, event_at=datetime(2026, 1, 1, 10), is_alarm=False, sensor_value="10"),
        Event(id=202, channel_id=11, event_at=datetime(2026, 1, 2, 10), is_alarm=True, sensor_value="20"),
        Event(id=203, channel_id=12, event_at=datetime(2026, 1, 2, 10), is_alarm=True, sensor_value="30"),
    ])
    await rbac_db.commit()

    response = await rbac_client.get(
        "/api/events?date_from=2026-01-02T00:00:00&object_id=1&sensor_type=temperature"
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["id"] == 202
    assert response.json()["items"][0]["object_id"] == 1


async def test_events_api_rejects_inverted_date_range(rbac_db, rbac_client):
    rbac_db.add(Permission(id="event", code="event.view", name="События", description="События"))
    await rbac_db.flush()
    await grant(rbac_db, "technician", permissions=["event"], districts=["d1"], objects=[1])
    response = await rbac_client.get(
        "/api/events?date_from=2026-02-01T00:00:00&date_to=2026-01-01T00:00:00"
    )
    assert response.status_code == 422


async def test_seed_is_idempotent_and_preserves_existing_roles(rbac_db):
    path = Path(__file__).resolve().parents[1] / "alembic/versions/d82a64e913f0_rbac_scopes.py"
    spec = importlib.util.spec_from_file_location("rbac_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    # Existing role IDs, names and user membership must not be overwritten.
    await grant(rbac_db, "manager", divisions=["v1"])
    connection = await rbac_db.connection()
    await connection.run_sync(migration.seed_rbac)
    count = await rbac_db.scalar(select(func.count()).select_from(role_permissions))
    await connection.run_sync(migration.seed_rbac)
    assert await rbac_db.scalar(select(func.count()).select_from(role_permissions)) == count
    manager = await rbac_db.scalar(select(Role).where(Role.code == "manager"))
    assert manager.id == "manager"
    assert manager.name == "manager"
    assert set(await rbac_db.scalars(select(Role.code))) == {"admin", "user", "dispatcher", "technician", "manager"}
    assert await visible(rbac_db) == {1, 2}
    for code, (_name, expected) in migration.ROLES.items():
        actual = set(await rbac_db.scalars(
            select(Permission.code).join(role_permissions).join(Role).where(Role.code == code)
        ))
        assert actual == set(expected)


async def test_revoked_role_loses_scope(rbac_db):
    await grant(rbac_db, "technician", districts=["d1"], objects=[1])
    await rbac_db.execute(delete(user_roles).where(user_roles.c.user_id == "u"))
    assert await visible(rbac_db) == set()
    assert list(await rbac_db.scalars(select(user_role_objects.c.object_id))) == []


async def test_events_inherit_channel_scope(rbac_db):
    from datetime import datetime

    await grant(rbac_db, "technician", districts=["d1"], objects=[1])
    rbac_db.add_all([
        Event(id=101, channel_id=11, event_at=datetime(2026, 1, 1), is_alarm=True),
        Event(id=102, channel_id=12, event_at=datetime(2026, 1, 1), is_alarm=True),
    ])
    await rbac_db.flush()
    query = accessible_events("u", "object.view").with_only_columns(Event.id)
    assert set(await rbac_db.scalars(query)) == {101}


async def test_anonymous_access_rejected(rbac_client):
    rbac_client.headers.pop("Authorization")
    for path in ("/api/objects", "/api/channels", "/api/admin/divisions"):
        assert (await rbac_client.get(path)).status_code == 401


async def test_territory_seed_is_strict_before_writing(rbac_db):
    with pytest.raises(ValueError, match="отсутствуют идентификаторы"):
        await seed_territories(rbac_db)
    assert set(await rbac_db.scalars(select(Division.code))) == {"v1", "v2"}


async def test_territory_seed_is_idempotent(rbac_db):
    rbac_db.add_all([
        Object(
            id=object_id,
            hierarchy_level=1,
            object_type="test",
            dispatch_name=str(object_id),
        )
        for object_id in OBJECT_DISTRICTS
    ])
    await rbac_db.flush()

    first = await seed_territories(rbac_db)
    second = await seed_territories(rbac_db)
    await rbac_db.flush()

    assert first == second
    assert first.objects_updated == 19
    assert set(DIVISIONS).issubset(set(await rbac_db.scalars(select(Division.code))))
    assert set(DISTRICTS).issubset(set(await rbac_db.scalars(select(District.code))))

    seeded_district_ids = select(District.id).where(District.code.in_(DISTRICTS))
    links_count = await rbac_db.scalar(
        select(func.count()).select_from(district_divisions).where(
            district_divisions.c.district_id.in_(seeded_district_ids)
        )
    )
    assert links_count == 20

    assigned = dict((await rbac_db.execute(
        select(Object.id, District.code)
        .join(District, District.id == Object.district_id)
        .where(Object.id.in_(OBJECT_DISTRICTS))
    )).all())
    assert assigned == OBJECT_DISTRICTS
