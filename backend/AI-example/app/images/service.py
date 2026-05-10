import os
import uuid

from fastapi import HTTPException, UploadFile

from app.core.config import settings


ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
}


async def save_uploaded_image(file: UploadFile, user_id: int):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type")

    extension = file.filename.split(".")[-1] if file.filename else "bin"
    filename = f"{uuid.uuid4()}.{extension}"

    user_dir = os.path.join(settings.IMAGE_UPLOAD_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)

    path = os.path.join(user_dir, filename)

    content = await file.read()

    with open(path, "wb") as f:
        f.write(content)

    return {
        "filename": filename,
        "url": f"/uploads/images/{user_id}/{filename}",
        "contentType": file.content_type,
        "sizeBytes": len(content),
    }
