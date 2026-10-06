"""Business logic for the digital photo frame album (khung ảnh kỹ thuật số).

Every uploaded image is re-encoded server-side with Pillow into:
  - a display JPEG, longest side at most DISPLAY_MAX_SIDE px;
  - a thumbnail JPEG, longest side at most THUMB_MAX_SIDE px.
Only these processed copies are stored (in the database - see the
AlbumPhoto model docstring for why), never the original file. The phone's
EXIF rotation is applied first so portrait photos are not shown sideways.
"""

import io

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.models.album_photo import AlbumPhoto
from app.repositories import album_repository as repo

# HEIC/HEIF (default iPhone photo format) only if the optional pillow-heif
# plugin is installed - otherwise such files are rejected with a clear message.
try:  # pragma: no cover - depends on an optional package
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:  # noqa: BLE001
    pass

DISPLAY_MAX_SIDE = 1280
THUMB_MAX_SIDE = 320
DISPLAY_QUALITY = 82
THUMB_QUALITY = 75
# Limit on the ORIGINAL upload (before downscaling). Phone photos are usually
# 3-8 MB; the web app already shrinks images in the browser before sending.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_CAPTION_LEN = 200


def _to_rgb(img: Image.Image) -> Image.Image:
    """Flatten transparency onto white and convert to RGB (JPEG has no alpha)."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        return bg
    return img.convert("RGB")


def _encode(img: Image.Image, max_side: int, quality: int) -> tuple[bytes, int, int]:
    copy = img.copy()
    copy.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    copy.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue(), copy.width, copy.height


def process_image(content: bytes) -> dict:
    """Decode, auto-rotate and downscale an uploaded image. Raises ValueError
    with a Vietnamese message if the file is not a usable image."""
    if not content:
        raise ValueError("File rỗng")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Ảnh quá lớn (tối đa 20MB)")
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise ValueError(
            "Không đọc được file ảnh - chỉ nhận ảnh JPG, PNG, WEBP (ảnh HEIC của "
            "iPhone hãy chọn định dạng 'Tương thích nhất' hoặc gửi qua bản web)."
        )
    img = ImageOps.exif_transpose(img)
    img = _to_rgb(img)
    display, w, h = _encode(img, DISPLAY_MAX_SIDE, DISPLAY_QUALITY)
    thumb, _, _ = _encode(img, THUMB_MAX_SIDE, THUMB_QUALITY)
    return {"image_data": display, "thumb_data": thumb, "width": w, "height": h,
            "size_bytes": len(display)}


def _clean_caption(caption: str | None) -> str | None:
    caption = (caption or "").strip()
    return caption[:MAX_CAPTION_LEN] or None


def upload_photo(db: Session, content: bytes, file_name: str | None,
                 caption: str | None = None, actor_id: int | None = None) -> AlbumPhoto:
    data = process_image(content)
    data.update({
        "file_name": (file_name or "")[:255] or None,
        "caption": _clean_caption(caption),
        "uploaded_by": actor_id,
    })
    return repo.create(db, data)


def list_photos(db: Session) -> list[AlbumPhoto]:
    return repo.list_all(db)


def get_image(db: Session, photo_id: int, thumb: bool = False) -> bytes | None:
    row = repo.get(db, photo_id, with_data=True)
    if row is None:
        return None
    return row.thumb_data if thumb else row.image_data


def update_caption(db: Session, photo_id: int, caption: str | None) -> AlbumPhoto | None:
    row = repo.get(db, photo_id)
    if row is None:
        return None
    return repo.update(db, row, {"caption": _clean_caption(caption)})


def delete_photo(db: Session, photo_id: int) -> bool:
    row = repo.get(db, photo_id)
    if row is None:
        return False
    repo.delete(db, row)
    return True
