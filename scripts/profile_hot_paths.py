#!/usr/bin/env python3
"""Profile TextHumanize hot paths on deterministic text sizes.

The script is intentionally dependency-free so it can run in release smoke
checks and on CI workers without pulling benchmark-only packages.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import platform
import statistics
import sys
import time
import tracemalloc
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


DEFAULT_SIZES = (1_000, 10_000, 100_000)
DEFAULT_OPERATIONS = ("detect_ai", "watermark_report", "analyze")
AVAILABLE_OPERATIONS = (
    "detect_ai",
    "detect_ai_fast",
    "watermark_report",
    "analyze",
    "humanize",
    "humanize_chunked",
)

_BASE_SENTENCES = (
    "Artificial intelligence tools can accelerate drafting, but production teams still need "
    "clear checks for tone, factual consistency, and semantic preservation.",
    "A practical humanization workflow keeps dates, prices, identifiers, quotes, and named "
    "entities stable while improving rhythm and reducing repetitive assistant-like phrasing.",
    "Detector scores should be treated as directional quality signals because external models "
    "change over time and may disagree on short or highly formal samples.",
    "For long-form content, the most expensive paths usually combine language detection, "
    "sentence analysis, watermark forensics, and multi-stage text restructuring.",
    "Release benchmarks should record the exact version, runtime, hardware, warm-up policy, "
    "input size, iteration count, and the command used to reproduce the measurement.",
)


Operation = Callable[[str, str], Any]


def build_sample_text(size_chars: int) -> str:
    """Return a deterministic AI-like sample with exactly *size_chars* characters."""
    if size_chars <= 0:
        raise ValueError("size_chars must be positive")

    chunks: list[str] = []
    idx = 0
    current_size = 0
    while current_size < size_chars:
        sentence = _BASE_SENTENCES[idx % len(_BASE_SENTENCES)]
        separator = "\n\n" if idx and idx % len(_BASE_SENTENCES) == 0 else " "
        chunk = sentence if not chunks else separator + sentence
        chunks.append(chunk)
        current_size += len(chunk)
        idx += 1
    return "".join(chunks)[:size_chars]


def percentile(values: Sequence[float], pct: float) -> float:
    """Return an interpolated percentile for *values*."""
    if not values:
        raise ValueError("percentile requires at least one value")
    if pct <= 0:
        return min(values)
    if pct >= 100:
        return max(values)

    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    lower_weight = upper - rank
    upper_weight = rank - lower
    return ordered[lower] * lower_weight + ordered[upper] * upper_weight


def parse_sizes(value: str) -> tuple[int, ...]:
    """Parse a comma-separated size list."""
    try:
        sizes = tuple(int(part.strip().replace("_", "")) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers") from exc
    if not sizes or any(size <= 0 for size in sizes):
        raise argparse.ArgumentTypeError("sizes must contain positive integers")
    return sizes


def parse_operations(value: str) -> tuple[str, ...]:
    """Parse operation names, expanding the `all` alias."""
    names = tuple(part.strip() for part in value.split(",") if part.strip())
    if names == ("all",):
        return AVAILABLE_OPERATIONS
    unknown = sorted(set(names) - set(AVAILABLE_OPERATIONS))
    if unknown:
        allowed = ", ".join((*AVAILABLE_OPERATIONS, "all"))
        raise argparse.ArgumentTypeError(
            f"unknown operation(s): {', '.join(unknown)}; allowed: {allowed}"
        )
    if not names:
        raise argparse.ArgumentTypeError("at least one operation is required")
    return names


def _clear_internal_caches() -> None:
    """Clear TextHumanize result caches so timed runs execute real work."""
    try:
        from texthumanize.core import result_cache

        result_cache.clear()
    except Exception:
        pass
    gc.collect()


def _operation_runner(name: str) -> Operation:
    import texthumanize as th

    if name == "detect_ai":
        return lambda text, lang: th.detect_ai(text, lang=lang)
    if name == "detect_ai_fast":
        return lambda text, lang: th.detect_ai_fast(text, lang=lang)
    if name == "watermark_report":
        return lambda text, lang: th.watermark_report(text, lang=lang, seed=42)
    if name == "analyze":
        return lambda text, lang: th.analyze(text, lang=lang)
    if name == "humanize":
        return lambda text, lang: th.humanize(text, lang=lang, profile="web", seed=42)
    if name == "humanize_chunked":
        return lambda text, lang: th.humanize_chunked(
            text,
            lang=lang,
            profile="web",
            seed=42,
            chunk_size=5_000,
            overlap=200,
            max_workers=1,
        )
    raise ValueError(f"unsupported operation: {name}")


def _time_operation(runner: Operation, text: str, lang: str) -> float:
    _clear_internal_caches()
    started = time.perf_counter()
    runner(text, lang)
    return time.perf_counter() - started


def _peak_memory_operation(runner: Operation, text: str, lang: str) -> int:
    """Return peak Python allocations for one uncached operation run."""
    _clear_internal_caches()
    was_tracing = tracemalloc.is_tracing()
    if was_tracing:
        tracemalloc.stop()
    tracemalloc.start()
    try:
        runner(text, lang)
        _, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
        if was_tracing:
            tracemalloc.start()
    return peak_bytes


def profile_hot_paths(
    *,
    sizes: Iterable[int] = DEFAULT_SIZES,
    operations: Iterable[str] = DEFAULT_OPERATIONS,
    iterations: int = 5,
    warmups: int = 1,
    lang: str = "en",
    measure_memory: bool = True,
) -> dict[str, Any]:
    """Profile selected operations and return a JSON-serializable report."""
    sizes_tuple = tuple(sizes)
    operations_tuple = tuple(operations)
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if warmups < 0:
        raise ValueError("warmups must be zero or positive")
    if any(size <= 0 for size in sizes_tuple):
        raise ValueError("sizes must be positive")
    if not operations_tuple:
        raise ValueError("operations must not be empty")

    import texthumanize as th

    samples: list[dict[str, Any]] = []
    for operation in operations_tuple:
        runner = _operation_runner(operation)
        for size in sizes_tuple:
            text = build_sample_text(size)
            for _ in range(warmups):
                _clear_internal_caches()
                runner(text, lang)

            timings = [_time_operation(runner, text, lang) for _ in range(iterations)]
            timings_ms = [round(value * 1000, 3) for value in timings]
            p50_ms = percentile(timings_ms, 50)
            p95_ms = percentile(timings_ms, 95)
            mean_ms = statistics.fmean(timings_ms)
            stdev_ms = statistics.pstdev(timings_ms) if len(timings_ms) > 1 else 0.0
            memory_peaks_kb: list[float] = []
            if measure_memory:
                memory_peak_bytes = [
                    _peak_memory_operation(runner, text, lang)
                    for _ in range(iterations)
                ]
                memory_peaks_kb = [
                    round(value / 1024, 3) for value in memory_peak_bytes
                ]
            memory_p50_kb = (
                round(percentile(memory_peaks_kb, 50), 3)
                if memory_peaks_kb
                else None
            )
            memory_p95_kb = (
                round(percentile(memory_peaks_kb, 95), 3)
                if memory_peaks_kb
                else None
            )

            samples.append(
                {
                    "operation": operation,
                    "size_chars": size,
                    "actual_chars": len(text),
                    "lang": lang,
                    "iterations": iterations,
                    "warmups": warmups,
                    "p50_ms": round(p50_ms, 3),
                    "p95_ms": round(p95_ms, 3),
                    "mean_ms": round(mean_ms, 3),
                    "stdev_ms": round(stdev_ms, 3),
                    "min_ms": round(min(timings_ms), 3),
                    "max_ms": round(max(timings_ms), 3),
                    "chars_per_sec_p50": round(size / (p50_ms / 1000), 1)
                    if p50_ms > 0 else None,
                    "tracemalloc_peak_kb_p50": memory_p50_kb,
                    "tracemalloc_peak_kb_p95": memory_p95_kb,
                    "timings_ms": timings_ms,
                    "tracemalloc_peaks_kb": memory_peaks_kb,
                }
            )

    return {
        "schema_version": "text-humanize.hot-path-profile.v1",
        "version": th.__version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "cache_policy": "clear_result_cache_before_each_timed_run",
        "memory_policy": (
            "tracemalloc_peak_during_separate_uncached_runs"
            if measure_memory
            else "disabled"
        ),
        "sizes": list(sizes_tuple),
        "operations": list(operations_tuple),
        "samples": samples,
    }


def _format_table(report: dict[str, Any]) -> str:
    lines = [
        f"TextHumanize {report['version']} hot-path profile",
        f"Cache policy: {report['cache_policy']}",
        f"Memory policy: {report['memory_policy']}",
        "",
        f"{'operation':<18} {'chars':>8} {'p50 ms':>10} {'p95 ms':>10} "
        f"{'chars/s p50':>13} {'peak KB p50':>13}",
        "-" * 81,
    ]
    for sample in report["samples"]:
        cps = sample["chars_per_sec_p50"]
        cps_text = f"{cps:,.0f}" if isinstance(cps, float) else "-"
        memory_p50 = sample["tracemalloc_peak_kb_p50"]
        memory_text = f"{memory_p50:,.1f}" if isinstance(memory_p50, float) else "-"
        lines.append(
            f"{sample['operation']:<18} {sample['actual_chars']:>8,} "
            f"{sample['p50_ms']:>10.3f} {sample['p95_ms']:>10.3f} "
            f"{cps_text:>13} {memory_text:>13}"
        )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Profile TextHumanize hot paths and report p50/p95 latency."
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=DEFAULT_SIZES,
        help="Comma-separated text sizes in characters (default: 1000,10000,100000).",
    )
    parser.add_argument(
        "--operations",
        type=parse_operations,
        default=DEFAULT_OPERATIONS,
        help=(
            "Comma-separated operations. Allowed: "
            f"{', '.join(AVAILABLE_OPERATIONS)} or all. "
            f"Default: {', '.join(DEFAULT_OPERATIONS)}."
        ),
    )
    parser.add_argument("--iterations", type=int, default=5, help="Timed runs per case.")
    parser.add_argument("--warmups", type=int, default=1, help="Warm-up runs per case.")
    parser.add_argument("--lang", default="en", help="Language code for generated samples.")
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable tracemalloc peak memory measurements.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table.")
    parser.add_argument("--output", help="Optional path for the JSON report.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        report = profile_hot_paths(
            sizes=args.sizes,
            operations=args.operations,
            iterations=args.iterations,
            warmups=args.warmups,
            lang=args.lang,
            measure_memory=not args.no_memory,
        )
    except ValueError as exc:
        parser.error(str(exc))

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload + "\n", encoding="utf-8")

    if args.json:
        print(payload)
    else:
        print(_format_table(report))
        if args.output:
            print(f"\nJSON report written to {os.fspath(Path(args.output))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
