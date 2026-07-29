"""Secure password hashing using PBKDF2-HMAC-SHA256 (stdlib, no secrets in code).

Never stores or logs plaintext passwords. Algorithm string is versioned so
future migrations (argon2, bcrypt) can be added without breaking existing hashes.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 260_000
SALT_BYTES = 16
HASH_BYTES = 32


class PasswordHasher:
    """Provider-neutral password hasher with constant-time verification."""

    def __init__(self, *, iterations: int = DEFAULT_ITERATIONS) -> None:
        if iterations < 100_000:
            raise ValueError("iterations must be at least 100000 for security.")
        self._iterations = iterations

    def hash(self, password: str) -> str:
        if not password:
            raise ValueError("password must not be blank.")
        salt = secrets.token_bytes(SALT_BYTES)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self._iterations,
            dklen=HASH_BYTES,
        )
        return f"{ALGORITHM}${self._iterations}${salt.hex()}${digest.hex()}"

    def verify(self, password: str, password_hash: str) -> bool:
        if not password or not password_hash:
            return False
        try:
            algorithm, iterations_s, salt_hex, digest_hex = password_hash.split("$", 3)
        except ValueError:
            return False
        if algorithm != ALGORITHM:
            return False
        try:
            iterations = int(iterations_s)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except ValueError:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)


_DEFAULT_HASHER = PasswordHasher()


def hash_password(password: str) -> str:
    return _DEFAULT_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _DEFAULT_HASHER.verify(password, password_hash)
