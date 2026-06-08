"""Bad-output regression bank.

Every known-bad humanization outcome (from issues or Promopilot cases) is
recorded as a deterministic entry here and enforced forever by the test suite.
This module loads and validates the packaged bank; :mod:`tests` turns each
entry into a regression assertion.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

_BANK_FILE = "bad_output_bank_v1.json"
_BANK_SCHEMA = "text-humanize.bad_output_bank.v1"
_VALID_CHECKS = {"preserve_token", "absent", "max_change_ratio"}
_REQUIRED_FIELDS = {"id", "lang", "input", "checks"}

__all__ = ["load_bad_output_bank", "validate_bad_output_bank"]


def _read_bank() -> dict[str, Any]:
    bank_path = resources.files("texthumanize").joinpath("data").joinpath(_BANK_FILE)
    with bank_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError(f"Invalid bad-output bank resource: {_BANK_FILE}")
    return data


def load_bad_output_bank(
    *,
    languages: list[str] | None = None,
    origins: list[str] | None = None,
    include_metadata: bool = False,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Load the packaged bad-output regression bank.

    Args:
        languages: Optional language filter.
        origins: Optional origin filter (e.g. ``issue``, ``promopilot``).
        include_metadata: Return the full document (schema, license, entries)
            instead of just the entry list.
    """
    data = _read_bank()
    wanted_langs = set(languages or [])
    wanted_origins = set(origins or [])
    entries = [
        entry for entry in data["entries"]
        if (not wanted_langs or entry.get("lang") in wanted_langs)
        and (not wanted_origins or entry.get("origin") in wanted_origins)
    ]
    if not include_metadata:
        return entries
    enriched = dict(data)
    enriched["entries"] = entries
    enriched["entry_count"] = len(entries)
    return enriched


def validate_bad_output_bank(
    bank: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate the bank structure and return a summary.

    Raises ``ValueError`` on malformed entries so CI fails fast when a bad
    contribution is added.
    """
    if bank is None:
        document = _read_bank()
        entries = document["entries"]
    elif isinstance(bank, dict):
        entries = bank.get("entries", [])
    else:
        entries = bank

    seen_ids: set[str] = set()
    for entry in entries:
        missing = _REQUIRED_FIELDS - set(entry)
        if missing:
            raise ValueError(f"Bad-output entry missing fields {sorted(missing)}: {entry.get('id')}")
        entry_id = str(entry["id"])
        if entry_id in seen_ids:
            raise ValueError(f"Duplicate bad-output entry id: {entry_id}")
        seen_ids.add(entry_id)
        if not isinstance(entry["checks"], list) or not entry["checks"]:
            raise ValueError(f"Bad-output entry {entry_id} needs at least one check")
        for check in entry["checks"]:
            kind = check.get("type")
            if kind not in _VALID_CHECKS:
                raise ValueError(
                    f"Bad-output entry {entry_id} has unknown check {kind!r}; "
                    f"expected one of {sorted(_VALID_CHECKS)}"
                )
            if "value" not in check:
                raise ValueError(f"Bad-output entry {entry_id} check {kind} missing value")

    return {
        "schema_version": _BANK_SCHEMA,
        "entry_count": len(entries),
        "ids": sorted(seen_ids),
    }
