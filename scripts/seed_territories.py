"""Fill divisions, districts and object-to-district assignments."""
import argparse
import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.dbapi.base import async_session
from app.dbapi.models import Object
from app.dbapi.models.access import District, Division, district_divisions, division_objects


DIVISIONS = {
    "dispatch-north": "Диспетчерская Север",
    "dispatch-south": "Диспетчерская Юг",
    "dispatch-west": "Диспетчерская Запад",
    "dispatch-east": "Диспетчерская Восток",
    "operations-arbat": "Служба эксплуатации Арбат",
    "operations-khamovniki": "Служба эксплуатации Хамовники",
    "operations-presnenskiy": "Служба эксплуатации Пресненский",
    "operations-tverskoy": "Служба эксплуатации Тверской",
    "operations-meshchanskiy-krasnoselskiy": "Служба эксплуатации Мещанский/Красносельский",
    "operations-basmanniy": "Служба эксплуатации Басманный",
    "operations-taganskiy": "Служба эксплуатации Таганский",
    "operations-zamoskvorechye-yakimanka": "Служба эксплуатации Замоскворечье/Якиманка",
}

DISTRICTS = {
    "arbat": ("Арбат", ("operations-arbat", "dispatch-west")),
    "khamovniki": ("Хамовники", ("operations-khamovniki", "dispatch-west")),
    "presnenskiy": ("Пресненский", ("operations-presnenskiy", "dispatch-west")),
    "tverskoy": ("Тверской", ("operations-tverskoy", "dispatch-north")),
    "meshchanskiy": ("Мещанский", ("operations-meshchanskiy-krasnoselskiy", "dispatch-north")),
    "krasnoselskiy": ("Красносельский", ("operations-meshchanskiy-krasnoselskiy", "dispatch-north")),
    "basmanniy": ("Басманный", ("operations-basmanniy", "dispatch-east")),
    "taganskiy": ("Таганский", ("operations-taganskiy", "dispatch-east")),
    "zamoskvorechye": ("Замоскворечье", ("operations-zamoskvorechye-yakimanka", "dispatch-south")),
    "yakimanka": ("Якиманка", ("operations-zamoskvorechye-yakimanka", "dispatch-south")),
}

OBJECT_DISTRICTS = {
    5333: "tverskoy",
    5003: "khamovniki",
    4369: "khamovniki",
    4177: "presnenskiy",
    5675: "basmanniy",
    3360: "khamovniki",
    3388: "zamoskvorechye",
    5218: "tverskoy",
    5657: "meshchanskiy",
    5578: "tverskoy",
    5591: "taganskiy",
    5132: "khamovniki",
    4543: "tverskoy",
    3902: "taganskiy",
    5011: "meshchanskiy",
    4610: "krasnoselskiy",
    5963: "taganskiy",
    111: "basmanniy",
    5122: "presnenskiy",
}


@dataclass(frozen=True)
class SeedResult:
    divisions: int
    districts: int
    objects_updated: int
    missing_object_ids: tuple[int, ...]


def _stable_id(kind: str, code: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mk_sensors/territories/{kind}/{code}"))


async def seed_territories(db: AsyncSession, *, allow_missing_objects: bool = False) -> SeedResult:
    existing_object_ids = set(await db.scalars(
        select(Object.id).where(Object.id.in_(OBJECT_DISTRICTS))
    ))
    missing = tuple(sorted(set(OBJECT_DISTRICTS) - existing_object_ids))
    if missing and not allow_missing_objects:
        raise ValueError(f"В таблице objects отсутствуют идентификаторы: {', '.join(map(str, missing))}")

    for code, name in DIVISIONS.items():
        await db.execute(
            insert(Division).values(id=_stable_id("division", code), code=code, name=name)
            .on_conflict_do_update(index_elements=[Division.code], set_={"name": name})
        )
    division_ids = dict((await db.execute(select(Division.code, Division.id))).all())

    for code, (name, linked_divisions) in DISTRICTS.items():
        primary_division_id = division_ids[linked_divisions[0]]
        await db.execute(
            insert(District).values(
                id=_stable_id("district", code), code=code, name=name,
                division_id=primary_division_id,
            ).on_conflict_do_update(
                index_elements=[District.code],
                set_={"name": name, "division_id": primary_division_id},
            )
        )
    district_ids = dict((await db.execute(select(District.code, District.id))).all())

    managed_district_ids = [district_ids[code] for code in DISTRICTS]
    await db.execute(delete(district_divisions).where(
        district_divisions.c.district_id.in_(managed_district_ids)
    ))
    links = [
        {"district_id": district_ids[district_code], "division_id": division_ids[division_code]}
        for district_code, (_name, division_codes) in DISTRICTS.items()
        for division_code in division_codes
    ]
    await db.execute(insert(district_divisions), links)

    for object_id in existing_object_ids:
        obj = await db.get(Object, object_id)
        obj.district_id = district_ids[OBJECT_DISTRICTS[object_id]]

    await db.execute(delete(division_objects).where(
        division_objects.c.object_id.in_(existing_object_ids)
    ))
    object_links = [
        {"object_id": object_id, "division_id": division_ids[division_code]}
        for object_id in existing_object_ids
        for division_code in DISTRICTS[OBJECT_DISTRICTS[object_id]][1]
    ]
    if object_links:
        await db.execute(insert(division_objects), object_links)

    return SeedResult(
        divisions=len(DIVISIONS),
        districts=len(DISTRICTS),
        objects_updated=len(existing_object_ids),
        missing_object_ids=missing,
    )


async def run(*, allow_missing_objects: bool, dry_run: bool) -> SeedResult:
    async with async_session() as db:
        try:
            result = await seed_territories(db, allow_missing_objects=allow_missing_objects)
            if dry_run:
                await db.rollback()
            else:
                await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Заполнить подразделения, районы и районы объектов")
    parser.add_argument(
        "--allow-missing-objects", action="store_true",
        help="Заполнить найденные объекты и вывести отсутствующие (по умолчанию ошибка)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Проверить данные и откатить транзакцию")
    args = parser.parse_args()
    try:
        result = asyncio.run(run(
            allow_missing_objects=args.allow_missing_objects,
            dry_run=args.dry_run,
        ))
    except ValueError as error:
        raise SystemExit(str(error)) from error

    mode = "Проверка завершена, изменения отменены" if args.dry_run else "Данные сохранены"
    print(
        f"{mode}: подразделений {result.divisions}, районов {result.districts}, "
        f"объектов обновлено {result.objects_updated}."
    )
    if result.missing_object_ids:
        print("Отсутствующие objects.id:", ", ".join(map(str, result.missing_object_ids)))


if __name__ == "__main__":
    main()
