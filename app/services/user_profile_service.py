"""Business logic for Cấu hình > Người dùng: màu đại diện + avatar.

Avatar có 3 dạng (users.avatar_preset):
  - None        -> frontend hiện chữ cái đầu tên trên nền màu đại diện;
  - "chibi:N"   -> ảnh chibi gợi ý thứ N (vẽ sẵn ở frontend, 0..CHIBI_COUNT-1);
  - "upload"    -> ảnh người dùng tải lên, cắt vuông giữa + thu nhỏ còn
                   AVATAR_SIDE px JPEG, lưu ở users.avatar_data.
"""

import io
import re
from datetime import datetime

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session, undefer
from sqlalchemy import select

from app.models.user import User
from app.services.album_service import MAX_UPLOAD_BYTES, _to_rgb

CHIBI_COUNT = 11  # khớp CHIBI_SVGS (preview.html) / bootChibiEmojis (Flutter)
AVATAR_SIDE = 256
AVATAR_QUALITY = 85
_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
_CHIBI_RE = re.compile(r"^chibi:(\d{1,2})$")


def update_profile(db: Session, user: User, changes: dict) -> User:
    """Apply color / avatar_preset (only keys present in `changes`).
    Raises ValueError (Vietnamese message) on invalid values."""
    if "color" in changes:
        color = (changes["color"] or "").strip()
        if color and not _COLOR_RE.match(color):
            raise ValueError("Màu không hợp lệ (dạng #RRGGBB)")
        user.color = color.upper() or None
    if "avatar_preset" in changes:
        preset = (changes["avatar_preset"] or "").strip()
        if preset:
            m = _CHIBI_RE.match(preset)
            if not m or int(m.group(1)) >= CHIBI_COUNT:
                raise ValueError("Avatar gợi ý không hợp lệ")
            user.avatar_preset = preset
        else:
            user.avatar_preset = None
        user.avatar_data = None
        user.avatar_updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    return user


def _square_avatar(content: bytes) -> bytes:
    if not content:
        raise ValueError("File rỗng")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError("Ảnh quá lớn (tối đa 20MB)")
    try:
        img = Image.open(io.BytesIO(content))
        img.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError):
        raise ValueError("Không đọc được file ảnh - chỉ nhận ảnh JPG, PNG, WEBP.")
    img = _to_rgb(ImageOps.exif_transpose(img))
    img = ImageOps.fit(img, (AVATAR_SIDE, AVATAR_SIDE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=AVATAR_QUALITY, optimize=True)
    return buf.getvalue()


def upload_avatar(db: Session, user: User, content: bytes) -> User:
    user.avatar_data = _square_avatar(content)
    user.avatar_preset = "upload"
    user.avatar_updated_at = datetime.now()
    db.commit()
    db.refresh(user)
    return user


def get_avatar_image(db: Session, user_id: int) -> bytes | None:
    row = db.scalar(select(User).options(undefer(User.avatar_data)).where(User.id == user_id))
    if row is None or row.avatar_preset != "upload":
        return None
    return row.avatar_data
