"""Quality, benchmark and release metrics for TextHumanize.

This module turns the building blocks (detector, watermark forensics, quality
score, readability) into the aggregate metrics tracked in the project roadmap:

* :func:`benchmark_leaderboard` — per language/domain detector + quality board.
* :func:`release_snapshot` — before/after detector, watermark, similarity,
  readability and latency p50/p95 for a release.
* :func:`acceptance_rate` — share of humanized outputs that pass quality gates.
* :func:`semantic_drift_rate` — share of rewrites that drift past a threshold.
* :func:`watermark_eval` — Unicode/statistical watermark false positive/negative
  rates over the packaged watermark samples.
* :func:`count_regression_examples` — size of the regression/bad-output banks.
* :func:`funnel_metrics` — audit → humanize → export/publish conversion.

Everything here is fully offline and deterministic so it can run in CI and
release checks. Heavy imports stay lazy inside the functions.
"""

from __future__ import annotations

import statistics
import time
from typing import Any

__all__ = [
    "acceptance_rate",
    "benchmark_leaderboard",
    "count_regression_examples",
    "funnel_metrics",
    "release_snapshot",
    "semantic_drift_rate",
    "watermark_eval",
]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] * (1.0 - frac) + ordered[high] * frac


# ─────────────────────────────────────────────────────────────
#  Benchmark leaderboard
# ─────────────────────────────────────────────────────────────

def benchmark_leaderboard(
    corpus: list[dict[str, Any]] | None = None,
    *,
    languages: list[str] | None = None,
    domains: list[str] | None = None,
    threshold: float = 0.50,
) -> dict[str, Any]:
    """Build a per language × domain leaderboard from the eval corpus.

    For every (language, domain) cell the board reports the AI recall, the
    human false-positive rate, the edited-AI flag rate and the average detector
    score, so progress can be tracked publicly per language and content type.
    """
    from texthumanize.benchmarks import _canonical_label, load_eval_corpus
    from texthumanize.core import detect_ai

    if corpus is None:
        loaded = load_eval_corpus()
        samples = loaded if isinstance(loaded, list) else []
    else:
        samples = list(corpus)

    if languages:
        samples = [s for s in samples if s.get("lang") in set(languages)]
    if domains:
        samples = [s for s in samples if s.get("domain") in set(domains)]

    cells: dict[tuple[str, str], dict[str, list[float]]] = {}
    for sample in samples:
        lang = str(sample.get("lang", "unknown"))
        domain = str(sample.get("domain", "general"))
        label = _canonical_label(str(sample.get("label", "")))
        detection = detect_ai(sample["text"], lang=lang)
        score = float(detection.get("combined_score", detection.get("score", 0.0)))
        cell = cells.setdefault((lang, domain), {
            "human": [], "raw_ai": [], "lightly_edited_ai": [],
            "heavily_edited_ai": [], "_all": [],
        })
        cell.setdefault(label, []).append(score)
        cell["_all"].append(score)

    rows: list[dict[str, Any]] = []
    for (lang, domain), scores in sorted(cells.items()):
        human = scores.get("human", [])
        raw_ai = scores.get("raw_ai", [])
        edited = scores.get("lightly_edited_ai", []) + scores.get("heavily_edited_ai", [])
        rows.append({
            "lang": lang,
            "domain": domain,
            "samples": len(scores["_all"]),
            "avg_score": round(statistics.mean(scores["_all"]), 4) if scores["_all"] else 0.0,
            "ai_recall": round(
                sum(s >= threshold for s in raw_ai) / len(raw_ai), 4
            ) if raw_ai else None,
            "human_false_positive_rate": round(
                sum(s >= threshold for s in human) / len(human), 4
            ) if human else None,
            "edited_ai_flag_rate": round(
                sum(s >= threshold for s in edited) / len(edited), 4
            ) if edited else None,
        })

    languages_seen = sorted({row["lang"] for row in rows})
    domains_seen = sorted({row["domain"] for row in rows})
    return {
        "schema_version": "text-humanize.leaderboard.v1",
        "threshold": threshold,
        "total_samples": sum(row["samples"] for row in rows),
        "languages": languages_seen,
        "domains": domains_seen,
        "rows": rows,
    }


# ─────────────────────────────────────────────────────────────
#  Release snapshot (before / after)
# ─────────────────────────────────────────────────────────────

_DEFAULT_SNAPSHOT_TEXTS = [
    "Furthermore, it is important to note that the utilization of this "
    "methodology facilitates optimal outcomes across all relevant domains.",
    "In today's fast-paced world, leveraging cutting-edge solutions is "
    "essential for businesses seeking to maximize their potential.",
    "Moreover, the implementation of robust frameworks ensures that "
    "stakeholders can effectively achieve their strategic objectives.",
]


def release_snapshot(
    texts: list[str] | None = None,
    lang: str = "en",
    *,
    intensity: int = 60,
) -> dict[str, Any]:
    """Capture before/after release metrics for a fixed sample set.

    Records detector score, watermark risk, semantic similarity, readability and
    the unified quality score before and after humanization, plus latency
    p50/p95. Intended to be stored per release for regression tracking.
    """
    from texthumanize.core import (
        _text_similarity,
        analyze,
        detect_ai_explain,
        humanize,
        quality_score_report,
        watermark_report,
    )

    payload = list(texts) if texts else list(_DEFAULT_SNAPSHOT_TEXTS)
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []

    for text in payload:
        before_ai = _clamp(float(detect_ai_explain(text, lang=lang, include_sentences=False).get("score", 0.0)))
        before_read = float(getattr(analyze(text, lang=lang), "flesch_kincaid_grade", 0.0))

        started = time.perf_counter()
        result = humanize(text, lang=lang, intensity=intensity)
        latency_ms = (time.perf_counter() - started) * 1000.0
        latencies.append(latency_ms)

        after = result.text
        after_ai = _clamp(float(detect_ai_explain(after, lang=lang, include_sentences=False).get("score", 0.0)))
        after_wm = _clamp(float(watermark_report(after, lang=lang, include_statistical=False).get("risk_score", 0.0)))
        after_read = float(getattr(analyze(after, lang=lang), "flesch_kincaid_grade", 0.0))
        similarity = _text_similarity(text, after)
        quality = quality_score_report(after, original=text, lang=lang, fast=True)

        rows.append({
            "chars": len(text),
            "detector_before": round(before_ai, 4),
            "detector_after": round(after_ai, 4),
            "detector_delta": round(after_ai - before_ai, 4),
            "watermark_after": round(after_wm, 4),
            "semantic_similarity": round(similarity, 4),
            "readability_before": round(before_read, 2),
            "readability_after": round(after_read, 2),
            "quality_score": quality["score"],
            "quality_grade": quality["grade"],
            "latency_ms": round(latency_ms, 3),
        })

    def _avg(key: str) -> float:
        return round(statistics.mean(row[key] for row in rows), 4) if rows else 0.0

    return {
        "schema_version": "text-humanize.release_snapshot.v1",
        "lang": lang,
        "intensity": intensity,
        "sample_count": len(rows),
        "averages": {
            "detector_before": _avg("detector_before"),
            "detector_after": _avg("detector_after"),
            "detector_delta": _avg("detector_delta"),
            "watermark_after": _avg("watermark_after"),
            "semantic_similarity": _avg("semantic_similarity"),
            "quality_score": _avg("quality_score"),
        },
        "latency_ms": {
            "p50": round(_percentile(latencies, 0.50), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
        },
        "rows": rows,
    }


# ─────────────────────────────────────────────────────────────
#  Acceptance rate & semantic drift
# ─────────────────────────────────────────────────────────────

def acceptance_rate(
    texts: list[str],
    lang: str = "en",
    *,
    quality_threshold: float = 0.7,
    intensity: int = 60,
) -> dict[str, Any]:
    """Estimate the share of humanized outputs that need no manual editing.

    An output is "accepted" when its unified quality score is at or above
    ``quality_threshold`` and grammar checking finds no issues. Returns the
    rate plus per-sample detail.
    """
    from texthumanize.core import humanize, quality_score_report
    from texthumanize.grammar import check_grammar

    rows: list[dict[str, Any]] = []
    accepted = 0
    for text in texts:
        result = humanize(text, lang=lang, intensity=intensity)
        quality = quality_score_report(result.text, original=text, lang=lang, fast=True)
        try:
            report = check_grammar(result.text, lang=lang)
            issues = len(getattr(report, "issues", []) or [])
        except Exception:
            issues = 0
        ok = quality["score"] >= quality_threshold and issues == 0
        accepted += int(ok)
        rows.append({
            "chars": len(text),
            "quality_score": quality["score"],
            "grade": quality["grade"],
            "grammar_issues": issues,
            "accepted": ok,
        })
    total = len(rows)
    return {
        "schema_version": "text-humanize.acceptance_rate.v1",
        "lang": lang,
        "quality_threshold": quality_threshold,
        "total": total,
        "accepted": accepted,
        "acceptance_rate": round(accepted / total, 4) if total else 0.0,
        "rows": rows,
    }


def semantic_drift_rate(
    pairs: list[tuple[str, str]] | list[list[str]],
    *,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Share of (original, rewritten) pairs whose similarity drops below threshold.

    A high drift rate means meaning is being lost too often.
    """
    from texthumanize.core import _text_similarity

    rows: list[dict[str, Any]] = []
    drifted = 0
    for pair in pairs:
        original, rewritten = pair[0], pair[1]
        similarity = _text_similarity(original, rewritten)
        is_drift = similarity < threshold
        drifted += int(is_drift)
        rows.append({
            "similarity": round(similarity, 4),
            "drifted": is_drift,
        })
    total = len(rows)
    return {
        "schema_version": "text-humanize.semantic_drift.v1",
        "threshold": threshold,
        "total": total,
        "drifted": drifted,
        "drift_rate": round(drifted / total, 4) if total else 0.0,
        "rows": rows,
    }


# ─────────────────────────────────────────────────────────────
#  Watermark false positive / false negative evaluation
# ─────────────────────────────────────────────────────────────

def watermark_eval(
    samples: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Measure Unicode/statistical watermark false positive/negative rates.

    For every sample the watermarked text should be flagged (a miss is a false
    negative) and its safe-cleaned variant should not be flagged (a hit is a
    false positive). Uses the packaged watermark contributor samples by default.
    """
    from texthumanize.contributor_packs import load_contributor_pack
    from texthumanize.core import watermark_report

    if samples is None:
        pack = load_contributor_pack("watermark_samples")
        samples = list(pack.get("entries", []))

    by_category: dict[str, dict[str, int]] = {}
    false_negatives = 0
    false_positives = 0
    positives = 0
    negatives = 0
    rows: list[dict[str, Any]] = []

    for sample in samples:
        lang = str(sample.get("lang", "en"))
        category = str(sample.get("category", "unknown"))
        cat = by_category.setdefault(category, {
            "positives": 0, "negatives": 0,
            "false_negatives": 0, "false_positives": 0,
        })
        marked = sample.get("sample_text", "")
        clean = sample.get("safe_clean_text")

        detected_marked = bool(
            watermark_report(marked, lang=lang, include_statistical=False).get("has_watermarks")
        )
        positives += 1
        cat["positives"] += 1
        if not detected_marked:
            false_negatives += 1
            cat["false_negatives"] += 1

        detected_clean = None
        if clean is not None:
            detected_clean = bool(
                watermark_report(clean, lang=lang, include_statistical=False).get("has_watermarks")
            )
            negatives += 1
            cat["negatives"] += 1
            if detected_clean:
                false_positives += 1
                cat["false_positives"] += 1

        rows.append({
            "id": sample.get("id"),
            "category": category,
            "detected_marked": detected_marked,
            "detected_clean": detected_clean,
        })

    return {
        "schema_version": "text-humanize.watermark_eval.v1",
        "positives": positives,
        "negatives": negatives,
        "false_negative_rate": round(false_negatives / positives, 4) if positives else 0.0,
        "false_positive_rate": round(false_positives / negatives, 4) if negatives else 0.0,
        "by_category": {
            category: {
                **counts,
                "false_negative_rate": round(
                    counts["false_negatives"] / counts["positives"], 4
                ) if counts["positives"] else 0.0,
                "false_positive_rate": round(
                    counts["false_positives"] / counts["negatives"], 4
                ) if counts["negatives"] else 0.0,
            }
            for category, counts in sorted(by_category.items())
        },
        "rows": rows,
    }


# ─────────────────────────────────────────────────────────────
#  Regression bank size & Promopilot funnel
# ─────────────────────────────────────────────────────────────

def count_regression_examples() -> dict[str, Any]:
    """Count regression examples across the bad-output bank and eval corpus."""
    from texthumanize.bad_output_bank import load_bad_output_bank
    from texthumanize.benchmarks import load_eval_corpus

    bank = load_bad_output_bank()
    corpus = load_eval_corpus()
    corpus_list = corpus if isinstance(corpus, list) else []

    by_source: dict[str, int] = {}
    for entry in bank:
        origin = str(entry.get("origin", "unknown"))
        by_source[origin] = by_source.get(origin, 0) + 1

    return {
        "schema_version": "text-humanize.regression_count.v1",
        "bad_output_bank": len(bank),
        "eval_corpus": len(corpus_list),
        "total": len(bank) + len(corpus_list),
        "bad_output_by_origin": dict(sorted(by_source.items())),
    }


_FUNNEL_STAGES = ("audit", "humanize", "export", "publish")


def funnel_metrics(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute audit → humanize → export → publish conversion from events.

    Each event is a dict with at least ``item_id`` and ``stage`` (one of
    ``audit``, ``humanize``, ``export``, ``publish``). The library computes the
    funnel; live event data is supplied by the host product (e.g. Promopilot).
    """
    reached: dict[str, set[str]] = {stage: set() for stage in _FUNNEL_STAGES}
    for event in events:
        stage = str(event.get("stage", ""))
        item_id = str(event.get("item_id", event.get("id", "")))
        if stage in reached and item_id:
            reached[stage].add(item_id)

    counts = {stage: len(reached[stage]) for stage in _FUNNEL_STAGES}
    audit_total = counts["audit"] or 1
    steps: list[dict[str, Any]] = []
    prev = counts["audit"]
    for stage in _FUNNEL_STAGES:
        current = counts[stage]
        steps.append({
            "stage": stage,
            "count": current,
            "rate_from_audit": round(current / audit_total, 4) if counts["audit"] else 0.0,
            "rate_from_prev": round(current / prev, 4) if prev else 0.0,
        })
        prev = current or prev

    return {
        "schema_version": "text-humanize.funnel.v1",
        "counts": counts,
        "overall_conversion": round(counts["publish"] / audit_total, 4) if counts["audit"] else 0.0,
        "steps": steps,
    }
