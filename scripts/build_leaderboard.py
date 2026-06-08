#!/usr/bin/env python3
"""Build the public per-language/domain benchmark leaderboard.

Runs the built-in detector over the licensed eval corpus and prints a
leaderboard as JSON (default) or Markdown. Fully offline.

Usage:
    python scripts/build_leaderboard.py --json
    python scripts/build_leaderboard.py --markdown
    python scripts/build_leaderboard.py --langs en,ru,uk --markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _to_markdown(board: dict) -> str:
    lines = [
        f"# TextHumanize Benchmark Leaderboard (threshold {board['threshold']})",
        "",
        f"Total samples: {board['total_samples']} · "
        f"languages: {', '.join(board['languages'])} · "
        f"domains: {', '.join(board['domains'])}",
        "",
        "| Lang | Domain | Samples | Avg score | AI recall | Human FP | Edited flag |",
        "|:-----|:-------|--------:|----------:|----------:|---------:|------------:|",
    ]
    for row in board["rows"]:
        def fmt(value: object) -> str:
            return "—" if value is None else f"{float(value):.2f}"
        lines.append(
            f"| {row['lang']} | {row['domain']} | {row['samples']} | "
            f"{row['avg_score']:.2f} | {fmt(row['ai_recall'])} | "
            f"{fmt(row['human_false_positive_rate'])} | {fmt(row['edited_ai_flag_rate'])} |"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build benchmark leaderboard")
    parser.add_argument("--langs", help="Comma-separated languages, e.g. en,ru,uk")
    parser.add_argument("--domains", help="Comma-separated domains")
    parser.add_argument("--threshold", type=float, default=0.50)
    parser.add_argument("--markdown", action="store_true", help="Markdown output")
    parser.add_argument("--json", action="store_true", help="JSON output (default)")
    args = parser.parse_args()

    from texthumanize.quality_metrics import benchmark_leaderboard

    languages = args.langs.split(",") if args.langs else None
    domains = args.domains.split(",") if args.domains else None
    board = benchmark_leaderboard(
        languages=languages, domains=domains, threshold=args.threshold
    )

    if args.markdown:
        print(_to_markdown(board))
    else:
        print(json.dumps(board, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
