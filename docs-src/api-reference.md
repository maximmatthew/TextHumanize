# API Reference

Full Python API reference for TextHumanize.

## Core Functions

### `humanize(text, lang, profile, intensity, ...)`

Humanize text using the 38-stage pipeline.

```python
from texthumanize import humanize

result = humanize(
    text="Your text here.",
    lang="en",           # "auto", "ru", "uk", "en", "de", ...
    profile="web",       # "chat", "web", "seo", "docs", "formal", ...
    intensity=60,        # 0-100
    seed=42,             # For reproducibility
    preserve={"urls": True, "code_blocks": True},
    constraints={"max_change_ratio": 0.3, "keep_keywords": ["API"]},
    target_style="copywriter",  # Style preset
    only_flagged=False,  # Only humanize AI-flagged sentences
    minimal=False,       # Alias for only_flagged=True
    custom_dict={"utilize": "use"},
    quality_gate="strict",  # rollback on quality regressions
)

# Returns HumanizeResult
result.text           # str — humanized text
result.original       # str — original text
result.lang           # str — detected/used language
result.profile        # str — profile used
result.intensity      # int — intensity used
result.changes        # list — changes made
result.change_ratio   # float — proportion changed
result.quality_score  # float — quality metric
result.metrics_before # dict — metrics before
result.metrics_after  # dict — metrics after
result.metrics_after["humanize_explain"]
# Promopilot-ready metadata:
# top_change_reasons, remaining_risks, sentence_report, AI score delta
```

### `detect_ai(text, lang)`

Detect AI-like style signals using the built-in detector ensemble.

```python
from texthumanize import detect_ai

result = detect_ai("Text to check.", lang="en")

result["score"]       # float 0-1 — AI probability
result["verdict"]     # "human_written" | "mixed" | "ai_generated"
result["confidence"]  # float 0-1
result["metrics"]     # dict — individual metric scores
```

### `detect_ai_explain(text, lang)`

Promopilot-ready AI detector report with calibrated score, confidence interval,
metric contributions, highlighted spans, reasons, and suggested actions.

```python
from texthumanize import detect_ai_explain

report = detect_ai_explain("Furthermore, it is important to note...", lang="en")
report["highlighted_spans"]
report["suggested_actions"]
```

### `quality_score_report(text, original=None, lang)`

Unified **TextHumanize Quality Score** — a single explainable score (0..1) with a
letter grade across seven dimensions: semantic similarity, naturalness,
readability, AI-pattern resistance, watermark cleanliness, edit balance, and
processing speed. Pass `original` (the pre-humanization text) to enable the
similarity and edit-balance dimensions; otherwise they are dropped and the
remaining weights renormalised. Use `weights=` to re-weight dimensions and
`fast=True` for a quicker, slightly coarser score.

```python
from texthumanize import humanize, quality_score_report

result = humanize("Furthermore, it is important to note...", lang="en")
score = quality_score_report(result.text, original=result.original, lang="en")
score["score"]            # composite 0..1
score["grade"]            # "A+".."F"
score["verdict"]          # excellent | good | fair | poor
score["dimensions"]       # per-dimension value, weight, and detail
score["recommendations"]  # actionable next steps
```

CLI:

```bash
texthumanize quality output.txt --reference input.txt --json
texthumanize input.txt --quality-score
```

### Product layer (`texthumanize.product`)

Higher-level building blocks for content products and integrations:

```python
from texthumanize import (
    audit_widget_html, audit_batch, compare_versions, content_plan_risk,
    make_brand_voice, brand_voice_lock, client_report_html,
)

# Paste-text audit widget (self-contained HTML)
html = audit_widget_html("Furthermore, it is important to note...", lang="en")

# Bulk audit of many pages (fetch text upstream, pass it in)
board = audit_batch([{"id": "p1", "url": "https://x", "text": "..."}], lang="en")

# Compare versions: original / AI draft / humanized / editor final
diff = compare_versions({"original": "...", "humanized": "..."}, lang="en")

# Pre-publication gate: publish / review / block per item
plan = content_plan_risk(["text 1", "text 2"], lang="en")

# Brand voice lock — keep important terms verbatim while humanizing
brand = make_brand_voice("Acme Cloud", locked_terms=["Acme Cloud"], tone="founder")
locked = brand_voice_lock("Acme Cloud helps teams ship...", brand, lang="en")

# Neutral, print-ready client report (no detector-bypass claims)
report_html = client_report_html("...", original="...", lang="en")
```

### Quality & release metrics (`texthumanize.quality_metrics`)

```python
from texthumanize import (
    benchmark_leaderboard, release_snapshot, acceptance_rate,
    semantic_drift_rate, watermark_eval, count_regression_examples, funnel_metrics,
)

board = benchmark_leaderboard(languages=["en", "ru", "uk"])  # per language/domain
snapshot = release_snapshot(lang="en")                        # before/after + latency p50/p95
watermark_eval()                                              # Unicode/statistical FP/FN
```

CLI helpers: `texthumanize widget input.txt > audit.html`, `texthumanize leaderboard --markdown`,
plus `scripts/build_leaderboard.py`, `scripts/release_snapshot.py`, and `scripts/dev_check.py`.

### `analyze(text, lang)`

Get text analysis report.

```python
from texthumanize import analyze

report = analyze("Text to analyze.", lang="en")
report.artificiality_score  # float 0-100
report.word_count           # int
```

### `explain(result)`

Get human-readable change report.

```python
from texthumanize import humanize, explain

result = humanize("Text.", lang="en")
print(explain(result))
```

## Async Functions

### `async_humanize(text, lang, ...)`

Async version of `humanize()` for use with asyncio/FastAPI.

```python
from texthumanize import async_humanize

result = await async_humanize("Text.", lang="en", profile="web")
```

### `async_detect_ai(text, lang)`

Async version of `detect_ai()`.

```python
from texthumanize import async_detect_ai

result = await async_detect_ai("Text.", lang="en")
```

## NLP Functions

### `paraphrase(text, lang, intensity, seed)`

```python
from texthumanize import paraphrase
result = paraphrase("Text.", lang="en")
```

### `analyze_tone(text, lang)` / `adjust_tone(text, target, lang)`

```python
from texthumanize import analyze_tone, adjust_tone

tone = analyze_tone("Formal text.", lang="en")
casual = adjust_tone("Formal text.", target="casual", lang="en")
```

### `detect_watermarks(text)` / `clean_watermarks(text)`

```python
from texthumanize import detect_watermarks, clean_watermarks

found = detect_watermarks(text)
clean = clean_watermarks(text)
```

### `watermark_report(text, lang)`

Unified Unicode + statistical watermark report with positions, safe cleanup,
p-value/z-score evidence, and optional aggressive neutralisation.

```python
from texthumanize import watermark_report

report = watermark_report("Te\u200bst", lang="en")
report["clean_safe"]["text"]
report["statistical"]["hypotheses"]
```

### `spin(text, lang)` / `spin_variants(text, count, lang)`

```python
from texthumanize import spin, spin_variants

result = spin("Text.", lang="en")
variants = spin_variants("Text.", count=5, lang="en")
```

### `analyze_coherence(text, lang)` / `full_readability(text, lang)`

```python
from texthumanize import analyze_coherence, full_readability

coherence = analyze_coherence("Paragraph text.", lang="en")
readability = full_readability("Text.", lang="en")
```

## Batch Functions

```python
from texthumanize import humanize_batch, humanize_batch_stream, humanize_chunked, detect_ai_batch

# Parallel batch
results = humanize_batch(["Text 1", "Text 2"], lang="en", max_workers=4)

# Memory-bounded streaming batch
for item in humanize_batch_stream(["Text 1", "Text 2"], lang="en", memory_limit_mb=128):
    print(item["index"], item["result"].text)

# Chunked (large documents)
result = humanize_chunked(large_text, chunk_size=3000, lang="en", memory_limit_mb=128)

# Batch AI detection
results = detect_ai_batch(["Text 1", "Text 2"], lang="en")
```

## Streaming

```python
from texthumanize import humanize_stream

for chunk in humanize_stream("Long text...", lang="en", memory_limit_mb=128):
    print(chunk, end="", flush=True)
```

## Pipeline & Plugins

```python
from texthumanize import Pipeline

def my_hook(text: str, lang: str) -> str:
    return text + "\n\n---\nProcessed"

Pipeline.register_hook(my_hook, after="naturalization")
Pipeline.clear_plugins()
```

## Classes

### `AutoTuner`

Feedback-based optimization.

```python
from texthumanize import AutoTuner

tuner = AutoTuner(lang="en", target_score=80)
result = tuner.tune("Text.", max_iterations=5)
```

### `BenchmarkSuite`

6-dimension quality benchmarking. See
[Benchmark Methodology](benchmark-methodology.md) for weights, corpus labels,
and reporting rules.

```python
from texthumanize import BenchmarkSuite

suite = BenchmarkSuite(lang="en")
report = suite.run("Text to benchmark.")
```

For complete reference, see [docs/API_REFERENCE.md](https://github.com/ksanyok/TextHumanize/blob/main/docs/API_REFERENCE.md).
