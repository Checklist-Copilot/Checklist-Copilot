import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.schemas.file import FileDeleteResponse, FileRead, FileUploadResponse
from app.services.auth import get_current_user
from app.services.files import (
    build_file_url,
    delete_file_for_user,
    fetch_file_bytes,
    get_file_for_user,
    upload_image_file,
    upload_pdf_file,
)


router = APIRouter(prefix="/files")


@router.post("/upload/image", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image_route(
    file: UploadFile = File(...),
    checklist_id: uuid.UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileUploadResponse:
    file_row = await upload_image_file(db, file, current_user.id, checklist_id)
    return FileUploadResponse(
        **FileRead.model_validate(file_row).model_dump(),
        url=build_file_url(file_row.id),
    )


@router.post("/upload/pdf", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf_route(
    file: UploadFile = File(...),
    checklist_id: uuid.UUID | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileUploadResponse:
    file_row = await upload_pdf_file(db, file, current_user.id, checklist_id)
    return FileUploadResponse(
        **FileRead.model_validate(file_row).model_dump(),
        url=build_file_url(file_row.id),
    )


@router.get("/{file_id}/raw")
async def get_file_raw_route(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """
    Stream the raw bytes of a stored file. The frontend uses this to render
    images (e.g. an `imageBlock.images[].url`) and to feed images to the AI
    /observe endpoint. Ownership is enforced — non-owners get 404.
    """
    file_row = get_file_for_user(db, file_id, current_user.id)
    if file_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    content, content_type = await fetch_file_bytes(file_row)
    return Response(content=content, media_type=content_type)


@router.delete("/delete_file/{file_id}", response_model=FileDeleteResponse)
async def delete_file_route(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileDeleteResponse:
    file_row = get_file_for_user(db, file_id, current_user.id)
    if file_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    await delete_file_for_user(db, file_row)
    return FileDeleteResponse(message="File deleted successfully.")
