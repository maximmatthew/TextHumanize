"""Tests for Streamlit-only HTML rendering helpers."""

from web.ui_rendering import (
    format_change_description,
    render_ai_highlight_html,
    render_inline_diff_html,
)


def test_inline_diff_marks_insertions_and_deletions():
    html = render_inline_diff_html("Alter Text bleibt.", "Neuer Text bleibt.")

    assert "<del" in html
    assert "Alter" in html
    assert "<ins" in html
    assert "Neuer" in html
    assert "bleibt" in html


def test_inline_diff_escapes_html_input():
    html = render_inline_diff_html("<script>alert(1)</script>", "<b>ok</b>")

    assert "<script>" not in html
    assert "<b>ok</b>" not in html
    assert "&lt;script&gt;" in html
    assert "&lt;b&gt;ok&lt;/b&gt;" in html


def test_ai_highlight_renders_overlapping_sentence_and_marker_spans():
    text = "Furthermore, this comprehensive method works."
    html = render_ai_highlight_html(
        text,
        [
            {
                "start": 0,
                "end": len(text),
                "kind": "sentence_ai_signal",
                "severity": "medium",
                "score": 0.52,
            },
            {
                "start": 0,
                "end": 11,
                "kind": "ai_marker",
                "severity": "high",
                "score": 0.91,
            },
        ],
    )

    assert "ai-highlight-sentence" in html
    assert "ai-highlight-marker" in html
    assert "Furthermore" in html
    assert "data-kind=\"ai_marker\"" in html


def test_ai_highlight_ignores_invalid_spans_and_escapes_text():
    html = render_ai_highlight_html(
        "<unsafe> text",
        [
            {"start": -5, "end": 3, "kind": "bad"},
            {"start": 10, "end": 10, "kind": "empty"},
            {"start": 999, "end": 1000, "kind": "outside"},
        ],
    )

    assert "<unsafe>" not in html
    assert "&lt;unsafe&gt;" in html
    assert "ai-highlight-" not in html


def test_format_change_description_translates_known_russian_pipeline_messages():
    examples = [
        (
            "Тип контента: article (уверенность 24%)",
            "Inhaltstyp: Artikel (Konfidenz 24%)",
        ),
        (
            "Текст уже естественный (AI=5%). Применяется только типографика.",
            "Text ist bereits natürlich (AI=5%). Es wird nur Typografie angewendet.",
        ),
        (
            "Водяные знаки: statistical_bias (удалено 0 символов)",
            "Wasserzeichen: statistical_bias (0 Zeichen entfernt)",
        ),
        ("Нормализация типографики", "Typografie normalisiert"),
        (
            "Финальная защита от чрезмерной разговорности, повторных маркеров "
            "и лишней экспрессивной пунктуации",
            "Finaler Schutz vor zu viel Umgangssprache, wiederholten Markern "
            "und übermäßiger expressiver Interpunktion",
        ),
    ]

    for source, expected in examples:
        assert format_change_description({"description": source}) == expected


def test_format_change_description_falls_back_to_change_type():
    assert format_change_description({"type": "unknown_step"}) == "unknown_step"
