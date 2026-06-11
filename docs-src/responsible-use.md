# Responsible Use

TextHumanize is designed for style normalization, readability improvement,
privacy-preserving audit workflows, and internal quality checks. It is not a
promise that text will pass external AI detectors.

## What TextHumanize Does

Use TextHumanize to:

- improve clarity, rhythm, sentence variety, and readability of drafts you are
  allowed to edit;
- audit AI-like style signals with the built-in detector and explainable
  reports;
- identify invisible Unicode, homoglyph, metadata, and statistical watermark
  signals in content you own or are authorized to inspect;
- preserve important terms, numbers, URLs, quotes, and entities while editing;
- build offline QA gates for content teams, SaaS products, and on-prem systems.

## What It Does Not Guarantee

TextHumanize does not guarantee passing GPTZero, Originality.ai, Turnitin, or
any other external detector. External detectors use different models, training
data, thresholds, and product policies. Treat TextHumanize detector scores as
internal quality signals, not universal truth.

Do not use TextHumanize to misrepresent authorship, bypass required disclosure,
remove provenance markers from third-party content without permission, or submit
work in contexts where AI assistance is prohibited.

## Detector Results

The built-in detector is useful for finding patterns such as formulaic
connectors, uniform sentence length, low burstiness, and overly regular style.
Its output should be interpreted with context:

| Signal | Use It For | Do Not Treat It As |
|--------|------------|--------------------|
| `detect_ai()` score | Internal style risk estimate | A universal AI verdict |
| `detect_ai_explain()` reasons | Editing guidance | Proof of authorship |
| Confidence interval | Reliability hint | A legal or academic standard |
| Sentence report | Targeted revision map | A requirement to rewrite every sentence |

Short texts, formal documents, legal copy, documentation, and highly templated
content can produce uncertain results. Prefer manual review when the decision is
high-impact.

## Watermark Forensics

Watermark tooling is split into safe cleanup and stronger neutralization:

- `watermark_report()` explains Unicode, homoglyph, invisible-character, and
  statistical findings.
- `clean_safe()` removes obvious invisible or confusable characters while
  preserving wording.
- `neutralise_aggressive()` can change lexical choices and should be opt-in,
  reviewed, and logged.

Use these tools for your own content, authorized audits, copy/paste hygiene,
malware-resistant text cleanup, and compliance workflows. Do not remove
provenance or attribution signals from content you do not control.

## Media Watermark Forensics (images / audio / video)

`detect_media_watermarks()` and `clean_media_watermarks()` apply the same
honest, forensics-first posture to media files:

- Detection covers **inspectable** signals only: C2PA / CAI manifests, XMP /
  EXIF provenance, embedded generation parameters, generator signatures, and
  basic LSB / spectral anomalies.
- It **cannot** detect or remove robust in-content neural watermarks such as
  Google **SynthID**. Those are embedded in the pixels or audio samples and are
  specifically designed to survive metadata stripping and re-encoding. Do not
  treat a clean report as proof that media is unwatermarked or human-made.
- Removal strips metadata/provenance (a standard privacy operation). Do **not**
  strip C2PA Content Credentials or attribution from media you do not own in
  order to misrepresent its origin — that defeats transparency efforts and may
  violate platform rules or law. Use it for your own files, authorized audits,
  and metadata-privacy hygiene.

## Integration Safeguards

For production integrations:

1. Show before/after diffs and change ratios to reviewers.
2. Enable semantic preservation for brand terms, named entities, numbers,
   prices, dates, URLs, quotes, and code.
3. Use `quality_gate="strict"` for workflows where meaning drift is expensive.
4. Prefer `minimal=True` or `--only-flagged` when only risky spans need edits.
5. Store non-sensitive metrics such as quality score, detector score, and
   watermark risk score for regression tracking.
6. Add human review for legal, medical, academic, financial, and policy content.
7. Avoid product copy that promises bypassing external detectors.

## Suggested Disclosure Language

For customer-facing reports, use neutral wording:

> This report identifies style, readability, AI-like pattern, and watermark risk
> signals using TextHumanize's offline internal models. Results may differ from
> external AI detectors and should be reviewed in context.

## Related APIs

- `humanize(..., quality_gate="strict")`
- `humanize(..., minimal=True)`
- `detect_ai_explain(text, lang)`
- `audit_report(text, lang)`
- `watermark_report(text, lang)`
- `clean_safe(text)`
- `neutralise_aggressive(text)`
- `texthumanize --fail-under-quality`
