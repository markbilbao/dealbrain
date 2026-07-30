"""Store namespace constants for Sprint 23 operational persistence."""

from __future__ import annotations

# Sprint 17 — User Platform
USERS = "user_platform.users"
SESSIONS = "user_platform.sessions"
PROFILES = "user_platform.profiles"
PREFERENCES = "user_platform.preferences"
SETTINGS = "user_platform.settings"
WISHLISTS = "user_platform.wishlists"
FAVORITE_BRANDS = "user_platform.favorite_brands"
FAVORITE_MARKETPLACES = "user_platform.favorite_marketplaces"
SAVED_PRODUCTS = "user_platform.saved_products"
SAVED_COMPARISONS = "user_platform.saved_comparisons"
RECOMMENDATION_HISTORY = "user_platform.recommendation_history"
SAVED_SEARCHES = "user_platform.saved_searches"
RECENTLY_VIEWED = "user_platform.recently_viewed"
PASSWORD_RESETS = "user_platform.password_resets"
EMAIL_VERIFICATIONS = "user_platform.email_verifications"
AUDIT_EVENTS = "user_platform.audit_events"

# Sprint 18 — Marketplace Data
MD_SOURCES = "marketplace_data.sources"
MD_CONFIGURATIONS = "marketplace_data.configurations"
MD_RAW_RECORDS = "marketplace_data.raw_records"
MD_OFFERS = "marketplace_data.offers"
MD_CONTENT_HASH = "marketplace_data.content_hash_index"
MD_PRICE_SNAPSHOTS = "marketplace_data.price_snapshots"
MD_INVENTORY_SNAPSHOTS = "marketplace_data.inventory_snapshots"
MD_IMPORT_BATCHES = "marketplace_data.import_batches"
MD_IMPORT_RECORDS = "marketplace_data.import_records"
MD_SYNC_JOBS = "marketplace_data.sync_jobs"
MD_SYNC_CONFLICTS = "marketplace_data.sync_conflicts"
MD_CHECKPOINTS = "marketplace_data.checkpoints"
MD_HEALTH = "marketplace_data.health"
MD_DEAD_LETTERS = "marketplace_data.dead_letters"
MD_CONNECTOR_RUNS = "marketplace_data.connector_runs"
MD_CATALOG = "marketplace_data.catalog_products"

# Sprint 19 — Alerts & Notifications
ALERT_RULES = "alerts.rules"
ALERT_EVALUATIONS = "alerts.evaluations"
ALERT_EVENTS = "alerts.events"
NC_NOTIFICATIONS = "notifications.notifications"
NC_DELIVERIES = "notifications.deliveries"
NC_TEMPLATES = "notifications.templates"
NC_DIGESTS = "notifications.digests"
NC_PREFERENCES = "notifications.preferences"
NC_UNSUBSCRIBE = "notifications.unsubscribe_tokens"

# Sprint 20 — Affiliate
AFF_MERCHANTS = "affiliate.merchants"
AFF_LINKS = "affiliate.links"
AFF_CLICKS = "affiliate.clicks"
AFF_ATTRIBUTIONS = "affiliate.attributions"
AFF_DISCLOSURES = "affiliate.disclosures"
AFF_META = "affiliate.meta"

# Sprint 21 — Merchant Platform
MERCH_ORGS = "merchant.organizations"
MERCH_ACCOUNTS = "merchant.accounts"
MERCH_ACCOUNT_TOKENS = "merchant.account_tokens"
MERCH_USERS = "merchant.users"
MERCH_MEMBERSHIPS = "merchant.memberships"
MERCH_INVITATIONS = "merchant.invitations"
MERCH_PRODUCTS = "merchant.product_submissions"
MERCH_OFFERS = "merchant.offer_submissions"
MERCH_MATCH_REVIEWS = "merchant.match_reviews"
MERCH_PROMOTIONS = "merchant.promotions"
MERCH_CAMPAIGNS = "merchant.campaigns"
MERCH_AUDIT = "merchant.audit_events"
MERCH_VERIFICATIONS = "merchant.verifications"
MERCH_MARKETPLACE_ACCOUNTS = "merchant.marketplace_accounts"
MERCH_PREFERENCES = "merchant.notification_preferences"

USER_PLATFORM_STORES = (
    USERS,
    SESSIONS,
    PROFILES,
    PREFERENCES,
    SETTINGS,
    WISHLISTS,
    FAVORITE_BRANDS,
    FAVORITE_MARKETPLACES,
    SAVED_PRODUCTS,
    SAVED_COMPARISONS,
    RECOMMENDATION_HISTORY,
    SAVED_SEARCHES,
    RECENTLY_VIEWED,
    PASSWORD_RESETS,
    EMAIL_VERIFICATIONS,
    AUDIT_EVENTS,
)

MARKETPLACE_DATA_STORES = (
    MD_SOURCES,
    MD_CONFIGURATIONS,
    MD_RAW_RECORDS,
    MD_OFFERS,
    MD_CONTENT_HASH,
    MD_PRICE_SNAPSHOTS,
    MD_INVENTORY_SNAPSHOTS,
    MD_IMPORT_BATCHES,
    MD_IMPORT_RECORDS,
    MD_SYNC_JOBS,
    MD_SYNC_CONFLICTS,
    MD_CHECKPOINTS,
    MD_HEALTH,
    MD_DEAD_LETTERS,
    MD_CONNECTOR_RUNS,
    MD_CATALOG,
)

ALERT_STORES = (ALERT_RULES, ALERT_EVALUATIONS, ALERT_EVENTS)
NOTIFICATION_STORES = (
    NC_NOTIFICATIONS,
    NC_DELIVERIES,
    NC_TEMPLATES,
    NC_DIGESTS,
    NC_PREFERENCES,
    NC_UNSUBSCRIBE,
)
AFFILIATE_STORES = (
    AFF_MERCHANTS,
    AFF_LINKS,
    AFF_CLICKS,
    AFF_ATTRIBUTIONS,
    AFF_DISCLOSURES,
    AFF_META,
)
MERCHANT_STORES = (
    MERCH_ORGS,
    MERCH_ACCOUNTS,
    MERCH_ACCOUNT_TOKENS,
    MERCH_USERS,
    MERCH_MEMBERSHIPS,
    MERCH_INVITATIONS,
    MERCH_PRODUCTS,
    MERCH_OFFERS,
    MERCH_MATCH_REVIEWS,
    MERCH_PROMOTIONS,
    MERCH_CAMPAIGNS,
    MERCH_AUDIT,
    MERCH_VERIFICATIONS,
    MERCH_MARKETPLACE_ACCOUNTS,
    MERCH_PREFERENCES,
)
