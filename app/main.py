"""FastAPI application entry point.

Run locally with:  uvicorn app.main:app --reload
Interactive docs:  http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed

# Importing app.models here ensures every table class is registered on Base
# before we call create_all(). Do not remove this import.
from app import models  # noqa: F401
from app.api.routes import (
    assets,
    auth,
    categories,
    notebook_items,
    reports,
    stocks,
    transactions,
    users,
)
from app.core.security import get_current_user

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook.

    On startup we make sure the tables exist and seed the default data. For a
    simple two-person app this "create tables on boot" approach is enough for
    development; production uses Alembic migrations instead (see alembic/).
    """
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)
    yield  # application runs while we are paused here


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Allow the Flutter app (a different origin) to call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
def health_check():
    """Simple endpoint to confirm the server is alive."""
    return {"status": "ok", "app": settings.app_name}


# Open endpoints (no login required): health check, login, and the user list
# (only names - needed by the login screen to offer a picker).
app.include_router(auth.router)
app.include_router(users.router)

# Protected endpoints: every data route requires a valid login token.
_auth = [Depends(get_current_user)]
app.include_router(assets.router, dependencies=_auth)
app.include_router(categories.router, dependencies=_auth)
app.include_router(notebook_items.router, dependencies=_auth)
app.include_router(transactions.router, dependencies=_auth)
app.include_router(stocks.router, dependencies=_auth)
app.include_router(reports.router, dependencies=_auth)
