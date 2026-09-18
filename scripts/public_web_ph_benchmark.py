#!/usr/bin/env python3
"""Provider-neutral PH public-web shopping benchmark harness.

Requires owner-supplied credentials for live mode. Never prints credentials.
Never claims certification. Does not scrape merchant sites.

Usage:
  uv run python scripts/public_web_ph_benchmark.py
  uv run python scripts/public_web_ph_benchmark.py --provider brave_search --live
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
from app.research.public_web_policy import public_web_provider_policy_audits  # noqa: E402

DEFAULT_FIXTURE = ROOT / "tests/fixtures/public_web_benchmark/non_production_search_hits.json"
LIVE_ENDPOINTS = {
    "brave_search": "https://api.search.brave.com/res/v1/web/search",
    "tavily_search": "https://api.tavily.com/search",
    "exa_search": "https://api.exa.ai/search",
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
            params={"q": query, "country": "PH", "search_lang": "en", "count": 10},
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
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    if any(
        token in serialized
        for token in (
            os.environ.get("BRAVE_SEARCH_API_KEY", "never-match-empty"),
            os.environ.get("TAVILY_API_KEY", "never-match-empty"),
            os.environ.get("EXA_API_KEY", "never-match-empty"),
        )
        if token
    ):
        raise RuntimeError("refusing to write an artifact that contains a credential")
    path.write_text(serialized + "\n", encoding="utf-8")


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
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/piqavi-public-web-benchmark"),
    )
    args = parser.parse_args(argv)
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
            args.output_dir / f"{provider_key}.json",
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
    _write_artifact(args.output_dir / "summary.json", envelope)
    print(json.dumps(envelope, ensure_ascii=False, indent=2))
    if args.live and missing and not reports:
        print("OWNER ACTION REQUIRED: live provider benchmark cannot run without credentials.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
