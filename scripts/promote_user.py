import argparse
import asyncio

from sqlalchemy import func, select

from app.dbapi.base import async_session
from app.dbapi.models.associations import user_roles
from app.dbapi.models.roles import Role
from app.dbapi.models.users import User


async def promote(email: str) -> None:
    async with async_session() as db:
        user = await db.scalar(select(User).where(func.lower(User.email) == email.lower()))
        if user is None:
            raise SystemExit(f"Пользователь {email!r} не найден")

        admin_role = await db.scalar(select(Role).where(Role.code == "admin"))
        if admin_role is None:
            raise SystemExit("Роль 'admin' не найдена. Выполните alembic upgrade head")

        exists = await db.scalar(
            select(user_roles.c.user_id).where(
                user_roles.c.user_id == user.id,
                user_roles.c.role_id == admin_role.id,
            )
        )
        if exists is None:
            await db.execute(
                user_roles.insert().values(user_id=user.id, role_id=admin_role.id)
            )
        await db.commit()
        print(f"Пользователю {email} назначена роль admin")


def main() -> None:
    parser = argparse.ArgumentParser(description="Назначить пользователю роль admin")
    parser.add_argument("email")
    args = parser.parse_args()
    asyncio.run(promote(args.email))


if __name__ == "__main__":
    main()
