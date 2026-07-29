"""Unit tests for PasswordHasher — hashing, verification, and format guarantees."""

from __future__ import annotations

import pytest
from app.auth.password import (
    ALGORITHM,
    DEFAULT_ITERATIONS,
    PasswordHasher,
    hash_password,
    verify_password,
)


class TestHashAndVerify:
    def test_hash_and_verify_round_trip(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("CorrectHorse123!")
        assert hasher.verify("CorrectHorse123!", digest) is True

    def test_verify_wrong_password_fails(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("CorrectHorse123!")
        assert hasher.verify("WrongPassword456!", digest) is False

    def test_verify_case_sensitive(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("CorrectHorse123!")
        assert hasher.verify("correcthorse123!", digest) is False

    def test_hash_blank_password_raises(self) -> None:
        hasher = PasswordHasher()
        with pytest.raises(ValueError):
            hasher.hash("")

    def test_verify_blank_password_returns_false(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("SomePassword123!")
        assert hasher.verify("", digest) is False

    def test_verify_blank_hash_returns_false(self) -> None:
        hasher = PasswordHasher()
        assert hasher.verify("SomePassword123!", "") is False

    def test_verify_none_like_empty_hash_returns_false(self) -> None:
        hasher = PasswordHasher()
        assert hasher.verify("SomePassword123!", None) is False  # type: ignore[arg-type]


class TestSaltsAndFormat:
    def test_different_salts_produce_different_hashes(self) -> None:
        hasher = PasswordHasher()
        first = hasher.hash("SamePassword123!")
        second = hasher.hash("SamePassword123!")
        assert first != second

    def test_both_salted_hashes_still_verify(self) -> None:
        hasher = PasswordHasher()
        first = hasher.hash("SamePassword123!")
        second = hasher.hash("SamePassword123!")
        assert hasher.verify("SamePassword123!", first) is True
        assert hasher.verify("SamePassword123!", second) is True

    def test_hash_format_has_four_dollar_separated_segments(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("FormatCheck123!")
        parts = digest.split("$")
        assert len(parts) == 4

    def test_algorithm_prefix_is_pbkdf2_sha256(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("FormatCheck123!")
        algorithm, _, _, _ = digest.split("$", 3)
        assert algorithm == "pbkdf2_sha256"
        assert algorithm == ALGORITHM

    def test_salt_segment_is_valid_hex(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("FormatCheck123!")
        _, _, salt_hex, _ = digest.split("$", 3)
        # Should not raise.
        bytes.fromhex(salt_hex)
        assert len(bytes.fromhex(salt_hex)) == 16

    def test_digest_segment_is_valid_hex(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("FormatCheck123!")
        _, _, _, digest_hex = digest.split("$", 3)
        bytes.fromhex(digest_hex)
        assert len(bytes.fromhex(digest_hex)) == 32

    def test_iterations_segment_matches_configured_iterations(self) -> None:
        hasher = PasswordHasher(iterations=150_000)
        digest = hasher.hash("FormatCheck123!")
        _, iterations_s, _, _ = digest.split("$", 3)
        assert int(iterations_s) == 150_000

    def test_hash_does_not_contain_plaintext_password(self) -> None:
        hasher = PasswordHasher()
        password = "SuperSecretPlaintext123!"
        digest = hasher.hash(password)
        assert password not in digest


class TestIterationsFloor:
    def test_default_iterations_meet_security_floor(self) -> None:
        assert DEFAULT_ITERATIONS >= 100_000

    def test_iterations_below_floor_raises(self) -> None:
        with pytest.raises(ValueError):
            PasswordHasher(iterations=99_999)

    def test_iterations_at_floor_is_allowed(self) -> None:
        hasher = PasswordHasher(iterations=100_000)
        digest = hasher.hash("BoundaryCheck123!")
        assert hasher.verify("BoundaryCheck123!", digest) is True

    def test_custom_high_iterations_respected_and_verifiable(self) -> None:
        hasher = PasswordHasher(iterations=310_000)
        digest = hasher.hash("HighIterations123!")
        _, iterations_s, _, _ = digest.split("$", 3)
        assert int(iterations_s) == 310_000
        assert hasher.verify("HighIterations123!", digest) is True


class TestVerifyRobustness:
    def test_verify_rejects_unknown_algorithm(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("Password123!")
        _, iterations_s, salt_hex, digest_hex = digest.split("$", 3)
        tampered = f"bcrypt${iterations_s}${salt_hex}${digest_hex}"
        assert hasher.verify("Password123!", tampered) is False

    def test_verify_rejects_malformed_hash_missing_segments(self) -> None:
        hasher = PasswordHasher()
        assert hasher.verify("Password123!", "pbkdf2_sha256$260000$abcd") is False

    def test_verify_rejects_non_numeric_iterations(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("Password123!")
        _, _, salt_hex, digest_hex = digest.split("$", 3)
        tampered = f"pbkdf2_sha256$notanumber${salt_hex}${digest_hex}"
        assert hasher.verify("Password123!", tampered) is False

    def test_verify_rejects_non_hex_salt(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("Password123!")
        _, iterations_s, _, digest_hex = digest.split("$", 3)
        tampered = f"pbkdf2_sha256${iterations_s}$zzzznothex${digest_hex}"
        assert hasher.verify("Password123!", tampered) is False

    def test_verify_tampered_digest_fails(self) -> None:
        hasher = PasswordHasher()
        digest = hasher.hash("Password123!")
        algorithm, iterations_s, salt_hex, digest_hex = digest.split("$", 3)
        flipped = ("0" if digest_hex[0] != "0" else "1") + digest_hex[1:]
        tampered = f"{algorithm}${iterations_s}${salt_hex}${flipped}"
        assert hasher.verify("Password123!", tampered) is False


class TestModuleLevelHelpers:
    def test_module_level_hash_password_and_verify_password(self) -> None:
        digest = hash_password("ModuleLevel123!")
        assert verify_password("ModuleLevel123!", digest) is True

    def test_module_level_verify_wrong_password_fails(self) -> None:
        digest = hash_password("ModuleLevel123!")
        assert verify_password("WrongOne456!", digest) is False

    def test_module_level_helpers_use_default_algorithm(self) -> None:
        digest = hash_password("ModuleLevel123!")
        assert digest.startswith(f"{ALGORITHM}$")
