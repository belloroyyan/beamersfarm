#!/usr/bin/env python3
"""Generate an app-server VAPID P-256 key pair without printing the private key."""

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRIVATE_KEY_PATH = PROJECT_ROOT / "instance" / "vapid_private.pem"


def main():
    PRIVATE_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if PRIVATE_KEY_PATH.exists():
        raise SystemExit(
            f"Refusing to overwrite existing private key: {PRIVATE_KEY_PATH}. "
            "Back it up and remove it manually only if you intend to rotate VAPID keys."
        )

    private_key = ec.generate_private_key(ec.SECP256R1())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    PRIVATE_KEY_PATH.write_bytes(private_pem)
    os.chmod(PRIVATE_KEY_PATH, 0o600)

    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_key = base64.urlsafe_b64encode(public_bytes).decode("ascii").rstrip("=")

    print("VAPID key pair generated. Keep the private PEM file secret and out of source control.")
    print(f"VAPID_PUBLIC_KEY={public_key}")
    print(f"VAPID_PRIVATE_KEY={PRIVATE_KEY_PATH}")
    print("VAPID_SUBJECT=mailto:your-real-operations-contact@example.com")
    print("For text-based deployment secrets, paste the full PEM file contents into the protected VAPID_PRIVATE_KEY setting; do not paste them into chat or source control.")


if __name__ == "__main__":
    main()
