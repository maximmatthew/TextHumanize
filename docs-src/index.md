# TextHumanize

**The most advanced open-source text naturalization engine**

Normalize style, improve readability, and audit AI-like style and watermark
signals - offline, private, and fast. External AI detector results are not
guaranteed.

---

## Key Numbers

| Metric | Value |
|--------|-------|
| **Lines of Code** | 235,000+ |
| **Pipeline Stages** | 38 |
| **Languages** | 25 + universal |
| **Tests** | 2,105+ passing |
| **Dependencies** | Zero |
| **Platforms** | Python · JS/TS · PHP |

## Why TextHumanize?

!!! success "Core Advantages"
    - **300-500 ms per paragraph** - fast enough for interactive workflows and batch jobs
    - **100% private** - all processing is local, your text never leaves your machine
    - **Precise control** - intensity 0-100, profiles, keyword preservation, strict gates
    - **25 languages** - full dictionaries + universal processor for any language
    - **Zero dependencies** - pure Python stdlib, starts in <100ms
    - **Reproducible** - seed-based PRNG, same input + seed = identical output
    - **AI and watermark audit** - explainable internal detector plus unified watermark forensics

## Quick Example

```python
from texthumanize import humanize, detect_ai

# Humanize text
result = humanize(
    "Furthermore, it is important to note that the implementation "
    "of this approach facilitates optimization.",
    lang="en",
    profile="web",
    intensity=70,
)
print(result.text)
# → "But this approach helps with optimization."

# Detect AI-generated text
ai = detect_ai("Text to check.", lang="en")
print(f"AI: {ai['score']:.0%} — {ai['verdict']}")
```

## 🎮 Live Demo

Try TextHumanize online: **[humanizekit.tester-buyreadysite.website](https://humanizekit.tester-buyreadysite.website/)**

## Getting Started

<div class="grid cards" markdown>

- :material-download: **[Installation](getting-started/installation.md)**

    pip install, from source, Docker, PHP, TypeScript

- :material-rocket-launch: **[Quick Start](getting-started/quickstart.md)**

    First steps with humanize(), detect_ai(), and more

- :material-cog: **[Profiles](getting-started/profiles.md)**

    10 built-in profiles for different content types

- :material-lock-check: **[Private Offline Workflow](getting-started/private-offline-workflow.md)**

    Local audit, safe cleanup, strict humanization, and review metrics

- :material-shield-check: **[Responsible Use](responsible-use.md)**

    Honest detector limits, watermark safeguards, and production review rules

</div>

## Integrations

TextHumanize works with all popular Python web frameworks:

- [FastAPI](integrations/fastapi.md) — async endpoints with dependency injection
- [Flask](integrations/flask.md) — blueprint with caching
- [Django](integrations/django.md) — middleware + template filters
- [WordPress](integrations/wordpress.md) — PHP plugin for WP content
