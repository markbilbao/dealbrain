"""Authentication application service — register, login, logout, session validation."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from app.auth.email import EmailDeliveryError, EmailSender, NullEmailSender
from app.auth.email_factory import allows_inline_identity_tokens, build_trusted_action_url
from app.auth.email_templates import (
    EMAIL_CHANGE_PATH,
    RESET_PATH,
    VERIFY_PATH,
    build_email_change_message,
    build_email_changed_notice,
    build_email_verification_message,
    build_password_reset_message,
)
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
    EMAIL_CHANGE_PURPOSE,
    AuthResult,
    EmailChangeRequest,
    EmailVerificationRequest,
    NotificationPreference,
    PasswordResetRequest,
    PolicyAcceptanceRecord,
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
    ConsentRepository,
    EmailChangeRepository,
    EmailVerificationRepository,
    PasswordResetRepository,
    ProfileRepository,
    SessionRepository,
    UserRepository,
)
from app.legal.publication import (
    POLICY_PRIVACY,
    POLICY_TERMS,
    LegalPublicationCatalog,
    PolicyType,
    unpublished_catalog,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8
PASSWORD_RESET_TTL = timedelta(hours=1)
EMAIL_VERIFICATION_TTL = timedelta(days=1)
EMAIL_CHANGE_TTL = timedelta(days=1)
GENERIC_RESET_DETAIL = (
    "If an account exists for this email, password reset instructions will be sent."
)
GENERIC_VERIFY_DETAIL = (
    "If an account exists for this email, verification instructions will be sent."
)
GENERIC_EMAIL_CHANGE_DETAIL = (
    "If this change can proceed, a confirmation email will be sent to the new address."
)
INVALID_RESET_TOKEN = "Invalid or expired reset token."
INVALID_VERIFY_TOKEN = "Invalid or expired verification token."
INVALID_EMAIL_CHANGE_TOKEN = "Invalid or expired email-change token."
EMAIL_CHANGE_COMPLETION_ERROR = "Unable to complete email change."


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
        email_changes: EmailChangeRepository | None = None,
        consents: ConsentRepository | None = None,
        legal_catalog: LegalPublicationCatalog | None = None,
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
        self._email_changes = email_changes
        self._consents = consents
        self._legal_catalog = legal_catalog or unpublished_catalog()
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

    def verify_password(self, user: User, password: str) -> bool:
        return self._hasher.verify(password, user.password_hash)

    def has_accepted(self, user_id: str, policy_type: PolicyType, version_id: str) -> bool:
        if self._consents is None:
            return False
        return self._consents.get(user_id, policy_type, version_id) is not None

    def accept_published_policy(
        self,
        user_id: str,
        policy_type: PolicyType,
        *,
        source: str = "account",
        actor: str | None = None,
    ) -> PolicyAcceptanceRecord:
        """Record acceptance of the current published version only.

        Unpublished or draft/approved-only versions cannot be accepted.
        Duplicate (user, type, version) writes return the original record.
        """
        version = self._legal_catalog.published(policy_type)
        if version is None:
            raise UserPlatformValidationError("No published policy version can be accepted.")
        if self._consents is None:
            raise UserPlatformValidationError("Consent persistence is not configured.")
        existing = self._consents.get(user_id, policy_type, version.version_id)
        if existing is not None:
            return existing
        now = self._clock()
        record = PolicyAcceptanceRecord(
            record_id=self._id_factory(),
            user_id=user_id,
            policy_type=policy_type,  # type: ignore[arg-type]
            version_id=version.version_id,
            accepted_at=now,
            source=source,  # type: ignore[arg-type]
            actor=actor or user_id,
        )
        saved = self._consents.save(record)
        if saved.record_id == record.record_id:
            self._audit.record(
                "policy_accepted",
                user_id=user_id,
                detail=policy_type,
                metadata={"version_id": version.version_id, "source": source},
            )
        return saved

    def _require_registration_consents(
        self,
        *,
        terms_accepted: bool,
        privacy_acknowledged: bool,
    ) -> None:
        """Enforce acceptance only when a published version requires it.

        Unpublished production catalogs record nothing and do not invent a
        checkbox contract.
        """
        if self._legal_catalog.requires_acceptance(POLICY_TERMS) and not terms_accepted:
            raise UserPlatformValidationError("Terms of Service must be accepted.")
        if self._legal_catalog.requires_acceptance(POLICY_PRIVACY) and not privacy_acknowledged:
            raise UserPlatformValidationError("Privacy Policy must be acknowledged.")

    def _persist_registration_consents(
        self,
        user_id: str,
        *,
        terms_accepted: bool,
        privacy_acknowledged: bool,
    ) -> None:
        if terms_accepted and self._legal_catalog.published(POLICY_TERMS) is not None:
            self.accept_published_policy(user_id, POLICY_TERMS, source="registration")
        if privacy_acknowledged and self._legal_catalog.published(POLICY_PRIVACY) is not None:
            self.accept_published_policy(user_id, POLICY_PRIVACY, source="registration")

    def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str,
        remember_me: bool = False,
        terms_accepted: bool = False,
        privacy_acknowledged: bool = False,
    ) -> AuthResult:
        self._require_enabled()
        cleaned_email = self._normalize_email(email)
        cleaned_name = display_name.strip()
        self._validate_password(password)
        if not cleaned_name:
            raise UserPlatformValidationError("display_name must not be blank.")
        self._require_registration_consents(
            terms_accepted=terms_accepted,
            privacy_acknowledged=privacy_acknowledged,
        )
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
        self._persist_registration_consents(
            user.user_id,
            terms_accepted=terms_accepted,
            privacy_acknowledged=privacy_acknowledged,
        )
        self._audit.record("register", user_id=user.user_id, detail="user_registered")
        self._issue_email_verification(user)
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
        """Enumeration-safe password-reset request. Never discloses membership."""
        self._require_enabled()
        cleaned = self._normalize_email(email)
        if not self._rate_limiter.check(f"password_reset:{cleaned}"):
            self._audit.record("rate_limited", detail="password_reset", metadata={"email": cleaned})
            raise UserPlatformRateLimitError("Too many password reset attempts. Try again later.")
        response = {
            "status": "accepted",
            "email_delivery": False,
            "detail": GENERIC_RESET_DETAIL,
        }
        user = self._users.get_by_email(cleaned)
        if user is None or self._password_resets is None:
            return response
        raw = self._create_password_reset(user)
        if allows_inline_identity_tokens():
            response["reset_token_demo_only"] = raw
        return response

    def confirm_password_reset(self, token: str, new_password: str) -> dict[str, Any]:
        """Validate a reset token, change the password, and revoke all sessions."""
        self._require_enabled()
        self._validate_password(new_password)
        raw = (token or "").strip()
        if not raw or self._password_resets is None:
            raise UserPlatformAuthError(INVALID_RESET_TOKEN)
        record = self._password_resets.get_by_token_hash(self.hash_token(raw))
        now = self._clock()
        if record is None or record.consumed or record.expires_at <= now:
            raise UserPlatformAuthError(INVALID_RESET_TOKEN)
        user = self._users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise UserPlatformAuthError(INVALID_RESET_TOKEN)
        updated = replace(
            user,
            password_hash=self._hasher.hash(new_password),
            updated_at=now,
        )
        self._users.save(updated)
        self._password_resets.mark_consumed(record.reset_id)
        self._sessions.revoke_all_for_user(user.user_id)
        self._audit.record(
            "password_changed",
            user_id=user.user_id,
            detail="password_reset_confirmed",
        )
        return {"status": "password_changed"}

    def request_email_verification(self, user_id: str) -> dict[str, Any]:
        self._require_enabled()
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserPlatformNotFoundError(user_id)
        if self._email_verifications is None:
            return {"status": "accepted", "email_delivery": False}
        raw = self._issue_email_verification(user)
        payload: dict[str, Any] = {
            "status": "accepted",
            "email_delivery": False,
        }
        if allows_inline_identity_tokens():
            payload["verification_token_demo_only"] = raw
        return payload

    def request_email_verification_by_email(self, email: str) -> dict[str, Any]:
        """Enumeration-safe public verification request."""
        self._require_enabled()
        cleaned = self._normalize_email(email)
        if not self._rate_limiter.check(f"email_verification:{cleaned}"):
            self._audit.record(
                "rate_limited",
                detail="email_verification",
                metadata={"email": cleaned},
            )
            raise UserPlatformRateLimitError("Too many verification attempts. Try again later.")
        response = {
            "status": "accepted",
            "email_delivery": False,
            "detail": GENERIC_VERIFY_DETAIL,
        }
        user = self._users.get_by_email(cleaned)
        if user is None or self._email_verifications is None:
            return response
        raw = self._issue_email_verification(user)
        if allows_inline_identity_tokens():
            response["verification_token_demo_only"] = raw
        return response

    def confirm_email_verification(self, token: str) -> dict[str, Any]:
        """Validate a verification token and mark the bound account verified."""
        self._require_enabled()
        raw = (token or "").strip()
        if not raw or self._email_verifications is None:
            raise UserPlatformAuthError(INVALID_VERIFY_TOKEN)
        record = self._email_verifications.get_by_token_hash(self.hash_token(raw))
        now = self._clock()
        if record is None or record.consumed or record.expires_at <= now:
            raise UserPlatformAuthError(INVALID_VERIFY_TOKEN)
        user = self._users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise UserPlatformAuthError(INVALID_VERIFY_TOKEN)
        updated = replace(user, email_verified=True, updated_at=now)
        self._users.save(updated)
        self._email_verifications.mark_consumed(record.verification_id)
        self._audit.record("email_verified", user_id=user.user_id)
        return {"status": "email_verified", "email_verified": True}

    def request_email_change(
        self,
        access_token: str | None,
        *,
        new_email: str,
        password: str,
    ) -> dict[str, Any]:
        """Request a change of the authenticated principal's email only.

        Client-supplied account selectors are ignored. The session principal
        is the only account authority. Occupied destinations do not create a
        token and do not change the HTTP contract.
        """
        self._require_enabled()
        user = self.current_user(access_token)
        if not self._rate_limiter.check(f"email_change:{user.user_id}"):
            self._audit.record(
                "rate_limited",
                user_id=user.user_id,
                detail="email_change",
            )
            raise UserPlatformRateLimitError("Too many email change attempts. Try again later.")
        if not self.verify_password(user, password):
            self._audit.record(
                "login_failure",
                user_id=user.user_id,
                detail="email_change_bad_password",
            )
            raise UserPlatformAuthError("Invalid credentials.")
        cleaned = self._normalize_email(new_email)
        if cleaned == user.email:
            raise UserPlatformValidationError(
                "New email must differ from the current account email."
            )
        response = {
            "status": "accepted",
            "email_delivery": False,
            "detail": GENERIC_EMAIL_CHANGE_DETAIL,
        }
        occupant = self._users.get_by_email(cleaned)
        if occupant is not None or self._email_changes is None:
            return response
        raw = self._create_email_change(user, cleaned)
        if allows_inline_identity_tokens():
            response["email_change_token_demo_only"] = raw
        return response

    def confirm_email_change(self, token: str) -> dict[str, Any]:
        """Confirm a purpose-bound email-change token and revoke sessions.

        Repository calls commit independently (no new transaction framework).
        Fail-closed ordering:

        1. Validate token, purpose, expiry, newest-request, and account.
        2. Recheck destination uniqueness. Conflict does not consume the token
           and does not mutate email or verified state.
        3. Determine whether this identity is already applied (retry state).
        4. Revoke every session for the bound user, including the confirming
           session. A revoke failure leaves email, verified state, and token
           unchanged and does not send the old-email notice.
        5. After successful revocation, persist the new email and
           ``email_verified=True``. Skip when already applied. A save failure
           leaves identity unchanged and the token unconsumed.
        6. Send the old-email notice only after a first-time identity mutation.
           Notice failure is audited and never rolls back the change.
        7. Consume the winning token and invalidate sibling tokens. A consume
           failure does not return success; prior sessions are already revoked.
        8. Return success only after revoke, persist (or already-applied), and
           consume succeed.
        """
        self._require_enabled()
        raw = (token or "").strip()
        if not raw or self._email_changes is None:
            raise UserPlatformAuthError(INVALID_EMAIL_CHANGE_TOKEN)
        record = self._email_changes.get_by_token_hash(self.hash_token(raw))
        now = self._clock()
        if (
            record is None
            or record.consumed
            or record.expires_at <= now
            or record.purpose != EMAIL_CHANGE_PURPOSE
        ):
            raise UserPlatformAuthError(INVALID_EMAIL_CHANGE_TOKEN)
        latest = self._latest_unconsumed_email_change(record.user_id)
        if latest is not None and latest.change_id != record.change_id:
            raise UserPlatformAuthError(INVALID_EMAIL_CHANGE_TOKEN)
        user = self._users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise UserPlatformAuthError(INVALID_EMAIL_CHANGE_TOKEN)
        occupant = self._users.get_by_email(record.new_email)
        if occupant is not None and occupant.user_id != user.user_id:
            raise UserPlatformAuthError(INVALID_EMAIL_CHANGE_TOKEN)
        old_email = user.email
        already_applied = user.email == record.new_email and user.email_verified
        try:
            self._sessions.revoke_all_for_user(user.user_id)
        except Exception as exc:  # noqa: BLE001 — fail closed; do not report success
            raise UserPlatformValidationError(EMAIL_CHANGE_COMPLETION_ERROR) from exc
        if not already_applied:
            updated = replace(
                user,
                email=record.new_email,
                email_verified=True,
                updated_at=now,
            )
            try:
                self._users.save(updated)
            except UserPlatformValidationError as exc:
                raise UserPlatformAuthError(INVALID_EMAIL_CHANGE_TOKEN) from exc
            self._send_email_changed_notice(old_email)
        try:
            self._email_changes.mark_consumed(record.change_id)
            self._email_changes.invalidate_for_user(user.user_id)
        except Exception as exc:  # noqa: BLE001 — fail closed; do not report success
            raise UserPlatformValidationError(EMAIL_CHANGE_COMPLETION_ERROR) from exc
        self._audit.record("email_change_confirmed", user_id=user.user_id)
        return {"status": "email_changed", "email_verified": True}

    def begin_oauth_link(self, provider: str, user_id: str) -> dict[str, Any]:
        self._audit.record("oauth_link_attempt", user_id=user_id, metadata={"provider": provider})
        return self._oauth.begin_link(provider, user_id)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _create_password_reset(self, user: User) -> str:
        assert self._password_resets is not None
        raw = secrets_token()
        now = self._clock()
        record = PasswordResetRequest(
            reset_id=self._id_factory(),
            user_id=user.user_id,
            token_hash=self.hash_token(raw),
            created_at=now,
            expires_at=now + PASSWORD_RESET_TTL,
        )
        self._password_resets.save(record)
        try:
            self._email.send(
                build_password_reset_message(
                    to_address=user.email,
                    action_url=self._action_url(RESET_PATH, raw),
                    expires_hours=1,
                )
            )
            self._audit.record("password_reset_requested", user_id=user.user_id)
        except EmailDeliveryError:
            self._audit.record(
                "password_reset_requested",
                user_id=user.user_id,
                detail="email_delivery_failed",
            )
        return raw

    def _issue_email_verification(self, user: User) -> str:
        if self._email_verifications is None:
            return ""
        raw = secrets_token()
        now = self._clock()
        record = EmailVerificationRequest(
            verification_id=self._id_factory(),
            user_id=user.user_id,
            token_hash=self.hash_token(raw),
            created_at=now,
            expires_at=now + EMAIL_VERIFICATION_TTL,
        )
        self._email_verifications.save(record)
        try:
            self._email.send(
                build_email_verification_message(
                    to_address=user.email,
                    action_url=self._action_url(VERIFY_PATH, raw),
                    expires_hours=24,
                )
            )
            self._audit.record("email_verification_requested", user_id=user.user_id)
        except EmailDeliveryError:
            self._audit.record(
                "email_verification_requested",
                user_id=user.user_id,
                detail="email_delivery_failed",
            )
        return raw

    def _action_url(self, path: str, token: str) -> str | None:
        from app.core.config import settings as app_settings

        base = (app_settings.public_app_base_url or "").strip()
        if not base:
            return None
        try:
            return build_trusted_action_url(base, path, token)
        except UserPlatformValidationError:
            return None

    def _create_email_change(self, user: User, new_email: str) -> str:
        assert self._email_changes is not None
        self._email_changes.invalidate_for_user(user.user_id)
        raw = secrets_token()
        now = self._clock()
        record = EmailChangeRequest(
            change_id=self._id_factory(),
            user_id=user.user_id,
            token_hash=self.hash_token(raw),
            new_email=new_email,
            purpose=EMAIL_CHANGE_PURPOSE,
            created_at=now,
            expires_at=now + EMAIL_CHANGE_TTL,
        )
        self._email_changes.save(record)
        try:
            self._email.send(
                build_email_change_message(
                    to_address=new_email,
                    action_url=self._action_url(EMAIL_CHANGE_PATH, raw),
                    expires_hours=24,
                )
            )
            self._audit.record("email_change_requested", user_id=user.user_id)
        except EmailDeliveryError:
            self._audit.record("email_change_delivery_failed", user_id=user.user_id)
        return raw

    def _latest_unconsumed_email_change(self, user_id: str) -> EmailChangeRequest | None:
        assert self._email_changes is not None
        active = [item for item in self._email_changes.list_for_user(user_id) if not item.consumed]
        if not active:
            return None
        return max(active, key=lambda item: (item.created_at, item.change_id))

    def _send_email_changed_notice(self, old_email: str) -> None:
        try:
            self._email.send(build_email_changed_notice(to_address=old_email))
        except EmailDeliveryError:
            self._audit.record(
                "email_change_delivery_failed",
                detail="old_email_notice",
            )

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
