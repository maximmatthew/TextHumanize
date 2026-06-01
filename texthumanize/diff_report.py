"""Отчёт об изменениях в нескольких форматах: text, HTML, JSON-patch.

Использование::

    from texthumanize import humanize, explain
    from texthumanize.diff_report import explain_html, explain_json_patch

    result = humanize("Некий текст для обработки.", lang="ru")
    print(explain_html(result))        # HTML с красными/зелёными блоками
    print(explain_json_patch(result))  # RFC 6902 JSON Patch
"""

from __future__ import annotations

import difflib
import html as html_mod
import json
import logging
import re
from typing import Any

from texthumanize.utils import HumanizeResult

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  HTML DIFF (inline, side-by-side)
# ═══════════════════════════════════════════════════════════════

_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       max-width: 900px; margin: 2em auto; padding: 0 1em;
       color: #24292f; background: #fff; }}
h1 {{ font-size: 1.3em; border-bottom: 1px solid #d0d7de; padding-bottom: .4em; }}
h2 {{ font-size: 1.05em; margin-top: 1.4em; }}
.meta {{ color: #656d76; font-size: .85em; margin-bottom: 1em; }}
.diff {{ font-family: 'SFMono-Regular', Consolas, 'Courier New', monospace;
         font-size: .9em; line-height: 1.6; white-space: pre-wrap;
         word-wrap: break-word; background: #f6f8fa; padding: 1em;
         border-radius: 6px; border: 1px solid #d0d7de; }}
.before-after {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1em;
                 margin: 1em 0; }}
.text-box {{ background: #f6f8fa; border: 1px solid #d0d7de;
             border-radius: 6px; padding: .8em; overflow: auto; }}
.text-box pre {{ white-space: pre-wrap; word-wrap: break-word; margin: 0;
                 font-family: 'SFMono-Regular', Consolas, 'Courier New', monospace;
                 font-size: .85em; line-height: 1.5; }}
del {{ background: #ffd7d5; text-decoration: line-through; color: #82071e; }}
ins {{ background: #ccffd8; text-decoration: none; color: #116329; }}
.metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: .8em;
            margin: 1em 0; font-size: .9em; }}
.metric {{ background: #f6f8fa; padding: .6em; border-radius: 4px; }}
.metric .label {{ color: #656d76; }}
.metric .value {{ font-weight: 600; }}
.section {{ margin-top: 1.2em; }}
.warning {{ background: #fff8c5; border: 1px solid #eac54f;
            border-radius: 4px; padding: .5em .7em; margin: .4em 0; }}
.span-item {{ border-bottom: 1px solid #eee; padding: .35em 0;
              font-size: .9em; }}
.span-kind {{ display: inline-block; background: #fff1e5; color: #9a3412;
              border-radius: 3px; padding: 0 .4em; font-size: .8em;
              font-weight: 500; margin-right: .4em; }}
.timing-list {{ background: #f6f8fa; border-radius: 4px; padding: .7em;
                font-size: .9em; }}
.timing-list code {{ color: #0969da; }}
.arrow-down {{ color: #1a7f37; }}
.arrow-up {{ color: #cf222e; }}
.changes {{ margin-top: 1.2em; }}
.change-item {{ padding: .3em 0; border-bottom: 1px solid #eee; }}
.change-type {{ display: inline-block; background: #ddf4ff; color: #0969da;
                border-radius: 3px; padding: 0 .4em; font-size: .8em;
                font-weight: 500; margin-right: .4em; }}
</style>
</head>
<body>
<h1>{title}</h1>
<div class="meta">{meta}</div>
<div class="metrics">{metrics}</div>
<h2>Before / After</h2>
<div class="before-after">
  <div class="text-box"><b>Before</b><pre>{before_text}</pre></div>
  <div class="text-box"><b>After</b><pre>{after_text}</pre></div>
</div>
<h2>Inline Diff</h2>
<div class="diff">{diff}</div>
{timings_section}
{warnings_section}
{spans_section}
{changes_section}
</body>
</html>"""


def explain_html(
    result: HumanizeResult,
    *,
    title: str = "TextHumanize — Change Report",
    show_changes: bool = True,
    elapsed_seconds: float | None = None,
    warnings: list[str] | None = None,
) -> str:
    """Render an HTML change report with inline diff.

    Args:
        result: A ``HumanizeResult`` from ``humanize()``.
        title: Page title.
        show_changes: Include the per-change breakdown table.

    Returns:
        A self-contained HTML string.
    """
    esc = html_mod.escape

    # Meta line
    report = explain_json_report(
        result,
        elapsed_seconds=elapsed_seconds,
        warnings=warnings,
        include_text=False,
    )
    summary = report["summary"]
    meta = (
        f"Language: <b>{esc(result.lang)}</b> &middot; "
        f"Profile: <b>{esc(result.profile)}</b> &middot; "
        f"Intensity: <b>{result.intensity}</b> &middot; "
        f"Change ratio: <b>{result.change_ratio:.1%}</b> &middot; "
        f"Quality: <b>{summary['quality_score']:.2f}</b> &middot; "
        f"Similarity: <b>{summary['similarity']:.2f}</b>"
    )

    # Metrics grid
    metrics_html = ""
    if result.metrics_before and result.metrics_after:
        items: list[tuple[str, str, float, float]] = [
            ("Artificiality", "", _g(result.metrics_before, "artificiality_score"),
             _g(result.metrics_after, "artificiality_score")),
            ("Avg sentence len", " words", _g(result.metrics_before, "avg_sentence_length"),
             _g(result.metrics_after, "avg_sentence_length")),
            ("Bureaucratic ratio", "", _g(result.metrics_before, "bureaucratic_ratio"),
             _g(result.metrics_after, "bureaucratic_ratio")),
            ("Connector ratio", "", _g(result.metrics_before, "connector_ratio"),
             _g(result.metrics_after, "connector_ratio")),
            ("Repetition", "", _g(result.metrics_before, "repetition_score"),
             _g(result.metrics_after, "repetition_score")),
            ("Typography", "", _g(result.metrics_before, "typography_score"),
             _g(result.metrics_after, "typography_score")),
        ]
        parts = []
        for label, unit, before, after in items:
            arrow_cls = (
                "arrow-down" if after < before else
                "arrow-up" if after > before else ""
            )
            arrow = "↓" if after < before else "↑" if after > before else "="
            parts.append(
                f'<div class="metric">'
                f'<span class="label">{esc(label)}</span><br>'
                f'<span class="value">{before:.2f}{unit} → '
                f'{after:.2f}{unit} '
                f'<span class="{arrow_cls}">{arrow}</span>'
                f'</span></div>'
            )
        metrics_html = "\n".join(parts)

    # Inline diff (word-level)
    diff_html = _word_diff_html(result.original, result.text)

    timings_section = _timings_html(report["timings"])
    warnings_section = _warnings_html(report["warnings"])
    spans_section = _spans_html(report["highlighted_spans"])

    # Changes list
    changes_section = ""
    if show_changes and result.changes:
        items_html = []
        for ch in result.changes[:50]:
            ctype = ch.get("type", "unknown")
            if "original" in ch and "replacement" in ch:
                desc = (
                    f'<del>{esc(str(ch["original"]))}</del> → '
                    f'<ins>{esc(str(ch["replacement"]))}</ins>'
                )
            elif "description" in ch:
                desc = esc(str(ch["description"]))
            else:
                desc = esc(str(ch))
            items_html.append(
                f'<div class="change-item">'
                f'<span class="change-type">{esc(ctype)}</span> '
                f'{desc}</div>'
            )
        if len(result.changes) > 50:
            items_html.append(
                f'<div class="change-item" style="color: #656d76">'
                f'… and {len(result.changes) - 50} more changes</div>'
            )
        changes_section = (
            '<div class="changes">'
            f'<h2>Changes ({len(result.changes)})</h2>'
            + "\n".join(items_html) + '</div>'
        )

    return _HTML_TEMPLATE.format(
        title=esc(title),
        meta=meta,
        metrics=metrics_html,
        before_text=esc(result.original),
        after_text=esc(result.text),
        diff=diff_html,
        timings_section=timings_section,
        warnings_section=warnings_section,
        spans_section=spans_section,
        changes_section=changes_section,
    )


# ═══════════════════════════════════════════════════════════════
#  JSON PATCH (RFC 6902-like)
# ═══════════════════════════════════════════════════════════════

def explain_json_patch(result: HumanizeResult) -> str:
    """Generate a JSON-patch-style change report.

    Each change is an operation with ``op``, ``path``, ``value``,
    and optional ``old`` fields, following the spirit of RFC 6902.

    Returns:
        JSON string (indented).
    """
    ops: list[dict[str, Any]] = []

    for i, ch in enumerate(result.changes):
        op: dict[str, Any] = {
            "op": "replace",
            "path": f"/text/change/{i}",
            "type": ch.get("type", "unknown"),
        }
        if "original" in ch and "replacement" in ch:
            op["old"] = ch["original"]
            op["value"] = ch["replacement"]
        elif "description" in ch:
            op["op"] = "info"
            op["value"] = ch["description"]
        ops.append(op)

    envelope: dict[str, Any] = {
        "version": "1.0",
        "lang": result.lang,
        "profile": result.profile,
        "intensity": result.intensity,
        "change_ratio": round(result.change_ratio, 4),
        "metrics_before": result.metrics_before,
        "metrics_after": result.metrics_after,
        "operations": ops,
    }
    return json.dumps(envelope, ensure_ascii=False, indent=2)


def explain_json_report(
    result: HumanizeResult,
    *,
    elapsed_seconds: float | None = None,
    warnings: list[str] | None = None,
    max_spans: int = 100,
    include_text: bool = True,
) -> dict[str, Any]:
    """Build a full before/after report for CI and product integrations.

    The report is intentionally stable and richer than the JSON patch format:
    it includes the original and processed text, highlighted diff spans,
    metrics, stage timings, warnings, and a compact change summary.
    """
    from texthumanize import __version__

    stage_timings = _normalise_timings(
        result.metrics_after.get("stage_timings")
        if result.metrics_after else None
    )
    pipeline_total = _safe_float(
        result.metrics_after.get("total_time")
        if result.metrics_after else None
    )
    if pipeline_total is None and stage_timings:
        pipeline_total = round(sum(stage_timings.values()), 6)

    report_warnings = _collect_warnings(result, warnings)
    highlighted_spans = _diff_spans(result.original, result.text, max_spans=max_spans)

    before: dict[str, Any] = _text_stats(result.original)
    after: dict[str, Any] = _text_stats(result.text)
    if include_text:
        before["text"] = result.original
        after["text"] = result.text

    return {
        "schema_version": "text-humanize.change_report.v1",
        "version": __version__,
        "summary": {
            "lang": result.lang,
            "profile": result.profile,
            "intensity": result.intensity,
            "change_ratio": round(result.change_ratio, 4),
            "similarity": round(result.similarity, 4),
            "quality_score": round(result.quality_score, 4),
            "changes_count": len(result.changes),
            "highlighted_spans_count": len(highlighted_spans),
        },
        # Backward-compatible top-level fields used by existing CLI consumers.
        "lang": result.lang,
        "profile": result.profile,
        "intensity": result.intensity,
        "change_ratio": round(result.change_ratio, 4),
        "similarity": round(result.similarity, 4),
        "quality_score": round(result.quality_score, 4),
        "before": before,
        "after": after,
        "highlighted_spans": highlighted_spans,
        "metrics": {
            "before": result.metrics_before,
            "after": result.metrics_after,
        },
        "timings": {
            "elapsed_seconds": (
                round(elapsed_seconds, 6)
                if elapsed_seconds is not None else None
            ),
            "pipeline_total_seconds": pipeline_total,
            "stage_timings": stage_timings,
        },
        "warnings": report_warnings,
        "changes": result.changes[:50],
    }


# ═══════════════════════════════════════════════════════════════
#  SIDE-BY-SIDE TEXT DIFF
# ═══════════════════════════════════════════════════════════════

def explain_side_by_side(
    result: HumanizeResult,
    width: int = 80,
) -> str:
    """Render a side-by-side diff of original vs processed text.

    Args:
        result: A ``HumanizeResult`` from ``humanize()``.
        width: Column width for each side.

    Returns:
        Text string with side-by-side columns.
    """
    orig_lines = result.original.splitlines()
    new_lines = result.text.splitlines()

    differ = difflib.unified_diff(
        orig_lines, new_lines,
        fromfile="Original", tofile="Processed",
        lineterm="",
    )
    return "\n".join(differ)


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def _safe_float(value: Any) -> float | None:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _normalise_timings(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    timings: dict[str, float] = {}
    for key, raw in value.items():
        parsed = _safe_float(raw)
        if parsed is not None:
            timings[str(key)] = parsed
    return timings


def _text_stats(text: str) -> dict[str, int]:
    return {
        "chars": len(text),
        "words": len(text.split()),
        "lines": len(text.splitlines()) or (1 if text else 0),
    }


def _collect_warnings(
    result: HumanizeResult,
    extra_warnings: list[str] | None = None,
) -> list[str]:
    warnings: list[str] = []
    if extra_warnings:
        warnings.extend(str(item) for item in extra_warnings if item)

    metrics_warnings = result.metrics_after.get("warnings") if result.metrics_after else None
    if isinstance(metrics_warnings, list):
        warnings.extend(str(item) for item in metrics_warnings if item)
    elif isinstance(metrics_warnings, str):
        warnings.append(metrics_warnings)

    explain = (
        result.metrics_after.get("humanize_explain", {})
        if result.metrics_after else {}
    )
    remaining_risks = (
        explain.get("remaining_risks", [])
        if isinstance(explain, dict) else []
    )
    if isinstance(remaining_risks, list):
        for risk in remaining_risks[:5]:
            if isinstance(risk, dict):
                msg = (
                    risk.get("reason")
                    or risk.get("description")
                    or risk.get("message")
                    or risk.get("type")
                )
                if msg:
                    warnings.append(str(msg))
            elif risk:
                warnings.append(str(risk))

    if result.quality_score < 0.5:
        warnings.append(
            f"quality_score is low ({result.quality_score:.2f}); review before publishing."
        )
    if result.change_ratio > 0.5:
        warnings.append(
            f"change_ratio is high ({result.change_ratio:.1%}); semantic review recommended."
        )

    deduped: list[str] = []
    seen: set[str] = set()
    for warning in warnings:
        cleaned = warning.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            deduped.append(cleaned)
    return deduped


def _tokens_with_offsets(text: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0), match.start(), match.end())
        for match in re.finditer(r"\S+|\s+", text)
    ]


def _bounds(tokens: list[tuple[str, int, int]], start: int, end: int, text_len: int) -> tuple[int, int]:
    if start < end and start < len(tokens):
        return tokens[start][1], tokens[end - 1][2]
    if start < len(tokens):
        offset = tokens[start][1]
        return offset, offset
    return text_len, text_len


def _preview(text: str, start: int, end: int, max_len: int = 180) -> str:
    snippet = text[start:end].strip()
    if len(snippet) <= max_len:
        return snippet
    return snippet[: max_len - 1] + "…"


def _diff_spans(
    original: str,
    modified: str,
    *,
    max_spans: int = 100,
) -> list[dict[str, Any]]:
    orig_tokens = _tokens_with_offsets(original)
    mod_tokens = _tokens_with_offsets(modified)
    orig_parts = [token for token, _, _ in orig_tokens]
    mod_parts = [token for token, _, _ in mod_tokens]

    spans: list[dict[str, Any]] = []
    sm = difflib.SequenceMatcher(None, orig_parts, mod_parts)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        before_start, before_end = _bounds(orig_tokens, i1, i2, len(original))
        after_start, after_end = _bounds(mod_tokens, j1, j2, len(modified))
        spans.append({
            "kind": f"diff_{tag}",
            "before_start": before_start,
            "before_end": before_end,
            "after_start": after_start,
            "after_end": after_end,
            "before_text": _preview(original, before_start, before_end),
            "after_text": _preview(modified, after_start, after_end),
        })
        if len(spans) >= max_spans:
            break
    return spans


def _timings_html(timings: dict[str, Any]) -> str:
    stage_timings = timings.get("stage_timings", {})
    elapsed = timings.get("elapsed_seconds")
    pipeline_total = timings.get("pipeline_total_seconds")
    if not stage_timings and elapsed is None and pipeline_total is None:
        return ""

    parts = []
    if elapsed is not None:
        parts.append(f"<div>Elapsed: <b>{float(elapsed):.3f}s</b></div>")
    if pipeline_total is not None:
        parts.append(f"<div>Pipeline total: <b>{float(pipeline_total):.3f}s</b></div>")
    for name, seconds in stage_timings.items():
        parts.append(
            f"<div><code>{html_mod.escape(str(name))}</code>: "
            f"{float(seconds):.3f}s</div>"
        )
    return (
        '<div class="section"><h2>Timings</h2>'
        f'<div class="timing-list">{"".join(parts)}</div></div>'
    )


def _warnings_html(warnings: list[str]) -> str:
    if not warnings:
        return ""
    items = "\n".join(
        f'<div class="warning">{html_mod.escape(warning)}</div>'
        for warning in warnings
    )
    return f'<div class="section"><h2>Warnings</h2>{items}</div>'


def _spans_html(spans: list[dict[str, Any]]) -> str:
    if not spans:
        return ""
    items = []
    for span in spans[:50]:
        before = html_mod.escape(str(span.get("before_text", "")))
        after = html_mod.escape(str(span.get("after_text", "")))
        kind = html_mod.escape(str(span.get("kind", "diff")))
        items.append(
            '<div class="span-item">'
            f'<span class="span-kind">{kind}</span> '
            f'<del>{before}</del> → <ins>{after}</ins>'
            '</div>'
        )
    if len(spans) > 50:
        items.append(
            f'<div class="span-item" style="color: #656d76">'
            f'… and {len(spans) - 50} more highlighted spans</div>'
        )
    return (
        '<div class="section">'
        f'<h2>Highlighted Spans ({len(spans)})</h2>'
        + "\n".join(items)
        + '</div>'
    )


def _g(d: dict | None, key: str, default: float = 0.0) -> float:
    """Safely get a float from a dict (metrics_before/after)."""
    if not d:
        return default
    return float(d.get(key, default))


def _word_diff_html(original: str, modified: str) -> str:
    """Produce an inline word-level diff with <del>/<ins> tags."""
    esc = html_mod.escape

    orig_words = re.findall(r'\S+|\s+', original)
    mod_words = re.findall(r'\S+|\s+', modified)

    sm = difflib.SequenceMatcher(None, orig_words, mod_words)
    parts: list[str] = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            parts.append(esc("".join(orig_words[i1:i2])))
        elif tag == "delete":
            parts.append(f'<del>{esc("".join(orig_words[i1:i2]))}</del>')
        elif tag == "insert":
            parts.append(f'<ins>{esc("".join(mod_words[j1:j2]))}</ins>')
        elif tag == "replace":
            parts.append(f'<del>{esc("".join(orig_words[i1:i2]))}</del>')
            parts.append(f'<ins>{esc("".join(mod_words[j1:j2]))}</ins>')

    return "".join(parts)
