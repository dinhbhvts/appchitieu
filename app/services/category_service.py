"""Business logic for categories.

Categories can never be deleted (see the model's docstring for why) - there
is deliberately no delete_category() here. "Removing" one means hiding it
(is_active = False) via update_category().
"""

from sqlalchemy.orm import Session

from app.repositories import category_repository as repo
from app.schemas.category import CategoryCreate, CategoryUpdate


def list_categories(db: Session, include_inactive: bool = False):
    return repo.list_all(db, include_inactive=include_inactive)


def create_category(db: Session, payload: CategoryCreate, actor_id=None):
    data = payload.model_dump()
    data["updated_by"] = actor_id
    return repo.create(db, data)


def update_category(db: Session, category_id: int, payload: CategoryUpdate, actor_id=None):
    row = repo.get(db, category_id)
    if row is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    changes["updated_by"] = actor_id
    return repo.update(db, row, changes)
