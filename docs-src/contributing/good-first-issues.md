# Good First Issues

These task briefs are designed for first-time contributors. Each item is small,
testable, and useful for improving TextHumanize quality without needing to know
the full 38-stage pipeline.

When opening or claiming an issue, use labels such as `good first issue`,
`language-pack`, `fixtures`, `docs`, `ai-markers`, or `watermark`.

## Language Packs

### Add Domain Phrases For One Language

**Goal:** Improve one existing language pack with natural phrases for a specific
domain such as SaaS, ecommerce, education, real estate, or healthcare.

**Suggested files:**

- `texthumanize/lang/<code>.py`
- `tests/test_multilang.py`
- `tests/test_golden.py`

**Acceptance criteria:**

- Add at least 20 domain-safe replacements or phrase patterns.
- Preserve brand names, URLs, prices, dates, and identifiers.
- Add 3-5 regression examples for the selected language/domain.
- Run `python -m pytest tests/test_multilang.py tests/test_golden.py -q`.

### Add Colloquial Fillers For Existing Language

**Goal:** Make outputs less robotic without over-humanizing them.

**Suggested files:**

- `texthumanize/lang/<code>.py`
- `tests/test_output_quality.py`

**Acceptance criteria:**

- Add 10-20 mild, professional fillers or transitions.
- Avoid slang that would be inappropriate for business content.
- Add tests showing output remains readable and semantic values are preserved.

## AI Marker Packs

### Add AI Markers For One Domain

**Goal:** Improve `detect_ai_explain()` suggestions for one formal domain:
legal, academic, documentation, finance, medical, support, or product copy.

**Suggested files:**

- `texthumanize/data/contributor_ai_markers_v1.json`
- `texthumanize/ai_markers.py`
- `tests/test_audit_round2.py`
- `tests/test_golden.py`

**Acceptance criteria:**

- Add domain-specific AI-like markers and safe suggested actions.
- Include at least 5 positive examples and 3 false-positive guard examples.
- Do not make formal human-written text score worse without reason.
- Use `python scripts/update_marker_packs.py --review-out marker_pack_review.md`
  when mining candidates from the licensed eval corpus.
- Run `validate_contributor_pack("ai_markers")` after JSON edits.

### Add Low-Risk Replacement Suggestions

**Goal:** Expand suggested actions for common AI-like patterns without changing
meaning.

**Suggested files:**

- `texthumanize/data/contributor_synonyms_v1.json`
- `texthumanize/core.py`
- `texthumanize/ai_markers.py`
- `tests/test_api_wrappers.py`

**Acceptance criteria:**

- Add suggestions for at least 10 high-frequency AI-like phrases.
- Suggestions must be neutral and not claim external detector bypass.
- Update tests for `detect_ai_explain()` output shape.
- Run `validate_contributor_pack("synonyms")` after JSON edits.

### Add Collocation Guard Examples

**Goal:** Improve natural replacement safety by documenting phrase pairs that
should not be broken by synonym substitution.

**Suggested files:**

- `texthumanize/data/contributor_collocations_v1.json`
- `texthumanize/collocation_engine.py`
- `tests/test_v015_features.py`

**Acceptance criteria:**

- Add common phrases with `preferred_contexts` and `blocked_replacements`.
- Keep examples synthetic and domain-safe.
- Add or update a deterministic collocation guard regression test.
- Run `validate_contributor_pack("collocations")` after JSON edits.

## Fixture Packs

### Add Benchmark Fixtures For One Domain

**Goal:** Expand benchmark coverage with safe, synthetic fixtures for a domain.

**Suggested files:**

- `tests/fixtures/`
- `tests/test_benchmark.py`
- `docs-src/benchmark-methodology.md`

**Acceptance criteria:**

- Add at least 12 examples across `human`, `raw_ai`,
  `lightly_edited_ai`, and `heavily_edited_ai` labels.
- Include metadata: `lang`, `domain`, `label`, `length_bucket`, `source`.
- Verify the new samples are discoverable through `index_eval_corpus()` and
  selectable with `load_eval_corpus()` filters.
- No private data, copied customer text, or unlicensed third-party text.
- Benchmark tests should remain deterministic.

### Add Cross-Runtime Parity Case

**Goal:** Improve Python/PHP/TypeScript behavior consistency.

**Suggested files:**

- `tests/fixtures/parity_cases.json`
- `tests/test_cross_runtime_parity.py`
- `php/tests/ParityFixturesTest.php`
- `js/tests/parity.test.ts`

**Acceptance criteria:**

- Add one focused fixture with protected terms and expected ranges.
- Keep assertions tolerant enough for runtime differences.
- Run the focused parity tests where available.

## Watermark Samples

### Add Unicode Watermark Regression Case

**Goal:** Improve `watermark_report()` coverage for invisible or confusable
characters.

**Suggested files:**

- `texthumanize/data/contributor_watermark_samples_v1.json`
- `tests/test_watermark.py`
- `texthumanize/watermark.py`

**Acceptance criteria:**

- Add a sample for one class: zero-width, soft hyphen, BOM, mixed scripts,
  fullwidth, variation selectors, or math homoglyphs.
- Assert positions, safe replacement, and clean text.
- Avoid changing lexical content in `clean_safe()`.
- Run `validate_contributor_pack("watermark_samples")` after JSON edits.

### Add Statistical Watermark Hypothesis Sample

**Goal:** Improve explainability for statistical watermark findings.

**Suggested files:**

- `tests/test_audit_round2.py`
- `texthumanize/watermark_forensics.py`

**Acceptance criteria:**

- Add a deterministic sample with expected z-score/p-value range.
- Keep thresholds broad enough to avoid flaky tests.
- Document whether the sample is synthetic and how it was generated.

## Documentation Examples

### Add A Private Workflow Variant

**Goal:** Extend the private offline workflow for a specific stack.

**Suggested files:**

- `examples/private_offline_workflow.py`
- `docs-src/getting-started/private-offline-workflow.md`
- `tests/test_examples.py`

**Acceptance criteria:**

- Add a short variant for CLI, FastAPI, or batch folder processing.
- Keep `backend="local"` and responsible-use language.
- Include compile/source regression checks.

### Add A Production Integration Note

**Goal:** Improve one framework integration page with privacy and safety defaults.

**Suggested files:**

- `docs-src/integrations/fastapi.md`
- `docs-src/integrations/flask.md`
- `docs-src/integrations/django.md`
- `docs-src/integrations/wordpress.md`

**Acceptance criteria:**

- Add request limits, timeout, error schema, and no-network guidance.
- Link to Responsible Use and Private Offline Workflow.
- Do not introduce marketing claims about bypassing external detectors.

## Bad Output Bank

### Convert One Bad Output Into A Regression Test

**Goal:** Turn a real quality failure into a permanent test.

**Suggested files:**

- `tests/test_regression_quality.py`
- `tests/test_golden.py`
- `tests/fixtures/`

**Acceptance criteria:**

- Anonymize the input and remove any private data.
- Add expected properties rather than brittle exact-output assertions.
- Cover at least one of: semantic drift, over-humanization, broken grammar,
  placeholder leak, watermark cleanup, or false-positive detector behavior.

## Pull Request Checklist

Before opening a PR:

- Run the smallest relevant test set.
- Add or update fixtures only when they are licensed, generated, or owned.
- Keep examples offline by default.
- Update documentation when behavior or public guidance changes.
- Avoid claims that TextHumanize guarantees passing external AI detectors.
