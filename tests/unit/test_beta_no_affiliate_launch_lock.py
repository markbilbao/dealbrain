"""2026-09-07 lock: public beta without affiliate monetization.

Documentation/configuration review only. Affiliate architecture stays.
Ranking/scoring paths must remain monetization-unaware.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.consumer.canonical_presentation import page_view_from_snapshot
from app.consumer.location import DeliveryContext
from app.consumer.pages import render_page
from app.domain.entities.decision_presentation import CanonicalProductPresentation
from app.domain.entities.decision_snapshot import (
    AffiliateNeutralitySnapshot,
    CanonicalDecisionSnapshot,
    CanonicalPiqScoreSnapshot,
    CanonicalRecommendationSnapshot,
    DecisionEvidenceSnapshot,
    EvaluatedProductSnapshot,
)
from app.domain.entities.shopping_assistant import ConversationOwner
from app.services.canonical_presentation_contract import attach_presentation_contract

ROOT = Path(__file__).resolve().parents[2]
START = datetime(2030, 1, 1, tzinfo=UTC)
DECISION_ID = "00000000-0000-4000-8000-000000000207"
OFFICIAL_ID = "official-retailer-canonical"
MARKETPLACE_ID = "marketplace-offer-canonical"

AFFILIATE_SERVICES = (
    "app/services/affiliate_merchant_service.py",
    "app/services/affiliate_link_service.py",
    "app/services/affiliate_tracking_service.py",
    "app/services/affiliate_reporting_service.py",
    "app/services/affiliate_disclosure_service.py",
)
AFFILIATE_DOCS = (
    "docs/AFFILIATE_LINK_SERVICE.md",
    "docs/AFFILIATE_ATTRIBUTION.md",
    "docs/AFFILIATE_REVENUE_ENGINE.md",
    "docs/AFFILIATE_DISCLOSURE.md",
    "docs/legal/PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md",
)
ROADMAP_DOCS = (
    "docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md",
    "docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md",
    "docs/roadmap/GAP_INVENTORY.md",
    "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md",
    "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md",
    "docs/roadmap/sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md",
    "docs/roadmap/sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md",
)
RANKING_MODULES = (
    "app/intelligence/dealscore/engine.py",
    "app/intelligence/recommendation/engine.py",
    "app/intelligence/shopping_assistant/recommendation.py",
)
INCOMPLETE_SPRINTS = (
    "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md",
    "docs/roadmap/sprints/SPRINT_37_MARKETCONTEXT_CURRENCY_LOCALIZATION.md",
    "docs/roadmap/sprints/SPRINT_38_CONNECTOR_RELIABILITY_DEGRADATION.md",
    "docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md",
    "docs/roadmap/sprints/SPRINT_40_SECURITY_ABUSE_HARDENING.md",
    "docs/roadmap/sprints/SPRINT_44_CLAIMS_APPROVALS_REHEARSAL.md",
    "docs/roadmap/sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md",
)
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _score(value: float, digest: str) -> CanonicalPiqScoreSnapshot:
    return CanonicalPiqScoreSnapshot(
        value=value,
        authority="canonical-piqscore-dealscore-engine",
        semantics_version="protected-existing-authority-v1",
        snapshot_sha256=digest * 64,
    )


def _snapshot() -> CanonicalDecisionSnapshot:
    base = CanonicalDecisionSnapshot(
        decision_id=DECISION_ID,
        context_version=1,
        owner=ConversationOwner(
            principal_type="guest",
            principal_id="guest-no-affiliate",
            session_id="session-no-affiliate",
            expires_at=START + timedelta(minutes=30),
        ),
        evaluated_products=(
            EvaluatedProductSnapshot(
                product_id=OFFICIAL_ID,
                display_name="Official Retailer Headphones",
                variant="black",
                canonical_piqscore=_score(91, "a"),
            ),
            EvaluatedProductSnapshot(
                product_id=MARKETPLACE_ID,
                display_name="Marketplace Headphones",
                variant="black",
                canonical_piqscore=_score(88, "b"),
            ),
        ),
        recommendation=CanonicalRecommendationSnapshot(
            authority="canonical-recommendation-engine",
            decision="buy",
            best_piq_product_id=OFFICIAL_ID,
            alternative_product_ids=(MARKETPLACE_ID,),
            snapshot_sha256="c" * 64,
        ),
        evidence=(
            DecisionEvidenceSnapshot(
                evidence_id="official-comfort",
                product_id=OFFICIAL_ID,
                topic="comfort",
                fact="canonical comfort evidence",
                source="captured-offer://comfort/official",
                captured_at=START,
                freshness="unknown",
                provenance_sha256="d" * 64,
            ),
        ),
        unknowns=("shipping to the selected delivery location is not verified",),
        affiliate_neutrality=AffiliateNeutralitySnapshot(),
        created_at=START,
        updated_at=START,
        data_classification="canonical_decision",
    )
    return attach_presentation_contract(
        base,
        product_presentation=(
            CanonicalProductPresentation(
                product_id=OFFICIAL_ID,
                brand="Official",
                model="Headphones",
                offer_url="https://www.example.com/offer",
            ),
        ),
        data_classification="canonical_decision",
    )


def test_owner_lock_records_zero_affiliate_public_beta() -> None:
    roadmap = _read("docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md")
    assert "OWNER ROADMAP LOCK — 2026-09-07" in roadmap
    assert "PUBLIC BETA MONETIZATION DEFERRED — PRODUCT VALIDATION LAUNCH LOCKED" in roadmap
    assert "without affiliate monetization" in roadmap
    assert "Affiliate revenue is not a launch requirement" in roadmap
    assert "September 30, 2026" in roadmap
    assert "ordinary outbound merchant links" in roadmap
    sprint32 = _read("docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md")
    assert "**Status:** In progress" in sprint32
    assert "Sprint 32 is **not complete**" in sprint32
    sprint45 = _read("docs/roadmap/sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md")
    assert "**Status:** Planned" in sprint45
    assert "no later than September 30, 2026" in sprint45
    sprint47 = _read("docs/roadmap/sprints/SPRINT_47_OFFER_TIMING_PROMOTIONS_BUYING_ACTION.md")
    assert "POST-BETA" in sprint47
    assert "does **not** pull Sprint 47 into pre-launch" in sprint47


def test_ec31_mixed_affiliate_proof_is_conditional() -> None:
    roadmap = _read("docs/roadmap/GLOBAL_PUBLIC_BETA_MASTER_ROADMAP.md")
    sprint45 = _read("docs/roadmap/sprints/SPRINT_45_CONTROLLED_GLOBAL_PUBLIC_BETA_LAUNCH.md")
    for text in (roadmap, sprint45):
        assert "a non-affiliate merchant can outrank an affiliate merchant" not in text
        assert "If affiliate-enabled merchants are active" in text
        assert "runtime mixed-monetization comparison is not required" in text
        assert "unknown shipping does not become zero" in text.lower() or (
            "unknown shipping does not become zero/free" in text
        )
        assert "unverified" in text.lower() and "voucher" in text.lower()
        assert "affiliate commission does not affect the result" in text
    assert "verified discount can reduce effective cost" in roadmap
    assert "verified applicable voucher can reduce effective cost" in roadmap
    assert "known shipping can increase effective cost" in roadmap


def test_external_register_defers_affiliate_without_deleting_history() -> None:
    register = _read("docs/roadmap/EXTERNAL_DEPENDENCY_REGISTER.md")
    assert "| EXT-07 |" in register
    assert "`not_started`" in register
    assert "not a September launch blocker" in register
    assert "SPRINT_26_SHOPEE_APPLICATION_EXECUTION.md" in register
    assert "affiliate approval as product-data permission" in register
    inventory = _read(
        "docs/roadmap/evidence/SPRINT_32_PHILIPPINES_SOURCE_CERTIFICATION_INVENTORY.md"
    )
    assert "initial affiliate-monetization targets" in inventory
    assert "no longer September affiliate launch dependencies" in inventory


def test_sprint39_priority_metrics_exclude_affiliate_conversion() -> None:
    sprint39 = _read("docs/roadmap/sprints/SPRINT_39_ANALYTICS_FEEDBACK_SUPPORT.md")
    assert "**Status:** Planned" in sprint39
    for metric in (
        "decision started",
        "decision completed",
        "Results viewed",
        "merchant outbound click",
        "decision completion rate",
        "outbound CTR",
        "repeat decisions",
        "return visits",
        "Recommendation helpful / not helpful",
        "incorrect price / product / source report",
        "insufficient-evidence outcome",
    ):
        assert metric in sprint39
    assert "no affiliate conversion/revenue metric is required" in sprint39
    assert "Preserve privacy/consent requirements" in sprint39


def test_affiliate_architecture_is_retained() -> None:
    for relative in AFFILIATE_SERVICES:
        path = ROOT / relative
        assert path.is_file(), f"missing affiliate service: {relative}"
        assert "class Affiliate" in path.read_text(encoding="utf-8")
    assert (ROOT / "app/affiliate").is_dir()
    assert (ROOT / "app/domain/entities/affiliate.py").is_file()
    engine = _read("docs/AFFILIATE_REVENUE_ENGINE.md")
    for phrase in (
        "No real affiliate APIs",
        "No real commissions",
        "No real conversions",
        "No billing",
        "No payouts",
        "No merchant portal",
    ):
        assert phrase in engine
    assert "deferred, not abandoned" in engine
    disclosure = _read("docs/legal/PIQSAVI_AFFILIATE_ADVERTISING_DISCLOSURE_COUNSEL_DRAFT.md")
    assert "Not for publication" in disclosure
    assert "does not publish this draft" in disclosure
    assert "Not evidence of legal approval" in disclosure


def test_ranking_modules_remain_monetization_unaware() -> None:
    forbidden = ("commission", "affiliate", "payout", "adsense", "sponsored")
    for relative in RANKING_MODULES:
        lowered = _read(relative).lower()
        for token in forbidden:
            assert token not in lowered, f"{relative} references {token!r}"


def test_incomplete_sprints_are_not_marked_complete() -> None:
    for relative in INCOMPLETE_SPRINTS:
        text = _read(relative)
        status_line = next(line for line in text.splitlines() if line.startswith("**Status:**"))
        assert "complete" not in status_line.lower() or "not complete" in status_line.lower()
        assert "Sprint 32 is **not complete**" in _read(
            "docs/roadmap/sprints/SPRINT_32_PHILIPPINES_MERCHANT_CERTIFICATION.md"
        )


def test_canonical_uuid_pages_omit_inactive_affiliate_disclosure() -> None:
    view = page_view_from_snapshot(
        _snapshot(),
        page="results",
        session_location=DeliveryContext(),
    )
    assert view.affiliate_disclosure == ""
    html = render_page(view)
    assert "View offer" in html
    assert "https://www.example.com/offer" in html
    assert "affiliate-note" not in html
    assert "affiliate link" not in html.lower()
    assert "may earn a commission" not in html.lower()
    assert "piqscore" in html.lower()


def test_empty_affiliate_note_is_not_rendered() -> None:
    view = page_view_from_snapshot(
        _snapshot(),
        page="results",
        session_location=DeliveryContext(),
    )
    empty = replace(view, affiliate_disclosure="   ")
    html = render_page(empty)
    assert "affiliate-note" not in html
    labeled = replace(view, affiliate_disclosure="PiqSavi may earn a commission")
    labeled_html = render_page(labeled)
    assert "affiliate-note" in labeled_html
    assert "PiqSavi may earn a commission" in labeled_html


def test_changed_docs_relative_links_resolve() -> None:
    missing: list[str] = []
    for relative in (*AFFILIATE_DOCS, *ROADMAP_DOCS, "docs/architecture/ARCHITECTURE_LOCK.md"):
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        for target in LINK_RE.findall(text):
            href = target.strip()
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            href = href.split("#", 1)[0].split(" ", 1)[0]
            if not href:
                continue
            resolved = (path.parent / href).resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                continue
            if not resolved.exists():
                missing.append(f"{relative} -> {href}")
    assert missing == []
