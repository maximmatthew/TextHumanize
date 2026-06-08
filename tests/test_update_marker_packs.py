"""Tests for the marker pack review script."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "update_marker_packs.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("update_marker_packs", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_pack(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "text-humanize.contributor_pack.v1",
                "pack": "ai_markers",
                "name": "Test pack",
                "license": {"id": "CC0-1.0"},
                "entries": [
                    {
                        "id": "ai_marker_en_docs_existing",
                        "lang": "en",
                        "domain": "docs",
                        "category": "phrases",
                        "marker": "It is important to note that",
                        "severity": "low",
                        "suggested_actions": ["delete when redundant"],
                        "source": "test",
                        "license": "CC0-1.0",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_corpus(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "text-humanize.eval_corpus.v1",
                "samples": [
                    {
                        "id": "sample_raw_ai",
                        "lang": "en",
                        "label": "raw_ai",
                        "domain": "product",
                        "text": (
                            "Furthermore, this comprehensive platform helps teams "
                            "optimize workflows and achieve measurable outcomes."
                        ),
                    },
                    {
                        "id": "sample_human",
                        "lang": "en",
                        "label": "human",
                        "domain": "product",
                        "text": "I checked the export and left a short note.",
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def test_update_marker_packs_generates_review_table_and_candidates(tmp_path):
    script = _load_script()
    corpus = tmp_path / "corpus.json"
    pack = tmp_path / "pack.json"
    review = tmp_path / "review.md"
    candidates = tmp_path / "candidates.json"
    _write_corpus(corpus)
    _write_pack(pack)

    rc = script.main([
        "--corpus", str(corpus),
        "--pack", str(pack),
        "--review-out", str(review),
        "--candidates-out", str(candidates),
        "--max-candidates", "10",
    ])

    assert rc == 0
    review_text = review.read_text(encoding="utf-8")
    assert "# AI Marker Pack Review" in review_text
    assert "|decision|marker|lang|category|" in review_text
    assert "furthermore" in review_text
    assert "sample_raw_ai" in review_text
    assert "It is important to note that" not in review_text

    payload = json.loads(candidates.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "text-humanize.marker_review_candidates.v1"
    assert payload["candidate_count"] >= 1
    assert any(item["marker"] == "furthermore" for item in payload["candidates"])


def test_update_marker_packs_applies_only_approved_rows(tmp_path):
    script = _load_script()
    pack = tmp_path / "pack.json"
    review = tmp_path / "review.md"
    _write_pack(pack)
    review.write_text(
        "\n".join([
            "# AI Marker Pack Review",
            "|decision|marker|lang|category|severity|domains|labels|sample_ids|count|suggested_actions|notes|",
            "|---|---|---|---|---|---|---|---|---|---|---|",
            "|approved|furthermore|en|connectors|medium|product|raw_ai|sample_raw_ai|1|remove redundant transition<br>start with the claim|reviewed|",
            "|TODO|comprehensive|en|adjectives|low|product|raw_ai|sample_raw_ai|1|delete if vague|skip|",
        ]),
        encoding="utf-8",
    )

    summary = script.apply_reviewed_rows(review, pack)
    data = json.loads(pack.read_text(encoding="utf-8"))

    assert summary == {"added": 1, "skipped": 0, "total_entries": 2}
    markers = {entry["marker"]: entry for entry in data["entries"]}
    assert "furthermore" in markers
    assert "comprehensive" not in markers
    assert markers["furthermore"]["domain"] == "product"
    assert markers["furthermore"]["source"] == "manual-review-from-eval-corpus"
