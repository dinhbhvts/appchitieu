"""Pydantic schemas for the digital photo frame album (AlbumPhoto)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlbumPhotoRead(BaseModel):
    """Photo metadata only - the image bytes are fetched separately via
    GET /album-photos/{id}/image (so listing stays lightweight)."""

    id: int
    caption: str | None = None
    file_name: str | None = None
    width: int
    height: int
    size_bytes: int
    uploaded_by: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlbumPhotoUpdate(BaseModel):
    caption: str | None = None
