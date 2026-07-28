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
        super().__init__(
            f"Cannot register canonical product; missing required fields: {fields}"
        )


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
