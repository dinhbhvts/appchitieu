"""Business logic for the family notebook (NotebookItem)."""

from sqlalchemy.orm import Session

from app.models.enums import NotebookItemType
from app.repositories import notebook_item_repository as repo
from app.schemas.notebook_item import NotebookItemCreate, NotebookItemUpdate


def list_items(db: Session, type: NotebookItemType | None = None, q: str | None = None):
    return repo.list_all(db, type=type, q=q)


def create_item(db: Session, payload: NotebookItemCreate, actor_id=None):
    data = payload.model_dump()
    data["updated_by"] = actor_id
    return repo.create(db, data)


def update_item(db: Session, item_id: int, payload: NotebookItemUpdate, actor_id=None):
    row = repo.get(db, item_id)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_by"] = actor_id
    return repo.update(db, row, changes)


def delete_item(db: Session, item_id: int) -> bool:
    row = repo.get(db, item_id)
    if row is None:
        return False
    repo.delete(db, row)
    return True
