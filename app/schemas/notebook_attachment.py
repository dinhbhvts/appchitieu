"""Pydantic schemas for NotebookAttachment ("Hồ sơ đính kèm")."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotebookAttachmentRead(BaseModel):
    id: int
    notebook_item_id: int
    file_name: str
    mime_type: str | None = None
    size_bytes: int | None = None
    drive_link: str | None = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
