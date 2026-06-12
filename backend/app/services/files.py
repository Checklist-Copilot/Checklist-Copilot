import io
import uuid
from contextlib import suppress
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Checklist
from app.db.models import File as FileModel

_PDF_TEXT_MAX_CHARS = 12_000

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


async def _download_from_supabase(bucket: str, storage_path: str) -> tuple[bytes, str]:
    """Fetch an object's bytes (and content-type) back from Supabase Storage."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase storage is not configured.",
        )

    download_url = f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}/{storage_path}"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(download_url, headers=headers)

    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Supabase download failed: {response.text}",
        )

    content_type = response.headers.get("content-type", "application/octet-stream")
    return response.content, content_type


async def fetch_file_bytes(file_row: FileModel) -> tuple[bytes, str]:
    """
    Download the raw bytes of a stored file. `file_row.file_name` doubles as
    the storage reference: "<bucket>/<user_id>/<file_id>.<ext>".
    """
    bucket, sep, storage_path = file_row.file_name.partition("/")
    if not sep or not storage_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file_name storage reference.",
        )
    return await _download_from_supabase(bucket, storage_path)


def build_file_url(file_id: uuid.UUID) -> str:
    """
    Canonical URL the frontend should use to fetch this file. The GET endpoint
    enforces auth and streams the bytes from Supabase.
    """
    return f"/api/files/{file_id}/raw"


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


def _validate_checklist_access(db: Session, checklist_id: uuid.UUID, user_id: uuid.UUID) -> None:
    stmt = select(Checklist.id).where(Checklist.id == checklist_id, Checklist.user_id == user_id)
    exists = db.scalar(stmt)
    if exists is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist not found or not owned by user: {checklist_id}",
        )


def list_files_for_checklist(
    db: Session,
    checklist_id: uuid.UUID,
    user_id: uuid.UUID,
    file_type: str | None = None,
) -> list[FileModel]:
    _validate_checklist_access(db, checklist_id, user_id)

    stmt = select(FileModel).where(FileModel.checklist_id == checklist_id, FileModel.user_id == user_id)
    if file_type is not None:
        stmt = stmt.where(FileModel.file_type == file_type)

    return list(db.scalars(stmt.order_by(FileModel.created_at.desc(), FileModel.id.desc())).all())


def _create_pending_file_metadata(
    db: Session,
    file_type: str,
    title: str | None,
    user_id: uuid.UUID,
    checklist_id: uuid.UUID | None,
) -> FileModel:
    file_row = FileModel(
        file_type=file_type,
        file_name="",
        title=title,
        user_id=user_id,
        checklist_id=checklist_id,
    )
    db.add(file_row)
    db.flush()
    return file_row


async def _upload_file_with_metadata_id(
    db: Session,
    file: UploadFile,
    content: bytes,
    file_type: str,
    bucket: str,
    ext: str,
    user_id: uuid.UUID,
    checklist_id: uuid.UUID | None,
) -> FileModel:
    file_row = _create_pending_file_metadata(db, file_type, file.filename, user_id, checklist_id)
    object_name = f"{user_id}/{file_row.id}{ext}"
    file_row.file_name = f"{bucket}/{object_name}"

    uploaded = False
    try:
        await _upload_to_supabase(bucket, object_name, file, content)
        uploaded = True
        db.commit()
    except Exception:
        db.rollback()
        if uploaded:
            with suppress(Exception):
                await _delete_from_supabase(bucket, object_name)
        raise

    db.refresh(file_row)
    return file_row


async def upload_image_file(
    db: Session,
    file: UploadFile,
    user_id: uuid.UUID,
    checklist_id: uuid.UUID | None = None,
) -> FileModel:
    if file.content_type not in _IMAGE_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG and JPEG images are allowed.")
    if checklist_id is not None:
        _validate_checklist_access(db, checklist_id, user_id)

    content = await file.read()
    ext = _extension_from_upload(file, ".png")
    return await _upload_file_with_metadata_id(
        db,
        file,
        content,
        "image",
        settings.SUPABASE_IMAGES_BUCKET,
        ext,
        user_id,
        checklist_id,
    )


async def upload_pdf_file(
    db: Session,
    file: UploadFile,
    user_id: uuid.UUID,
    checklist_id: uuid.UUID | None = None,
) -> FileModel:
    if file.content_type not in _PDF_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed.")
    if checklist_id is not None:
        _validate_checklist_access(db, checklist_id, user_id)

    content = await file.read()
    ext = _extension_from_upload(file, ".pdf")
    return await _upload_file_with_metadata_id(
        db,
        file,
        content,
        "pdf",
        settings.SUPABASE_PDFS_BUCKET,
        ext,
        user_id,
        checklist_id,
    )


def get_file_for_user(db: Session, file_id: uuid.UUID, user_id: uuid.UUID) -> FileModel | None:
    stmt = select(FileModel).where(FileModel.id == file_id, FileModel.user_id == user_id)
    return db.scalar(stmt)


def get_files_for_checklist(db: Session, checklist_id: uuid.UUID) -> list[FileModel]:
    stmt = select(FileModel).where(FileModel.checklist_id == checklist_id)
    return list(db.scalars(stmt).all())


def get_pdf_files_for_checklist(db: Session, checklist_id: uuid.UUID) -> list[FileModel]:
    stmt = select(FileModel).where(
        FileModel.checklist_id == checklist_id,
        FileModel.file_type == "pdf",
    )
    return list(db.scalars(stmt).all())


def extract_pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""

    reader = PdfReader(io.BytesIO(pdf_bytes))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    combined = "\n".join(parts)
    return combined[:_PDF_TEXT_MAX_CHARS]


async def delete_file_for_user(db: Session, file_row: FileModel) -> None:
    bucket, sep, storage_path = file_row.file_name.partition("/")
    if not sep or not storage_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file_name storage reference.")

    await _delete_from_supabase(bucket, storage_path)
    db.delete(file_row)
    db.commit()
