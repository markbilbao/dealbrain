"""Unit tests for User Platform security hooks: rate limiting, CSRF, audit, MFA/OAuth
extension points, and password-storage guarantees."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.auth.security import (
    AuditLogger,
    CsrfTokenService,
    MfaExtensionPoint,
    OAuthExtensionPoint,
    RateLimiterHook,
    secrets_token,
)
from app.auth.service import AuthService
from app.user.fixtures import DEMO_PASSWORD, seed_demo_users
from app.user.memory import InMemoryUserPlatformStore


class _MutableClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def __call__(self) -> datetime:
        return self._now

    def advance(self, **kwargs: float) -> None:
        self._now = self._now + timedelta(**kwargs)


class TestRateLimiterHook:
    def test_allows_up_to_max_attempts(self) -> None:
        limiter = RateLimiterHook(max_attempts=3, window_seconds=60)
        assert limiter.check("key") is True
        assert limiter.check("key") is True
        assert limiter.check("key") is True

    def test_blocks_after_max_attempts(self) -> None:
        limiter = RateLimiterHook(max_attempts=2, window_seconds=60)
        assert limiter.check("key") is True
        assert limiter.check("key") is True
        assert limiter.check("key") is False

    def test_different_keys_have_independent_buckets(self) -> None:
        limiter = RateLimiterHook(max_attempts=1, window_seconds=60)
        assert limiter.check("key-a") is True
        assert limiter.check("key-b") is True
        assert limiter.check("key-a") is False

    def test_window_expiry_allows_new_attempts(self) -> None:
        clock = _MutableClock(datetime(2026, 7, 29, 12, 0, tzinfo=UTC))
        limiter = RateLimiterHook(max_attempts=1, window_seconds=30, clock=clock)
        assert limiter.check("key") is True
        assert limiter.check("key") is False
        clock.advance(seconds=31)
        assert limiter.check("key") is True

    def test_reset_clears_bucket_for_key(self) -> None:
        limiter = RateLimiterHook(max_attempts=1, window_seconds=60)
        assert limiter.check("key") is True
        assert limiter.check("key") is False
        limiter.reset("key")
        assert limiter.check("key") is True

    def test_reset_unknown_key_is_noop(self) -> None:
        limiter = RateLimiterHook(max_attempts=1, window_seconds=60)
        limiter.reset("never-used-key")  # Should not raise.


class TestCsrfTokenService:
    def test_issue_returns_nonempty_token(self) -> None:
        csrf = CsrfTokenService()
        token = csrf.issue()
        assert token
        assert isinstance(token, str)

    def test_issue_generates_unique_tokens(self) -> None:
        csrf = CsrfTokenService()
        tokens = {csrf.issue() for _ in range(10)}
        assert len(tokens) == 10

    def test_validate_matching_tokens_succeeds(self) -> None:
        csrf = CsrfTokenService()
        token = csrf.issue()
        assert csrf.validate(token, token) is True

    def test_validate_rejects_mismatched_tokens(self) -> None:
        csrf = CsrfTokenService()
        assert csrf.validate("expected-token", "different-token") is False

    def test_validate_rejects_missing_expected(self) -> None:
        csrf = CsrfTokenService()
        assert csrf.validate(None, "provided-token") is False

    def test_validate_rejects_missing_provided(self) -> None:
        csrf = CsrfTokenService()
        assert csrf.validate("expected-token", None) is False

    def test_validate_rejects_both_missing(self) -> None:
        csrf = CsrfTokenService()
        assert csrf.validate(None, None) is False

    def test_custom_token_factory_is_used(self) -> None:
        csrf = CsrfTokenService(token_factory=lambda: "fixed-token")
        assert csrf.issue() == "fixed-token"


class TestSecretsToken:
    def test_secrets_token_returns_urlsafe_string(self) -> None:
        token = secrets_token()
        assert isinstance(token, str)
        assert token

    def test_secrets_token_length_scales_with_nbytes(self) -> None:
        short_token = secrets_token(nbytes=8)
        long_token = secrets_token(nbytes=64)
        assert len(long_token) > len(short_token)


class TestAuditLogger:
    def test_record_returns_security_event(self) -> None:
        audit = AuditLogger()
        event = audit.record("login_success", user_id="user-1", detail="ok")
        assert event.event_type == "login_success"
        assert event.user_id == "user-1"

    def test_recent_returns_recorded_events(self) -> None:
        audit = AuditLogger()
        audit.record("login_success", user_id="user-1")
        events = audit.recent(user_id="user-1")
        assert len(events) == 1

    def test_recent_filters_by_user_id(self) -> None:
        audit = AuditLogger()
        audit.record("login_success", user_id="user-1")
        audit.record("login_success", user_id="user-2")
        events = audit.recent(user_id="user-1")
        assert all(e.user_id == "user-1" for e in events)

    def test_recent_without_user_id_returns_all(self) -> None:
        audit = AuditLogger()
        audit.record("login_success", user_id="user-1")
        audit.record("logout", user_id="user-2")
        events = audit.recent()
        assert len(events) == 2

    def test_recent_respects_limit(self) -> None:
        audit = AuditLogger()
        for i in range(10):
            audit.record("login_success", user_id=f"user-{i}")
        events = audit.recent(limit=3)
        assert len(events) == 3

    def test_record_includes_metadata(self) -> None:
        audit = AuditLogger()
        event = audit.record("rate_limited", detail="login", metadata={"email": "a@b.com"})
        assert event.metadata["email"] == "a@b.com"

    def test_record_persists_to_repository_when_provided(self) -> None:
        store = InMemoryUserPlatformStore()
        audit = AuditLogger(store.audit)
        audit.record("login_success", user_id="user-1")
        events = store.audit.list_events(user_id="user-1")
        assert len(events) == 1


class TestMfaExtensionPoint:
    def test_is_enabled_returns_false(self) -> None:
        mfa = MfaExtensionPoint()
        assert mfa.is_enabled("any-user") is False

    def test_challenge_returns_not_implemented_status(self) -> None:
        mfa = MfaExtensionPoint()
        response = mfa.challenge("any-user")
        assert response["status"] == "not_implemented"
        assert response["mfa_required"] is False

    def test_challenge_includes_supported_methods_list(self) -> None:
        mfa = MfaExtensionPoint()
        response = mfa.challenge("any-user")
        assert response["methods"] == []

    def test_supported_methods_is_empty_tuple_by_default(self) -> None:
        mfa = MfaExtensionPoint()
        assert mfa.supported_methods == ()


class TestOAuthExtensionPoint:
    def test_begin_link_returns_not_implemented_status(self) -> None:
        oauth = OAuthExtensionPoint()
        response = oauth.begin_link("google", "user-1")
        assert response["status"] == "not_implemented"

    def test_begin_link_echoes_provider_and_user(self) -> None:
        oauth = OAuthExtensionPoint()
        response = oauth.begin_link("github", "user-42")
        assert response["provider"] == "github"
        assert response["user_id"] == "user-42"

    def test_supported_providers_is_empty_tuple_by_default(self) -> None:
        oauth = OAuthExtensionPoint()
        assert oauth.supported_providers == ()


class TestNoPlaintextPasswordStorage:
    def test_no_plaintext_passwords_in_seeded_store(self) -> None:
        store = InMemoryUserPlatformStore()
        seed_demo_users(store)
        for user in store.users.list_users():
            assert DEMO_PASSWORD not in user.password_hash
            assert user.password_hash.startswith("pbkdf2_sha256$")

    def test_user_to_dict_excludes_password_hash_by_default(self) -> None:
        store = InMemoryUserPlatformStore()
        seed_demo_users(store)
        user = store.users.list_users()[0]
        payload = user.to_dict()
        assert "password_hash" not in payload

    def test_user_to_dict_includes_password_hash_only_when_requested(self) -> None:
        store = InMemoryUserPlatformStore()
        seed_demo_users(store)
        user = store.users.list_users()[0]
        payload = user.to_dict(include_sensitive=True)
        assert "password_hash" in payload
        assert DEMO_PASSWORD not in payload["password_hash"]


class TestTokenHashSecrecy:
    def test_session_to_dict_excludes_token_hash_by_default(self) -> None:
        store = InMemoryUserPlatformStore()
        seed_demo_users(store)
        auth = AuthService(
            users=store.users,
            sessions=store.sessions,
            profiles=store.profiles,
            audit=AuditLogger(store.audit),
        )
        result = auth.login(email="student@example.com", password=DEMO_PASSWORD)
        payload = result.session.to_dict()
        assert "token_hash" not in payload
        assert "csrf_token" not in payload

    def test_token_hash_not_equal_to_raw_access_token(self) -> None:
        store = InMemoryUserPlatformStore()
        seed_demo_users(store)
        auth = AuthService(
            users=store.users,
            sessions=store.sessions,
            profiles=store.profiles,
            audit=AuditLogger(store.audit),
        )
        result = auth.login(email="student@example.com", password=DEMO_PASSWORD)
        assert result.session.token_hash != result.access_token
        assert len(result.session.token_hash) == 64  # sha256 hex digest length
