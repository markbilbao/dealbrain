"""Authentication application service — register, login, logout, session validation."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.auth.email import EmailMessage, EmailSender, NullEmailSender
from app.auth.password import PasswordHasher, hash_password, verify_password
from app.auth.security import (
    AuditLogger,
    CsrfTokenService,
    MfaExtensionPoint,
    OAuthExtensionPoint,
    RateLimiterHook,
    secrets_token,
)
from app.domain.entities.user_platform import (
    AuthResult,
    EmailVerificationRequest,
    NotificationPreference,
    PasswordResetRequest,
    ProfileVersion,
    User,
    UserPreference,
    UserProfile,
    UserSession,
    UserSettings,
    Wishlist,
)
from app.domain.exceptions import (
    UserPlatformAuthError,
    UserPlatformConflictError,
    UserPlatformNotFoundError,
    UserPlatformRateLimitError,
    UserPlatformValidationError,
)
from app.domain.interfaces.user_platform_repository import (
    EmailVerificationRepository,
    PasswordResetRepository,
    ProfileRepository,
    SessionRepository,
    UserRepository,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8


class AuthService:
    """Register / login / logout / session validation with security hooks."""

    def __init__(
        self,
        *,
        users: UserRepository,
        sessions: SessionRepository,
        profiles: ProfileRepository,
        password_resets: PasswordResetRepository | None = None,
        email_verifications: EmailVerificationRepository | None = None,
        password_hasher: PasswordHasher | None = None,
        email_sender: EmailSender | None = None,
        rate_limiter: RateLimiterHook | None = None,
        csrf: CsrfTokenService | None = None,
        audit: AuditLogger | None = None,
        mfa: MfaExtensionPoint | None = None,
        oauth: OAuthExtensionPoint | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        session_ttl_seconds: int = 3600,
        remember_me_ttl_seconds: int = 2_592_000,
        enabled: bool = True,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._profiles = profiles
        self._password_resets = password_resets
        self._email_verifications = email_verifications
        self._hasher = password_hasher or PasswordHasher()
        self._email = email_sender or NullEmailSender()
        self._rate_limiter = rate_limiter or RateLimiterHook(max_attempts=20, window_seconds=60)
        self._csrf = csrf or CsrfTokenService()
        self._audit = audit or AuditLogger()
        self._mfa = mfa or MfaExtensionPoint()
        self._oauth = oauth or OAuthExtensionPoint()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._session_ttl = session_ttl_seconds
        self._remember_ttl = remember_me_ttl_seconds
        self._enabled = enabled

    def _require_enabled(self) -> None:
        if not self._enabled:
            raise UserPlatformValidationError("User platform authentication is disabled.")

    def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        remember_me: bool = False,
    ) -> AuthResult:
        self._require_enabled()
        cleaned_email = self._normalize_email(email)
        cleaned_name = display_name.strip()
        self._validate_password(password)
        if not cleaned_name:
            raise UserPlatformValidationError("display_name must not be blank.")
        if not self._rate_limiter.check(f"register:{cleaned_email}"):
            self._audit.record("rate_limited", detail="register", metadata={"email": cleaned_email})
            raise UserPlatformRateLimitError("Too many registration attempts. Try again later.")
        if self._users.get_by_email(cleaned_email) is not None:
            raise UserPlatformConflictError(f"Email already registered: {cleaned_email}")

        now = self._clock()
        user = User(
            user_id=self._id_factory(),
            email=cleaned_email,
            password_hash=self._hasher.hash(password),
            display_name=cleaned_name,
            is_active=True,
            email_verified=False,
            created_at=now,
            updated_at=now,
        )
        self._users.save(user)
        self._bootstrap_profile(user)
        self._audit.record("register", user_id=user.user_id, detail="user_registered")
        return self._issue_session(user, remember_me=remember_me)

    def login(
        self,
        *,
        email: str,
        password: str,
        remember_me: bool = False,
        user_agent: str | None = None,
        ip_hint: str | None = None,
    ) -> AuthResult:
        self._require_enabled()
        cleaned_email = self._normalize_email(email)
        rate_key = f"login:{cleaned_email}"
        if not self._rate_limiter.check(rate_key):
            self._audit.record("rate_limited", detail="login", metadata={"email": cleaned_email})
            raise UserPlatformRateLimitError("Too many login attempts. Try again later.")

        user = self._users.get_by_email(cleaned_email)
        if user is None or not user.is_active:
            self._audit.record(
                "login_failure", detail="unknown_or_inactive", metadata={"email": cleaned_email}
            )
            raise UserPlatformAuthError("Invalid email or password.")
        if not self._hasher.verify(password, user.password_hash):
            self._audit.record("login_failure", user_id=user.user_id, detail="bad_password")
            raise UserPlatformAuthError("Invalid email or password.")

        # MFA extension point — never blocks in Sprint 17.
        if self._mfa.is_enabled(user.user_id):
            self._audit.record("mfa_challenge", user_id=user.user_id)
            raise UserPlatformAuthError("MFA required but not implemented in Sprint 17.")

        self._rate_limiter.reset(rate_key)
        self._audit.record("login_success", user_id=user.user_id)
        return self._issue_session(
            user,
            remember_me=remember_me,
            user_agent=user_agent,
            ip_hint=ip_hint,
        )

    def logout(self, access_token: str | None) -> None:
        self._require_enabled()
        if not access_token:
            return
        session = self.validate_session(access_token, raise_on_invalid=False)
        if session is None:
            return
        self._sessions.revoke(session.session_id)
        self._audit.record("logout", user_id=session.user_id, detail=session.session_id)

    def validate_session(
        self,
        access_token: str | None,
        *,
        raise_on_invalid: bool = True,
    ) -> UserSession | None:
        self._require_enabled()
        if not access_token or not access_token.strip():
            if raise_on_invalid:
                raise UserPlatformAuthError("Missing session token.")
            return None
        token_hash = self.hash_token(access_token.strip())
        session = self._sessions.get_by_token_hash(token_hash)
        if session is None or session.revoked:
            if raise_on_invalid:
                raise UserPlatformAuthError("Invalid or revoked session.")
            return None
        now = self._clock()
        if session.expires_at <= now:
            self._sessions.revoke(session.session_id)
            self._audit.record("session_expired", user_id=session.user_id)
            if raise_on_invalid:
                raise UserPlatformAuthError("Session expired.")
            return None
        refreshed = UserSession(
            session_id=session.session_id,
            user_id=session.user_id,
            token_hash=session.token_hash,
            created_at=session.created_at,
            expires_at=session.expires_at,
            remember_me=session.remember_me,
            last_seen_at=now,
            user_agent=session.user_agent,
            ip_hint=session.ip_hint,
            csrf_token=session.csrf_token,
            revoked=False,
        )
        self._sessions.save(refreshed)
        return refreshed

    def current_user(self, access_token: str | None) -> User:
        session = self.validate_session(access_token)
        assert session is not None
        user = self._users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            raise UserPlatformAuthError("Authenticated user is inactive or missing.")
        return user

    def request_password_reset(self, email: str) -> dict[str, Any]:
        """Architecture-only: creates a reset token record and queues a null email."""
        self._require_enabled()
        cleaned = self._normalize_email(email)
        user = self._users.get_by_email(cleaned)
        # Always return generic response to avoid account enumeration.
        response = {
            "status": "accepted",
            "email_delivery": False,
            "detail": "If the account exists, a reset token was prepared (email not sent).",
        }
        if user is None or self._password_resets is None:
            return response
        raw = secrets_token()
        now = self._clock()
        record = PasswordResetRequest(
            reset_id=self._id_factory(),
            user_id=user.user_id,
            token_hash=self.hash_token(raw),
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        self._password_resets.save(record)
        self._email.send(
            EmailMessage(
                to_address=user.email,
                subject="DealBrain password reset",
                body_text=f"Reset token (demo only, not emailed): {raw}",
                template_id="password_reset",
            )
        )
        self._audit.record("password_reset_requested", user_id=user.user_id)
        response["reset_token_demo_only"] = raw
        return response

    def request_email_verification(self, user_id: str) -> dict[str, Any]:
        self._require_enabled()
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserPlatformNotFoundError(user_id)
        if self._email_verifications is None:
            return {"status": "accepted", "email_delivery": False}
        raw = secrets_token()
        now = self._clock()
        record = EmailVerificationRequest(
            verification_id=self._id_factory(),
            user_id=user.user_id,
            token_hash=self.hash_token(raw),
            created_at=now,
            expires_at=now + timedelta(days=1),
        )
        self._email_verifications.save(record)
        self._email.send(
            EmailMessage(
                to_address=user.email,
                subject="Verify your DealBrain email",
                body_text=f"Verification token (demo only, not emailed): {raw}",
                template_id="email_verification",
            )
        )
        self._audit.record("email_verification_requested", user_id=user.user_id)
        return {
            "status": "accepted",
            "email_delivery": False,
            "verification_token_demo_only": raw,
        }

    def begin_oauth_link(self, provider: str, user_id: str) -> dict[str, Any]:
        self._audit.record("oauth_link_attempt", user_id=user_id, metadata={"provider": provider})
        return self._oauth.begin_link(provider, user_id)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _issue_session(
        self,
        user: User,
        *,
        remember_me: bool = False,
        user_agent: str | None = None,
        ip_hint: str | None = None,
    ) -> AuthResult:
        now = self._clock()
        ttl = self._remember_ttl if remember_me else self._session_ttl
        raw_token = secrets_token(48)
        csrf = self._csrf.issue()
        session = UserSession(
            session_id=self._id_factory(),
            user_id=user.user_id,
            token_hash=self.hash_token(raw_token),
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            remember_me=remember_me,
            last_seen_at=now,
            user_agent=user_agent,
            ip_hint=ip_hint,
            csrf_token=csrf,
            revoked=False,
        )
        self._sessions.save(session)
        return AuthResult(user=user, session=session, access_token=raw_token, csrf_token=csrf)

    def _bootstrap_profile(self, user: User) -> UserProfile:
        now = self._clock()
        preferences = UserPreference(user_id=user.user_id, updated_at=now)
        profile = UserProfile(
            user_id=user.user_id,
            display_name=user.display_name,
            preferences=preferences,
            wishlist=Wishlist(user_id=user.user_id, product_ids=(), updated_at=now),
            version=ProfileVersion(
                user_id=user.user_id, version=1, changed_at=now, change_summary="created"
            ),
        )
        self._profiles.save_profile(profile)
        self._profiles.save_settings(
            UserSettings(
                user_id=user.user_id,
                notification_settings=NotificationPreference(user_id=user.user_id),
                privacy_settings={"share_community_activity": False},
                community_settings={"show_trusted_reviews": True},
                updated_at=now,
            )
        )
        return profile

    @staticmethod
    def _normalize_email(email: str) -> str:
        cleaned = email.strip().lower()
        if not cleaned or not _EMAIL_RE.match(cleaned):
            raise UserPlatformValidationError("email must be a valid address.")
        return cleaned

    @staticmethod
    def _validate_password(password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise UserPlatformValidationError(
                f"password must be at least {MIN_PASSWORD_LENGTH} characters."
            )
        if password.lower() == password or password.upper() == password:
            raise UserPlatformValidationError("password must include mixed case characters.")
        if not any(ch.isdigit() for ch in password):
            raise UserPlatformValidationError("password must include at least one digit.")


# Re-export helpers for callers that import from the service module.
__all__ = ["AuthService", "hash_password", "verify_password", "MIN_PASSWORD_LENGTH"]
