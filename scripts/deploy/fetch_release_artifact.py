#!/usr/bin/env python3
"""Fetch and locate the release-manifest artifact from a Build Image workflow run.

This helper validates GitHub Actions metadata via `gh` CLI. It does not mutate
the downloaded manifest.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path


class FetchError(RuntimeError):
    """Raised when artifact fetch/metadata checks fail."""


def _gh_json(args: list[str]) -> dict | list:
    proc = subprocess.run(
        ["gh", *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise FetchError(proc.stderr.strip() or f"gh failed: {' '.join(args)}")
    return json.loads(proc.stdout)


def assert_build_run(run_id: str, *, require_main: bool = True) -> dict:
    data = _gh_json(
        [
            "run",
            "view",
            str(run_id),
            "--json",
            "conclusion,headSha,event,workflowName,status,headBranch,url,databaseId",
        ]
    )
    if not isinstance(data, dict):
        raise FetchError("unexpected gh run view payload")
    if data.get("status") != "completed":
        raise FetchError(f"build run not completed: {data.get('status')}")
    if data.get("conclusion") != "success":
        raise FetchError(f"build run conclusion not success: {data.get('conclusion')}")
    if data.get("workflowName") != "Build Image":
        raise FetchError(f"workflow must be 'Build Image', got {data.get('workflowName')!r}")
    if require_main and data.get("headBranch") != "main":
        raise FetchError(f"build run must be for main, got branch {data.get('headBranch')!r}")
    head_sha = str(data.get("headSha", ""))
    if len(head_sha) != 40:
        raise FetchError(f"invalid headSha: {head_sha!r}")
    return data


def assert_ci_run(test_run_id: str, expected_sha: str) -> dict:
    data = _gh_json(
        [
            "run",
            "view",
            str(test_run_id),
            "--json",
            "conclusion,headSha,workflowName,status,headBranch,event",
        ]
    )
    if not isinstance(data, dict):
        raise FetchError("unexpected gh run view payload for CI")
    if data.get("status") != "completed" or data.get("conclusion") != "success":
        raise FetchError("CI run must be completed successfully")
    # CI workflow name is "CI"
    name = str(data.get("workflowName", ""))
    if name not in {"CI", "ci"} and name.lower() != "ci":
        raise FetchError(f"test workflow must be CI, got {name!r}")
    if data.get("headSha") != expected_sha:
        raise FetchError(
            f"CI headSha mismatch: {data.get('headSha')} != {expected_sha}"
        )
    return data


def download_release_manifest(run_id: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    artifacts = _gh_json(
        ["api", f"repos/{{owner}}/{{repo}}/actions/runs/{run_id}/artifacts"]
    )
    items = artifacts.get("artifacts") or [] if isinstance(artifacts, dict) else artifacts
    matches = [
        a
        for a in items
        if str(a.get("name", "")).startswith("release-manifest-") and not a.get("expired")
    ]
    if len(matches) != 1:
        raise FetchError(
            f"expected exactly one release-manifest artifact, found {len(matches)}"
        )
    name = matches[0]["name"]
    proc = subprocess.run(
        ["gh", "run", "download", str(run_id), "-n", name, "-D", str(dest_dir)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise FetchError(proc.stderr.strip() or "gh run download failed")

    candidates = list(dest_dir.rglob("release-manifest.json"))
    if len(candidates) != 1:
        # Also accept zip extraction layouts
        zips = list(dest_dir.glob("*.zip"))
        for zpath in zips:
            with zipfile.ZipFile(zpath) as zf:
                zf.extractall(dest_dir)
        candidates = list(dest_dir.rglob("release-manifest.json"))
    if len(candidates) != 1:
        raise FetchError(
            f"expected exactly one release-manifest.json after download, found {len(candidates)}"
        )
    return candidates[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-workflow-run-id", required=True)
    parser.add_argument("--dest", type=Path, required=True)
    parser.add_argument("--assert-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        meta = assert_build_run(args.build_workflow_run_id)
        if args.assert_only:
            print(json.dumps(meta, sort_keys=True))
            return 0
        path = download_release_manifest(args.build_workflow_run_id, args.dest)
        print(str(path))
    except FetchError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
