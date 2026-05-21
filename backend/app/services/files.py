import uuid
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import File as FileModel

_IMAGE_CONTENT_TYPES = {"image/png", "image/jpeg"}
_PDF_CONTENT_TYPES = {"application/pdf"}


def _extension_from_upload(file: UploadFile, default_ext: str) -> str:
    if file.filename:
        suffix = Path(file.filename).suffix.lower()
        if suffix:
            return suffix
    return default_ext


async def _upload_to_supabase(bucket: str, storage_path: str, file: UploadFile, content: bytes) -> None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage is not configured.",
        )

    upload_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": file.content_type or "application/octet-stream",
        "x-upsert": "false",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(upload_url, headers=headers, content=content)

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase upload failed: {response.text}",
        )


async def _delete_from_supabase(bucket: str, storage_path: str) -> None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage is not configured.",
        )

    delete_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"prefixes": [storage_path]}

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.request("DELETE", delete_url, headers=headers, json=payload)

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase delete failed: {response.text}",
        )

    # Supabase returns the deleted objects list; enforce that at least one object was deleted.
    try:
        deleted = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase delete returned non-JSON response: {response.text}",
        ) from exc

    if not isinstance(deleted, list) or len(deleted) == 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase delete did not remove object at path: {storage_path}",
        )


def _persist_file_metadata(db: Session, file_type: str, file_name: str, user_id: uuid.UUID) -> FileModel:
    file_row = FileModel(file_type=file_type, file_name=file_name, user_id=user_id)
    db.add(file_row)
    db.commit()
    db.refresh(file_row)
    return file_row


async def upload_image_file(db: Session, file: UploadFile, user_id: uuid.UUID) -> FileModel:
    if file.content_type not in _IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG and JPEG images are allowed.")

    content = await file.read()
    ext = _extension_from_upload(file, ".png")
    object_name = f"{user_id}/{uuid.uuid4()}{ext}"

    await _upload_to_supabase(settings.SUPABASE_IMAGES_BUCKET, object_name, file, content)
    return _persist_file_metadata(db, "image", f"{settings.SUPABASE_IMAGES_BUCKET}/{object_name}", user_id)


async def upload_pdf_file(db: Session, file: UploadFile, user_id: uuid.UUID) -> FileModel:
    if file.content_type not in _PDF_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed.")

    content = await file.read()
    ext = _extension_from_upload(file, ".pdf")
    object_name = f"{user_id}/{uuid.uuid4()}{ext}"

    await _upload_to_supabase(settings.SUPABASE_PDFS_BUCKET, object_name, file, content)
    return _persist_file_metadata(db, "pdf", f"{settings.SUPABASE_PDFS_BUCKET}/{object_name}", user_id)


def get_file_for_user(db: Session, file_id: uuid.UUID, user_id: uuid.UUID) -> FileModel | None:
    stmt = select(FileModel).where(FileModel.id == file_id, FileModel.user_id == user_id)
    print(f"[files.get_file_for_user] file_id={file_id} user_id={user_id}")
    return db.scalar(stmt)


async def delete_file_for_user(db: Session, file_row: FileModel) -> None:
    bucket, sep, storage_path = file_row.file_name.partition("/")
    if not sep or not storage_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file_name storage reference.")

    await _delete_from_supabase(bucket, storage_path)
    db.delete(file_row)
    db.commit()
