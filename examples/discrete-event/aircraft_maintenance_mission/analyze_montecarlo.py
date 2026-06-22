#!/usr/bin/env python3
"""Aggregate mission-summary rows (kind=3) from multiple Monte Carlo run CSVs.

Usage:
  python3 analyze_montecarlo.py /tmp/aircraft-mission-montecarlo-conf
"""

from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path
from typing import Dict, List


def _as_float(value: str) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _quantile(sorted_values: List[float], q: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = q * (len(sorted_values) - 1)
    lo = int(idx)
    hi = min(len(sorted_values) - 1, lo + 1)
    if hi == lo:
        return sorted_values[lo]
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac


def summarize(values: List[float]) -> Dict[str, float]:
    if not values:
        return {
            "n": 0,
            "mean": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p5": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "std": 0.0,
        }
    values = sorted(values)
    n = len(values)
    mean = sum(values) / n
    std = (sum((x - mean) ** 2 for x in values) / n) ** 0.5
    return {
        "n": float(n),
        "mean": mean,
        "min": min(values),
        "max": max(values),
        "p5": _quantile(values, 0.05),
        "p50": _quantile(values, 0.50),
        "p95": _quantile(values, 0.95),
        "std": std,
    }


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/aircraft-mission-montecarlo-conf")
    if not out_dir.exists():
        raise SystemExit(f"output dir not found: {out_dir}")

    run_files = sorted(out_dir.glob("run_*.csv"))
    if not run_files:
        raise SystemExit(f"no run_*.csv found in {out_dir}")

    metric_values: Dict[str, List[float]] = {}
    run_count = 0
    for run_file in run_files:
        with run_file.open() as f:
            rows = list(csv.DictReader(f))
        summary_rows = [r for r in rows if str(r.get("kind")) == "3"]
        if not summary_rows:
            continue
        run_count += 1
        row = summary_rows[0]
        for key, val in row.items():
            if key.startswith("summary_"):
                metric_values.setdefault(key, []).append(_as_float(val))

    print(f"Run summaries loaded: {run_count}/{len(run_files)}")
    if run_count == 0:
        return

    target_keys = [
        "summary_mission_reliability",
        "summary_sortie_rate",
        "summary_success_when_dispatched",
        "summary_parts_level_end",
        "summary_part_shortage_events",
        "summary_part_wait_total",
        "summary_planned_missions",
        "summary_dispatched_missions",
        "summary_successful_missions",
        "summary_failed_missions",
        "summary_canceled_missions",
        "summary_crew_wait_total",
    ]

    for key in target_keys:
        s = summarize(metric_values.get(key, []))
        print(
            f"{key}: n={int(s['n'])}, mean={s['mean']:.4f}, std={s['std']:.4f}, "
            f"p5={s['p5']:.4f}, p50={s['p50']:.4f}, p95={s['p95']:.4f}, "
            f"min={s['min']:.4f}, max={s['max']:.4f}"
        )


if __name__ == "__main__":
    main()
