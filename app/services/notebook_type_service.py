"""Business logic for notebook types (danh mục tiện ích).

Mirrors category_service.py: no delete_type() on purpose - "removing" one
means hiding it (is_active = False) via update_type(), so existing
notebook_items rows never point at a type that vanished.
"""

import re
import unicodedata

from sqlalchemy.orm import Session

from app.repositories import notebook_type_repository as repo
from app.schemas.notebook_type import NotebookTypeCreate, NotebookTypeUpdate


def _slugify(name: str) -> str:
    """Turn a Vietnamese display name into a short ASCII machine key, e.g.
    "Tài khoản ngân hàng" -> "tai_khoan_ngan_hang". Users type Vietnamese;
    the key is an internal implementation detail they never see."""
    # Strip diacritics (NFD-decompose, drop combining marks).
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_only = "".join(c for c in decomposed if not unicodedata.combining(c))
    ascii_only = ascii_only.replace("đ", "d").replace("Đ", "D")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return slug or "loai"


def _unique_key(db: Session, base_key: str) -> str:
    """Append _2, _3, ... if base_key is already taken."""
    key = base_key
    n = 2
    while repo.get_by_key(db, key) is not None:
        key = f"{base_key}_{n}"
        n += 1
    return key


def list_types(db: Session, include_inactive: bool = False):
    return repo.list_all(db, include_inactive=include_inactive)


def create_type(db: Session, payload: NotebookTypeCreate, actor_id=None):
    key = _unique_key(db, _slugify(payload.name))
    data = {
        "key": key,
        "name": payload.name,
        "icon": payload.icon,
        "is_default": False,
        "updated_by": actor_id,
    }
    return repo.create(db, data)


def update_type(db: Session, type_id: int, payload: NotebookTypeUpdate, actor_id=None):
    row = repo.get(db, type_id)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_by"] = actor_id
    return repo.update(db, row, changes)
