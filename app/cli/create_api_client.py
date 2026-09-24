"""Create or rotate the service token used by automatic sensor ingestion."""
import argparse
import asyncio
import re
import uuid

from sqlalchemy import select

from app.dbapi.base import async_session
from app.dbapi.models import ApiClient, User
from app.utils.api_keys import generate_api_token, hash_api_token


def _technical_email(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise ValueError("Имя должно содержать латинские буквы или цифры")
    return f"api-client+{slug}@internal.invalid"


async def create_or_rotate(name: str) -> str:
    token = generate_api_token()
    async with async_session() as db:
        client = await db.scalar(select(ApiClient).where(ApiClient.name == name))
        if client is None:
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                email=_technical_email(name),
                name=f"API: {name}",
                is_active=True,
            )
            db.add(user)
            await db.flush()
            client = ApiClient(
                name=name,
                token_hash=hash_api_token(token),
                user_id=user_id,
                is_active=True,
            )
            db.add(client)
        else:
            client.token_hash = hash_api_token(token)
            client.is_active = True
            client.last_used_at = None
            user = await db.get(User, client.user_id)
            if user is None:
                raise RuntimeError("Техническая учётная запись API-клиента не найдена")
            user.is_active = True
        await db.commit()
    return token


async def run(name: str) -> None:
    token = await create_or_rotate(name)
    print("Сервисный токен создан. Скопируйте его сейчас: повторно он не выводится.")
    print(token)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Создать или заменить токен автоматического приёма показаний",
    )
    parser.add_argument("--name", default="sensors", help="Имя API-клиента")
    args = parser.parse_args()
    asyncio.run(run(args.name.strip()))


if __name__ == "__main__":
    main()
