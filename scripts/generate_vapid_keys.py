"""Generate a VAPID key pair for Web Push notifications (thông báo nhắc sự
kiện sắp tới - xem app/services/push_service.py).

Run ONCE (on your own machine, not the server):
    python -m scripts.generate_vapid_keys

Prints two values - paste them as environment variables on Render:
    VAPID_PUBLIC_KEY  = ...
    VAPID_PRIVATE_KEY = ...

Do NOT regenerate these after devices have subscribed - every existing
subscription would need to re-subscribe (the public key is baked into each
browser's push subscription at creation time). See TRIEN_KHAI.md mục 7.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from py_vapid import Vapid02 as Vapid  # noqa: E402
from cryptography.hazmat.primitives import serialization  # noqa: E402


def run() -> None:
    v = Vapid()
    v.generate_keys()

    # Public key: raw uncompressed EC point, base64url (no padding) - the
    # exact format browsers require for PushManager.subscribe()'s
    # applicationServerKey.
    raw_public = v.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(raw_public).rstrip(b"=").decode()

    # Private key: raw 32-byte scalar, base64url (no padding) - the format
    # py_vapid.Vapid.from_string() (used by pywebpush) expects when given a
    # plain string instead of a PEM file path.
    private_value = v.private_key.private_numbers().private_value
    private_b64 = base64.urlsafe_b64encode(
        private_value.to_bytes(32, "big")
    ).rstrip(b"=").decode()

    print("Dan 2 dong nay vao Environment cua Render (Muc 7 trong TRIEN_KHAI.md):\n")
    print(f"VAPID_PUBLIC_KEY={public_b64}")
    print(f"VAPID_PRIVATE_KEY={private_b64}")


if __name__ == "__main__":
    run()
