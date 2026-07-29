"""Domain exceptions for Product Identity and related use cases.

Raised by domain/intelligence services. HTTP mapping belongs in the API layer.
"""

from uuid import UUID


class ProductNotFoundError(Exception):
    """Raised when a CRUD product cannot be found by identifier."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")


class InsufficientCanonicalIdentityError(Exception):
    """Raised when a parsed product lacks fields required for registration."""

    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = missing_fields
        fields = ", ".join(missing_fields)
        super().__init__(f"Cannot register canonical product; missing required fields: {fields}")


class CanonicalProductNotFoundError(Exception):
    """Raised when a canonical registry product cannot be found."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(f"Canonical product not found: {product_id}")


class InvalidProductRelationError(Exception):
    """Raised when a product relationship cannot be created or queried."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class UnsupportedProductError(Exception):
    """Raised when a listing cannot be resolved into a usable product identity.

    Covers blank titles and parses that lack registry-required identity fields.
    """

    def __init__(self, title: str, reason: str) -> None:
        self.title = title
        self.reason = reason
        super().__init__(reason)


class DealScoreValidationError(Exception):
    """Raised when DealScore inputs cannot be evaluated safely.

    Typical causes: mixed currencies, empty result sets after validation,
    or universally invalid listing inputs.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PriceHistoryValidationError(Exception):
    """Raised when price history cannot be computed safely.

    Typical causes: mixed currencies in one statistics request, empty
    observation sets, or production attempts to load mock fixtures.
    """

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CollectionValidationError(Exception):
    """Raised when marketplace collection inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CollectionJobNotFoundError(Exception):
    """Raised when a scheduled collection job cannot be found."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Collection job not found: {job_id}")


class CollectionRunNotFoundError(Exception):
    """Raised when a collection run cannot be found."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Collection run not found: {run_id}")


class CollectionRunImmutableError(Exception):
    """Raised when a completed collection run would be mutated."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Collection run is immutable after completion: {run_id}")


class CollectionConcurrentRunError(Exception):
    """Raised when a job is already executing."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        super().__init__(f"Collection job is already running: {job_id}")


class CollectionJobNotRunnableError(Exception):
    """Raised when a disabled or paused job cannot be executed."""

    def __init__(self, job_id: str, reason: str) -> None:
        self.job_id = job_id
        self.reason = reason
        super().__init__(f"Collection job {job_id} cannot run: {reason}")


class WatchlistValidationError(Exception):
    """Raised when watchlist or alert inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class WatchlistNotFoundError(Exception):
    """Raised when a watchlist cannot be found."""

    def __init__(self, watchlist_id: str) -> None:
        self.watchlist_id = watchlist_id
        super().__init__(f"Watchlist not found: {watchlist_id}")


class WatchlistItemNotFoundError(Exception):
    """Raised when a watchlist item cannot be found."""

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Watchlist item not found: {item_id}")


class AlertNotFoundError(Exception):
    """Raised when an alert cannot be found."""

    def __init__(self, alert_id: str) -> None:
        self.alert_id = alert_id
        super().__init__(f"Alert not found: {alert_id}")


class ReviewValidationError(Exception):
    """Raised when review intelligence inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ReviewNotFoundError(Exception):
    """Raised when no review snapshots exist for a product."""

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"No review snapshots found for product: {product_id}")


class ReviewSummaryValidationError(Exception):
    """Raised when review summary inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ReviewSummaryNotFoundError(Exception):
    """Raised when no review summary exists for a product."""

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"No review summary found for product: {product_id}")


class AIProviderUnavailableError(Exception):
    """Raised when an AI review provider cannot serve a request."""

    def __init__(self, provider: str, reason: str, *, error_code: str = "unavailable") -> None:
        self.provider = provider
        self.reason = reason
        self.error_code = error_code
        super().__init__(f"AI provider {provider} unavailable: {reason}")


class AIProviderTimeoutError(AIProviderUnavailableError):
    """Raised when a provider exceeds the configured timeout."""

    def __init__(self, provider: str, timeout_seconds: float) -> None:
        super().__init__(
            provider,
            f"timed out after {timeout_seconds}s",
            error_code="timeout",
        )


class AIProviderRateLimitError(AIProviderUnavailableError):
    """Raised when a provider reports rate limiting."""

    def __init__(self, provider: str) -> None:
        super().__init__(provider, "rate limited", error_code="rate_limited")


class AIProviderMalformedResponseError(AIProviderUnavailableError):
    """Raised when provider output fails structural parsing."""

    def __init__(self, provider: str, detail: str) -> None:
        super().__init__(provider, detail, error_code="malformed")


class ShoppingAssistantValidationError(Exception):
    """Raised when shopping assistant inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ShoppingAssistantNotFoundError(Exception):
    """Raised when a shopping assistant conversation or resource is missing."""

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"Shopping assistant resource not found: {resource_id}")


class CommunityIntelligenceValidationError(Exception):
    """Raised when community intelligence inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class CommunityIntelligenceNotFoundError(Exception):
    """Raised when community evidence or a product intelligence payload is missing."""

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"Community intelligence resource not found: {resource_id}")


class KnowledgeGraphValidationError(Exception):
    """Raised when knowledge graph inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class KnowledgeGraphNotFoundError(Exception):
    """Raised when a knowledge graph node, edge, or path resource is missing."""

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"Knowledge graph resource not found: {resource_id}")


class PersonalAgentValidationError(Exception):
    """Raised when personal shopping agent inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class PersonalAgentNotFoundError(Exception):
    """Raised when a customer profile or personal recommendation resource is missing."""

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"Personal agent resource not found: {resource_id}")


class UserPlatformValidationError(Exception):
    """Raised when user platform inputs cannot be processed safely."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UserPlatformNotFoundError(Exception):
    """Raised when a user platform resource cannot be found."""

    def __init__(self, resource_id: str) -> None:
        self.resource_id = resource_id
        super().__init__(f"User platform resource not found: {resource_id}")


class UserPlatformAuthError(Exception):
    """Raised when authentication or authorization fails."""

    def __init__(self, message: str = "Authentication required.") -> None:
        self.message = message
        super().__init__(message)


class UserPlatformConflictError(Exception):
    """Raised when a unique constraint (e.g. email) would be violated."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UserPlatformRateLimitError(Exception):
    """Raised when a rate-limiting hook rejects an action."""

    def __init__(self, message: str = "Rate limit exceeded.") -> None:
        self.message = message
        super().__init__(message)
