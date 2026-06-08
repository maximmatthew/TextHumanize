"""Tests for texthumanize.quality_metrics."""

from __future__ import annotations

import texthumanize as th
from texthumanize.quality_metrics import (
    acceptance_rate,
    benchmark_leaderboard,
    count_regression_examples,
    funnel_metrics,
    release_snapshot,
    semantic_drift_rate,
    watermark_eval,
)


class TestLeaderboard:
    def test_schema_and_rows(self) -> None:
        board = benchmark_leaderboard()
        assert board["schema_version"] == "text-humanize.leaderboard.v1"
        assert board["total_samples"] > 0
        assert board["rows"]
        row = board["rows"][0]
        for key in ("lang", "domain", "samples", "avg_score"):
            assert key in row

    def test_language_filter(self) -> None:
        board = benchmark_leaderboard(languages=["en"])
        assert board["languages"] == ["en"]


class TestReleaseSnapshot:
    def test_snapshot(self) -> None:
        snap = release_snapshot(["Furthermore, it is important to note the utilization of synergy."], lang="en")
        assert snap["schema_version"] == "text-humanize.release_snapshot.v1"
        assert snap["sample_count"] == 1
        assert "p50" in snap["latency_ms"] and "p95" in snap["latency_ms"]
        assert 0.0 <= snap["averages"]["quality_score"] <= 1.0


class TestAcceptanceAndDrift:
    def test_acceptance_rate(self) -> None:
        report = acceptance_rate(
            ["This is a clear and friendly sentence that reads naturally."],
            lang="en",
        )
        assert report["schema_version"] == "text-humanize.acceptance_rate.v1"
        assert 0.0 <= report["acceptance_rate"] <= 1.0
        assert report["total"] == 1

    def test_semantic_drift_rate(self) -> None:
        report = semantic_drift_rate([
            ("the quick brown fox", "the quick brown fox"),
            ("alpha beta gamma", "completely unrelated words here now"),
        ])
        assert report["schema_version"] == "text-humanize.semantic_drift.v1"
        assert report["total"] == 2
        assert report["drifted"] == 1
        assert report["drift_rate"] == 0.5


class TestWatermarkEval:
    def test_clean_fixtures_have_no_errors(self) -> None:
        result = watermark_eval()
        assert result["schema_version"] == "text-humanize.watermark_eval.v1"
        # The packaged samples are well-formed: every watermarked text should be
        # detected and every clean variant should pass.
        assert result["false_negative_rate"] == 0.0
        assert result["false_positive_rate"] == 0.0
        assert result["by_category"]


class TestRegressionCountAndFunnel:
    def test_count_regression_examples(self) -> None:
        report = count_regression_examples()
        assert report["schema_version"] == "text-humanize.regression_count.v1"
        assert report["total"] == report["bad_output_bank"] + report["eval_corpus"]
        assert report["bad_output_bank"] > 0

    def test_funnel_metrics(self) -> None:
        events = [
            {"item_id": "a", "stage": "audit"},
            {"item_id": "a", "stage": "humanize"},
            {"item_id": "a", "stage": "export"},
            {"item_id": "a", "stage": "publish"},
            {"item_id": "b", "stage": "audit"},
            {"item_id": "b", "stage": "humanize"},
        ]
        report = funnel_metrics(events)
        assert report["schema_version"] == "text-humanize.funnel.v1"
        assert report["counts"]["audit"] == 2
        assert report["counts"]["publish"] == 1
        assert report["overall_conversion"] == 0.5

    def test_public_exports(self) -> None:
        for name in ("benchmark_leaderboard", "release_snapshot", "acceptance_rate",
                     "semantic_drift_rate", "watermark_eval",
                     "count_regression_examples", "funnel_metrics"):
            assert hasattr(th, name)
            assert name in th.__all__
