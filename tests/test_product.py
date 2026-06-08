"""Tests for texthumanize.product (Promopilot-facing building blocks)."""

from __future__ import annotations

import texthumanize as th
from texthumanize.product import (
    audit_batch,
    audit_widget_html,
    brand_voice_lock,
    client_report_html,
    compare_versions,
    content_plan_risk,
    make_brand_voice,
)

AI_TEXT = "Furthermore, it is important to note the utilization of synergy to maximize value."
HUMAN_TEXT = "We shipped the update on Tuesday and the team is happy with it."


class TestAuditWidget:
    def test_self_contained_html(self) -> None:
        html = audit_widget_html(AI_TEXT, lang="en")
        assert "thz-widget" in html
        assert "<style>" in html
        assert "AI &amp; Watermark Audit" in html
        # Neutral disclaimer, no bypass promises.
        assert "does not" in html and "guarantee" in html


class TestAuditBatch:
    def test_mixed_items(self) -> None:
        report = audit_batch([
            HUMAN_TEXT,
            {"id": "p2", "url": "https://x.example.com", "text": AI_TEXT},
        ], lang="en")
        assert report["schema_version"] == "text-humanize.audit_batch.v1"
        assert report["total"] == 2
        assert report["rows"][1]["url"] == "https://x.example.com"
        assert 0.0 <= report["high_risk_rate"] <= 1.0


class TestCompareVersions:
    def test_versions(self) -> None:
        report = compare_versions({
            "original": "It is imperative to utilize this methodology.",
            "humanized": "You should use this method.",
        }, lang="en")
        assert report["schema_version"] == "text-humanize.version_compare.v1"
        assert "original" in report["versions_present"]
        assert "humanized" in report["versions_present"]
        humanized = report["per_version"]["humanized"]
        assert "similarity_vs_original" in humanized
        assert "change_ratio_vs_original" in humanized


class TestContentPlanRisk:
    def test_gates(self) -> None:
        report = content_plan_risk([HUMAN_TEXT, AI_TEXT], lang="en")
        assert report["schema_version"] == "text-humanize.content_plan_risk.v1"
        assert report["total"] == 2
        assert sum(report["gate_counts"].values()) == 2
        for row in report["rows"]:
            assert row["gate"] in {"publish", "review", "block"}


class TestBrandVoice:
    def test_lock_preserves_terms(self) -> None:
        brand = make_brand_voice("Acme Cloud", locked_terms=["Acme Cloud"], tone="founder")
        assert brand["schema_version"] == "text-humanize.brand_voice.v1"
        result = brand_voice_lock(
            "Acme Cloud is a leading platform that leverages synergy to maximize value.",
            brand, lang="en", seed=1,
        )
        assert result["schema_version"] == "text-humanize.brand_voice_lock.v1"
        assert "Acme Cloud" in result["text"]
        assert result["locked_intact"] is True
        assert result["violations"] == []


class TestClientReport:
    def test_html_report(self) -> None:
        html = client_report_html(
            HUMAN_TEXT, lang="en",
            original="It is imperative to utilize this methodology effectively.",
        )
        assert html.startswith("<!DOCTYPE html>")
        assert "Quality dimensions" in html
        assert "Before / After" in html
        assert "does not" in html and "guarantee" in html

    def test_no_reference(self) -> None:
        html = client_report_html(HUMAN_TEXT, lang="en")
        assert html.startswith("<!DOCTYPE html>")
        assert "Before / After" not in html


def test_public_exports() -> None:
    for name in ("audit_widget_html", "audit_batch", "compare_versions",
                 "content_plan_risk", "make_brand_voice", "brand_voice_lock",
                 "client_report_html"):
        assert hasattr(th, name)
        assert name in th.__all__
