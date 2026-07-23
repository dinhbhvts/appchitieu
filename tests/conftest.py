"""Pytest fixtures.

We point the app at a temporary, throwaway SQLite database so tests never touch
your real data. The DATABASE_URL environment variable is set BEFORE the app is
imported, so the app picks up the test database.
"""

import os
import tempfile

import pytest

# Create a temp file and tell the app to use it - must happen before imports.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """A fresh database + test client for each test function."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Seed the default users/categories, same as a real startup would.
    from app.core.database import SessionLocal
    from app.core.seed import seed

    with SessionLocal() as db:
        seed(db)
        # Grab the first user's id so we can log the test client in.
        from app.models.user import User
        first_user_id = db.query(User).order_by(User.id).first().id

    # Protected endpoints now require a login token, so attach one for every
    # request the test client makes.
    from app.core.security import create_access_token
    token = create_access_token(first_user_id)

    with TestClient(app) as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c
