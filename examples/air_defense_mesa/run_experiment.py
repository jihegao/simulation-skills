"""Run reproducible Air Defense Mesa experiments."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import statistics
from pathlib import Path
from typing import Any

from examples.air_defense_mesa.model import AirDefenseModel


FINAL_METRICS = (
    "assets_destroyed",
    "assets_alive",
    "aircraft_destroyed",
    "aircraft_departed",
    "active_aircraft",
    "missiles_fired",
    "missiles_hit",
    "missiles_missed",
)


def _parameter_grid(parameters: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    sweep_keys = [key for key, value in parameters.items() if isinstance(value, list)]
    fixed = {key: value for key, value in parameters.items() if key not in sweep_keys}
    if not sweep_keys:
        return [], [dict(fixed)]
    values = [parameters[key] for key in sweep_keys]
    grid = []
    for combo in itertools.product(*values):
        item = dict(fixed)
        item.update(dict(zip(sweep_keys, combo)))
        grid.append(item)
    return sweep_keys, grid


def _scenario_label(parameters: dict[str, Any], sweep_keys: list[str]) -> str:
    if not sweep_keys:
        return "baseline"
    return ",".join(f"{key}={parameters[key]}" for key in sweep_keys)


def run_experiment(config: dict[str, Any], output_dir: Path | str) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    steps = int(config.get("steps", 80))
    seeds = list(config.get("seeds", [1]))
    parameters = dict(config.get("parameters", {}))
    sweep_keys, parameter_sets = _parameter_grid(parameters)

    rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    run_id = 0
    for params in parameter_sets:
        scenario = _scenario_label(params, sweep_keys)
        for seed in seeds:
            model = AirDefenseModel(seed=seed, **params)
            for step in range(steps + 1):
                snapshot = model.snapshot()
                row = {
                    "run_id": run_id,
                    "scenario": scenario,
                    "seed": seed,
                    "step": step,
                    **params,
                    **snapshot,
                }
                rows.append(row)
                if step < steps:
                    model.step()
            final_rows.append(rows[-1])
            run_id += 1

    fieldnames = sorted({key for row in rows for key in row})
    with (output_path / "run_rows.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    aggregate_metrics: dict[str, dict[str, float]] = {}
    for scenario in sorted({row["scenario"] for row in final_rows}):
        scenario_rows = [row for row in final_rows if row["scenario"] == scenario]
        aggregate_metrics[scenario] = {}
        for metric in FINAL_METRICS:
            values = [float(row[metric]) for row in scenario_rows]
            aggregate_metrics[scenario][f"{metric}_mean"] = statistics.fmean(values)
            aggregate_metrics[scenario][f"{metric}_min"] = min(values)
            aggregate_metrics[scenario][f"{metric}_max"] = max(values)

    summary = {
        "experiment_name": config.get("experiment_name", "air_defense_experiment"),
        "steps": steps,
        "seeds": seeds,
        "run_count": run_id,
        "sweep_parameters": sweep_keys,
        "parameters": parameters,
        "aggregate_metrics": aggregate_metrics,
        "source_boundary": (
            "Behavioral Mesa reproduction of the local AnyLogic PLE Air Defense System model; "
            "not an AnyLogic runtime import."
        ),
    }
    (output_path / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Mesa Air Defense experiment.")
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("experiment.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/air_defense"))
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    summary = run_experiment(config, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
