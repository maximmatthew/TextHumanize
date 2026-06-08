#!/usr/bin/env python3
"""Fast offline pre-release sanity checks.

Local PHP/JS/mypy/full-pytest runners can hang in some sandboxes, so this
script runs a quick, dependency-free set of invariants that catch the most
common release breakages (version drift, hardcoded version asserts, quality
rounding, broken data fixtures) in a couple of seconds.

Usage:
    python scripts/dev_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _check_version_sync() -> list[str]:
    from scripts.check_version_sync import main as version_main
    return [] if version_main() == 0 else ["check_version_sync failed"]


def _check_import_smoke() -> list[str]:
    import texthumanize as th
    problems = []
    for name in ("humanize", "quality_score_report", "audit_widget_html",
                 "benchmark_leaderboard", "watermark_eval", "load_bad_output_bank"):
        if not hasattr(th, name):
            problems.append(f"missing public export: {name}")
    return problems


def _check_quality_rounding() -> list[str]:
    from texthumanize import quality_score_report
    problems = []
    for n in range(1, 40):
        text = f"word{n} " * n + "This is a natural sentence here."
        report = quality_score_report(text, lang="en")
        if report["score_100"] != round(report["score"] * 100.0, 1):
            problems.append(f"score_100 mismatch at n={n}")
            break
    return problems


def _check_watermark_fixtures() -> list[str]:
    from texthumanize.quality_metrics import watermark_eval
    result = watermark_eval()
    problems = []
    if result["false_negative_rate"] > 0.0:
        problems.append(f"watermark FN rate {result['false_negative_rate']} > 0")
    if result["false_positive_rate"] > 0.0:
        problems.append(f"watermark FP rate {result['false_positive_rate']} > 0")
    return problems


def _check_bad_output_bank() -> list[str]:
    from texthumanize.bad_output_bank import validate_bad_output_bank
    try:
        validate_bad_output_bank()
    except Exception as exc:
        return [f"bad_output_bank invalid: {exc}"]
    return []


def main() -> int:
    checks = [
        ("version sync", _check_version_sync),
        ("import smoke", _check_import_smoke),
        ("quality rounding", _check_quality_rounding),
        ("watermark fixtures", _check_watermark_fixtures),
        ("bad output bank", _check_bad_output_bank),
    ]
    failed = False
    for name, fn in checks:
        problems = fn()
        if problems:
            failed = True
            print(f"✗ {name}")
            for problem in problems:
                print(f"   - {problem}")
        else:
            print(f"✓ {name}")
    if failed:
        print("\ndev_check FAILED")
        return 1
    print("\ndev_check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
