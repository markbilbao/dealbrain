#!/usr/bin/env python3
"""Compare Ruff lint/format output against a committed baseline (Sprint 25a).

Policy: pre-existing debt is grandfathered. CI fails only when *new* violations
appear (or an unformatted file is newly introduced). Clearing debt is allowed
and does not require an immediate baseline rewrite.

Usage:
    uv run python scripts/check_ruff_baseline.py
    uv run python scripts/check_ruff_baseline.py --update
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "tests" / "lint" / "baselines" / "ruff.baseline.json"
DEFAULT_TARGETS = ("app", "tests")


def _rel(path: str | Path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _run_ruff(args: list[str]) -> list[dict]:
    cmd = [sys.executable, "-m", "ruff", *args]
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # Ruff exits 1 when diagnostics exist; still parse stdout JSON.
    if proc.returncode not in (0, 1):
        sys.stderr.write(proc.stderr or proc.stdout or "ruff failed\n")
        raise SystemExit(proc.returncode)
    raw = proc.stdout.strip()
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise SystemExit(f"Unexpected ruff JSON payload type: {type(data)!r}")
    return data


def collect_snapshot(targets: tuple[str, ...] = DEFAULT_TARGETS) -> dict:
    check_diags = _run_ruff(
        ["check", "--output-format=json", *targets],
    )
    format_diags = _run_ruff(
        ["format", "--check", "--output-format=json", *targets],
    )

    check_counts: Counter[str] = Counter()
    for item in check_diags:
        key = f"{_rel(item['filename'])}:{item['code']}"
        check_counts[key] += 1

    unformatted = sorted({_rel(item["filename"]) for item in format_diags})

    return {
        "version": 1,
        "targets": list(targets),
        "check": dict(sorted(check_counts.items())),
        "format_unformatted": unformatted,
        "totals": {
            "check": int(sum(check_counts.values())),
            "format_unformatted": len(unformatted),
        },
    }


def load_baseline(path: Path = BASELINE_PATH) -> dict:
    if not path.is_file():
        raise SystemExit(
            f"Missing Ruff baseline at {path}. Generate with "
            "`uv run python scripts/check_ruff_baseline.py --update`."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def write_baseline(snapshot: dict, path: Path = BASELINE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def compare(baseline: dict, current: dict) -> list[str]:
    """Return human-readable regression messages (empty => pass)."""
    regressions: list[str] = []

    base_check = Counter(baseline.get("check", {}))
    curr_check = Counter(current.get("check", {}))
    for key, count in sorted(curr_check.items()):
        prior = base_check.get(key, 0)
        if count > prior:
            regressions.append(f"new/increased lint: {key} baseline={prior} current={count}")

    base_fmt = set(baseline.get("format_unformatted", []))
    curr_fmt = set(current.get("format_unformatted", []))
    for path in sorted(curr_fmt - base_fmt):
        regressions.append(f"newly unformatted file: {path}")

    return regressions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="Rewrite the committed baseline from the current tree (intentional only).",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_PATH,
        help=f"Baseline path (default: {BASELINE_PATH})",
    )
    args = parser.parse_args(argv)

    snapshot = collect_snapshot()
    if args.update:
        write_baseline(snapshot, args.baseline)
        totals = snapshot["totals"]
        print(
            f"Wrote {args.baseline} "
            f"(check={totals['check']}, unformatted={totals['format_unformatted']})"
        )
        print("Commit this file intentionally when ratcheting or freezing debt.")
        return 0

    baseline = load_baseline(args.baseline)
    regressions = compare(baseline, snapshot)
    cleared_check = sum(baseline.get("check", {}).values()) - sum(
        snapshot.get("check", {}).values()
    )
    cleared_fmt = len(baseline.get("format_unformatted", [])) - len(
        snapshot.get("format_unformatted", [])
    )

    print(
        "Ruff baseline gate: "
        f"check={snapshot['totals']['check']} "
        f"(baseline {baseline.get('totals', {}).get('check', '?')}), "
        f"unformatted={snapshot['totals']['format_unformatted']} "
        f"(baseline {baseline.get('totals', {}).get('format_unformatted', '?')})"
    )
    if cleared_check > 0 or cleared_fmt > 0:
        print(
            f"Debt reduced (check -{max(cleared_check, 0)}, "
            f"format -{max(cleared_fmt, 0)}); consider --update to ratchet."
        )

    if regressions:
        print("FAIL: new Ruff regressions vs committed baseline:", file=sys.stderr)
        for line in regressions:
            print(f"  - {line}", file=sys.stderr)
        print(
            "Fix the new issues, or intentionally refresh with "
            "`uv run python scripts/check_ruff_baseline.py --update`.",
            file=sys.stderr,
        )
        return 1

    print("OK: no new Ruff lint/format regressions vs baseline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
