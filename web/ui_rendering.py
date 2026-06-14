"""HTML rendering helpers for the local Streamlit UI."""

from __future__ import annotations

import difflib
import html
import re
from typing import Any


_TOKEN_RE = re.compile(r"<[^>]+>|\s+|\w+|[^\w\s]+", re.UNICODE)

_CONTENT_TYPE_LABELS = {
    "article": "Artikel",
    "tutorial": "Tutorial",
    "academic": "Akademisch",
    "chat": "Chat",
    "code": "Code",
    "mixed_code": "Gemischt mit Code",
    "general": "Allgemein",
}

_DESCRIPTION_TRANSLATIONS = {
    "Нормализация типографики": "Typografie normalisiert",
    (
        "Финальная защита от чрезмерной разговорности, повторных маркеров "
        "и лишней экспрессивной пунктуации"
    ): (
        "Finaler Schutz vor zu viel Umgangssprache, wiederholten Markern "
        "und übermäßiger expressiver Interpunktion"
    ),
}


def render_inline_diff_html(original: str, modified: str) -> str:
    """Render a safe inline word diff for Streamlit."""
    original_tokens = _tokenize(original)
    modified_tokens = _tokenize(modified)
    matcher = difflib.SequenceMatcher(None, original_tokens, modified_tokens)

    parts: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        before = html.escape("".join(original_tokens[i1:i2]))
        after = html.escape("".join(modified_tokens[j1:j2]))
        if tag == "equal":
            parts.append(before)
        elif tag == "delete":
            parts.append(f'<del class="diff-delete">{before}</del>')
        elif tag == "insert":
            parts.append(f'<ins class="diff-insert">{after}</ins>')
        elif tag == "replace":
            if before:
                parts.append(f'<del class="diff-delete">{before}</del>')
            if after:
                parts.append(f'<ins class="diff-insert">{after}</ins>')

    return (
        '<div class="review-box diff-review" role="region" '
        'aria-label="Inline-Diff">'
        f'{"".join(parts)}'
        '</div>'
    )


def render_ai_highlight_html(text: str, highlighted_spans: list[dict[str, Any]]) -> str:
    """Render AI-risk spans over escaped text, resolving overlaps by priority."""
    spans = _normalise_spans(text, highlighted_spans)
    if not spans:
        return (
            '<div class="review-box ai-review" role="region" '
            'aria-label="AI-Markierungen">'
            f'{html.escape(text)}'
            '</div>'
        )

    boundaries = {0, len(text)}
    for span in spans:
        boundaries.add(span["start"])
        boundaries.add(span["end"])
    ordered = sorted(boundaries)

    parts: list[str] = []
    for start, end in zip(ordered, ordered[1:]):
        if start >= end:
            continue
        fragment = html.escape(text[start:end])
        active = [
            span for span in spans
            if span["start"] <= start and end <= span["end"]
        ]
        if not active:
            parts.append(fragment)
            continue

        span = max(active, key=_span_priority)
        kind = html.escape(str(span.get("kind", "ai_signal")))
        severity = html.escape(str(span.get("severity", "medium")))
        category = _span_category(span)
        score = span.get("score")
        title = f"{kind}"
        if isinstance(score, (int, float)):
            title = f"{kind}: {score:.0%}"

        parts.append(
            f'<mark class="ai-highlight ai-highlight-{category} '
            f'ai-highlight-{severity}" data-kind="{kind}" '
            f'title="{html.escape(title)}">{fragment}</mark>'
        )

    return (
        '<div class="review-box ai-review" role="region" '
        'aria-label="AI-Markierungen">'
        f'{"".join(parts)}'
        '</div>'
    )


def format_change_description(change: dict[str, Any]) -> str:
    """Return a German UI label for a pipeline change entry."""
    raw = str(change.get("description") or "").strip()
    if not raw:
        return str(change.get("type", "Unbekannter Schritt"))

    if raw in _DESCRIPTION_TRANSLATIONS:
        return _DESCRIPTION_TRANSLATIONS[raw]

    content_match = re.fullmatch(
        r"Тип контента: ([\w_]+) \(уверенность ([^)]+)\)",
        raw,
    )
    if content_match:
        content_type, confidence = content_match.groups()
        label = _CONTENT_TYPE_LABELS.get(content_type, content_type)
        return f"Inhaltstyp: {label} (Konfidenz {confidence})"

    natural_match = re.fullmatch(
        r"Текст уже естественный \(AI=([^)]+)\)\. Применяется только типографика\.",
        raw,
    )
    if natural_match:
        return (
            f"Text ist bereits natürlich (AI={natural_match.group(1)}). "
            "Es wird nur Typografie angewendet."
        )

    watermark_match = re.fullmatch(
        r"Водяные знаки: (.+) \(удалено (\d+) символов\)",
        raw,
    )
    if watermark_match:
        watermark_types, removed = watermark_match.groups()
        return f"Wasserzeichen: {watermark_types} ({removed} Zeichen entfernt)"

    adaptive_match = re.fullmatch(
        r"Адаптация: AI-скор=([^,]+), intensity (\d+)→(\d+)",
        raw,
    )
    if adaptive_match:
        ai_score, before, after = adaptive_match.groups()
        return f"Adaptive Intensität: AI-Score={ai_score}, Intensität {before}→{after}"

    return raw


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text or "")


def _normalise_spans(text: str, spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    text_len = len(text)
    for span in spans or []:
        try:
            start = int(span.get("start"))
            end = int(span.get("end"))
        except (TypeError, ValueError):
            continue
        if start < 0 or start >= text_len or end <= start:
            continue
        end = min(end, text_len)
        valid.append({**span, "start": start, "end": end})
    return valid


def _span_category(span: dict[str, Any]) -> str:
    kind = str(span.get("kind", "")).lower()
    if kind == "ai_marker" or "marker" in kind:
        return "marker"
    return "sentence"


def _span_priority(span: dict[str, Any]) -> tuple[int, int, int]:
    severity_order = {"low": 1, "medium": 2, "high": 3}
    category_order = {"sentence": 1, "marker": 2}
    severity = str(span.get("severity", "medium")).lower()
    return (
        category_order.get(_span_category(span), 1),
        severity_order.get(severity, 2),
        int(span.get("end", 0)) - int(span.get("start", 0)),
    )
