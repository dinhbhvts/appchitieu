"""Application configuration.

This module centralizes every configurable value (database URL, app name,
CORS origins) in a single place. We read them from environment variables so the
same code runs unchanged on a laptop (SQLite) and on a cloud server
(PostgreSQL). Nothing else in the codebase should read os.environ directly.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings.

    pydantic-settings automatically loads matching keys from a local ".env"
    file and from real environment variables (env vars win over the file).
    """

    # Human-friendly name shown in the auto-generated API docs.
    app_name: str = "VibeApp - Quan ly thu chi"

    # Database connection string.
    # - Development default: a local SQLite file (no server needed).
    # - Production: set DATABASE_URL to a PostgreSQL URL, e.g.
    #   postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = "sqlite:///./vibeapp.db"

    # Origins allowed to call this API from a browser (CORS).
    # "*" is fine while developing; tighten it in production.
    cors_origins: str = "*"

    # Secret key used to sign login tokens (JWT). MUST be overridden in
    # production by setting the SECRET_KEY environment variable to a long
    # random string. If it leaks, anyone could forge a login.
    secret_key: str = "dev-only-change-me-in-production"

    # How long a login stays valid, in days. 30 days keeps a family app
    # convenient (no daily re-login) while still expiring eventually.
    access_token_expire_days: int = 30

    # Key used to REVERSIBLY encrypt sensitive notebook fields (currently:
    # saved account passwords in the "Sổ tay" / "Tài khoản" utility). This is
    # different from secret_key (used for one-way login token signing) -
    # MUST be overridden in production via the ACCOUNT_ENCRYPTION_KEY env
    # var, and must NOT change afterwards or previously-saved passwords
    # become unreadable.
    account_encryption_key: str = "dev-only-change-me-in-production-acct-key"

    # Google Drive attachment storage (Sổ tay > Thông tin cá nhân > Hồ sơ đính
    # kèm). Uses OAuth2 as the app owner's OWN Google account (a stored
    # refresh token), NOT a service account - Google service accounts have
    # zero storage quota of their own and cannot create files in a regular
    # "My Drive" folder (only in a paid Google Workspace Shared Drive), so a
    # service account fundamentally cannot work here for a personal Gmail
    # account. See TRIEN_KHAI.md mục 3C for the one-time setup (run
    # backend/scripts/get_drive_refresh_token.py once to obtain the refresh
    # token). All empty = attachment upload is disabled (returns a clear
    # error), everything else in the app still works.
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_refresh_token: str = ""
    google_drive_folder_id: str = ""

    # Web Push (thông báo nhắc sự kiện sắp tới - xem app/services/push_service.py).
    # VAPID key pair identifies THIS server to the browser's push service
    # (FCM/APNs); generate once with `python -m scripts.generate_vapid_keys`
    # and set both as env vars in production - see TRIEN_KHAI.md mục 7. The
    # public key is safe to expose (served via GET /push/vapid-public-key);
    # the private key must stay secret. Empty = push notifications disabled
    # (subscribe/send just no-op with a clear error), everything else in the
    # app still works.
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    # Contact email required by the Web Push protocol (RFC 8292 "sub"
    # claim) - shown to browser vendors only if they need to contact the
    # server owner about abuse; not shown to the end user.
    vapid_claim_email: str = "admin@example.com"
    # Shared secret the daily GitHub Actions workflow sends in the
    # "X-Cron-Secret" header to POST /push/run-daily - that endpoint has no
    # logged-in user (it's a server-to-server call), so this is its only
    # gate. MUST be overridden in production (empty = endpoint refuses every
    # call, so an unset secret fails closed, not open).
    notify_cron_secret: str = ""
    # How many days ahead counts as "sắp tới" for the daily reminder push
    # (matches the user's request: "trong vòng 3 ngày sắp có sự kiện").
    push_reminder_days: int = 3

    # Tell pydantic to read a ".env" file sitting next to where we run the app.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return a single, cached Settings instance.

    lru_cache guarantees the .env file is parsed only once per process, and
    every caller shares the exact same object.
    """
    return Settings()
