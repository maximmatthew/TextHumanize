#!/usr/bin/env python3
"""Capture a before/after release snapshot.

Records detector score, watermark risk, semantic similarity, readability,
unified quality score and latency p50/p95 for a fixed sample set. Store the
JSON per release to track regressions over time. Fully offline.

Usage:
    python scripts/release_snapshot.py --json
    python scripts/release_snapshot.py --lang en --intensity 70
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture release snapshot")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--intensity", type=int, default=60)
    parser.add_argument("--input", help="Optional text file (one sample per line)")
    args = parser.parse_args()

    from texthumanize import __version__
    from texthumanize.quality_metrics import release_snapshot

    texts = None
    if args.input:
        texts = [
            line.strip()
            for line in Path(args.input).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    snapshot = release_snapshot(texts, lang=args.lang, intensity=args.intensity)
    snapshot["version"] = __version__
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
