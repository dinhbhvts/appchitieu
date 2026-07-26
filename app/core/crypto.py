"""Reversible encryption for sensitive notebook fields.

Login passwords (app.core.security) are hashed one-way - the server can
verify them but never read them back. Saved THIRD-PARTY account passwords
(the "Tài khoản" notebook utility - e.g. a saved Wifi or banking login) are
different: the couple needs to look them up again later, so they must be
decryptable. We use symmetric encryption (Fernet: AES128-CBC + HMAC) instead
of hashing for that one field.
"""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

settings = get_settings()


def _fernet() -> Fernet:
    """Build the Fernet cipher from ACCOUNT_ENCRYPTION_KEY.

    Fernet requires a 32-byte urlsafe-base64 key. Rather than force the .env
    value to already be in that exact format, we derive a stable 32-byte key
    from whatever string is configured via SHA-256 - this lets a plain
    passphrase be used in production while still producing a valid Fernet key.
    """
    raw = settings.account_encryption_key.encode("utf-8")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_text(plain: str | None) -> str | None:
    """Encrypt a string for storage. None passes through unchanged (nothing
    to encrypt - e.g. a notebook item that has no password set)."""
    if plain is None or plain == "":
        return None
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_text(cipher: str | None) -> str | None:
    """Decrypt a string previously produced by encrypt_text(). Returns None
    if there was nothing encrypted, or if it can't be decrypted (e.g. the
    encryption key was rotated after this row was saved) - fails safe
    instead of crashing the whole list."""
    if cipher is None:
        return None
    try:
        return _fernet().decrypt(cipher.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
