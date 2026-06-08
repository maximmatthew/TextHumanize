"""External validation framework — benchmark against external AI detectors.

Provides tools to evaluate TextHumanize effectiveness by comparing
AI detection scores before and after humanization.

Usage::

    from texthumanize.benchmarks import ValidationSuite
    suite = ValidationSuite()
    report = suite.run_all(texts, lang="en")
    suite.print_report(report)
"""

from __future__ import annotations

import json
import logging
import time
from importlib import resources
from typing import Any

from texthumanize.core import detect_ai, humanize

logger = logging.getLogger(__name__)

_EVAL_CORPUS_FILE = "eval_corpus_v1.json"
_DETECTOR_BENCHMARK_LABELS = [
    "human",
    "raw_ai",
    "lightly_edited_ai",
    "heavily_edited_ai",
]
_EVAL_CORPUS_INDEX_FIELDS = (
    "lang",
    "domain",
    "length_bucket",
    "source",
    "label",
)
_LABEL_ALIASES = {
    "ai": "raw_ai",
    "edited_ai": "lightly_edited_ai",
    "human": "human",
    "raw_ai": "raw_ai",
    "lightly_edited_ai": "lightly_edited_ai",
    "heavily_edited_ai": "heavily_edited_ai",
}


# ---------------------------------------------------------------------------
# Standard evaluation texts
# ---------------------------------------------------------------------------

_EVAL_TEXTS_EN = [
    (
        "Furthermore, it is important to note that the utilization of advanced "
        "methodologies has significantly contributed to the overall improvement "
        "of systemic outcomes. The implementation of comprehensive strategies "
        "ensures that all stakeholders benefit from the enhanced framework. "
        "Additionally, the integration of holistic approaches facilitates the "
        "achievement of optimal results across various domains.",
        "ai",
    ),
    (
        "So I was thinking about this the other day - you know how sometimes "
        "things just don't work the way you'd expect? Yeah, that happened "
        "again. Tried to fix the sink, ended up flooding half the kitchen. "
        "My wife wasn't thrilled, to say the least. Lesson learned though.",
        "human",
    ),
    (
        "The comprehensive examination of relevant literature reveals several "
        "key findings that merit consideration. Firstly, the data suggests a "
        "significant correlation between the implementation of evidence-based "
        "practices and positive outcomes. Secondly, the analysis indicates that "
        "organizational culture plays a crucial role.",
        "ai",
    ),
    (
        "Look, I'm not gonna pretend I have all the answers here. But from "
        "what I've seen working in this field, the biggest mistake people make "
        "is overthinking it. Just start somewhere, make mistakes, learn from "
        "them. It's really not rocket science — just common sense.",
        "human",
    ),
]

_EVAL_TEXTS_RU = [
    (
        "Кроме того, необходимо отметить, что применение передовых методологий "
        "значительно способствовало общему улучшению системных результатов. "
        "Внедрение комплексных стратегий обеспечивает извлечение пользы всеми "
        "заинтересованными сторонами из улучшенных рамок.",
        "ai",
    ),
    (
        "Знаешь, я долго думал над этим вопросом, и вот что понял — нет "
        "смысла гнаться за совершенством. Сделал как получилось, посмотрел "
        "что вышло, поправил. И так по кругу. Жизнь — она не по учебнику идёт.",
        "human",
    ),
]

def _read_eval_corpus_resource() -> dict[str, Any]:
    """Read the packaged licensed evaluation corpus."""
    corpus_path = resources.files("texthumanize").joinpath("data").joinpath(
        _EVAL_CORPUS_FILE
    )
    with corpus_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("samples"), list):
        raise ValueError(f"Invalid eval corpus resource: {_EVAL_CORPUS_FILE}")
    return data


def _canonical_label(label: str) -> str:
    """Normalize legacy benchmark labels to the licensed corpus taxonomy."""
    canonical = _LABEL_ALIASES.get(label)
    if canonical is None:
        valid = ", ".join(_DETECTOR_BENCHMARK_LABELS)
        raise ValueError(f"Unsupported benchmark label {label!r}; expected one of {valid}")
    return canonical


def _normalize_benchmark_sample(sample: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow normalized sample copy."""
    required = ("id", "lang", "label", "domain", "text")
    missing = [key for key in required if not sample.get(key)]
    if missing:
        raise ValueError(
            f"Benchmark sample {sample.get('id', '<unknown>')!r} missing: "
            f"{', '.join(missing)}"
        )
    normalized = dict(sample)
    normalized["label"] = _canonical_label(str(normalized["label"]))
    normalized.setdefault("length_bucket", "unknown")
    normalized.setdefault("source", "custom")
    normalized.setdefault("origin", "custom")
    normalized.setdefault("license", "custom")
    return normalized


def load_eval_corpus(
    *,
    languages: list[str] | None = None,
    labels: list[str] | None = None,
    domains: list[str] | None = None,
    length_buckets: list[str] | None = None,
    sources: list[str] | None = None,
    include_metadata: bool = False,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Load the packaged licensed eval corpus.

    The built-in corpus is intentionally small, fully offline, and explicitly
    licensed for redistribution. Labels are normalized to:
    ``human``, ``raw_ai``, ``lightly_edited_ai``, ``heavily_edited_ai``.
    """
    data = _read_eval_corpus_resource()
    wanted_languages = set(languages or [])
    wanted_labels = {_canonical_label(label) for label in labels} if labels else set()
    wanted_domains = set(domains or [])
    wanted_length_buckets = set(length_buckets or [])
    wanted_sources = set(sources or [])
    samples = [
        _normalize_benchmark_sample(sample)
        for sample in data["samples"]
        if (not wanted_languages or sample.get("lang") in wanted_languages)
        and (
            not wanted_labels
            or _canonical_label(str(sample.get("label", ""))) in wanted_labels
        )
        and (not wanted_domains or sample.get("domain") in wanted_domains)
        and (
            not wanted_length_buckets
            or sample.get("length_bucket") in wanted_length_buckets
        )
        and (not wanted_sources or sample.get("source") in wanted_sources)
    ]
    if not include_metadata:
        return samples
    enriched = dict(data)
    enriched["samples"] = samples
    enriched["sample_count"] = len(samples)
    enriched["languages"] = sorted({sample["lang"] for sample in samples})
    enriched["domains"] = sorted({sample["domain"] for sample in samples})
    enriched["length_buckets"] = sorted({sample["length_bucket"] for sample in samples})
    enriched["sources"] = sorted({sample["source"] for sample in samples})
    enriched["index"] = index_eval_corpus(samples)
    return enriched


def index_eval_corpus(
    samples: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Index eval corpus fixtures by language, domain, length, source and label.

    The returned ``fields`` map stores sample ids for deterministic fixture
    selection, while ``counts`` gives a compact summary for benchmark reports.
    """
    if samples is None:
        normalized_samples = load_eval_corpus()
        if not isinstance(normalized_samples, list):
            raise ValueError("Expected load_eval_corpus() to return a sample list")
        samples_to_index = normalized_samples
    else:
        samples_to_index = [
            _normalize_benchmark_sample(sample)
            for sample in samples
        ]

    fields: dict[str, dict[str, list[str]]] = {
        field: {}
        for field in _EVAL_CORPUS_INDEX_FIELDS
    }
    for sample in samples_to_index:
        sample_id = str(sample["id"])
        for field in _EVAL_CORPUS_INDEX_FIELDS:
            value = str(sample.get(field, "unknown"))
            fields[field].setdefault(value, []).append(sample_id)

    fields = {
        field: {
            value: sorted(sample_ids)
            for value, sample_ids in sorted(values.items())
        }
        for field, values in fields.items()
    }
    return {
        "schema_version": "text-humanize.eval_corpus_index.v1",
        "total": len(samples_to_index),
        "fields": fields,
        "counts": {
            field: {
                value: len(sample_ids)
                for value, sample_ids in values.items()
            }
            for field, values in fields.items()
        },
    }


def _score_to_label(
    score: float,
    threshold: float,
    edited_threshold: float,
    heavily_edited_threshold: float,
) -> str:
    if score >= threshold:
        return "raw_ai"
    if score >= edited_threshold:
        return "lightly_edited_ai"
    if score >= heavily_edited_threshold:
        return "heavily_edited_ai"
    return "human"


def detector_benchmark(
    corpus: list[dict[str, Any]] | None = None,
    *,
    languages: list[str] | None = None,
    threshold: float = 0.50,
    edited_threshold: float = 0.35,
    heavily_edited_threshold: float = 0.25,
    include_details: bool = True,
) -> dict[str, Any]:
    """Benchmark the detector on human, raw-AI and edited-AI samples by language.

    The benchmark is fully offline and intentionally small enough for CI and
    release checks. It reports distribution metrics rather than claiming
    universal detector accuracy.
    """
    from texthumanize import __version__

    corpus_metadata: dict[str, Any] | None = None
    if corpus is None:
        loaded = load_eval_corpus(include_metadata=True)
        corpus_metadata = loaded if isinstance(loaded, dict) else None
        samples = list(corpus_metadata["samples"]) if corpus_metadata else []
    else:
        samples = [_normalize_benchmark_sample(sample) for sample in corpus]
    selected_languages = (
        list(languages)
        if languages
        else sorted({sample["lang"] for sample in samples})
    )

    started = time.time()
    per_language: dict[str, Any] = {}
    all_details: list[dict[str, Any]] = []

    for lang in selected_languages:
        lang_samples = [sample for sample in samples if sample.get("lang") == lang]
        details: list[dict[str, Any]] = []
        label_scores: dict[str, list[float]] = {
            label: []
            for label in _DETECTOR_BENCHMARK_LABELS
        }
        correct = 0

        for sample in lang_samples:
            detection = detect_ai(sample["text"], lang=lang)
            score = float(detection.get("combined_score", detection.get("score", 0.0)))
            label = _canonical_label(str(sample["label"]))
            predicted = _score_to_label(
                score,
                threshold,
                edited_threshold,
                heavily_edited_threshold,
            )
            label_scores.setdefault(label, []).append(score)

            if label == "human":
                sample_correct = score < threshold
            elif label == "raw_ai":
                sample_correct = score >= threshold
            elif label == "lightly_edited_ai":
                sample_correct = score >= edited_threshold
            else:
                sample_correct = score < threshold
            correct += int(sample_correct)

            row = {
                "id": sample["id"],
                "lang": lang,
                "domain": sample.get("domain", "general"),
                "length_bucket": sample.get("length_bucket", "unknown"),
                "label": label,
                "predicted": predicted,
                "score": round(score, 4),
                "verdict": detection.get("verdict", predicted),
                "correct": sample_correct,
                "source": sample.get("source", "custom"),
                "origin": sample.get("origin", "custom"),
                "license": sample.get("license", "custom"),
            }
            details.append(row)
            all_details.append(row)

        total = len(lang_samples)
        human_scores = label_scores.get("human", [])
        raw_ai_scores = label_scores.get("raw_ai", [])
        lightly_edited_scores = label_scores.get("lightly_edited_ai", [])
        heavily_edited_scores = label_scores.get("heavily_edited_ai", [])
        all_edited_scores = lightly_edited_scores + heavily_edited_scores

        def avg(values: list[float]) -> float:
            return round(sum(values) / len(values), 4) if values else 0.0

        per_language[lang] = {
            "total": total,
            "accuracy": round(correct / total, 4) if total else 0.0,
            "avg_score_by_label": {
                "human": avg(human_scores),
                "raw_ai": avg(raw_ai_scores),
                "lightly_edited_ai": avg(lightly_edited_scores),
                "heavily_edited_ai": avg(heavily_edited_scores),
            },
            "human_false_positive_rate": round(
                sum(score >= threshold for score in human_scores) / len(human_scores),
                4,
            ) if human_scores else 0.0,
            "raw_ai_recall": round(
                sum(score >= threshold for score in raw_ai_scores) / len(raw_ai_scores),
                4,
            ) if raw_ai_scores else 0.0,
            "ai_recall": round(
                sum(score >= threshold for score in raw_ai_scores) / len(raw_ai_scores),
                4,
            ) if raw_ai_scores else 0.0,
            "lightly_edited_ai_flag_rate": round(
                sum(score >= edited_threshold for score in lightly_edited_scores)
                / len(lightly_edited_scores),
                4,
            ) if lightly_edited_scores else 0.0,
            "heavily_edited_ai_flag_rate": round(
                sum(score >= heavily_edited_threshold for score in heavily_edited_scores)
                / len(heavily_edited_scores),
                4,
            ) if heavily_edited_scores else 0.0,
            "edited_ai_flag_rate": round(
                sum(score >= edited_threshold for score in all_edited_scores)
                / len(all_edited_scores),
                4,
            ) if all_edited_scores else 0.0,
            "details": details if include_details else [],
        }

    total_samples = len(all_details)
    total_correct = sum(1 for row in all_details if row["correct"])
    benchmark_report: dict[str, Any] = {
        "schema_version": "1.0",
        "version": __version__,
        "threshold": threshold,
        "edited_threshold": edited_threshold,
        "heavily_edited_threshold": heavily_edited_threshold,
        "languages": selected_languages,
        "labels": list(_DETECTOR_BENCHMARK_LABELS),
        "label_aliases": {
            "ai": "raw_ai",
            "edited_ai": "lightly_edited_ai",
        },
        "corpus": {
            "source": "builtin" if corpus is None else "custom",
            "schema_version": corpus_metadata.get("schema_version")
            if corpus_metadata else None,
            "name": corpus_metadata.get("name") if corpus_metadata else None,
            "license": corpus_metadata.get("license") if corpus_metadata else None,
            "sample_count": len(samples),
            "index": corpus_metadata.get("index") if corpus_metadata else None,
        },
        "overall": {
            "total": total_samples,
            "accuracy": round(total_correct / total_samples, 4)
            if total_samples
            else 0.0,
        },
        "per_language": per_language,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    if include_details:
        benchmark_report["details"] = all_details
    return benchmark_report


class ValidationResult:
    """Result of a single validation test."""

    __slots__ = (
        "actual_label",
        "ai_score_after",
        "ai_score_before",
        "humanize_time_ms",
        "lang",
        "text_after",
        "text_before",
    )

    def __init__(
        self,
        text_before: str,
        text_after: str,
        ai_score_before: float,
        ai_score_after: float,
        actual_label: str,
        lang: str,
        humanize_time_ms: float,
    ) -> None:
        self.text_before = text_before
        self.text_after = text_after
        self.ai_score_before = ai_score_before
        self.ai_score_after = ai_score_after
        self.actual_label = actual_label
        self.lang = lang
        self.humanize_time_ms = humanize_time_ms

    @property
    def score_drop(self) -> float:
        return self.ai_score_before - self.ai_score_after

    @property
    def detection_correct_before(self) -> bool:
        if self.actual_label == "ai":
            return self.ai_score_before > 0.5
        return self.ai_score_before <= 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_before": self.text_before[:80],
            "text_after": self.text_after[:80],
            "ai_score_before": self.ai_score_before,
            "ai_score_after": self.ai_score_after,
            "score_drop": self.score_drop,
            "actual_label": self.actual_label,
            "lang": self.lang,
            "humanize_time_ms": self.humanize_time_ms,
        }


class ValidationSuite:
    """Run validation benchmarks against the TextHumanize pipeline.

    Evaluates:
    1. AI detection accuracy (can we correctly classify AI vs human?)
    2. Humanization effectiveness (does humanization lower AI scores?)
    3. Quality preservation (is humanized text still readable?)
    """

    def __init__(
        self,
        profiles: list[str] | None = None,
        intensities: list[int] | None = None,
    ) -> None:
        self.profiles = profiles or ["web", "chat", "seo"]
        self.intensities = intensities or [40, 60, 80]

    def _get_eval_texts(self, lang: str) -> list[tuple[str, str]]:
        """Get evaluation texts for a language."""
        if lang == "ru":
            return _EVAL_TEXTS_RU + _EVAL_TEXTS_EN
        return _EVAL_TEXTS_EN + _EVAL_TEXTS_RU

    def validate_detection(
        self,
        texts: list[tuple[str, str]] | None = None,
        lang: str = "en",
    ) -> dict[str, Any]:
        """Validate AI detection accuracy.

        Args:
            texts: Optional list of (text, label) pairs. Uses built-in if None.
            lang: Language code.

        Returns:
            Dict with accuracy, precision, recall, F1 metrics.
        """
        if texts is None:
            texts = self._get_eval_texts(lang)

        tp = fp = tn = fn = 0
        results = []
        for text, label in texts:
            try:
                report = detect_ai(text, lang=lang)
                score = report.get("combined_score", report.get("score", 0.5))
                predicted = "ai" if score > 0.5 else "human"
            except Exception:
                score = 0.5
                predicted = "unknown"

            results.append({
                "text": text[:60],
                "label": label,
                "predicted": predicted,
                "score": round(score, 4),
            })

            if label == "ai":
                if predicted == "ai":
                    tp += 1
                else:
                    fn += 1
            else:
                if predicted == "human":
                    tn += 1
                else:
                    fp += 1

        n = max(tp + fp + tn + fn, 1)
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-9)

        return {
            "accuracy": (tp + tn) / n,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
            "details": results,
        }

    def validate_humanization(
        self,
        texts: list[str] | None = None,
        lang: str = "en",
        profile: str = "web",
        intensity: int = 60,
    ) -> dict[str, Any]:
        """Validate humanization effectiveness.

        Measures how much humanization reduces AI detection scores.

        Returns:
            Dict with avg_score_drop, success_rate, results.
        """
        if texts is None:
            texts = [t for t, label in self._get_eval_texts(lang) if label == "ai"]

        results: list[ValidationResult] = []
        for text in texts:
            try:
                before = detect_ai(text, lang=lang)
                before_score = before.get("combined_score", before.get("score", 0.5))

                t0 = time.time()
                humanized = humanize(text, lang=lang, profile=profile, intensity=intensity)
                htime = (time.time() - t0) * 1000

                after = detect_ai(humanized.text, lang=lang)
                after_score = after.get("combined_score", after.get("score", 0.5))

                results.append(ValidationResult(
                    text_before=text, text_after=humanized.text,
                    ai_score_before=before_score, ai_score_after=after_score,
                    actual_label="ai", lang=lang,
                    humanize_time_ms=htime,
                ))
            except Exception as e:
                logger.warning("Validation error: %s", e)

        if not results:
            return {"avg_score_drop": 0.0, "success_rate": 0.0, "results": []}

        avg_drop = sum(r.score_drop for r in results) / len(results)
        success = sum(1 for r in results if r.ai_score_after < 0.5)
        avg_time = sum(r.humanize_time_ms for r in results) / len(results)

        return {
            "profile": profile,
            "intensity": intensity,
            "avg_score_drop": round(avg_drop, 4),
            "success_rate": success / len(results),
            "avg_humanize_ms": round(avg_time, 1),
            "n_texts": len(results),
            "results": [r.to_dict() for r in results],
        }

    def run_all(
        self,
        texts: list[tuple[str, str]] | None = None,
        lang: str = "en",
    ) -> dict[str, Any]:
        """Run complete validation suite.

        Returns comprehensive report with detection accuracy and
        humanization effectiveness across all profiles/intensities.
        """
        t0 = time.time()

        report: dict[str, Any] = {
            "lang": lang,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Detection accuracy
        report["detection"] = self.validate_detection(texts, lang=lang)

        # Humanization effectiveness per profile/intensity
        humanization_results = []
        ai_texts = [t for t, label in (texts or self._get_eval_texts(lang)) if label == "ai"]

        for profile in self.profiles:
            for intensity in self.intensities:
                result = self.validate_humanization(
                    texts=ai_texts, lang=lang, profile=profile, intensity=intensity,
                )
                humanization_results.append(result)

        report["humanization"] = humanization_results
        report["elapsed_seconds"] = round(time.time() - t0, 1)

        return report

    @staticmethod
    def print_report(report: dict[str, Any]) -> None:
        """Print a human-readable validation report."""
        print("=" * 60)
        print("  TextHumanize Validation Report")
        print("=" * 60)

        det = report.get("detection", {})
        print("\n  Detection Accuracy:")
        print(f"    Accuracy:  {det.get('accuracy', 0):.1%}")
        print(f"    Precision: {det.get('precision', 0):.2f}")
        print(f"    Recall:    {det.get('recall', 0):.2f}")
        print(f"    F1:        {det.get('f1', 0):.2f}")

        print("\n  Humanization Effectiveness:")
        for h in report.get("humanization", []):
            print(
                f"    {h['profile']:>6s} @ {h['intensity']:>3d}%: "
                f"avg_drop={h['avg_score_drop']:+.2f}, "
                f"success={h['success_rate']:.0%}, "
                f"time={h['avg_humanize_ms']:.0f}ms"
            )

        print(f"\n  Elapsed: {report.get('elapsed_seconds', 0):.1f}s")
        print("=" * 60)

    @staticmethod
    def save_report(report: dict[str, Any], path: str) -> None:
        """Save report as JSON."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        logger.info("Report saved to %s", path)
