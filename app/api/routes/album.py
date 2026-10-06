"""HTTP endpoints for the digital photo frame album (Tổng quan > khung ảnh)."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.album import AlbumPhotoRead, AlbumPhotoUpdate
from app.schemas.common import Message
from app.services import album_service as service

router = APIRouter(prefix="/album-photos", tags=["album"])


@router.get("", response_model=list[AlbumPhotoRead])
def list_photos(db: Session = Depends(get_db)):
    """All photos (metadata only), newest first."""
    return service.list_photos(db)


@router.post("", response_model=AlbumPhotoRead, status_code=201)
async def upload_photo(
    file: UploadFile = File(...),
    caption: str | None = Form(None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Upload one photo - it is auto-rotated and downscaled server-side."""
    content = await file.read()
    try:
        return service.upload_photo(db, content, file.filename, caption, actor_id=current.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{photo_id}/image")
def get_image(photo_id: int, size: str = "full", db: Session = Depends(get_db)):
    """The image bytes (JPEG). size=thumb for the small grid version. A photo
    never changes once uploaded, so browsers may cache it for a long time."""
    data = service.get_image(db, photo_id, thumb=(size == "thumb"))
    if data is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    return Response(
        content=data, media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


@router.patch("/{photo_id}", response_model=AlbumPhotoRead)
def update_photo(photo_id: int, payload: AlbumPhotoUpdate, db: Session = Depends(get_db)):
    row = service.update_caption(db, photo_id, payload.caption)
    if row is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    return row


@router.delete("/{photo_id}", response_model=Message)
def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    if not service.delete_photo(db, photo_id):
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh")
    return Message(detail="Đã xóa ảnh khỏi album")
