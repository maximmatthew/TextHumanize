#!/usr/bin/env python3
"""Fail CI if release version is inconsistent across package manifests."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _extract(pattern: str, text: str, file: str) -> str:
    m = re.search(pattern, text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError(f"Unable to parse version from {file}")
    return m.group(1)


def _require_contains(file: str, text: str, needle: str) -> None:
    if needle not in text:
        raise RuntimeError(f"{file} does not contain expected release reference: {needle}")


def main() -> int:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    expected = _extract(r'^version\s*=\s*"([^"]+)"', pyproject, "pyproject.toml")

    checks: list[tuple[str, str]] = []

    checks.append((
        "texthumanize/__init__.py",
        _extract(
            r'__version__\s*=\s*"([^"]+)"',
            (ROOT / "texthumanize" / "__init__.py").read_text(encoding="utf-8"),
            "texthumanize/__init__.py",
        ),
    ))

    for rel in ("package.json", "js/package.json", "js/package-lock.json", "composer.json", "php/composer.json"):
        obj = json.loads((ROOT / rel).read_text(encoding="utf-8"))
        checks.append((rel, obj["version"]))

    checks.append((
        "js/src/version.ts",
        _extract(
            r"VERSION\s*=\s*'([^']+)'",
            (ROOT / "js" / "src" / "version.ts").read_text(encoding="utf-8"),
            "js/src/version.ts",
        ),
    ))

    checks.append((
        "php/src/TextHumanize.php",
        _extract(
            r"public const VERSION = '([^']+)'",
            (ROOT / "php" / "src" / "TextHumanize.php").read_text(encoding="utf-8"),
            "php/src/TextHumanize.php",
        ),
    ))

    mismatches = [(file, version) for file, version in checks if version != expected]
    if mismatches:
        print(f"Version mismatch: expected {expected}")
        for file, version in mismatches:
            print(f" - {file}: {version}")
        return 1

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    changelog_versions = [
        version for version in re.findall(r"^## \[([^\]]+)\]", changelog, flags=re.MULTILINE)
        if version.lower() != "unreleased"
    ]
    if not changelog_versions:
        print("CHANGELOG.md does not contain a release entry")
        return 1
    changelog_latest = changelog_versions[0]
    if changelog_latest != expected:
        print(f"CHANGELOG.md latest entry mismatch: expected {expected}, got {changelog_latest}")
        return 1

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    try:
        _require_contains("README.md", readme, f"What's New in v{expected}")
        _require_contains("README.md", readme, f"pip install texthumanize=={expected}")
        _require_contains("README.md", readme, f"TextHumanize v{expected}")
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print(f"Version sync OK: {expected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
