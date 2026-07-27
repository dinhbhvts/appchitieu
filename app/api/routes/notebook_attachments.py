"""HTTP endpoints for "Hồ sơ đính kèm" (file attachments) on a notebook item."""

from pydantic import BaseModel

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.drive import DriveError, DriveNotConfigured
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import Message
from app.schemas.notebook_attachment import NotebookAttachmentRead
from app.services import notebook_attachment_service as service


class RenameAttachmentPayload(BaseModel):
    file_name: str

router = APIRouter(tags=["notebook-attachments"])


@router.post(
    "/notebook-items/{item_id}/attachments",
    response_model=NotebookAttachmentRead,
    status_code=201,
)
async def upload_attachment(
    item_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Upload one file (ảnh/PDF/Word) and attach it to a notebook item."""
    content = await file.read()
    try:
        return service.upload_attachment(
            db, item_id, file.filename or "file", file.content_type, content,
            actor_id=current.id,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DriveNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DriveError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/notebook-items/{item_id}/attachments",
    response_model=list[NotebookAttachmentRead],
)
def list_attachments(item_id: int, db: Session = Depends(get_db)):
    """List the (non-deleted) attachments on a notebook item."""
    return service.list_attachments(db, item_id)


@router.patch(
    "/notebook-attachments/{attachment_id}",
    response_model=NotebookAttachmentRead,
)
def rename_attachment(
    attachment_id: int,
    payload: RenameAttachmentPayload,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Rename an attachment - also renames the real file on Google Drive."""
    try:
        row = service.rename_attachment(db, attachment_id, payload.file_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DriveNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DriveError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy file đính kèm")
    return row


@router.delete("/notebook-attachments/{attachment_id}", response_model=Message)
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)):
    """Remove an attachment - deletes both the app's reference AND the real
    file on Google Drive (see NotebookAttachment.is_deleted)."""
    if not service.delete_attachment(db, attachment_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy file đính kèm")
    return Message(detail="Đã xóa file đính kèm")
