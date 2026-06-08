"""Product-facing building blocks for integrations such as Promopilot.

These functions compose the core audit, watermark, quality and humanization
primitives into the shapes a content product needs:

* :func:`audit_widget_html` — paste-text audit widget (score, reasons, risk map,
  safe improvements) as a self-contained HTML fragment.
* :func:`audit_batch` — bulk audit of many texts/pages (detector, watermark,
  readability, quality) for sitemap/folder workflows.
* :func:`compare_versions` — original / AI draft / humanized / editor-final
  comparison with per-version scores and pairwise diffs.
* :func:`content_plan_risk` — pre-publication AI/watermark/quality gate per
  planned content item.
* :func:`make_brand_voice` / :func:`brand_voice_lock` — a brand profile that
  locks important terms and humanizes around them.
* :func:`client_report_html` — neutral client report (print-ready HTML) with no
  detector-bypass promises.

All functions are offline; callers fetch any remote pages and pass the text in.
"""

from __future__ import annotations

import html as _html
from typing import Any

__all__ = [
    "audit_batch",
    "audit_widget_html",
    "brand_voice_lock",
    "client_report_html",
    "compare_versions",
    "content_plan_risk",
    "make_brand_voice",
]

_DISCLAIMER = (
    "This report describes internal style, readability and risk signals. It "
    "improves naturalness and removes watermark artifacts; it does not "
    "guarantee bypassing any external AI detector."
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _risk_band(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score >= 0.34:
        return "medium"
    return "low"


# ─────────────────────────────────────────────────────────────
#  Audit widget (HTML)
# ─────────────────────────────────────────────────────────────

def _spans_html(spans: list[dict[str, Any]], esc: Any) -> str:
    if not spans:
        return "<p class='thz-empty'>No flagged spans.</p>"
    items = []
    for span in spans[:20]:
        text = esc(str(span.get("text", span.get("phrase", ""))))
        kind = esc(str(span.get("type", span.get("reason", "signal"))))
        items.append(f"<li><code>{text}</code> <span class='thz-tag'>{kind}</span></li>")
    return "<ul class='thz-spans'>" + "".join(items) + "</ul>"


def audit_widget_html(text: str, lang: str = "auto") -> str:
    """Return a self-contained HTML audit widget for a single text.

    Shows the unified quality score, AI/watermark risk, the highlighted risk
    map and concrete safe improvements. No external assets or scripts.
    """
    from texthumanize.core import audit_report, quality_score_report

    audit = audit_report(text, lang=lang)
    resolved_lang = str(audit.get("lang") or lang)
    quality = quality_score_report(text, lang=resolved_lang, fast=True)
    ai = audit.get("ai", {})
    watermark = audit.get("watermark", {})
    esc = _html.escape

    ai_risk = _clamp(float(ai.get("score", 0.0)))
    wm_risk = _clamp(float(watermark.get("risk_score", 0.0)))
    spans = list(ai.get("highlighted_spans", [])) + list(watermark.get("highlighted_spans", []))
    actions = audit.get("suggested_actions", []) or quality.get("recommendations", [])
    actions_html = "".join(f"<li>{esc(str(a))}</li>" for a in actions[:6])

    return f"""<div class="thz-widget" lang="{esc(resolved_lang)}">
<style>
.thz-widget{{font-family:system-ui,Arial,sans-serif;max-width:640px;border:1px solid #e2e6ea;border-radius:12px;padding:20px;color:#1b1f24}}
.thz-widget h3{{margin:0 0 12px;font-size:18px}}
.thz-grade{{display:inline-block;font-size:28px;font-weight:700;margin-right:10px}}
.thz-bar{{height:10px;border-radius:6px;background:#eef1f4;overflow:hidden;margin:6px 0 14px}}
.thz-bar>i{{display:block;height:100%}}
.thz-row{{display:flex;justify-content:space-between;font-size:13px;margin:4px 0}}
.thz-spans{{margin:8px 0;padding-left:18px;font-size:13px}}
.thz-spans code{{background:#fbeaea;padding:1px 4px;border-radius:4px}}
.thz-tag{{color:#8a6d3b;font-size:11px;margin-left:6px}}
.thz-empty{{color:#6c757d;font-size:13px}}
.thz-note{{color:#6c757d;font-size:11px;margin-top:14px;border-top:1px solid #eee;padding-top:10px}}
.high{{background:#dc3545}}.medium{{background:#fd7e14}}.low{{background:#28a745}}
</style>
<h3>AI &amp; Watermark Audit</h3>
<div><span class="thz-grade">{esc(quality["grade"])}</span>Quality {quality["score_100"]:.0f}/100 &middot; {esc(quality["verdict"])}</div>
<div class="thz-bar"><i class="{_risk_band(1.0 - quality["score"])}" style="width:{quality["score"] * 100:.0f}%"></i></div>
<div class="thz-row"><span>AI-pattern risk</span><strong>{ai_risk * 100:.0f}% ({_risk_band(ai_risk)})</strong></div>
<div class="thz-row"><span>Watermark risk</span><strong>{wm_risk * 100:.0f}% ({_risk_band(wm_risk)})</strong></div>
<h4>Risk map</h4>
{_spans_html(spans, esc)}
<h4>Safe improvements</h4>
<ul>{actions_html}</ul>
<p class="thz-note">{esc(_DISCLAIMER)}</p>
</div>"""


# ─────────────────────────────────────────────────────────────
#  Bulk audit
# ─────────────────────────────────────────────────────────────

def _coerce_items(items: list[Any]) -> list[dict[str, Any]]:
    coerced: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            coerced.append({
                "id": str(item.get("id", item.get("url", index))),
                "text": str(item.get("text", "")),
                "url": item.get("url"),
            })
        else:
            coerced.append({"id": str(index), "text": str(item), "url": None})
    return coerced


def audit_batch(items: list[Any], lang: str = "auto") -> dict[str, Any]:
    """Audit many texts/pages at once (detector, watermark, readability, quality).

    ``items`` may be plain strings or dicts with ``id``/``url``/``text``. Fetch
    sitemap or page text upstream and pass it in; this stays fully offline.
    """
    from texthumanize.core import (
        analyze,
        detect_ai_explain,
        quality_score_report,
        watermark_report,
    )

    coerced = _coerce_items(items)
    rows: list[dict[str, Any]] = []
    high_risk = 0
    for entry in coerced:
        text = entry["text"]
        ai = detect_ai_explain(text, lang=lang, include_sentences=False)
        resolved_lang = str(ai.get("lang") or lang)
        wm = watermark_report(text, lang=resolved_lang, include_statistical=False)
        report = analyze(text, lang=resolved_lang)
        quality = quality_score_report(text, lang=resolved_lang, fast=True)
        ai_risk = _clamp(float(ai.get("score", 0.0)))
        wm_risk = _clamp(float(wm.get("risk_score", 0.0)))
        is_high = ai_risk >= 0.66 or wm_risk >= 0.5
        high_risk += int(is_high)
        rows.append({
            "id": entry["id"],
            "url": entry["url"],
            "lang": resolved_lang,
            "chars": len(text),
            "ai_risk": round(ai_risk, 4),
            "ai_verdict": ai.get("verdict"),
            "watermark_risk": round(wm_risk, 4),
            "has_watermarks": bool(wm.get("has_watermarks")),
            "readability_grade": round(float(getattr(report, "flesch_kincaid_grade", 0.0)), 2),
            "quality_score": quality["score"],
            "quality_grade": quality["grade"],
            "high_risk": is_high,
        })

    total = len(rows)
    return {
        "schema_version": "text-humanize.audit_batch.v1",
        "total": total,
        "high_risk": high_risk,
        "high_risk_rate": round(high_risk / total, 4) if total else 0.0,
        "rows": rows,
    }


# ─────────────────────────────────────────────────────────────
#  Version comparison
# ─────────────────────────────────────────────────────────────

_VERSION_ORDER = ("original", "ai_draft", "humanized", "editor_final")


def compare_versions(versions: dict[str, str], lang: str = "auto") -> dict[str, Any]:
    """Compare text versions (original / AI draft / humanized / editor final).

    Returns per-version detector risk, watermark risk and quality score, plus
    change ratio and semantic similarity of each version against the original.
    """
    from texthumanize.core import (
        _text_similarity,
        detect_ai_explain,
        quality_score_report,
        watermark_report,
    )
    from texthumanize.utils import HumanizeResult

    present = [name for name in _VERSION_ORDER if versions.get(name)]
    present += [name for name in versions if name not in _VERSION_ORDER and versions.get(name)]
    reference = versions.get("original")

    per_version: dict[str, Any] = {}
    for name in present:
        text = versions[name]
        ai = detect_ai_explain(text, lang=lang, include_sentences=False)
        resolved_lang = str(ai.get("lang") or lang)
        wm = watermark_report(text, lang=resolved_lang, include_statistical=False)
        quality = quality_score_report(
            text,
            original=reference if (reference and name != "original") else None,
            lang=resolved_lang,
            fast=True,
        )
        entry: dict[str, Any] = {
            "chars": len(text),
            "ai_risk": round(_clamp(float(ai.get("score", 0.0))), 4),
            "watermark_risk": round(_clamp(float(wm.get("risk_score", 0.0))), 4),
            "quality_score": quality["score"],
            "quality_grade": quality["grade"],
        }
        if reference and name != "original":
            change = HumanizeResult(
                original=reference, text=text, lang=resolved_lang,
                profile="web", intensity=60,
            ).change_ratio
            entry["change_ratio_vs_original"] = round(change, 4)
            entry["similarity_vs_original"] = round(_text_similarity(reference, text), 4)
        per_version[name] = entry

    return {
        "schema_version": "text-humanize.version_compare.v1",
        "versions_present": present,
        "per_version": per_version,
    }


# ─────────────────────────────────────────────────────────────
#  Content-plan risk gate
# ─────────────────────────────────────────────────────────────

def content_plan_risk(
    items: list[Any],
    lang: str = "auto",
    *,
    block_threshold: float = 0.66,
    review_threshold: float = 0.40,
) -> dict[str, Any]:
    """Flag AI/watermark/quality risk for planned content before publication.

    Each item is gated as ``publish``, ``review`` or ``block`` based on the
    combined AI-pattern and watermark risk.
    """
    from texthumanize.core import (
        detect_ai_explain,
        quality_score_report,
        watermark_report,
    )

    coerced = _coerce_items(items)
    rows: list[dict[str, Any]] = []
    gate_counts = {"publish": 0, "review": 0, "block": 0}
    for entry in coerced:
        text = entry["text"]
        ai = detect_ai_explain(text, lang=lang, include_sentences=False)
        resolved_lang = str(ai.get("lang") or lang)
        wm = watermark_report(text, lang=resolved_lang, include_statistical=False)
        quality = quality_score_report(text, lang=resolved_lang, fast=True)
        ai_risk = _clamp(float(ai.get("score", 0.0)))
        wm_risk = _clamp(float(wm.get("risk_score", 0.0)))
        combined = max(ai_risk, wm_risk)
        if combined >= block_threshold:
            gate = "block"
        elif combined >= review_threshold:
            gate = "review"
        else:
            gate = "publish"
        gate_counts[gate] += 1
        rows.append({
            "id": entry["id"],
            "ai_risk": round(ai_risk, 4),
            "watermark_risk": round(wm_risk, 4),
            "combined_risk": round(combined, 4),
            "quality_grade": quality["grade"],
            "gate": gate,
        })

    return {
        "schema_version": "text-humanize.content_plan_risk.v1",
        "total": len(rows),
        "gate_counts": gate_counts,
        "block_threshold": block_threshold,
        "review_threshold": review_threshold,
        "rows": rows,
    }


# ─────────────────────────────────────────────────────────────
#  Brand voice lock
# ─────────────────────────────────────────────────────────────

def make_brand_voice(
    name: str,
    *,
    locked_terms: list[str] | None = None,
    banned_replacements: dict[str, str] | None = None,
    tone: str | None = None,
    profile: str = "marketing",
) -> dict[str, Any]:
    """Create a reusable brand-voice profile.

    ``locked_terms`` are always preserved verbatim; ``banned_replacements`` maps
    forbidden substitutions to the term that must be kept; ``tone`` maps to a
    ``target_style`` preset.
    """
    return {
        "schema_version": "text-humanize.brand_voice.v1",
        "name": name,
        "locked_terms": list(locked_terms or []),
        "banned_replacements": dict(banned_replacements or {}),
        "tone": tone,
        "profile": profile,
    }


def brand_voice_lock(
    text: str,
    brand: dict[str, Any],
    lang: str = "auto",
    *,
    intensity: int = 60,
    seed: int | None = None,
) -> dict[str, Any]:
    """Humanize text while locking a brand's important terms.

    Locked terms are forced into both ``brand_terms`` preservation and
    ``keep_keywords``; the result is verified so any term that was present in
    the input is still present in the output.
    """
    from texthumanize.core import humanize

    locked = [str(term) for term in brand.get("locked_terms", []) if str(term).strip()]
    profile = str(brand.get("profile", "marketing"))
    tone = brand.get("tone")

    result = humanize(
        text,
        lang=lang,
        profile=profile,
        intensity=intensity,
        seed=seed,
        target_style=tone,
        preserve={"brand_terms": locked},
        constraints={"keep_keywords": locked},
    )

    violations = [
        term for term in locked
        if term in text and term not in result.text
    ]
    return {
        "schema_version": "text-humanize.brand_voice_lock.v1",
        "brand": brand.get("name"),
        "lang": result.lang,
        "text": result.text,
        "locked_terms": locked,
        "violations": violations,
        "locked_intact": not violations,
        "change_ratio": round(result.change_ratio, 4),
    }


# ─────────────────────────────────────────────────────────────
#  Client report (HTML)
# ─────────────────────────────────────────────────────────────

def client_report_html(
    text: str,
    lang: str = "auto",
    *,
    original: str | None = None,
    title: str = "Content Quality Report",
) -> str:
    """Return a neutral, print-ready HTML client report.

    Combines the quality score, AI/watermark risk and (optional) before/after
    text. The wording is deliberately neutral and never promises detector
    bypass.
    """
    from texthumanize.core import audit_report, quality_score_report

    audit = audit_report(text, lang=lang)
    resolved_lang = str(audit.get("lang") or lang)
    quality = quality_score_report(text, original=original, lang=resolved_lang, fast=True)
    esc = _html.escape

    dim_rows = "".join(
        f"<tr><td>{esc(str(dim.get('label', key)))}</td>"
        f"<td>{float(dim.get('value', 0.0)) * 100:.0f}/100</td></tr>"
        for key, dim in quality.get("dimensions", {}).items()
    )
    rec_rows = "".join(f"<li>{esc(str(r))}</li>" for r in quality.get("recommendations", [])[:6])
    before_after = ""
    if original is not None:
        before_after = f"""<h2>Before / After</h2>
<div class="thz-cols"><div><h3>Original</h3><p>{esc(original)}</p></div>
<div><h3>Revised</h3><p>{esc(text)}</p></div></div>"""

    ai_risk = _clamp(float(audit.get("ai", {}).get("score", 0.0)))
    wm_risk = _clamp(float(audit.get("watermark", {}).get("risk_score", 0.0)))

    return f"""<!DOCTYPE html>
<html lang="{esc(resolved_lang)}"><head><meta charset="utf-8">
<title>{esc(title)}</title>
<style>
body{{font-family:system-ui,Arial,sans-serif;color:#1b1f24;max-width:820px;margin:32px auto;padding:0 20px}}
h1{{font-size:24px}}h2{{font-size:18px;margin-top:28px}}
.thz-score{{font-size:40px;font-weight:700}}
table{{border-collapse:collapse;width:100%;margin-top:8px}}
td,th{{border:1px solid #e2e6ea;padding:6px 10px;text-align:left;font-size:14px}}
.thz-cols{{display:flex;gap:20px}}.thz-cols>div{{flex:1}}
.thz-note{{color:#6c757d;font-size:12px;margin-top:28px;border-top:1px solid #eee;padding-top:12px}}
</style></head><body>
<h1>{esc(title)}</h1>
<p class="thz-score">{quality["grade"]} &middot; {quality["score_100"]:.0f}/100</p>
<p>Overall quality verdict: <strong>{esc(quality["verdict"])}</strong>.</p>
<h2>Risk signals</h2>
<table><tr><th>Signal</th><th>Level</th></tr>
<tr><td>AI-pattern risk</td><td>{ai_risk * 100:.0f}% ({_risk_band(ai_risk)})</td></tr>
<tr><td>Watermark risk</td><td>{wm_risk * 100:.0f}% ({_risk_band(wm_risk)})</td></tr></table>
<h2>Quality dimensions</h2>
<table><tr><th>Dimension</th><th>Score</th></tr>{dim_rows}</table>
<h2>Recommendations</h2><ul>{rec_rows}</ul>
{before_after}
<p class="thz-note">{esc(_DISCLAIMER)}</p>
</body></html>"""
