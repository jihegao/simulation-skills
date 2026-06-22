"""Run SimPy scenarios from JSON experiment configurations."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_model(model_file: str, class_name: str):
    module_path = Path(model_file).resolve()
    spec = importlib.util.spec_from_file_location("simpy_model", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load model from: {model_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model_cls = getattr(module, class_name, None)
    if model_cls is None:
        raise RuntimeError(f"class not found in {model_file}: {class_name}")
    return model_cls


def _mean_or_zero(values: Iterable[float]) -> float:
    values_list = list(values)
    return 0.0 if not values_list else statistics.mean(values_list)


def _row_fields(rows: List[Dict[str, Any]]) -> List[str]:
    fields = set()
    for row in rows:
        fields.update(row.keys())
    base = ["time", "kind"]
    ordered = base + sorted(fields - set(base))
    return ordered


def _summarize_run(
    rows: List[Dict[str, Any]],
    *,
    setting_name: str,
    setting_value: float,
    run_id: int,
    seed: int,
    horizon: float,
    params: Dict[str, Any],
) -> Dict[str, Any]:
    task_rows = [r for r in rows if int(r.get("kind", 0)) == 1]
    sample_rows = [r for r in rows if int(r.get("kind", 0)) == 2]

    completed = len(task_rows)
    queue_wait = _mean_or_zero((float(r["queue_wait"]) for r in task_rows))
    service = _mean_or_zero((float(r["service_time"]) for r in task_rows))
    task_time = _mean_or_zero((float(r["task_time"]) for r in task_rows))
    parts_wait = _mean_or_zero((float(r["parts_wait"]) for r in task_rows))

    p95_queue = 0.0
    if completed >= 2:
        p95_queue = sorted(float(r["queue_wait"]) for r in task_rows)[int(0.95 * (completed - 1))]

    stockouts = sum(int(r.get("summary_shortage_events", 0)) for r in rows if int(r.get("kind", 0)) == 3)
    if stockouts == 0:
        stockouts = sum(int(r.get("order_backlog", 0)) for r in task_rows)

    shortage_wait = sum(float(r.get("parts_wait", 0.0)) for r in task_rows)
    reorders = sum(int(r.get("summary_reorders", 0)) for r in rows if int(r.get("kind", 0)) == 3)
    parts_end = (
        next((float(r.get("summary_parts_level_end")) for r in rows if int(r.get("kind", 0)) == 3), 0.0)
    )

    avg_queue = _mean_or_zero((float(r.get("sample_bay_queue", 0.0)) for r in sample_rows))
    avg_util_bay = _mean_or_zero((float(r.get("sample_bay_util", 0.0)) for r in sample_rows))
    avg_util_crew = _mean_or_zero((float(r.get("sample_crew_util", 0.0)) for r in sample_rows))

    return {
        "setting": setting_name,
        "value": float(setting_value),
        "run_id": run_id,
        "seed": seed,
        "horizon": float(horizon),
        "completed": completed,
        "throughput_rate": completed / max(1e-9, float(horizon)),
        "mean_queue_wait": queue_wait,
        "p95_queue_wait": p95_queue,
        "mean_service_time": service,
        "mean_task_time": task_time,
        "mean_parts_wait": parts_wait,
        "stockout_events": stockouts,
        "part_shortage_wait": shortage_wait,
        "reorders": reorders,
        "parts_level_end": parts_end,
        "avg_bay_queue": avg_queue,
        "avg_bay_util": avg_util_bay,
        "avg_crew_util": avg_util_crew,
        "mean_param_arrival": float(params.get("arrival_mean", 0.0)),
        "mean_param_service": float(params.get("service_time_mean", 0.0)),
        "mean_param_bays": float(params.get("maintenance_bays", 0)),
        "run_label": f"{setting_name}_{setting_value}_{run_id}",
    }


def run_experiments_from_config(
    config: Dict[str, Any],
    output_dir: Path,
    install_dir: Path | None = None,
) -> Dict[str, Any]:
    # install_dir is currently reserved for runner parity with other workflows
    # (dependencies are expected in current interpreter in this workspace).
    model_path = config["model_path"]
    model_class = config["model_class"]
    model_cls = _resolve_model(model_path, model_class)

    default_run = dict(config.get("default_run", {}))
    fixed = dict(config.get("fixed_parameters", {}))
    horizon = float(default_run.get("horizon", 200))
    sample_interval = float(default_run.get("sample_interval", 2.0))
    run_seed = int(default_run.get("seed", 123))

    sweep = config.get("sweep") or {}
    if isinstance(sweep, dict):
        parameter = sweep.get("param")
        values = list(sweep.get("values", []))
        runs_per_value = int(sweep.get("runs_per_value", 1))
        seed_start = int(sweep.get("seed_start", run_seed))
    else:
        parameter = None
        values = [None]
        runs_per_value = 1
        seed_start = run_seed

    output_dir.mkdir(parents=True, exist_ok=True)
    all_summary = []
    all_run_labels = []
    all_rows: List[Dict[str, Any]] = []
    run_counter = 0

    if not values:
        values = [None]

    for idx, value in enumerate(values):
        setting = "baseline" if parameter is None else str(value)
        label = parameter or "baseline"
        if parameter is not None:
            fixed_value = dict(fixed)
            fixed_value[parameter] = value
        else:
            fixed_value = dict(fixed)

        for rep in range(runs_per_value):
            seed = seed_start + idx * runs_per_value + rep
            params = dict(fixed_value)
            run_label = f"{label}_{value if value is not None else 'base'}_run{rep + 1}"
            params["sample_interval"] = sample_interval
            model = model_cls(seed=seed, **params)
            rows = model.run(until=horizon)

            for row in rows:
                row["run_seed"] = seed
                row["run_label"] = run_label
                row["sweep_setting"] = value if value is not None else "baseline"

            run_path = output_dir / f"run_{run_label}.csv"
            with run_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=_row_fields(rows))
                writer.writeheader()
                writer.writerows(rows)

            summary_row = _summarize_run(
                rows,
                setting_name=label,
                setting_value=0.0 if value is None else float(value),
                run_id=run_counter + 1,
                seed=seed,
                horizon=horizon,
                params=params,
            )
            all_summary.append(summary_row)
            all_rows.extend(rows)
            all_run_labels.append(run_label)
            run_counter += 1

    summary_csv = output_dir / "summary.csv"
    summary_fields = sorted(all_summary[0].keys()) if all_summary else ["setting"]
    with summary_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(all_summary)

    summary_json = output_dir / "summary.json"
    summary_json.write_text(
        json.dumps(
            {
                "runs": run_counter,
                "summary_rows": all_summary,
                "config": config,
                "outputs": {
                    "rows_csv": [str(output_dir / f"run_{label}.csv") for label in all_run_labels]
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return {
        "output_dir": str(output_dir),
        "summary_csv": str(summary_csv),
        "summary_json": str(summary_json),
        "run_count": run_counter,
        "summary": all_summary,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run configurable SimPy experiments.")
    parser.add_argument("--model", help="Optional model module path (overrides config)")
    parser.add_argument("--config", required=True, help="Experiment JSON configuration file")
    parser.add_argument("--output-dir", required=True, help="Experiment output directory")
    parser.add_argument("--install-dir", default=None, help="Reserved for compatibility")
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    config_path = Path(args.config).resolve()
    config = _read_json(config_path)
    config = dict(config)
    if args.model is not None:
        config["model_path"] = args.model

    # Allow relative model_path in config to be relative to config file directory.
    model_path = Path(config["model_path"])
    if not model_path.is_absolute():
        cwd_candidate = (Path.cwd() / model_path).resolve()
        cfg_dir_candidate = (config_path.parent / model_path).resolve()
        if cwd_candidate.exists():
            config["model_path"] = str(cwd_candidate)
        elif cfg_dir_candidate.exists():
            config["model_path"] = str(cfg_dir_candidate)
        else:
            raise FileNotFoundError(f"Cannot locate model file: {model_path}")

    result = run_experiments_from_config(config, Path(args.output_dir), Path(args.install_dir) if args.install_dir else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
