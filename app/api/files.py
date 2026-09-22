import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File as UploadField, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import CurrentUser, require_permission
from app.config import settings
from app.dbapi.base import get_async_session
from app.dbapi.models.files import File, Files
from app.dbapi.models.users import User
from app.schemas.files import FileModel, FilePage

router = APIRouter(prefix="/files", tags=["files"])
Db = Annotated[AsyncSession, Depends(get_async_session)]


def _safe_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if settings.ALLOWED_EXTENSIONS and extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Тип файла не поддерживается")
    return extension


async def _owned_file(file_id: str, user: User, db: AsyncSession) -> File:
    record = await db.get(File, file_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не найден")
    if record.user_id != user.id and not user.is_admin():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к файлу")
    return record


@router.post("", response_model=FileModel, status_code=status.HTTP_201_CREATED)
async def upload_file(upload: Annotated[UploadFile, UploadField()], db: Db, current_user: Annotated[User, Depends(require_permission("file.upload"))]):
    original_name = Path(upload.filename or "file").name[:255]
    extension = _safe_extension(original_name)
    file_id = str(uuid.uuid4())
    stored_name = f"{file_id}{extension}"
    target = (settings.upload_dir / stored_name).resolve()
    if target.parent != settings.upload_dir.resolve():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Некорректное имя файла")
    size = 0
    try:
        with target.open("xb") as output:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_FILE_SIZE:
                    raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Файл превышает допустимый размер")
                output.write(chunk)
        record = File(id=file_id, user_id=current_user.id, original_name=original_name, stored_name=stored_name, path=str(target), size=size, content_type=(upload.content_type or "application/octet-stream")[:255])
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record
    except Exception:
        target.unlink(missing_ok=True)
        await db.rollback()
        raise
    finally:
        await upload.close()


@router.get("", response_model=FilePage)
async def list_files(current_user: CurrentUser, db: Db, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str | None = Query(None, max_length=255)):
    items, total = await Files.page(page=page, page_size=page_size, user_id=current_user.id, search=search, db=db)
    return FilePage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{file_id}/download")
async def download_file(file_id: str, current_user: CurrentUser, db: Db):
    record = await _owned_file(file_id, current_user, db)
    path = Path(record.path)
    if not path.is_file():
        raise HTTPException(status.HTTP_410_GONE, "Файл отсутствует в хранилище")
    return FileResponse(path, filename=record.original_name, media_type=record.content_type)


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(file_id: str, current_user: CurrentUser, db: Db):
    record = await _owned_file(file_id, current_user, db)
    path = Path(record.path)
    await db.delete(record)
    await db.commit()
    path.unlink(missing_ok=True)
