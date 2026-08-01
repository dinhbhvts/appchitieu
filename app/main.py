"""FastAPI application entry point.

Run locally with:  uvicorn app.main:app --reload
Interactive docs:  http://127.0.0.1:8000/docs
"""

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings

logger = logging.getLogger("vibeapp")
from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed

# Importing app.models here ensures every table class is registered on Base
# before we call create_all(). Do not remove this import.
from app import models  # noqa: F401
from app.api.routes import (
    assets,
    auth,
    categories,
    lunar,
    notebook_attachments,
    notebook_items,
    notebook_types,
    reports,
    savings,
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

    NOTE: we deliberately do NOT run Alembic migrations automatically here.
    It looks tempting (it would remove the manual "don't forget to run
    `alembic upgrade head` after deploying" step - see the real incident this
    almost "fixed" in a past revision of this file), but testing it exposed a
    genuine data-loss risk: if `alembic_version` is ever out of sync with the
    database's actual shape (e.g. an interrupted migration, or a database
    whose tables were originally created via create_all() before Alembic was
    ever run against it - a state this project's own tables have been in
    before, see TRIEN_KHAI.md mục 3B), running "upgrade head" blind can apply
    a batch_alter_table step that DROPS a column Alembic doesn't expect to
    see yet, even though the column is already correctly there. That is an
    unacceptable risk for a personal finance app ("Dữ liệu phải an toàn" -
    style-guide.md) to take silently on every boot. Migrations stay a
    deliberate, manual, watched step (TRIEN_KHAI.md mục 3B) instead.
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


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all for any exception a route doesn't handle itself.

    Without this, an unhandled exception (e.g. a DB error, a bug in new
    code) crashes past FastAPI's normal error handling before the CORS
    middleware gets a chance to add its headers to the response - the
    browser then reports a generic, misleading "Failed to fetch" instead of
    the real error, because it treats the header-less response as a network
    failure rather than an HTTP error it can read.

    Registering a handler here (as opposed to letting Starlette's default
    ServerErrorMiddleware handle it) keeps the response INSIDE the
    middleware stack, so CORS headers are still attached and the frontend
    sees a normal JSON error it can display - instead of "Failed to fetch".

    The real traceback is logged server-side (visible in Render's logs) so
    the actual bug can be diagnosed; the client only gets a generic message
    plus the exception's short description (not a full traceback, to avoid
    leaking internals).
    """
    logger.error("Unhandled exception on %s %s:\n%s",
                 request.method, request.url.path, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Đã có lỗi xảy ra ở máy chủ. Vui lòng thử lại sau ít "
                       f"phút. Chi tiết: {exc.__class__.__name__}: {exc}"
        },
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
app.include_router(notebook_attachments.router, dependencies=_auth)
app.include_router(notebook_types.router, dependencies=_auth)
app.include_router(lunar.router, dependencies=_auth)
app.include_router(transactions.router, dependencies=_auth)
app.include_router(stocks.router, dependencies=_auth)
app.include_router(savings.router, dependencies=_auth)
app.include_router(reports.router, dependencies=_auth)
