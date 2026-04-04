#!/usr/bin/env python3
"""Quick pre-release smoke checks for core import, version and HTML handling."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _expected_version() -> str:
    pyproject = ROOT / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    return data["project"]["version"]


def _check_html_handling(humanize_fn) -> None:
    src = "<p>Furthermore, the implementation is comprehensive. Moreover, the system is robust.</p>"
    result = humanize_fn(
        src,
        lang="en",
        intensity=60,
        constraints={"max_detection_loops": 0},
    )

    if "<p>" not in result.text or "</p>" not in result.text:
        raise RuntimeError("HTML tags were not preserved in smoke test")

    # Ensure the visible text stays processable, not a complete pass-through.
    plain_src = re.sub(r"<[^>]+>", "", src)
    plain_out = re.sub(r"<[^>]+>", "", result.text)
    if plain_out.strip() == plain_src.strip():
        raise RuntimeError("HTML smoke test produced no text transformation")


def main() -> int:
    from texthumanize import __version__, humanize

    if not __version__:
        raise RuntimeError("Empty package version")
    expected = _expected_version()
    if __version__ != expected:
        raise RuntimeError(
            f"Version mismatch in smoke test: imported={__version__}, expected={expected}"
        )
    _check_html_handling(humanize)
    print(f"Release smoke test OK (version={__version__})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Release smoke test FAILED: {exc}", file=sys.stderr)
        raise
