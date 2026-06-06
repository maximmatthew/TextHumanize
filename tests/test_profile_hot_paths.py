from __future__ import annotations

import pytest

from scripts.profile_hot_paths import (
    build_sample_text,
    parse_operations,
    parse_sizes,
    percentile,
    profile_hot_paths,
)


def test_build_sample_text_is_deterministic_and_sized() -> None:
    first = build_sample_text(1_000)
    second = build_sample_text(1_000)

    assert first == second
    assert len(first) == 1_000
    assert "Artificial intelligence" in first


def test_percentile_interpolates_values() -> None:
    values = [10.0, 20.0, 30.0, 40.0]

    assert percentile(values, 50) == pytest.approx(25.0)
    assert percentile(values, 95) == pytest.approx(38.5)


def test_parse_helpers_validate_cli_values() -> None:
    assert parse_sizes("1_000,10000") == (1_000, 10_000)
    assert parse_operations("detect_ai,watermark_report") == (
        "detect_ai",
        "watermark_report",
    )
    assert "humanize" in parse_operations("all")


def test_profile_hot_paths_returns_stable_schema() -> None:
    report = profile_hot_paths(
        sizes=[256],
        operations=["detect_ai_fast"],
        iterations=1,
        warmups=0,
        lang="en",
    )

    assert report["schema_version"] == "text-humanize.hot-path-profile.v1"
    assert report["memory_policy"] == "tracemalloc_peak_during_separate_uncached_runs"
    assert report["sizes"] == [256]
    assert report["operations"] == ["detect_ai_fast"]
    assert len(report["samples"]) == 1

    sample = report["samples"][0]
    assert sample["operation"] == "detect_ai_fast"
    assert sample["actual_chars"] == 256
    assert sample["iterations"] == 1
    assert sample["p50_ms"] >= 0
    assert sample["p95_ms"] >= sample["p50_ms"]
    assert sample["chars_per_sec_p50"] is None or sample["chars_per_sec_p50"] > 0
    assert sample["tracemalloc_peak_kb_p50"] is not None
    assert sample["tracemalloc_peak_kb_p95"] is not None
    assert sample["tracemalloc_peak_kb_p95"] >= sample["tracemalloc_peak_kb_p50"]
    assert len(sample["tracemalloc_peaks_kb"]) == 1


def test_profile_hot_paths_can_disable_memory_measurement() -> None:
    report = profile_hot_paths(
        sizes=[128],
        operations=["detect_ai_fast"],
        iterations=1,
        warmups=0,
        lang="en",
        measure_memory=False,
    )

    sample = report["samples"][0]
    assert report["memory_policy"] == "disabled"
    assert sample["tracemalloc_peak_kb_p50"] is None
    assert sample["tracemalloc_peak_kb_p95"] is None
    assert sample["tracemalloc_peaks_kb"] == []
