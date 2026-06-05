# Profiles

TextHumanize includes 9 built-in profiles optimized for different content types.

## Profile Table

| Profile | Use Case | Sentence Length | Colloquialisms | Default Intensity |
|---------|----------|:---------:|:---------:|:---------:|
| `chat` | Messaging, social media | 8–18 words | High | 80 |
| `web` | Blog posts, articles | 10–22 words | Medium | 60 |
| `seo` | SEO content (keyword-safe) | 12–25 words | None | 40 |
| `docs` | Technical documentation | 12–28 words | None | 50 |
| `formal` | Academic, legal | 15–30 words | None | 30 |
| `academic` | Research papers | 15–30 words | None | 25 |
| `marketing` | Sales, promo copy | 8–20 words | Medium | 70 |
| `social` | Social media posts | 6–15 words | High | 85 |
| `email` | Business emails | 10–22 words | Medium | 50 |

## Usage

```python
from texthumanize import humanize

# Blog article
result = humanize(text, lang="en", profile="web", intensity=60)

# SEO with keyword protection
result = humanize(text, lang="en", profile="seo", intensity=40,
                  constraints={"keep_keywords": ["API", "cloud"]})

# Casual chat
result = humanize(text, lang="en", profile="chat", intensity=80)

# Academic paper
result = humanize(text, lang="en", profile="academic", intensity=25)
```

## Style Presets

9 built-in style/idiolect presets that emulate different writing personas:

| Preset | Style |
|--------|-------|
| `student` | Casual, short sentences, simple vocabulary |
| `copywriter` | Punchy, varied rhythm, active voice |
| `scientist` | Precise, longer sentences, technical terms |
| `journalist` | Clear, factual, inverted pyramid |
| `blogger` | Conversational, personal, engaging |
| `editor` / `редактор` | Polished, restrained, publication-ready |
| `founder` / `основатель` | Direct, strategic, personal |
| `expert` / `эксперт` | Evidence-led, domain-aware, practical |
| `support` / `поддержка` | Helpful, calm, short support replies |

```python
result = humanize(text, lang="en", target_style="copywriter")
result = humanize(text, lang="en", target_style="редактор")
```
