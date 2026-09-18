#!/usr/bin/env python3
"""Provider-neutral PH public-web shopping benchmark harness.

Requires owner-supplied credentials for live mode. Never prints credentials.
Never claims certification. Does not scrape merchant sites.

Usage:
  uv run python scripts/public_web_ph_benchmark.py
  uv run python scripts/public_web_ph_benchmark.py --provider brave_search --live
  uv run python scripts/public_web_ph_benchmark.py \\
    --provider tavily_search --extract-live \\
    --search-report /tmp/piqsavi-tavily-ph/tavily_search.json \\
    --output-dir /tmp/piqsavi-tavily-extract-ph
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.research.public_web_benchmark import (  # noqa: E402
    NON_PRODUCTION_FIXTURE_MARKER,
    PublicWebBenchmarkIntent,
    assert_non_production_fixture,
    credential_env_name,
    evaluate_public_web_hit,
    load_public_web_benchmark_intents,
    owner_action_required,
    summarize_public_web_benchmark,
)
from app.research.public_web_extract import (  # noqa: E402
    DEFAULT_EXTRACT_DEPTH,
    DEFAULT_EXTRACT_OUTPUT_DIR,
    DEFAULT_SEARCH_REPORT_PATH,
    MAX_EXTRACT_SAMPLE_URLS,
    MISSING_SEARCH_REPORT_MESSAGE,
    PRIVATE_LOCAL_LIVE_ARTIFACT,
    TAVILY_EXTRACT_ENDPOINT,
    TAVILY_EXTRACT_MAX_URLS_PER_REQUEST,
    ExtractSampleError,
    MissingSearchReportError,
    assert_artifact_has_no_secrets,
    documented_basic_extract_credit_max,
    evaluate_extracted_page,
    select_extract_sample_from_report,
)
from app.research.public_web_policy import (  # noqa: E402
    brave_web_search_request_params,
    public_web_provider_policy_audits,
)

DEFAULT_FIXTURE = ROOT / "tests/fixtures/public_web_benchmark/non_production_search_hits.json"
DEFAULT_SEARCH_OUTPUT_DIR = Path("/tmp/piqavi-public-web-benchmark")
LIVE_ENDPOINTS = {
    "brave_search": "https://api.search.brave.com/res/v1/web/search",
    "tavily_search": "https://api.tavily.com/search",
    "exa_search": "https://api.exa.ai/search",
    "tavily_extract": TAVILY_EXTRACT_ENDPOINT,
}


def _secret_from_env(provider_key: str) -> str:
    return os.environ.get(credential_env_name(provider_key), "").strip()


def _load_fixture(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert_non_production_fixture(payload)
    return payload


def _hits_from_fixture(
    payload: dict[str, Any], intent: PublicWebBenchmarkIntent
) -> list[dict[str, str]]:
    rows = payload.get("results_by_intent", {}).get(intent.intent_id, [])
    cleaned: list[dict[str, str]] = []
    for row in rows:
        cleaned.append(
            {
                "title": str(row.get("title", "")),
                "url": str(row.get("url", "")),
                "snippet": str(row.get("snippet", "")),
            }
        )
    return cleaned


def _live_hits(provider_key: str, query: str, secret: str) -> tuple[list[dict[str, str]], int]:
    """Call an official search API. Does not fetch merchant product pages."""

    import httpx

    if provider_key == "brave_search":
        response = httpx.get(
            LIVE_ENDPOINTS[provider_key],
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": secret,
            },
            params=brave_web_search_request_params(query, count=10),
            timeout=20.0,
        )
        response.raise_for_status()
        web = response.json().get("web", {}).get("results", [])
        hits = [
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("description", "")),
            }
            for item in web
        ]
        return hits, 1
    if provider_key == "tavily_search":
        response = httpx.post(
            LIVE_ENDPOINTS[provider_key],
            json={
                "api_key": secret,
                "query": query,
                "country": "philippines",
                "topic": "general",
                "max_results": 10,
                "include_answer": False,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        hits = [
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("content", "")),
            }
            for item in response.json().get("results", [])
        ]
        return hits, 1
    if provider_key == "exa_search":
        response = httpx.post(
            LIVE_ENDPOINTS[provider_key],
            headers={"Authorization": f"Bearer {secret}"},
            json={"query": query, "numResults": 10, "type": "auto"},
            timeout=20.0,
        )
        response.raise_for_status()
        hits = [
            {
                "title": str(item.get("title", "")),
                "url": str(item.get("url", "")),
                "snippet": str(item.get("text") or item.get("highlights") or ""),
            }
            for item in response.json().get("results", [])
        ]
        return hits, 1
    raise ValueError(f"unsupported provider {provider_key}")


def _evaluate_provider(
    *,
    provider_key: str,
    intents: tuple[PublicWebBenchmarkIntent, ...],
    live: bool,
    fixture_payload: dict[str, Any] | None,
    secret: str,
) -> dict[str, Any]:
    evaluations = []
    seen_urls: set[str] = set()
    requests_made = 0
    retrieved_at = datetime.now(tz=UTC) if live else None
    for intent in intents:
        if live:
            hits, used = _live_hits(provider_key, intent.query, secret)
            requests_made += used
        else:
            assert fixture_payload is not None
            hits = _hits_from_fixture(fixture_payload, intent)
        for hit in hits:
            url = hit["url"]
            if not url:
                continue
            duplicate = url in seen_urls
            seen_urls.add(url)
            _result, evaluation = evaluate_public_web_hit(
                intent=intent,
                provider_key=provider_key,
                source_url=url,
                title=hit["title"],
                snippet=str(hit["snippet"])[:500],
                retrieved_at=retrieved_at,
                duplicate=duplicate,
                test_fixture=not live,
            )
            evaluations.append(evaluation)
    summary = summarize_public_web_benchmark(
        provider_key=provider_key,
        intents=intents,
        evaluations=tuple(evaluations),
        requests_made=requests_made if live else len(intents),
        live=live,
        fixture=not live,
    )
    return {
        "provider_key": provider_key,
        "live": live,
        "fixture": not live,
        "fixture_marker": None if live else NON_PRODUCTION_FIXTURE_MARKER,
        "production_certified": False,
        "closes_sprint_32": False,
        "summary": summary.to_dict(),
        "evaluations": [item.to_dict() for item in evaluations],
        "policy_audit": next(
            item.to_dict()
            for item in public_web_provider_policy_audits()
            if item.provider_key == provider_key
        ),
    }


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    assert_artifact_has_no_secrets(
        payload,
        (
            os.environ.get("BRAVE_SEARCH_API_KEY", ""),
            os.environ.get("TAVILY_API_KEY", ""),
            os.environ.get("EXA_API_KEY", ""),
        ),
    )
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(serialized + "\n", encoding="utf-8")


def _live_extract(urls: list[str], secret: str) -> dict[str, Any]:
    """Call the official Tavily Extract API only. Does not fetch merchant pages."""

    import httpx

    if len(urls) > MAX_EXTRACT_SAMPLE_URLS:
        raise ExtractSampleError(f"first extract benchmark max is {MAX_EXTRACT_SAMPLE_URLS} URLs")
    if len(urls) > TAVILY_EXTRACT_MAX_URLS_PER_REQUEST:
        raise ExtractSampleError(
            f"Tavily Extract documents a max of {TAVILY_EXTRACT_MAX_URLS_PER_REQUEST} "
            "URLs per request"
        )
    try:
        response = httpx.post(
            TAVILY_EXTRACT_ENDPOINT,
            headers={"Authorization": f"Bearer {secret}"},
            json={
                "urls": urls,
                "extract_depth": DEFAULT_EXTRACT_DEPTH,
                "include_images": False,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Tavily Extract HTTP {exc.response.status_code}") from None
    except httpx.HTTPError:
        raise RuntimeError("Tavily Extract request failed") from None
    if not isinstance(payload, dict):
        raise RuntimeError("Tavily Extract returned a non-object response")
    return payload


def _extract_results_by_url(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    mapped: dict[str, dict[str, Any]] = {}
    for row in payload.get("results") or []:
        if isinstance(row, dict) and row.get("url"):
            mapped[str(row["url"])] = row
    for row in payload.get("failed_results") or []:
        if isinstance(row, dict) and row.get("url"):
            mapped.setdefault(str(row["url"]), row)
    return mapped


def _run_extract_mode(
    *,
    search_report: Path,
    output_dir: Path,
    live: bool,
    persist_raw: bool,
) -> int:
    try:
        selected = select_extract_sample_from_report(search_report)
    except MissingSearchReportError as exc:
        envelope = {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "mode": "extract",
            "live": live,
            "production_certified": False,
            "closes_sprint_32": False,
            "certifies_tavily": False,
            "certifies_retailer": False,
            "scraping": False,
            "environment_mutation": False,
            "owner_action_required": [
                {
                    "owner_action_required": "yes",
                    "reason": MISSING_SEARCH_REPORT_MESSAGE,
                    "missing_file": str(search_report),
                }
            ],
        }
        _write_artifact(output_dir / "summary.json", envelope)
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        print(str(exc))
        return 2
    except ExtractSampleError as exc:
        envelope = {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "mode": "extract",
            "live": live,
            "production_certified": False,
            "closes_sprint_32": False,
            "scraping": False,
            "owner_action_required": [{"owner_action_required": "yes", "reason": str(exc)}],
        }
        _write_artifact(output_dir / "summary.json", envelope)
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        print(str(exc))
        return 2

    selection_payload = {
        "artifact_kind": PRIVATE_LOCAL_LIVE_ARTIFACT if live else NON_PRODUCTION_FIXTURE_MARKER,
        "mode": "extract_sample",
        "provider_key": "tavily_search",
        "extract_depth": DEFAULT_EXTRACT_DEPTH,
        "max_urls": MAX_EXTRACT_SAMPLE_URLS,
        "selected_count": len(selected),
        "documented_max_basic_credits_if_all_succeed": documented_basic_extract_credit_max(
            len(selected)
        ),
        "credit_basis": (
            "Official Tavily docs 2026-09-18: basic extract = 1 API credit per 5 "
            "successful extractions; failed extractions are not charged. Methodology "
            "only; not an invoice; not a live performance report."
        ),
        "marketplace_excluded": True,
        "advanced_not_run": True,
        "production_certified": False,
        "closes_sprint_32": False,
        "selected": [item.to_dict() for item in selected],
    }
    _write_artifact(output_dir / "selected_urls.json", selection_payload)
    if not live:
        envelope = {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "mode": "extract_select_only",
            "live": False,
            "production_certified": False,
            "closes_sprint_32": False,
            "certifies_tavily": False,
            "scraping": False,
            "environment_mutation": False,
            "selected_count": len(selected),
            "documented_max_basic_credits_if_all_succeed": documented_basic_extract_credit_max(
                len(selected)
            ),
            "output_dir": str(output_dir),
        }
        _write_artifact(output_dir / "summary.json", envelope)
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return 0

    secret = _secret_from_env("tavily_search")
    if not secret:
        required = owner_action_required("tavily_search")
        envelope = {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "mode": "extract",
            "live": True,
            "production_certified": False,
            "closes_sprint_32": False,
            "certifies_tavily": False,
            "scraping": False,
            "environment_mutation": False,
            "owner_action_required": [required],
            "selected_count": len(selected),
        }
        _write_artifact(output_dir / "summary.json", envelope)
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        print("OWNER ACTION REQUIRED: live Tavily Extract cannot run without TAVILY_API_KEY.")
        return 2

    retrieved_at = datetime.now(tz=UTC)
    raw_response = _live_extract([item.source_url for item in selected], secret)
    by_url = _extract_results_by_url(raw_response)
    evaluations = []
    for item in selected:
        row = by_url.get(item.source_url, {})
        raw_content = row.get("raw_content") if isinstance(row, dict) else None
        succeeded = isinstance(raw_content, str) and bool(raw_content.strip())
        evaluation = evaluate_extracted_page(
            source_url=item.source_url,
            raw_content=raw_content if isinstance(raw_content, str) else None,
            retrieved_at=retrieved_at,
            extraction_succeeded=succeeded,
            merchant_identity=item.merchant_identity,
            seed_product_identity=item.product_identity,
            test_fixture=False,
        )
        evaluations.append(evaluation.to_dict())
        if persist_raw and isinstance(raw_content, str) and raw_content:
            raw_name = content_safe_stem(item.source_url)
            raw_payload = {
                "artifact_kind": PRIVATE_LOCAL_LIVE_ARTIFACT,
                "warning": "PRIVATE_LOCAL_LIVE_ARTIFACT — never commit extracted retailer page text",
                "source_url": item.source_url,
                "retrieved_at": retrieved_at.isoformat(),
                "raw_content": raw_content,
            }
            _write_artifact(output_dir / "raw" / f"{raw_name}.json", raw_payload)

    report = {
        "artifact_kind": PRIVATE_LOCAL_LIVE_ARTIFACT,
        "warning": (
            "PRIVATE_LOCAL_LIVE_ARTIFACT. Tavily terms restrict disclosure to "
            "third parties of performance information or analysis relating to "
            "its Services. Do not commit this file."
        ),
        "provider_key": "tavily_search",
        "mode": "extract",
        "live": True,
        "extract_depth": DEFAULT_EXTRACT_DEPTH,
        "advanced_not_run": True,
        "raw_content_persisted": persist_raw,
        "production_certified": False,
        "closes_sprint_32": False,
        "certifies_tavily": False,
        "certifies_retailer": False,
        "scraping": False,
        "source_policy_default": "unknown",
        "technical_level_b_candidate_is_not_offer_evidence": True,
        "evaluations": evaluations,
    }
    _write_artifact(output_dir / "tavily_extract.json", report)
    envelope = {
        "generated_at": retrieved_at.isoformat(),
        "mode": "extract",
        "live": True,
        "artifact_kind": PRIVATE_LOCAL_LIVE_ARTIFACT,
        "production_certified": False,
        "closes_sprint_32": False,
        "certifies_tavily": False,
        "certifies_retailer": False,
        "scraping": False,
        "environment_mutation": False,
        "extract_depth": DEFAULT_EXTRACT_DEPTH,
        "selected_count": len(selected),
        "evaluation_count": len(evaluations),
        "raw_content_persisted": persist_raw,
        "output_dir": str(output_dir),
        "documented_max_basic_credits_if_all_succeed": documented_basic_extract_credit_max(
            len(selected)
        ),
    }
    _write_artifact(output_dir / "summary.json", envelope)
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    return 0


def content_safe_stem(source_url: str) -> str:
    host = source_url.replace("https://", "").replace("http://", "")
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in host)
    return cleaned[:80] or "extract"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="PH public-web shopping benchmark. Live mode needs owner credentials."
    )
    parser.add_argument(
        "--provider",
        choices=("brave_search", "tavily_search", "exa_search", "all"),
        default="all",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call official search APIs. Requires env credentials. Does not scrape merchants.",
    )
    parser.add_argument(
        "--extract-live",
        action="store_true",
        help=(
            "Call official Tavily Extract only, using a prior search report. "
            "Requires TAVILY_API_KEY. Does not scrape merchants. basic depth only."
        ),
    )
    parser.add_argument(
        "--extract-select-only",
        action="store_true",
        help=(
            "Select the first extract URL sample from a prior search report. "
            "Does not call Tavily and does not require an API key."
        ),
    )
    parser.add_argument(
        "--search-report",
        type=Path,
        default=DEFAULT_SEARCH_REPORT_PATH,
        help="Prior Tavily Search JSON report used as the extract URL source.",
    )
    parser.add_argument(
        "--persist-raw",
        action="store_true",
        help=(
            "LOCAL DEBUG ONLY. Persist extracted page text under the output dir. "
            "Never commit. Default is off."
        ),
    )
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
    )
    args = parser.parse_args(argv)
    extract_mode = args.extract_live or args.extract_select_only
    if args.extract_live and args.extract_select_only:
        print("Choose only one of --extract-live or --extract-select-only.")
        return 2
    if extract_mode and args.live:
        print("Extract mode cannot be combined with --live search.")
        return 2
    if extract_mode and args.provider not in {"tavily_search", "all"}:
        print("Extract mode is Tavily-only for this Sprint 32 technical benchmark.")
        return 2
    output_dir = args.output_dir or (
        DEFAULT_EXTRACT_OUTPUT_DIR if extract_mode else DEFAULT_SEARCH_OUTPUT_DIR
    )
    if extract_mode:
        return _run_extract_mode(
            search_report=args.search_report,
            output_dir=output_dir,
            live=args.extract_live,
            persist_raw=bool(args.persist_raw) and args.extract_live,
        )
    providers = (
        ("brave_search", "tavily_search", "exa_search")
        if args.provider == "all"
        else (args.provider,)
    )
    intents = load_public_web_benchmark_intents()
    reports = []
    missing = []
    fixture_payload = None if args.live else _load_fixture(args.fixture)
    for provider_key in providers:
        if args.live:
            secret = _secret_from_env(provider_key)
            if not secret:
                missing.append(owner_action_required(provider_key))
                continue
            report = _evaluate_provider(
                provider_key=provider_key,
                intents=intents,
                live=True,
                fixture_payload=None,
                secret=secret,
            )
        else:
            report = _evaluate_provider(
                provider_key=provider_key,
                intents=intents,
                live=False,
                fixture_payload=fixture_payload,
                secret="",
            )
        reports.append(report)
        _write_artifact(
            output_dir / f"{provider_key}.json",
            report,
        )
    envelope = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "live": args.live,
        "production_certified": False,
        "closes_sprint_32": False,
        "scraping": False,
        "environment_mutation": False,
        "owner_action_required": missing,
        "reports": [
            {
                "provider_key": item["provider_key"],
                "summary": item["summary"],
                "evaluation_count": len(item["evaluations"]),
            }
            for item in reports
        ],
    }
    _write_artifact(output_dir / "summary.json", envelope)
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    if args.live and missing and not reports:
        print("OWNER ACTION REQUIRED: live provider benchmark cannot run without credentials.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
