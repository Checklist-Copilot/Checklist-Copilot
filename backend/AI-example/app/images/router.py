from fastapi import APIRouter, Depends, File, UploadFile

from app.auth.service import get_current_user
from app.db.models import User
from app.images.service import save_uploaded_image


router = APIRouter()


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    return await save_uploaded_image(file, current_user.id)
