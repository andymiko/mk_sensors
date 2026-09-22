from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.admin import router as admin_router
from app.api.access import router as access_router
from app.api.objects import router as objects_router
from app.api.assignments import router as assignments_router
from app.api.dependencies import CurrentUser
from app.config import settings
from app.dbapi.base import get_async_session
from app.dbapi.models.auths import Auths
from app.schemas.auths import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.users import UserRead
from app.utils.security import create_access_token


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type"])
app.include_router(admin_router, prefix=settings.API_PREFIX)
app.include_router(access_router, prefix=settings.API_PREFIX)
app.include_router(objects_router, prefix=settings.API_PREFIX)
app.include_router(assignments_router, prefix=settings.API_PREFIX)


@app.post(f"{settings.API_PREFIX}/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Annotated[AsyncSession, Depends(get_async_session)]):
    try:
        return await Auths.insert_new_auth(str(request.email).lower(), request.password, request.name.strip(), db=db)
    except IntegrityError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким email уже существует") from None


@app.post(f"{settings.API_PREFIX}/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Annotated[AsyncSession, Depends(get_async_session)]):
    user = await Auths.authenticate_user(str(request.email).lower(), request.password, db=db)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль")
    return TokenResponse(access_token=create_access_token({"sub": user.id}), token_type="bearer")


@app.get(f"{settings.API_PREFIX}/me", response_model=UserRead)
async def me(current_user: CurrentUser):
    return current_user


@app.get(f"{settings.API_PREFIX}/health")
async def health():
    return {"status": "ok"}
