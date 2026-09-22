"""Create demo operational users and attach them to roles and divisions."""
import argparse
import asyncio
from pathlib import Path
import sys
import uuid
from dataclasses import dataclass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dbapi.base import async_session
from app.dbapi.models import Auth, Role, User
from app.dbapi.models.access import Division, user_divisions
from app.dbapi.models.associations import user_roles
from app.utils.security import get_password_hash
from scripts.seed_territories import DIVISIONS


DISPATCHERS = {
    "dispatch-north": ("dispatcher.north", "Диспетчер Север"),
    "dispatch-south": ("dispatcher.south", "Диспетчер Юг"),
    "dispatch-west": ("dispatcher.west", "Диспетчер Запад"),
    "dispatch-east": ("dispatcher.east", "Диспетчер Восток"),
}

OPERATIONS = {
    "operations-arbat": ("arbat", "Арбат"),
    "operations-khamovniki": ("khamovniki", "Хамовники"),
    "operations-presnenskiy": ("presnenskiy", "Пресненский"),
    "operations-tverskoy": ("tverskoy", "Тверской"),
    "operations-meshchanskiy-krasnoselskiy": (
        "meshchanskiy-krasnoselskiy", "Мещанский/Красносельский",
    ),
    "operations-basmanniy": ("basmanniy", "Басманный"),
    "operations-taganskiy": ("taganskiy", "Таганский"),
    "operations-zamoskvorechye-yakimanka": (
        "zamoskvorechye-yakimanka", "Замоскворечье/Якиманка",
    ),
}


@dataclass(frozen=True)
class SeedUser:
    email_local: str
    name: str
    role_code: str
    division_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedResult:
    created: int
    updated: int
    total: int


def build_user_catalog() -> tuple[SeedUser, ...]:
    users = [
        SeedUser(local, name, "dispatcher", (division_code,))
        for division_code, (local, name) in DISPATCHERS.items()
    ]
    users.extend(
        SeedUser(
            f"technician.{email_part}.{number}",
            f"Техник {division_name} {number}",
            "technician",
            (division_code,),
        )
        for division_code, (email_part, division_name) in OPERATIONS.items()
        for number in range(1, 4)
    )
    users.extend([
        SeedUser("administrator", "Администратор системы", "admin", tuple(DIVISIONS)),
        SeedUser("manager", "Руководитель", "manager", tuple(DIVISIONS)),
    ])
    return tuple(users)


USERS = build_user_catalog()


def _stable_id(email: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"mk_sensors/seed-user/{email}"))


def _email(local: str, domain: str) -> str:
    return str(TypeAdapter(EmailStr).validate_python(f"{local}@{domain}"))


async def seed_users(
    db: AsyncSession,
    *,
    password: str,
    domain: str = "example.com",
    reset_passwords: bool = False,
) -> SeedResult:
    if not 8 <= len(password) <= 128:
        raise ValueError("Пароль должен содержать от 8 до 128 символов")
    domain = domain.strip().lower().lstrip("@")
    if not domain or "@" in domain:
        raise ValueError("Передайте домен без символа @")

    required_roles = {user.role_code for user in USERS}
    roles = {
        role.code: role.id
        for role in await db.scalars(select(Role).where(Role.code.in_(required_roles)))
    }
    missing_roles = sorted(required_roles - roles.keys())
    if missing_roles:
        raise ValueError(
            "Не найдены роли: " + ", ".join(missing_roles) + ". Выполните alembic upgrade head"
        )

    required_divisions = {
        code for user in USERS for code in user.division_codes
    }
    divisions = {
        division.code: division.id
        for division in await db.scalars(
            select(Division).where(Division.code.in_(required_divisions))
        )
    }
    missing_divisions = sorted(required_divisions - divisions.keys())
    if missing_divisions:
        raise ValueError(
            "Не найдены подразделения: " + ", ".join(missing_divisions)
            + ". Сначала выполните scripts/seed_territories.py"
        )

    created = 0
    updated = 0
    for definition in USERS:
        email = _email(definition.email_local, domain)
        user = await db.scalar(
            select(User).where(func.lower(User.email) == email.lower())
        )
        if user is None:
            user = User(
                id=_stable_id(email),
                email=email,
                name=definition.name,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            created += 1
        else:
            user.email = email
            user.name = definition.name
            user.is_active = True
            updated += 1

        credential = await db.get(Auth, user.id)
        if credential is None:
            credential = Auth(
                id=user.id,
                email=email,
                password=get_password_hash(password),
                is_active=True,
            )
            db.add(credential)
        else:
            credential.email = email
            credential.is_active = True
            if reset_passwords:
                credential.password = get_password_hash(password)

        await db.execute(delete(user_roles).where(user_roles.c.user_id == user.id))
        await db.execute(user_roles.insert().values(
            user_id=user.id,
            role_id=roles[definition.role_code],
        ))
        await db.execute(delete(user_divisions).where(user_divisions.c.user_id == user.id))
        if definition.division_codes:
            await db.execute(user_divisions.insert(), [
                {"user_id": user.id, "division_id": divisions[code]}
                for code in definition.division_codes
            ])

    return SeedResult(created=created, updated=updated, total=len(USERS))


async def run(
    *, password: str, domain: str, reset_passwords: bool, dry_run: bool,
) -> SeedResult:
    async with async_session() as db:
        try:
            result = await seed_users(
                db,
                password=password,
                domain=domain,
                reset_passwords=reset_passwords,
            )
            if dry_run:
                await db.rollback()
            else:
                await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Создать диспетчеров, техников, администратора и руководителя",
    )
    parser.add_argument(
        "--password", required=True,
        help="Начальный пароль новых пользователей (8–128 символов)",
    )
    parser.add_argument(
        "--domain", default="example.com",
        help="Домен создаваемых email без @ (по умолчанию example.com)",
    )
    parser.add_argument(
        "--reset-passwords", action="store_true",
        help="Заменить пароль уже существующих seed-пользователей",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Проверить создание и откатить транзакцию",
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(run(
            password=args.password,
            domain=args.domain,
            reset_passwords=args.reset_passwords,
            dry_run=args.dry_run,
        ))
    except ValueError as error:
        raise SystemExit(str(error)) from error

    mode = "Проверка завершена, изменения отменены" if args.dry_run else "Пользователи сохранены"
    print(
        f"{mode}: создано {result.created}, обновлено {result.updated}, всего {result.total}."
    )


if __name__ == "__main__":
    main()
