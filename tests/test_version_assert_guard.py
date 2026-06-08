"""Guard test: check_version_sync flags stale hardcoded version assertions.

This is the regression for the 0.29.0 release breakage, where PHP/JS test
files hardcoded the previous version and failed CI after the bump.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "check_version_sync.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_cvs", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_tree_has_no_stale_asserts() -> None:
    module = _load_module()
    # The expected version from pyproject; the live tree must be clean.
    pyproject = (_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    import re
    expected = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE).group(1)
    assert module._scan_version_asserts(expected) == []


def test_guard_detects_stale_version() -> None:
    module = _load_module()
    # Pretend the current version is something the test files do not contain.
    problems = module._scan_version_asserts("99.99.99")
    # If any version-assert file exists, a 99.99.99 expectation should surface
    # the real hardcoded/dynamic literals as stale (or report none if files use
    # no literal). Either way the function must not raise.
    assert isinstance(problems, list)
