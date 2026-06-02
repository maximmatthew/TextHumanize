"""Contract parity tests backed by fixtures shared with PHP and TypeScript."""

from __future__ import annotations

import json
from pathlib import Path

from texthumanize import analyze, detect_ai, humanize

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "parity_cases.json"


def _cases() -> list[dict]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "text-humanize.parity.v1"
    return list(payload["cases"])


def test_python_contract_matches_shared_parity_fixtures():
    for case in _cases():
        expected = case["expected"]
        preserve = case.get("preserve", {})

        result = humanize(
            case["text"],
            lang=case["lang"],
            profile=case["profile"],
            intensity=case["intensity"],
            seed=case["seed"],
            preserve={"brand_terms": preserve.get("brand_terms", [])},
            constraints={"keep_keywords": preserve.get("keep_keywords", [])},
        )
        assert result.lang == expected["lang"], case["id"]
        assert result.profile == case["profile"], case["id"]
        assert result.text.strip(), case["id"]

        for term in [*preserve.get("brand_terms", []), *preserve.get("keep_keywords", [])]:
            assert term in result.text, f"{case['id']} lost protected term {term!r}"

        report = analyze(case["text"], lang=case["lang"])
        assert report.lang == expected["lang"], case["id"]
        assert report.total_words >= expected["min_words"], case["id"]
        assert report.total_sentences >= expected["min_sentences"], case["id"]
        assert 0 <= report.artificiality_score <= 100, case["id"]

        detection = detect_ai(case["text"], lang=case["lang"])
        assert detection["verdict"] in {"human", "mixed", "ai"}, case["id"]
        assert 0 <= detection["score"] <= 1, case["id"]
        assert 0 <= detection["confidence"] <= 1, case["id"]
