"""Unit tests for AuthService — register, login, logout, sessions, and security hooks."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from app.auth.security import AuditLogger, RateLimiterHook
from app.auth.service import AuthService
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformConflictError,
    UserPlatformRateLimitError,
    UserPlatformValidationError,
)
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore

DEMO_EMAIL = "student@example.com"


class _MutableClock:
    """Deterministic, manually advanceable clock for session TTL tests."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now = self._now + timedelta(**kwargs)


def make_auth(
    *,
    clock: Callable[[], datetime] | None = None,
    session_ttl_seconds: int = 3600,
    remember_me_ttl_seconds: int = 2_592_000,
    rate_limiter: RateLimiterHook | None = None,
    seed: bool = True,
) -> tuple[AuthService, InMemoryUserPlatformStore]:
    store = InMemoryUserPlatformStore()
    if seed:
        seed_demo_users(store)
    auth = AuthService(
        users=store.users,
        sessions=store.sessions,
        profiles=store.profiles,
        password_resets=store.password_resets,
        email_verifications=store.email_verifications,
        audit=AuditLogger(store.audit),
        clock=clock,
        session_ttl_seconds=session_ttl_seconds,
        remember_me_ttl_seconds=remember_me_ttl_seconds,
        rate_limiter=rate_limiter,
    )
    return auth, store


class TestRegister:
    def test_register_creates_user_and_session(self) -> None:
        auth, _store = make_auth(seed=False)
        result = auth.register(
            email="new.user@example.com",
            password="ValidPass123!",
            display_name="New User",
        )
        assert result.user.email == "new.user@example.com"
        assert result.user.display_name == "New User"
        assert result.access_token
        assert result.session.user_id == result.user.user_id

    def test_register_normalizes_email_case_and_whitespace(self) -> None:
        auth, _store = make_auth(seed=False)
        result = auth.register(
            email="  Mixed.Case@Example.com  ",
            password="ValidPass123!",
            display_name="Mixed Case",
        )
        assert result.user.email == "mixed.case@example.com"

    def test_register_duplicate_email_raises_conflict(self) -> None:
        auth, _store = make_auth()
        with pytest.raises(UserPlatformConflictError):
            auth.register(
                email=DEMO_EMAIL,
                password="ValidPass123!",
                display_name="Duplicate",
            )

    def test_register_weak_password_too_short_raises(self) -> None:
        auth, _store = make_auth(seed=False)
        with pytest.raises(UserPlatformValidationError):
            auth.register(email="short@example.com", password="Sh0rt!", display_name="Short")

    def test_register_password_missing_digit_raises(self) -> None:
        auth, _store = make_auth(seed=False)
        with pytest.raises(UserPlatformValidationError):
            auth.register(
                email="nodigits@example.com",
                password="NoDigitsHere!",
                display_name="No Digits",
            )

    def test_register_password_missing_mixed_case_raises(self) -> None:
        auth, _store = make_auth(seed=False)
        with pytest.raises(UserPlatformValidationError):
            auth.register(
                email="lower@example.com",
                password="alllowercase123",
                display_name="Lower",
            )

    def test_register_invalid_email_raises_validation(self) -> None:
        auth, _store = make_auth(seed=False)
        with pytest.raises(UserPlatformValidationError):
            auth.register(
                email="not-an-email",
                password="ValidPass123!",
                display_name="Bad Email",
            )

    def test_register_blank_display_name_raises(self) -> None:
        auth, _store = make_auth(seed=False)
        with pytest.raises(UserPlatformValidationError):
            auth.register(
                email="blank.name@example.com",
                password="ValidPass123!",
                display_name="   ",
            )

    def test_register_bootstraps_profile_and_settings(self) -> None:
        auth, store = make_auth(seed=False)
        result = auth.register(
            email="profiled@example.com",
            password="ValidPass123!",
            display_name="Profiled",
        )
        profile = store.profiles.get_profile(result.user.user_id)
        settings = store.profiles.get_settings(result.user.user_id)
        assert profile is not None
        assert settings is not None

    def test_register_password_never_stored_plaintext(self) -> None:
        auth, store = make_auth(seed=False)
        result = auth.register(
            email="secure@example.com",
            password="ValidPass123!",
            display_name="Secure",
        )
        stored = store.users.get_by_id(result.user.user_id)
        assert stored is not None
        assert "ValidPass123!" not in stored.password_hash


class TestLogin:
    def test_login_success_returns_auth_result(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        assert result.user.email == DEMO_EMAIL
        assert result.access_token
        assert result.session.revoked is False

    def test_login_bad_password_raises_auth_error(self) -> None:
        auth, _store = make_auth()
        with pytest.raises(UserPlatformAuthError):
            auth.login(email=DEMO_EMAIL, password="WrongPassword123!")

    def test_login_unknown_email_raises_auth_error(self) -> None:
        auth, _store = make_auth()
        with pytest.raises(UserPlatformAuthError):
            auth.login(email="ghost@example.com", password="WhoKnows123!")

    def test_login_inactive_user_raises_auth_error(self) -> None:
        auth, store = make_auth()
        user = store.users.get_by_email(DEMO_EMAIL)
        assert user is not None
        from dataclasses import replace

        store.users.save(replace(user, is_active=False))
        with pytest.raises(UserPlatformAuthError):
            auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)

    def test_login_remember_me_uses_longer_ttl(self) -> None:
        clock = _MutableClock(datetime(2026, 7, 29, 12, 0, tzinfo=UTC))
        auth, _store = make_auth(
            clock=clock,
            session_ttl_seconds=3600,
            remember_me_ttl_seconds=2_592_000,
        )
        default_result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD, remember_me=False)
        remembered_result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD, remember_me=True)

        default_ttl = (default_result.session.expires_at - clock()).total_seconds()
        remembered_ttl = (remembered_result.session.expires_at - clock()).total_seconds()
        assert remembered_ttl > default_ttl
        assert remembered_result.session.remember_me is True
        assert default_result.session.remember_me is False

    def test_login_records_user_agent_and_ip_hint(self) -> None:
        auth, _store = make_auth()
        result = auth.login(
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            user_agent="pytest-agent",
            ip_hint="203.0.113.5",
        )
        assert result.session.user_agent == "pytest-agent"
        assert result.session.ip_hint == "203.0.113.5"

    def test_login_issues_csrf_token(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        assert result.csrf_token
        assert result.session.csrf_token == result.csrf_token


class TestLogout:
    def test_logout_revokes_session(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        auth.logout(result.access_token)
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(result.access_token)

    def test_logout_with_none_token_is_noop(self) -> None:
        auth, _store = make_auth()
        auth.logout(None)  # Should not raise.

    def test_logout_with_unknown_token_is_noop(self) -> None:
        auth, _store = make_auth()
        auth.logout("not-a-real-token")  # Should not raise.

    def test_logout_twice_is_idempotent(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        auth.logout(result.access_token)
        auth.logout(result.access_token)  # Should not raise the second time.


class TestSessionValidation:
    def test_validate_session_returns_session_for_valid_token(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        session = auth.validate_session(result.access_token)
        assert session is not None
        assert session.user_id == result.user.user_id

    def test_validate_session_raises_for_missing_token(self) -> None:
        auth, _store = make_auth()
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(None)

    def test_validate_session_raises_for_blank_token(self) -> None:
        auth, _store = make_auth()
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session("   ")

    def test_validate_session_returns_none_when_raise_on_invalid_false(self) -> None:
        auth, _store = make_auth()
        session = auth.validate_session(None, raise_on_invalid=False)
        assert session is None

    def test_validate_session_raises_for_revoked_token(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        auth.logout(result.access_token)
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(result.access_token)

    def test_validate_session_expired_raises(self) -> None:
        clock = _MutableClock(datetime(2026, 7, 29, 12, 0, tzinfo=UTC))
        auth, _store = make_auth(clock=clock, session_ttl_seconds=60)
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        clock.advance(seconds=61)
        with pytest.raises(UserPlatformAuthError):
            auth.validate_session(result.access_token)

    def test_validate_session_expired_returns_none_when_not_raising(self) -> None:
        clock = _MutableClock(datetime(2026, 7, 29, 12, 0, tzinfo=UTC))
        auth, _store = make_auth(clock=clock, session_ttl_seconds=60)
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        clock.advance(seconds=61)
        session = auth.validate_session(result.access_token, raise_on_invalid=False)
        assert session is None

    def test_validate_session_refreshes_last_seen_at(self) -> None:
        clock = _MutableClock(datetime(2026, 7, 29, 12, 0, tzinfo=UTC))
        auth, _store = make_auth(clock=clock)
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        clock.advance(seconds=30)
        refreshed = auth.validate_session(result.access_token)
        assert refreshed is not None
        assert refreshed.last_seen_at == clock()


class TestCurrentUser:
    def test_current_user_returns_user(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        user = auth.current_user(result.access_token)
        assert user.email == DEMO_EMAIL

    def test_current_user_raises_for_invalid_token(self) -> None:
        auth, _store = make_auth()
        with pytest.raises(UserPlatformAuthError):
            auth.current_user("garbage-token")

    def test_current_user_raises_when_user_inactive(self) -> None:
        auth, store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        user = store.users.get_by_id(result.user.user_id)
        assert user is not None
        from dataclasses import replace

        store.users.save(replace(user, is_active=False))
        with pytest.raises(UserPlatformAuthError):
            auth.current_user(result.access_token)


class TestRateLimiting:
    def test_login_rate_limited_after_many_attempts(self) -> None:
        limiter = RateLimiterHook(max_attempts=3, window_seconds=60)
        auth, _store = make_auth(rate_limiter=limiter)
        for _ in range(3):
            with pytest.raises(UserPlatformAuthError):
                auth.login(email=DEMO_EMAIL, password="WrongPassword123!")
        with pytest.raises(UserPlatformRateLimitError):
            auth.login(email=DEMO_EMAIL, password="WrongPassword123!")

    def test_register_rate_limited_after_many_attempts(self) -> None:
        # Rate limiting keys on the target email, so repeated attempts against the
        # same address exhaust the bucket even after the first attempt succeeds.
        limiter = RateLimiterHook(max_attempts=2, window_seconds=60)
        auth, _store = make_auth(seed=False, rate_limiter=limiter)
        auth.register(email="repeat@example.com", password="ValidPass123!", display_name="A1")
        with pytest.raises(UserPlatformConflictError):
            auth.register(email="repeat@example.com", password="ValidPass123!", display_name="A2")
        with pytest.raises(UserPlatformRateLimitError):
            auth.register(email="repeat@example.com", password="ValidPass123!", display_name="A3")

    def test_successful_login_resets_rate_limit_bucket(self) -> None:
        limiter = RateLimiterHook(max_attempts=5, window_seconds=60)
        auth, _store = make_auth(rate_limiter=limiter)
        for _ in range(4):
            with pytest.raises(UserPlatformAuthError):
                auth.login(email=DEMO_EMAIL, password="WrongPassword123!")
        # Successful login should reset the bucket for this email.
        auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        # Should be able to attempt again without hitting the rate limit immediately.
        with pytest.raises(UserPlatformAuthError):
            auth.login(email=DEMO_EMAIL, password="WrongPassword123!")


class TestPasswordValidationRules:
    @pytest.mark.parametrize(
        "password",
        [
            "short1A",
            "alllowercase1",
            "ALLUPPERCASE1",
            "NoDigitsHereAtAll",
        ],
    )
    def test_invalid_passwords_are_rejected(self, password: str) -> None:
        auth, _store = make_auth(seed=False)
        with pytest.raises(UserPlatformValidationError):
            auth.register(email="rules@example.com", password=password, display_name="Rules")

    @pytest.mark.parametrize(
        "password",
        [
            "ValidPass123!",
            "AnotherOk9x",
            "Str0ngEnough",
        ],
    )
    def test_valid_passwords_are_accepted(self, password: str) -> None:
        auth, _store = make_auth(seed=False)
        result = auth.register(
            email=f"ok-{abs(hash(password))}@example.com",
            password=password,
            display_name="Rules OK",
        )
        assert result.user.is_active is True


class TestPasswordResetArchitecture:
    """Sprint 17 ships password reset architecture only — no email is sent."""

    def test_password_reset_request_returns_generic_response(self) -> None:
        auth, _store = make_auth()
        response = auth.request_password_reset(DEMO_EMAIL)
        assert response["status"] == "accepted"
        assert response["email_delivery"] is False

    def test_password_reset_unknown_email_returns_same_generic_response(self) -> None:
        auth, _store = make_auth()
        response = auth.request_password_reset("ghost@example.com")
        assert response["status"] == "accepted"
        assert response["email_delivery"] is False
        assert "reset_token_demo_only" not in response

    def test_password_reset_known_email_creates_reset_record(self) -> None:
        auth, store = make_auth()
        user = store.users.get_by_email(DEMO_EMAIL)
        assert user is not None
        auth.request_password_reset(DEMO_EMAIL)
        events = store.audit.list_events(user_id=user.user_id)
        assert any(e.event_type == "password_reset_requested" for e in events)

    def test_password_reset_does_not_send_real_email(self) -> None:
        auth, _store = make_auth()
        response = auth.request_password_reset(DEMO_EMAIL)
        assert response["email_delivery"] is False
        assert response["status"] == "accepted"
        assert response["detail"] == (
            "If an account exists for this email, password reset instructions will be sent."
        )


class TestEmailVerificationArchitecture:
    """Sprint 17 ships email verification architecture only — no email is sent."""

    def test_email_verification_request_returns_demo_token(self) -> None:
        auth, store = make_auth()
        user = store.users.get_by_email(DEMO_EMAIL)
        assert user is not None
        response = auth.request_email_verification(user.user_id)
        assert response["status"] == "accepted"
        assert response["email_delivery"] is False
        assert "verification_token_demo_only" in response

    def test_email_verification_unknown_user_raises_not_found(self) -> None:
        from app.domain.exceptions import UserPlatformNotFoundError

        auth, _store = make_auth()
        with pytest.raises(UserPlatformNotFoundError):
            auth.request_email_verification("no-such-user")

    def test_email_verification_records_audit_event(self) -> None:
        auth, store = make_auth()
        user = store.users.get_by_email(DEMO_EMAIL)
        assert user is not None
        auth.request_email_verification(user.user_id)
        events = store.audit.list_events(user_id=user.user_id)
        assert any(e.event_type == "email_verification_requested" for e in events)


class TestTokenHashing:
    def test_hash_token_is_deterministic(self) -> None:
        assert AuthService.hash_token("abc123") == AuthService.hash_token("abc123")

    def test_hash_token_differs_for_different_inputs(self) -> None:
        assert AuthService.hash_token("abc123") != AuthService.hash_token("abc124")

    def test_token_hash_never_equals_raw_token(self) -> None:
        auth, _store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        assert result.session.token_hash != result.access_token

    def test_session_repository_never_persists_raw_token(self) -> None:
        auth, store = make_auth()
        result = auth.login(email=DEMO_EMAIL, password=DEMO_PASSWORD)
        stored = store.sessions.get_by_id(result.session.session_id)
        assert stored is not None
        assert stored.token_hash != result.access_token
        assert result.access_token not in stored.token_hash


class TestOAuthExtensionPoint:
    def test_begin_oauth_link_returns_not_implemented(self) -> None:
        auth, store = make_auth()
        user = store.users.get_by_email(DEMO_EMAIL)
        assert user is not None
        response = auth.begin_oauth_link("google", user.user_id)
        assert response["status"] == "not_implemented"
        assert response["provider"] == "google"
