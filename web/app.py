"""TextHumanize — Streamlit-Weboberfläche.

Start:
    streamlit run web/app.py

Oder über die CLI:
    python -m texthumanize web
"""
from __future__ import annotations

import sys
import os
import time

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

from ui_rendering import (
    format_change_description,
    render_ai_highlight_html,
    render_inline_diff_html,
)

st.set_page_config(
    page_title="TextHumanize",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0.5rem; }
    .sub-header  { color: #888; margin-bottom: 1.5rem; }
    .metric-card {
        background: #f8f9fa; border-radius: 8px; padding: 1rem;
        text-align: center; border: 1px solid #e0e0e0;
    }
    .metric-value { font-size: 1.8rem; font-weight: 700; }
    .metric-label { font-size: 0.85rem; color: #666; }
    .score-high   { color: #e53e3e; }
    .score-medium { color: #d69e2e; }
    .score-low    { color: #38a169; }
    .review-box {
        background: #f8f9fa; border: 1px solid #d0d7de;
        border-radius: 8px; padding: 1rem; max-height: 360px;
        overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere;
        font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        font-size: 0.92rem; line-height: 1.65;
    }
    .diff-review del, .diff-delete {
        background: #ffe2e0; color: #8a1f17; text-decoration: line-through;
        border-radius: 3px; padding: 0.05rem 0.12rem;
    }
    .diff-review ins, .diff-insert {
        background: #d9fbe4; color: #126b34; text-decoration: none;
        border-radius: 3px; padding: 0.05rem 0.12rem;
    }
    .ai-legend { display: flex; gap: .75rem; flex-wrap: wrap; margin: .25rem 0 .6rem; color: #666; font-size: .9rem; }
    .legend-swatch { display: inline-block; width: .9rem; height: .9rem; border-radius: 3px; margin-right: .25rem; vertical-align: -0.12rem; border: 1px solid rgba(0,0,0,.08); }
    .legend-sentence { background: #fff3cd; }
    .legend-marker { background: #ffc9c4; }
    .ai-review { font-family: inherit; }
    .ai-highlight { border-radius: 3px; padding: 0.04rem 0.1rem; }
    .ai-highlight-sentence { background: #fff3cd; color: inherit; }
    .ai-highlight-marker { background: #ffc9c4; color: #7f1d1d; box-shadow: inset 0 -2px 0 rgba(185, 28, 28, .35); }
    .ai-highlight-high { background: #ffc9c4; }
    .ai-highlight-medium { background: #ffe8a3; }
    .ai-highlight-low { background: #fff3cd; }
    div[data-testid="stTextArea"] textarea { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)


# ── Imports ──────────────────────────────────────────────
@st.cache_resource
def load_texthumanize():
    """Lazy-load TextHumanize to avoid import overhead on every rerun."""
    import texthumanize as th
    from texthumanize.lang import LANGUAGES
    return th, LANGUAGES


th, LANGUAGES = load_texthumanize()

PROFILE_PRESETS = {
    "Literatur / Prosa": {
        "profile": "prose",
        "corpus_profile": "editorial",
    },
    "Web / Artikel": {"profile": "web"},
    "Chat / Dialog": {"profile": "chat"},
    "SEO / Keywords": {"profile": "seo"},
    "Dokumentation": {"profile": "docs"},
    "Formell": {"profile": "formal"},
    "Akademisch": {"profile": "academic"},
    "Marketing": {"profile": "marketing"},
    "Social Media": {"profile": "social"},
    "E-Mail": {"profile": "email"},
}

# ── Sidebar ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Einstellungen")

    LANG_NAMES = {
        "auto": "🌐 Automatisch erkennen",
        "en": "🇬🇧 Englisch", "ru": "🇷🇺 Russisch", "uk": "🇺🇦 Ukrainisch",
        "de": "🇩🇪 Deutsch", "fr": "🇫🇷 Französisch", "es": "🇪🇸 Spanisch",
        "it": "🇮🇹 Italiano", "pl": "🇵🇱 Polski", "pt": "🇵🇹 Português",
        "nl": "🇳🇱 Nederlands", "sv": "🇸🇪 Svenska", "cs": "🇨🇿 Čeština",
        "ro": "🇷🇴 Română", "hu": "🇭🇺 Magyar", "da": "🇩🇰 Dansk",
        "ar": "🇸🇦 العربية", "zh": "🇨🇳 中文", "ja": "🇯🇵 日本語",
        "ko": "🇰🇷 한국어", "tr": "🇹🇷 Türkçe",
        "hi": "🇮🇳 हिन्दी", "vi": "🇻🇳 Tiếng Việt", "th": "🇹🇭 ไทย",
        "id": "🇮🇩 Bahasa Indonesia", "he": "🇮🇱 עברית",
    }
    lang_options = ["auto"] + sorted(LANGUAGES.keys())
    lang = st.selectbox(
        "Textsprache",
        lang_options,
        index=lang_options.index("de") if "de" in lang_options else 0,
        format_func=lambda x: LANG_NAMES.get(x, x.upper()),
    )

    st.markdown("---")

    mode = st.radio(
        "Modus",
        ["🔍 AI-Erkennung", "✍️ Humanisierung", "🛡️ PHANTOM™", "⚡ ASH™"],
        index=1,
    )

    with st.expander("ℹ️ Modus kurz erklärt"):
        st.markdown(
            "- **AI-Erkennung** analysiert nur, verändert den Text nicht.\n"
            "- **Humanisierung** nutzt die normale Pipeline für natürlichere Sprache.\n"
            "- **PHANTOM™** optimiert stärker gegen den internen AI-Score.\n"
            "- **ASH™** passt statistische Signatur und Rhythmus an; experimenteller und stärker."
        )

    if mode in ["✍️ Humanisierung", "🛡️ PHANTOM™", "⚡ ASH™"]:
        intensity = st.slider("Intensität", 10, 100, 45, step=5)
        profile_label = st.selectbox(
            "Profil",
            list(PROFILE_PRESETS.keys()),
            index=0,
        )
        profile_config = PROFILE_PRESETS[profile_label]
        profile = profile_config["profile"]
        target_style = profile_config.get("target_style")
        corpus_profile = profile_config.get("corpus_profile")
    else:
        intensity = 60
        profile_label = "Web / Artikel"
        profile = "web"
        target_style = None
        corpus_profile = None

    st.markdown("---")
    st.markdown("### 📊 Über das Projekt")
    st.markdown(f"**TextHumanize v{th.__version__}**")
    st.markdown(f"Sprachen: **{len(LANGUAGES)}**")
    st.markdown("Pipeline: **22 Stufen**")
    st.markdown("MLP: **50.433 Parameter**")

# ── Main Area ────────────────────────────────────────────
st.markdown('<div class="main-header">✍️ TextHumanize</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Text → natürlicher Text. Lokal, ohne API.</div>', unsafe_allow_html=True)

# Input
text = st.text_area(
    "Text zur Verarbeitung einfügen:",
    height=200,
    placeholder="Künstliche Intelligenz hat zahlreiche Branchen nachhaltig verändert...",
)

# Action button
col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 4])
with col_btn1:
    run_btn = st.button("🚀 Starten", type="primary", use_container_width=True)
with col_btn2:
    clear_btn = st.button("🗑️ Leeren", use_container_width=True)

if clear_btn:
    st.rerun()

if run_btn and text.strip():
    effective_lang = lang if lang != "auto" else "auto"

    # ── Detection Mode ──
    if mode == "🔍 AI-Erkennung":
        with st.spinner("Text wird analysiert..."):
            t0 = time.perf_counter()
            result = th.detect_ai_explain(text, lang=effective_lang)
            elapsed = time.perf_counter() - t0

        raw_detection = result.get("raw_detection", {}) or {}
        score = result.get("score", raw_detection.get("combined_score", 0))
        verdict = result.get("verdict", "unknown")
        confidence = result.get("confidence", 0)

        # Score display
        score_class = "score-high" if score > 0.55 else ("score-medium" if score > 0.34 else "score-low")
        verdict_emoji = "🤖" if verdict == "ai" else ("🔀" if verdict == "mixed" else "👤")

        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value {score_class}">{score:.0%}</div>
                <div class="metric-label">AI-Wahrscheinlichkeit</div>
            </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{verdict_emoji} {verdict}</div>
                <div class="metric-label">Einschätzung</div>
            </div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{confidence:.0%}</div>
                <div class="metric-label">Konfidenz</div>
            </div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="metric-card">
                <div class="metric-value">{elapsed*1000:.0f} ms</div>
                <div class="metric-label">Zeit</div>
            </div>""", unsafe_allow_html=True)

        # Detailed metrics
        metrics = result.get("metrics", {}) or raw_detection.get("metrics", {})
        if metrics:
            st.markdown("### 📊 Detailmetriken")
            metrics_data = {
                "Entropie": metrics.get("entropy", 0),
                "Burstiness": metrics.get("burstiness", 0),
                "Lexik": metrics.get("vocabulary", 0),
                "Zipf": metrics.get("zipf", 0),
                "Stilometrie": metrics.get("stylometry", 0),
                "AI-Muster": metrics.get("ai_patterns", 0),
                "Interpunktion": metrics.get("punctuation", 0),
                "Kohärenz": metrics.get("coherence", 0),
                "Grammatik": metrics.get("grammar_perfection", 0),
                "Satzanfänge": metrics.get("opening_diversity", 0),
                "Lesbarkeit": metrics.get("readability_consistency", 0),
                "Rhythmus": metrics.get("rhythm", 0),
            }

            cols = st.columns(4)
            for i, (name, val) in enumerate(metrics_data.items()):
                with cols[i % 4]:
                    bar_color = "#e53e3e" if val > 0.55 else ("#d69e2e" if val > 0.35 else "#38a169")
                    st.markdown(f"**{name}**: {val:.0%}")
                    st.progress(val)

        # Component scores
        highlighted_spans = result.get("highlighted_spans", [])
        st.markdown("### 🖍️ Markierter Text")
        st.markdown(
            '<div class="ai-legend">'
            '<span><span class="legend-swatch legend-sentence"></span>Auffälliger Satz</span>'
            '<span><span class="legend-swatch legend-marker"></span>Konkreter AI-Marker</span>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            render_ai_highlight_html(text, highlighted_spans),
            unsafe_allow_html=True,
        )

        heuristic = raw_detection.get("heuristic_score", 0)
        stat = raw_detection.get("stat_probability")
        neural = raw_detection.get("neural_probability")
        st.markdown("### 🧠 Ensemble-Komponenten")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Heuristik", f"{heuristic:.0%}")
        with c2:
            st.metric("Statistik", f"{stat:.0%}" if stat is not None else "N/A")
        with c3:
            st.metric("Neuronales Netz (MLP)", f"{neural:.0%}" if neural is not None else "N/A")

    # ── Humanization Mode ──
    elif mode == "✍️ Humanisierung":
        with st.spinner("Text wird humanisiert..."):
            t0 = time.perf_counter()
            result = th.humanize(
                text,
                lang=effective_lang,
                intensity=intensity,
                profile=profile,
                target_style=target_style,
            )
            elapsed = time.perf_counter() - t0

        st.markdown("---")

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Änderung", f"{result.change_ratio:.0%}")
        with col2:
            st.metric("Qualität", f"{result.quality_score:.0%}")
        with col3:
            st.metric("Sprache", result.lang.upper())
        with col4:
            st.metric("Zeit", f"{elapsed:.1f}s")

        # Result text
        st.markdown("### 📝 Ergebnis")
        st.text_area("Verarbeiteter Text:", value=result.text, height=200)

        st.markdown("### 🧾 Änderungsansicht")
        st.markdown(
            render_inline_diff_html(result.original, result.text),
            unsafe_allow_html=True,
        )

        # AI score before/after
        ai_before = result.metrics_before.get("artificiality_score", 0)
        ai_after = result.metrics_after.get("artificiality_score", 0)
        st.markdown("### 📉 AI Score")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Vorher", f"{ai_before:.0f}%")
        with c2:
            st.metric("Nachher", f"{ai_after:.0f}%")
        with c3:
            drop = ai_before - ai_after
            st.metric("Senkung", f"−{drop:.0f}%", delta=f"-{drop:.0f}%")

        # Changes log
        if result.changes:
            with st.expander(f"📋 Änderungsprotokoll ({len(result.changes)} Schritte)"):
                for change in result.changes[:50]:
                    desc = format_change_description(change)
                    st.markdown(f"- {desc}")

    # ── PHANTOM™ Mode ──
    elif mode == "🛡️ PHANTOM™":
        with st.spinner("PHANTOM™ verarbeitet den Text..."):
            t0 = time.perf_counter()
            result = th.humanize(
                text,
                lang=effective_lang,
                intensity=intensity,
                profile=profile,
                target_style=target_style,
                phantom=True,
                phantom_budget=intensity / 100,
                phantom_target=0.30,
            )
            elapsed = time.perf_counter() - t0

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sprache", result.lang.upper())
        with col2:
            phantom_steps = sum(
                1 for change in result.changes
                if str(change.get("type", "")).lower() == "phantom"
            )
            st.metric("PHANTOM-Schritte", str(phantom_steps))
        with col3:
            st.metric("Zeit", f"{elapsed:.1f}s")

        st.markdown("### 📝 PHANTOM™-Ergebnis")
        st.text_area("Verarbeiteter Text:", value=result.text, height=200)

        st.markdown("### 🧾 Änderungsansicht")
        st.markdown(
            render_inline_diff_html(result.original, result.text),
            unsafe_allow_html=True,
        )

        # Detection before/after
        with st.spinner("Erkennung wird geprüft..."):
            det_before = th.detect_ai(text, lang=effective_lang)
            det_after = th.detect_ai(result.text, lang=effective_lang)
        score_before = det_before.get("combined_score", 0)
        score_after = det_after.get("combined_score", 0)
        drop = (score_before - score_after) * 100

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("AI vorher", f"{score_before:.0%}")
        with c2:
            st.metric("AI nachher", f"{score_after:.0%}")
        with c3:
            st.metric("Senkung", f"−{drop:.0f}%", delta=f"-{drop:.0f}%")

    # ── ASH™ Mode ──
    elif mode == "⚡ ASH™":
        with st.spinner("ASH™ verarbeitet den Text..."):
            t0 = time.perf_counter()
            result = th.ash_humanize(
                text,
                lang=effective_lang,
                intensity=intensity / 100,
                pipeline_intensity=intensity,
                pipeline_profile=profile,
                corpus_profile=corpus_profile,
            )
            elapsed = time.perf_counter() - t0

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sprache", result.lang.upper())
        with col2:
            n_ops = len(result.changes) if hasattr(result, 'changes') else 0
            st.metric("Änderungen", str(n_ops))
        with col3:
            st.metric("Zeit", f"{elapsed:.1f}s")

        st.markdown("### 📝 ASH™-Ergebnis")
        st.text_area("Verarbeiteter Text:", value=result.text, height=200)

        st.markdown("### 🧾 Änderungsansicht")
        st.markdown(
            render_inline_diff_html(getattr(result, "original", text), result.text),
            unsafe_allow_html=True,
        )

        # Detection
        with st.spinner("Erkennung wird geprüft..."):
            det_before = th.detect_ai(text, lang=effective_lang)
            det_after = th.detect_ai(result.text, lang=effective_lang)
        score_before = det_before.get("combined_score", 0)
        score_after = det_after.get("combined_score", 0)
        drop = (score_before - score_after) * 100

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("AI vorher", f"{score_before:.0%}")
        with c2:
            st.metric("AI nachher", f"{score_after:.0%}")
        with c3:
            st.metric("Senkung", f"−{drop:.0f}%", delta=f"-{drop:.0f}%")

elif run_btn:
    st.warning("⚠️ Bitte füge einen Text zur Verarbeitung ein.")

# ── Footer ───────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: #aaa; font-size: 0.85rem;'>"
    f"TextHumanize v{th.__version__} • {len(LANGUAGES)} Sprachen • "
    f"<a href='https://github.com/TextHumanize' style='color: #888;'>GitHub</a>"
    f"</div>",
    unsafe_allow_html=True,
)
