"""Session management — expiration, revocation, and validation helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.auth.service import AuthService
from app.domain.entities.user_platform import UserSession
from app.domain.exceptions import UserPlatformAuthError
from app.domain.interfaces.user_platform_repository import SessionRepository


class SessionService:
    """Thin facade around session repository + AuthService validation."""

    def __init__(
        self,
        *,
        sessions: SessionRepository,
        auth: AuthService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sessions = sessions
        self._auth = auth
        self._clock = clock or (lambda: datetime.now(UTC))

    def validate(self, access_token: str | None) -> UserSession:
        session = self._auth.validate_session(access_token)
        if session is None:
            raise UserPlatformAuthError("Invalid session.")
        return session

    def revoke(self, session_id: str) -> None:
        self._sessions.revoke(session_id)

    def revoke_all(self, user_id: str) -> int:
        return self._sessions.revoke_all_for_user(user_id)

    def list_active(self, user_id: str) -> list[UserSession]:
        now = self._clock()
        return [
            s for s in self._sessions.list_for_user(user_id) if not s.revoked and s.expires_at > now
        ]

    def is_expired(self, session: UserSession) -> bool:
        return session.expires_at <= self._clock() or session.revoked
