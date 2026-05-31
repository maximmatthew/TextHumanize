# Watermark Detection & Cleaning

Detect and remove invisible Unicode watermarks, homoglyph substitutions,
metadata markers, and statistical LLM watermark signals.

## Detect

```python
from texthumanize import detect_watermarks

result = detect_watermarks("Te\u200bxt wi\u200bth hid\u200bden ch\u200bars")
print(result)  # Types found, locations, confidence
```

## Clean

```python
from texthumanize import clean_watermarks

clean = clean_watermarks("Te\u200bxt wi\u200bth hid\u200bden ch\u200bars")
print(clean)  # "Text with hidden chars"
```

## Unified Report

```python
from texthumanize import watermark_report

report = watermark_report("Te\u200bxt wi\u200bth hidden marks", lang="en")
print(report["risk_score"])
print(report["highlighted_spans"])  # positions, codepoints, replacements
print(report["clean_safe"]["text"])  # safe Unicode/metadata cleanup
```

For statistical signals, pass `aggressive=True` to include an optional
`neutralise_aggressive` branch with lexical changes and a diff.

## Watermark Types

| Type | Description |
|------|------------|
| Zero-width characters | U+200B, U+200C, U+200D, U+FEFF |
| Homoglyph substitution | Latin/Cyrillic lookalikes |
| Invisible Unicode | Combining marks, variation selectors |
| Whitespace encoding | Tab/space patterns |
| Metadata | Hidden formatting markers |
| Statistical watermark | Green-list style z-score and gamma/window/hash hypotheses |
