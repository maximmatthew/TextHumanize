# Benchmark Methodology

This page explains how TextHumanize benchmark numbers should be produced and
interpreted. The goal is reproducible quality tracking, not universal claims
about external AI detectors.

## Reporting Requirements

Every public benchmark should include:

- TextHumanize version and git commit.
- Runtime: Python/PHP/Node version, OS, CPU, and whether the run is local or CI.
- Input corpus: language, domain, label, length bucket, and sample count.
- Processing settings: profile, intensity, seed, `quality_gate`, `minimal`, and
  PHANTOM settings when used.
- Warm-up policy: cold start excluded or included.
- Threading policy: single thread, worker count, or batch configuration.
- Exact command used to reproduce the run.

Do not compare latency across machines unless the hardware and runtime are
reported. Do not compare detector numbers across external products unless the
same texts, dates, and detector versions are documented.

## Corpus Labels

Use explicit labels instead of vague buckets:

| Label | Meaning |
|-------|---------|
| `human` | Human-written text from licensed or owned sources |
| `raw_ai` | Unedited LLM draft |
| `edited_ai` | AI draft with light manual or tool-assisted editing |
| `humanized` | Output produced by TextHumanize |
| `editor_final` | Human-reviewed final version |

Track language, domain, and length separately. Recommended domains: SEO,
blog, product, landing page, support, academic, legal, documentation, finance,
and social copy.

## Detector Benchmarks

TextHumanize detector benchmarks measure the built-in detector only:

- `avg_score_by_label`: average built-in score per corpus label.
- false-positive rate: share of `human` samples flagged as AI-like.
- AI recall: share of `raw_ai` samples flagged as AI-like.
- edited-AI flag rate: share of `edited_ai` samples still flagged.
- score reduction: before/after delta in percentage points.

These numbers are internal quality signals. They do not guarantee passing
GPTZero, Originality.ai, Turnitin, or any other external detector.

```bash
texthumanize detector-benchmark --langs en,ru,uk --json
```

## Humanization Quality

`BenchmarkSuite` reports six normalized dimensions:

| Dimension | Weight | What It Measures |
|-----------|:------:|------------------|
| Detection internal pass | 25% | Whether humanized text falls below the built-in detector threshold |
| Naturalness | 20% | Word language-model naturalness score |
| Meaning retention | 20% | Semantic similarity between original and output |
| Diversity | 15% | Jaccard distance across generated outputs |
| Length preservation | 10% | Output length stays near original length |
| Perplexity boost | 10% | Output moves toward a less uniform word distribution |

The overall score is a weighted average of these dimensions. Treat it as a
regression metric for TextHumanize outputs, not a human preference score.

```python
from texthumanize import BenchmarkSuite

suite = BenchmarkSuite(lang="en")
report = suite.run_all([
    {"original": original_text, "humanized": result.text},
])
print(report.overall_score)
```

## Latency Benchmarks

Latency should be reported with:

- p50 and p95 when running more than one sample;
- input size in characters and words;
- whether first-call initialization is included;
- batch size and worker count;
- timeout and max input limits.

For release notes, prefer a table like:

| Function | Size | p50 | p95 | p50 peak KB | Notes |
|----------|------|-----|-----|-------------|-------|
| `humanize()` | 1k chars | TBD | TBD | TBD | warm, single thread |
| `detect_ai()` | 1k chars | TBD | TBD | TBD | warm, single thread |
| `watermark_report()` | 1k chars | TBD | TBD | TBD | warm, single thread |

Use the dependency-free hot-path profiler before releases to generate the
1k/10k/100k p50/p95 latency and tracemalloc peak-memory snapshot:

```bash
python scripts/profile_hot_paths.py --sizes 1000,10000,100000 --json
```

`tracemalloc` tracks Python allocation peaks during separate uncached runs. It
does not measure full process RSS, so compare numbers only across identical
runtime, hardware, and command settings.

## Watermark Benchmarks

Report Unicode and statistical watermark tests separately:

- Unicode/homoglyph tests: precision, recall, positions recovered, safe
  replacement correctness.
- Statistical tests: gamma, n-gram context, hash window, z-score, p-value,
  confidence, and false-positive rate on clean human text.
- Cleanup tests: `clean_safe()` semantic preservation and
  `neutralise_aggressive()` change ratio.

## Limitations

- Short texts can be unreliable because they do not contain enough style signal.
- Formal domains can look AI-like because they naturally use templates and
  consistent phrasing.
- Detector thresholds are not interchangeable across products.
- Rule-based quality metrics do not replace human review for high-impact
  content.
- Benchmarks should be versioned; numbers may change after dictionary, detector,
  or pipeline updates.

## Recommended Release Snapshot

For each release, publish:

```text
Version:
Commit:
Date:
Runtime:
Corpus:
Languages:
Profiles/intensity:
Detector avg scores by label:
False-positive / recall:
Semantic similarity:
Quality score:
Watermark precision/recall:
Latency p50/p95:
Known limitations:
```
