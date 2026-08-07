"""Public consumer brand and score presentation helpers.

Public product brand is PiqSavi. Internal technical codename remains DealBrain.
Public score feature is PiqScore. Internal scoring contract remains DealScore.

These helpers are for consumer-visible presentation strings only. They must not
be applied to machine identifiers, JSON field names, routes, or class names.
"""

from __future__ import annotations

PUBLIC_BRAND = "PiqSavi"
PUBLIC_TAGLINE = "Your AI Personal Shopper"
INTERNAL_CODENAME = "DealBrain"

PUBLIC_SCORE_NAME = "PiqScore"
INTERNAL_SCORE_NAME = "DealScore"
PUBLIC_PERSONAL_SCORE_LABEL = "Personalized PiqScore"


def present_public_brand_text(text: str) -> str:
    """Rewrite residual internal-codename branding for consumer-visible copy.

    Replaces only the exact token ``DealBrain``.
    """
    if INTERNAL_CODENAME not in text:
        return text
    return text.replace(INTERNAL_CODENAME, PUBLIC_BRAND)


def present_public_score_text(text: str) -> str:
    """Rewrite consumer-visible DealScore feature naming to PiqScore.

    Ordered exact-token replacements avoid emitting ``PersonalPiqScore`` and
    avoid uncontrolled ``Deal`` → ``Piq`` mutation.
    """
    if (
        "PersonalDealScore" not in text
        and "Personal DealScore" not in text
        and "Personal Deal Score" not in text
        and "Deal Scores" not in text
        and "Deal Score" not in text
        and INTERNAL_SCORE_NAME not in text
    ):
        return text
    # Personal variants first so DealScore substitution cannot create PersonalPiqScore.
    updated = text.replace("PersonalDealScore", PUBLIC_PERSONAL_SCORE_LABEL)
    updated = updated.replace("Personal DealScore", PUBLIC_PERSONAL_SCORE_LABEL)
    updated = updated.replace("Personal Deal Score", PUBLIC_PERSONAL_SCORE_LABEL)
    updated = updated.replace("DealScores", f"{PUBLIC_SCORE_NAME}s")
    updated = updated.replace("Deal Scores", f"{PUBLIC_SCORE_NAME}s")
    updated = updated.replace(INTERNAL_SCORE_NAME, PUBLIC_SCORE_NAME)
    updated = updated.replace("Deal Score", PUBLIC_SCORE_NAME)
    return updated


def present_consumer_text(text: str) -> str:
    """Compose master-brand and score presentation for consumer-visible copy."""
    return present_public_score_text(present_public_brand_text(text))
