"""Run parameter sweeps for the BDI polarization Mesa example."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from examples.bdi_polarization_mesa.model import BDIPolarizationModel
from examples.bdi_polarization_mesa.opencode_sampler import load_behavior_samples


FINAL_METRICS = (
    "belief_mean",
    "belief_variance",
    "polarization_index",
    "extreme_share",
    "action_rate",
    "mobilize_rate",
    "mean_recommendation_alignment",
    "group_actions",
    "content_pool_size",
    "llm_sampled_agents",
    "llm_mean_abs_belief",
)


def _expand_parameters(parameters: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    sweep_keys = sorted(key for key, value in parameters.items() if isinstance(value, list))
    fixed = {key: value for key, value in parameters.items() if key not in sweep_keys}
    if not sweep_keys:
        return [], [fixed]
    combinations: list[dict[str, Any]] = []
    for values in itertools.product(*(parameters[key] for key in sweep_keys)):
        combo = dict(fixed)
        combo.update(dict(zip(sweep_keys, values, strict=True)))
        combinations.append(combo)
    return sweep_keys, combinations


def _scenario_label(row: dict[str, Any], sweep_parameters: list[str]) -> str:
    if not sweep_parameters:
        return "baseline"
    return ", ".join(f"{name}={row[name]}" for name in sweep_parameters)


def run_experiment(config: dict[str, Any], output_dir: Path | str) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    steps = int(config.get("steps", 80))
    seeds = [int(seed) for seed in config.get("seeds", [1])]
    sweep_parameters, parameter_sets = _expand_parameters(dict(config.get("parameters", {})))
    llm_behavior_samples, llm_sampling = load_behavior_samples(config.get("llm_sampling"), target)

    time_rows: list[dict[str, Any]] = []
    final_rows: list[dict[str, Any]] = []
    run_id = 0
    for params in parameter_sets:
        for seed in seeds:
            model = BDIPolarizationModel(seed=seed, llm_behavior_samples=llm_behavior_samples, **params)
            for step in range(steps + 1):
                snapshot = model.snapshot()
                row = {
                    "run_id": run_id,
                    "seed": seed,
                    "step": step,
                    **params,
                    **snapshot,
                }
                time_rows.append(row)
                if step < steps:
                    model.step()
            final_rows.append(time_rows[-1])
            run_id += 1

    fieldnames = sorted({key for row in time_rows for key in row})
    with (target / "run_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(time_rows)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in final_rows:
        grouped[_scenario_label(row, sweep_parameters)].append(row)

    aggregate_metrics = {
        scenario: {
            f"{metric}_mean": mean(float(row[metric]) for row in values)
            for metric in FINAL_METRICS
        }
        for scenario, values in sorted(grouped.items())
    }
    aggregate_metrics.update(
        {
            scenario: {
                **values,
                **{
                    f"{metric}_min": min(float(row[metric]) for row in grouped[scenario])
                    for metric in ("polarization_index", "extreme_share", "action_rate")
                },
                **{
                    f"{metric}_max": max(float(row[metric]) for row in grouped[scenario])
                    for metric in ("polarization_index", "extreme_share", "action_rate")
                },
            }
            for scenario, values in aggregate_metrics.items()
        }
    )

    summary = {
        "model": "BDI Recommendation Polarization",
        "experiment_name": config.get("experiment_name", "bdi_recommendation_polarization"),
        "question": (
            "Can a BDI agent population reproduce group polarization when recommender "
            "selection and group-action feedback amplify identity-consistent content?"
        ),
        "steps": steps,
        "seeds": seeds,
        "run_count": len(final_rows),
        "sweep_parameters": sweep_parameters,
        "aggregate_metrics": aggregate_metrics,
        "primary_metrics": ["polarization_index", "extreme_share", "action_rate"],
        "llm_boundary": (
            "llm_agent_fraction marks agents whose BDI behavior parameters are sampled before "
            "the run. The default experiment attempts local opencode CLI sampling and caches "
            "the resulting profiles; simulation steps never call an external model."
        ),
        "llm_sampling": llm_sampling,
        "llm_behavior_samples": llm_behavior_samples,
        "evidence_boundary": (
            "Exploratory mechanism reproduction only. The model tests whether the encoded "
            "BDI/recommender/group-action rules can generate polarization-like dynamics; "
            "it is not calibrated evidence about a real platform or population."
        ),
    }
    (target / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the BDI polarization experiment.")
    parser.add_argument("--config", type=Path, default=Path("examples/bdi_polarization_mesa/experiment.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/bdi_polarization"))
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    summary = run_experiment(config, args.output_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
