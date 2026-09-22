import uuid

from sqlalchemy import String, Boolean, ForeignKey, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import mapped_column, Mapped, selectinload

from app.dbapi.base import Base, get_async_db_context

from app.dbapi.models.associations import user_roles
from app.dbapi.models.roles import Role
from app.dbapi.models.users import User

from app.schemas.users import PermissionModel, RoleModel, UserRead
from app.utils.security import get_password_hash, verify_password_async


PLACEHOLDER_HASH = get_password_hash("placeholder")


class Auth(Base):

    __tablename__ = "auth"

    id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthsTable:


    async def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        is_active: bool = True,
        db: AsyncSession | None = None
    ) -> UserRead | None:

        async with get_async_db_context(db) as session:

            new_id = str(uuid.uuid4())
            hashed_password = get_password_hash(password)

            credential = Auth(
                id=new_id,
                email=email,
                password=hashed_password,
                is_active=is_active
            )

            user = User(
                id=new_id,
                email=email,
                name=name,
                is_active=is_active,
            )
            try:
                # FK auth.id -> users.id требует, чтобы профиль был записан первым.
                session.add(user)
                await session.flush()

                session.add(credential)
                await session.flush()

                role = await session.scalar(
                    select(Role)
                    .where(Role.code == "user")
                    .options(selectinload(Role.permissions))
                )
                if role is None:
                    raise RuntimeError("Базовая роль 'user' не создана")
                await session.execute(
                    user_roles.insert().values(user_id=new_id, role_id=role.id)
                )
                await session.commit()
            except IntegrityError:
                await session.rollback()
                raise
            except Exception:
                await session.rollback()
                raise

            return UserRead(
                id=new_id,
                email=email,
                name=name,
                is_active=is_active,
                roles=[RoleModel.model_validate(role)],
                role_codes=["user"],
                permission_codes=[permission.code for permission in role.permissions],
                permissions=[PermissionModel.model_validate(permission) for permission in role.permissions],
            )


    async def authenticate_user(
        self,
        email: str,
        password: str,
        db: AsyncSession | None = None,
    ) -> UserRead | None:
        async with get_async_db_context(db) as session:
            row = (
                await session.execute(
                    select(Auth, User)
                    .join(User, User.id == Auth.id)
                    .where(func.lower(Auth.email) == email.lower())
                    .options(
                        selectinload(User.roles).selectinload(Role.permissions)
                    )
                )
            ).one_or_none()

            if row is None:
                await verify_password_async(password, PLACEHOLDER_HASH)
                return None

            credential, user = row
            if not credential.is_active or not user.is_active:
                await verify_password_async(password, PLACEHOLDER_HASH)
                return None

            if not await verify_password_async(password, credential.password):
                return None

            return UserRead.model_validate(user)


    async def update_user_email_by_id(
        self,
        id: str,
        email: str,
        db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as session:
            auth_row = await session.get(Auth, id)
            if auth_row is None:
                return False

            user_row = await session.get(User, id)
            if user_row is None:
                return False

            auth_row.email = email
            user_row.email = email
            await session.commit()
            return True
    async def update_user_password_by_id(
        self,
        id: str,
        new_password: str,
        db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as session:
            auth_row = await session.get(Auth, id)
            if auth_row is None:
                return False

            auth_row.password = get_password_hash(new_password)
            await session.commit()
            return True

    async def delete_auth_by_id(
        self,
        id: str,
        db: AsyncSession | None = None
    ) -> bool:
        async with get_async_db_context(db) as session:
            auth_row = await session.get(Auth, id)
            user_row = await session.get(User, id)
            if auth_row is None and user_row is None:
                return False

            await session.execute(delete(User).where(User.id == id))
            await session.execute(delete(Auth).where(Auth.id == id))
            await session.commit()
            return True


Auths = AuthsTable()
