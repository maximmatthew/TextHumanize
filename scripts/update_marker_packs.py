#!/usr/bin/env python3
"""Build manual review tables for AI marker pack updates.

The default mode is intentionally non-mutating: it scans a licensed eval corpus,
extracts AI-marker candidates using existing marker dictionaries, and writes a
Markdown review table plus optional JSON candidate data. Pack updates happen
only when a reviewer edits the table and marks rows as approved.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PACK = ROOT / "texthumanize" / "data" / "contributor_ai_markers_v1.json"
AI_LABELS = {"raw_ai", "lightly_edited_ai"}
APPROVED_DECISIONS = {"approved", "approve", "yes", "y", "accept"}
REVIEW_COLUMNS = (
    "decision",
    "marker",
    "lang",
    "category",
    "severity",
    "domains",
    "labels",
    "sample_ids",
    "count",
    "suggested_actions",
    "notes",
)


@dataclass
class MarkerCandidate:
    """Candidate AI marker found in one or more corpus samples."""

    marker: str
    lang: str
    category: str
    severity: str
    domains: set[str] = field(default_factory=set)
    labels: set[str] = field(default_factory=set)
    sample_ids: set[str] = field(default_factory=set)
    count: int = 0
    suggested_actions: tuple[str, ...] = ()

    def key(self) -> tuple[str, str, str]:
        return (self.lang, self.category, self.marker.casefold())

    def to_dict(self) -> dict[str, Any]:
        return {
            "marker": self.marker,
            "lang": self.lang,
            "category": self.category,
            "severity": self.severity,
            "domains": sorted(self.domains),
            "labels": sorted(self.labels),
            "sample_ids": sorted(self.sample_ids),
            "count": self.count,
            "suggested_actions": list(self.suggested_actions),
        }


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def load_corpus(path: Path | None = None) -> list[dict[str, Any]]:
    """Load samples from a corpus file or the packaged eval corpus."""
    if path is None:
        from texthumanize.benchmarks import load_eval_corpus

        samples = load_eval_corpus()
        if not isinstance(samples, list):
            raise ValueError("Expected packaged eval corpus to return sample list")
        return samples

    data = _load_json(path)
    samples = data.get("samples")
    if not isinstance(samples, list):
        raise ValueError(f"{path} must contain a samples array")
    return [dict(sample) for sample in samples]


def load_marker_pack(path: Path = DEFAULT_PACK) -> dict[str, Any]:
    """Load a contributor AI marker pack from disk."""
    data = _load_json(path)
    if data.get("pack") != "ai_markers" or not isinstance(data.get("entries"), list):
        raise ValueError(f"{path} is not an ai_markers contributor pack")
    return data


def _parse_csv_filter(value: str | None) -> set[str]:
    if not value:
        return set()
    return {part.strip() for part in value.split(",") if part.strip()}


def _severity_for_category(category: str) -> str:
    if category in {"phrases", "connectors"}:
        return "medium"
    if category in {"adverbs", "adjectives", "verbs"}:
        return "low"
    return "medium"


def _actions_for_category(category: str) -> tuple[str, ...]:
    if category == "connectors":
        return (
            "remove redundant transition",
            "replace with a concrete sentence start",
        )
    if category == "phrases":
        return (
            "replace formulaic phrase with a specific claim",
            "add source detail or concrete next step",
        )
    if category == "verbs":
        return (
            "replace formal verb with a simpler verb when meaning is preserved",
            "keep technical usage when it is domain-specific",
        )
    if category in {"adverbs", "adjectives"}:
        return (
            "replace generic modifier with a measurable detail",
            "delete if it does not change the meaning",
        )
    return ("manual reviewer should define safe action",)


def _contains_marker(text: str, marker: str) -> bool:
    normalized_text = text.casefold()
    normalized_marker = marker.casefold()
    if " " in normalized_marker or "-" in normalized_marker:
        return normalized_marker in normalized_text
    pattern = rf"(?<![\w'-]){re.escape(normalized_marker)}(?![\w'-])"
    return re.search(pattern, normalized_text, flags=re.UNICODE) is not None


def _existing_marker_keys(pack: dict[str, Any]) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for entry in pack.get("entries", []):
        if isinstance(entry, dict) and entry.get("lang") and entry.get("marker"):
            keys.add((str(entry["lang"]), str(entry["marker"]).casefold()))
    return keys


def build_marker_candidates(
    samples: Iterable[dict[str, Any]],
    *,
    pack: dict[str, Any],
    languages: set[str] | None = None,
    domains: set[str] | None = None,
    labels: set[str] | None = None,
    max_candidates: int = 100,
) -> list[MarkerCandidate]:
    """Extract reviewable AI marker candidates from corpus samples."""
    from texthumanize.ai_markers import load_ai_markers

    wanted_languages = languages or set()
    wanted_domains = domains or set()
    wanted_labels = labels or AI_LABELS
    existing = _existing_marker_keys(pack)
    candidates: dict[tuple[str, str, str], MarkerCandidate] = {}

    for sample in samples:
        lang = str(sample.get("lang", ""))
        label = str(sample.get("label", ""))
        domain = str(sample.get("domain", "general"))
        text = str(sample.get("text", ""))
        sample_id = str(sample.get("id", "unknown"))
        if not text or label not in wanted_labels:
            continue
        if wanted_languages and lang not in wanted_languages:
            continue
        if wanted_domains and domain not in wanted_domains:
            continue

        markers_by_category = load_ai_markers(lang)
        for category, markers in markers_by_category.items():
            for marker in sorted(markers):
                if (lang, marker.casefold()) in existing:
                    continue
                if not _contains_marker(text, marker):
                    continue

                severity = _severity_for_category(category)
                candidate = MarkerCandidate(
                    marker=marker,
                    lang=lang,
                    category=category,
                    severity=severity,
                    suggested_actions=_actions_for_category(category),
                )
                key = candidate.key()
                current = candidates.setdefault(key, candidate)
                current.domains.add(domain)
                current.labels.add(label)
                current.sample_ids.add(sample_id)
                current.count += 1

    ranked = sorted(
        candidates.values(),
        key=lambda item: (
            -item.count,
            item.lang,
            item.category,
            item.marker.casefold(),
        ),
    )
    return ranked[:max_candidates]


def _escape_cell(value: object) -> str:
    text = str(value)
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def render_review_table(candidates: Sequence[MarkerCandidate]) -> str:
    """Render a Markdown review table for manual approval."""
    lines = [
        "# AI Marker Pack Review",
        "",
        "Set `decision` to `approved` for rows that should be merged into "
        "`contributor_ai_markers_v1.json`. Leave all other rows unchanged.",
        "",
        "|" + "|".join(REVIEW_COLUMNS) + "|",
        "|" + "|".join("---" for _ in REVIEW_COLUMNS) + "|",
    ]
    for candidate in candidates:
        row = {
            "decision": "TODO",
            "marker": candidate.marker,
            "lang": candidate.lang,
            "category": candidate.category,
            "severity": candidate.severity,
            "domains": ", ".join(sorted(candidate.domains)),
            "labels": ", ".join(sorted(candidate.labels)),
            "sample_ids": ", ".join(sorted(candidate.sample_ids)),
            "count": candidate.count,
            "suggested_actions": "<br>".join(candidate.suggested_actions),
            "notes": "",
        }
        lines.append("|" + "|".join(_escape_cell(row[col]) for col in REVIEW_COLUMNS) + "|")
    lines.append("")
    return "\n".join(lines)


def _split_review_row(line: str) -> list[str]:
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for ch in line.strip():
        if escaped:
            current.append(ch)
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == "|":
            cells.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    cells.append("".join(current).strip())
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return cells


def read_approved_review_rows(path: Path) -> list[dict[str, str]]:
    """Read approved rows from a generated Markdown review table."""
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = _split_review_row(line)
        if not cells:
            continue
        if cells == list(REVIEW_COLUMNS):
            header = cells
            continue
        if cells[0].replace("-", "").strip() == "" or header is None:
            continue
        if len(cells) != len(header):
            continue
        row = dict(zip(header, cells))
        if row["decision"].strip().casefold() in APPROVED_DECISIONS:
            rows.append(row)
    return rows


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return slug[:48] or "marker"


def _next_entry_id(pack: dict[str, Any], lang: str, domain: str, marker: str) -> str:
    existing = {
        str(entry.get("id", ""))
        for entry in pack.get("entries", [])
        if isinstance(entry, dict)
    }
    base = f"ai_marker_{lang}_{domain}_{_slug(marker)}"
    if base not in existing:
        return base
    index = 2
    while f"{base}_{index}" in existing:
        index += 1
    return f"{base}_{index}"


def apply_reviewed_rows(review_path: Path, pack_path: Path = DEFAULT_PACK) -> dict[str, Any]:
    """Merge approved review rows into an AI marker contributor pack."""
    pack = load_marker_pack(pack_path)
    entries = pack["entries"]
    existing = _existing_marker_keys(pack)
    added = 0
    skipped = 0

    for row in read_approved_review_rows(review_path):
        lang = row["lang"]
        marker = row["marker"]
        if (lang, marker.casefold()) in existing:
            skipped += 1
            continue
        domains = [part.strip() for part in row["domains"].split(",") if part.strip()]
        domain = domains[0] if domains else "general"
        actions = [
            part.strip()
            for part in row["suggested_actions"].split("<br>")
            if part.strip()
        ] or ["review and add a safe replacement action"]
        entry = {
            "id": _next_entry_id(pack, lang, domain, marker),
            "lang": lang,
            "domain": domain,
            "category": row["category"] or "manual_review",
            "marker": marker,
            "severity": row["severity"] or "medium",
            "suggested_actions": actions,
            "false_positive_guards": [
                row["notes"] or "manual review required before runtime promotion"
            ],
            "source": "manual-review-from-eval-corpus",
            "license": "CC0-1.0",
        }
        entries.append(entry)
        existing.add((lang, marker.casefold()))
        added += 1

    pack["entries"] = entries
    pack["entry_count"] = len(entries)
    pack_path.write_text(
        json.dumps(pack, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"added": added, "skipped": skipped, "total_entries": len(entries)}


def write_review_files(
    *,
    corpus_path: Path | None,
    pack_path: Path,
    review_out: Path,
    candidates_out: Path | None,
    languages: set[str],
    domains: set[str],
    labels: set[str],
    max_candidates: int,
) -> dict[str, Any]:
    """Generate review files and return a summary."""
    samples = load_corpus(corpus_path)
    pack = load_marker_pack(pack_path)
    candidates = build_marker_candidates(
        samples,
        pack=pack,
        languages=languages,
        domains=domains,
        labels=labels or AI_LABELS,
        max_candidates=max_candidates,
    )
    review_out.parent.mkdir(parents=True, exist_ok=True)
    review_out.write_text(render_review_table(candidates), encoding="utf-8")

    if candidates_out is not None:
        candidates_out.parent.mkdir(parents=True, exist_ok=True)
        candidates_out.write_text(
            json.dumps(
                {
                    "schema_version": "text-humanize.marker_review_candidates.v1",
                    "candidate_count": len(candidates),
                    "candidates": [candidate.to_dict() for candidate in candidates],
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

    return {
        "review_out": str(review_out),
        "candidates_out": str(candidates_out) if candidates_out else None,
        "candidate_count": len(candidates),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate and apply manual AI-marker pack review tables.",
    )
    parser.add_argument("--corpus", type=Path, help="Corpus JSON with samples array.")
    parser.add_argument(
        "--pack",
        type=Path,
        default=DEFAULT_PACK,
        help="Contributor AI marker pack path.",
    )
    parser.add_argument(
        "--review-out",
        type=Path,
        default=ROOT / "marker_pack_review.md",
        help="Markdown review table output path.",
    )
    parser.add_argument(
        "--candidates-out",
        type=Path,
        help="Optional JSON candidate output path.",
    )
    parser.add_argument("--langs", help="Comma-separated language filter.")
    parser.add_argument("--domains", help="Comma-separated domain filter.")
    parser.add_argument(
        "--labels",
        default="raw_ai,lightly_edited_ai",
        help="Comma-separated corpus labels to scan.",
    )
    parser.add_argument("--max-candidates", type=int, default=100)
    parser.add_argument(
        "--apply-reviewed",
        type=Path,
        help="Apply approved rows from a generated Markdown review table.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_candidates <= 0:
        parser.error("--max-candidates must be positive")

    if args.apply_reviewed:
        summary = apply_reviewed_rows(args.apply_reviewed, args.pack)
    else:
        summary = write_review_files(
            corpus_path=args.corpus,
            pack_path=args.pack,
            review_out=args.review_out,
            candidates_out=args.candidates_out,
            languages=_parse_csv_filter(args.langs),
            domains=_parse_csv_filter(args.domains),
            labels=_parse_csv_filter(args.labels),
            max_candidates=args.max_candidates,
        )
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
