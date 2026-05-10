from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    filename: str
    url: str
    contentType: str | None = None
    sizeBytes: int | None = None
