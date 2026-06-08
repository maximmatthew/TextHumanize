"""Bad-output regression bank: every known-bad case is enforced forever.

Each entry in the packaged bank is turned into a deterministic regression
assertion: run ``humanize`` with the stored seed/options and verify the
recorded invariants (tokens preserved, bad patterns absent, change bounded).
"""

from __future__ import annotations

import pytest

import texthumanize as th
from texthumanize.bad_output_bank import (
    load_bad_output_bank,
    validate_bad_output_bank,
)

_BANK = load_bad_output_bank()


class TestBadOutputBankStructure:
    def test_public_exports(self) -> None:
        assert callable(th.load_bad_output_bank)
        assert callable(th.validate_bad_output_bank)
        assert "load_bad_output_bank" in th.__all__

    def test_validate(self) -> None:
        summary = validate_bad_output_bank()
        assert summary["schema_version"] == "text-humanize.bad_output_bank.v1"
        assert summary["entry_count"] == len(_BANK)
        assert len(summary["ids"]) == len(set(summary["ids"]))

    def test_filters(self) -> None:
        en = load_bad_output_bank(languages=["en"])
        assert en and all(e["lang"] == "en" for e in en)
        doc = load_bad_output_bank(include_metadata=True)
        assert doc["schema_version"] == "text-humanize.bad_output_bank.v1"


@pytest.mark.parametrize("entry", _BANK, ids=[e["id"] for e in _BANK])
def test_bad_output_regression(entry: dict) -> None:
    preserve = entry.get("preserve") or {}
    brand = preserve.get("brand_terms") or []
    result = th.humanize(
        entry["input"],
        lang=entry["lang"],
        profile=entry.get("profile", "web"),
        intensity=entry.get("intensity", 60),
        seed=entry.get("seed"),
        preserve=preserve,
        constraints={"keep_keywords": brand},
    )
    out = result.text
    for check in entry["checks"]:
        kind, value = check["type"], check["value"]
        if kind == "preserve_token":
            assert value in out, f"{entry['id']}: lost protected token {value!r}"
        elif kind == "absent":
            assert value not in out, f"{entry['id']}: bad pattern {value!r} reappeared"
        elif kind == "max_change_ratio":
            assert result.change_ratio <= value, (
                f"{entry['id']}: change ratio {result.change_ratio:.3f} > {value}"
            )
