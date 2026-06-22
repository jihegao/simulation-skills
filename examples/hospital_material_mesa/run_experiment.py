"""Run parameter sweeps for the Hospital Material Handling Mesa model."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from examples.hospital_material_mesa.model import HospitalMaterialHandlingModel


def _expand_parameters(parameters: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    sweep_keys = [key for key, value in parameters.items() if isinstance(value, list)]
    fixed = {key: value for key, value in parameters.items() if key not in sweep_keys}
    if not sweep_keys:
        return [], [fixed]
    combinations: list[dict[str, Any]] = []
    for values in itertools.product(*(parameters[key] for key in sweep_keys)):
        combo = dict(fixed)
        combo.update(dict(zip(sweep_keys, values, strict=True)))
        combinations.append(combo)
    return sorted(sweep_keys), combinations


def run_experiment(config: dict[str, Any], output_dir: Path | str) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    steps = int(config.get("steps", 144))
    seeds = [int(seed) for seed in config.get("seeds", [1])]
    sweep_parameters, parameter_sets = _expand_parameters(config.get("parameters", {}))
    rows: list[dict[str, Any]] = []

    for params in parameter_sets:
        for seed in seeds:
            model = HospitalMaterialHandlingModel(seed=seed, **params)
            for _ in range(steps):
                model.step()
            rows.append({"seed": seed, "steps": steps, **params, **model.snapshot()})

    fieldnames = sorted({key for row in rows for key in row})
    with (target / "run_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = ", ".join(f"{name}={row[name]}" for name in sweep_parameters) if sweep_parameters else "baseline"
        grouped[key].append(row)

    metric_names = [
        "agv_utilization",
        "pending_carts",
        "meal_completed",
        "laundry_completed",
        "waste_completed",
        "avg_meal_wait_seconds",
        "avg_laundry_wait_seconds",
        "avg_waste_wait_seconds",
    ]
    aggregate_metrics = {
        key: {f"{metric}_mean": mean(float(row[metric]) for row in values) for metric in metric_names}
        for key, values in sorted(grouped.items())
    }
    summary = {
        "model": "Hospital Material Handling Mesa",
        "steps": steps,
        "seeds": seeds,
        "run_count": len(rows),
        "sweep_parameters": sweep_parameters,
        "aggregate_metrics": aggregate_metrics,
    }
    (target / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hospital Material Handling Mesa experiment.")
    parser.add_argument("--config", type=Path, default=Path("examples/hospital_material_mesa/experiment.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/hospital_material"))
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    summary = run_experiment(config, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
