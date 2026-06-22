#!/usr/bin/env python3
"""Run a SimPy DES parameter sweep from a JSON experiment config."""

from __future__ import annotations

import argparse
import csv
import importlib.util
from importlib import metadata
import itertools
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys


SIMPY_REQUIREMENT = "simpy>=4,<5"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to a Python file defining the SimPy model class.")
    parser.add_argument("--config", required=True, help="Path to a JSON experiment config.")
    parser.add_argument("--output-dir", required=True, help="Directory for CSV run data and summary.json.")
    parser.add_argument(
        "--install-dir",
        help="Optional virtualenv directory. If SimPy is missing, create/reuse this env and rerun inside it.",
    )
    return parser.parse_args()


def venv_python(install_dir: Path) -> Path:
    if os.name == "nt":
        return install_dir / "Scripts" / "python.exe"
    return install_dir / "bin" / "python"


def simpy_version_satisfies(version_text: str) -> bool:
    parts = version_text.split(".")
    try:
        major = int(parts[0])
    except (IndexError, ValueError):
        return False
    return major == 4


def current_python_has_required_simpy() -> bool:
    try:
        version_text = metadata.version("simpy")
    except metadata.PackageNotFoundError:
        return False
    return simpy_version_satisfies(version_text)


def python_has_required_simpy(python: Path) -> bool:
    code = (
        "from importlib import metadata; "
        "try: version = metadata.version('simpy')\n"
        "except metadata.PackageNotFoundError: raise SystemExit(1)\n"
        "try: major = int(version.split('.')[0])\n"
        "except (IndexError, ValueError): raise SystemExit(1)\n"
        "raise SystemExit(0 if major == 4 else 1)"
    )
    completed = subprocess.run(
        [str(python), "-c", code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return completed.returncode == 0


def create_virtualenv(install_dir: Path) -> None:
    subprocess.run([sys.executable, "-m", "venv", str(install_dir)], check=True, text=True)


def ensure_simpy(args: argparse.Namespace) -> None:
    if current_python_has_required_simpy():
        return

    if os.environ.get("DES_SIMPY_BOOTSTRAPPED") == "1":
        raise SystemExit(
            "The required SimPy version is still unavailable after bootstrapping. "
            f"Install {SIMPY_REQUIREMENT} or inspect the virtual environment."
        )

    if not args.install_dir:
        raise SystemExit(
            "SimPy 4 is not installed for this Python. Re-run with --install-dir "
            f"to create a local environment containing {SIMPY_REQUIREMENT}."
        )

    install_dir = Path(args.install_dir).resolve()
    python = venv_python(install_dir)
    if not python.exists():
        create_virtualenv(install_dir)

    if not python_has_required_simpy(python):
        subprocess.run([str(python), "-m", "pip", "install", SIMPY_REQUIREMENT], check=True, text=True)

    env = os.environ.copy()
    env["DES_SIMPY_BOOTSTRAPPED"] = "1"
    completed = subprocess.run([str(python), str(Path(__file__).resolve()), *sys.argv[1:]], env=env, text=True)
    raise SystemExit(completed.returncode)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_model_class(model_path: Path, class_name: str):
    spec = importlib.util.spec_from_file_location("des_user_model", model_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load model module from {model_path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(model_path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(model_path.parent))
        except ValueError:
            pass
    try:
        return getattr(module, class_name)
    except AttributeError as exc:
        raise SystemExit(f"Model module does not define class {class_name!r}") from exc


def expand_parameters(parameters: dict) -> list[dict]:
    keys = list(parameters)
    values = [value if isinstance(value, list) else [value] for value in parameters.values()]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def numeric_items(row: dict) -> dict[str, float]:
    numeric = {}
    for key, value in row.items():
        if key == "time":
            continue
        if isinstance(value, (int, float)):
            numeric[key] = float(value)
    return numeric


def run_single(model_class, params: dict, seed: int | None, until: float) -> list[dict]:
    kwargs = dict(params)
    if seed is not None:
        kwargs["seed"] = seed
    model = model_class(**kwargs)
    if not hasattr(model, "run"):
        raise SystemExit(f"{model_class.__name__} must implement run(until: float) -> list[dict]")
    rows = model.run(until)
    if not rows:
        raise SystemExit(f"{model_class.__name__}.run() returned no rows")
    if "time" not in rows[-1]:
        raise SystemExit(f"{model_class.__name__}.run() rows must include a time field")
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = ["time"]
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize_runs(config: dict, records: list[dict]) -> dict:
    final_rows = [record["final"] for record in records]
    metric_names = sorted({key for row in final_rows for key in numeric_items(row)})
    metrics = {}
    for name in metric_names:
        values = [numeric_items(row)[name] for row in final_rows if name in numeric_items(row)]
        if values:
            metrics[name] = {
                "mean": statistics.fmean(values),
                "min": min(values),
                "max": max(values),
            }

    varied = {
        key: value
        for key, value in config.get("parameters", {}).items()
        if isinstance(value, list) and len(value) > 1
    }
    effects = {}
    primary_metric = config.get("primary_metric") or (metric_names[0] if metric_names else None)
    if primary_metric:
        for parameter in varied:
            grouped: dict[str, list[float]] = {}
            for record in records:
                value = record["parameters"].get(parameter)
                metric_value = numeric_items(record["final"]).get(primary_metric)
                if metric_value is not None:
                    grouped.setdefault(str(value), []).append(metric_value)
            if grouped:
                effects[parameter] = {
                    value: statistics.fmean(values)
                    for value, values in sorted(grouped.items())
                }

    return {
        "experiment": config.get("experiment_name", "simpy_experiment"),
        "framework": "simpy",
        "model_class": config["model_class"],
        "until": config["until"],
        "run_count": len(records),
        "seeds": config.get("seeds", []),
        "metrics": metrics,
        "parameter_effects": effects,
        "interpretation": build_interpretation(config, metrics, effects, len(records)),
        "runs": records,
    }


def build_interpretation(config: dict, metrics: dict, effects: dict, run_count: int) -> str:
    primary = config.get("primary_metric")
    if primary not in metrics and metrics:
        primary = sorted(metrics)[0]
    if not primary:
        return f"Ran {run_count} SimPy runs, but no numeric final metrics were reported."

    stats = metrics[primary]
    parts = [
        f"Ran {run_count} seeded SimPy runs through simulated time {config.get('until')}.",
        f"Final {primary} averaged {stats['mean']:.4f} (range {stats['min']:.4f} to {stats['max']:.4f}).",
    ]
    for parameter, values in effects.items():
        formatted = ", ".join(f"{value}: {metric:.4f}" for value, metric in values.items())
        parts.append(f"Grouped by {parameter}, mean final {primary} was {formatted}.")
    parts.append(
        "Treat these results as simulation evidence under the encoded event rules; "
        "they do not prove external-world causality without calibration and sensitivity checks."
    )
    return " ".join(parts)


def main() -> int:
    args = parse_args()
    ensure_simpy(args)

    model_path = Path(args.model).resolve()
    config_path = Path(args.config).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_json(config_path)
    for required in ["model_class", "parameters", "until"]:
        if required not in config:
            raise SystemExit(f"Config missing required field: {required}")

    model_class = load_model_class(model_path, config["model_class"])
    parameter_sets = expand_parameters(config.get("parameters", {}))
    seeds = config.get("seeds", [None])
    until = float(config["until"])

    records = []
    run_index = 0
    for params in parameter_sets:
        for seed in seeds:
            rows = run_single(model_class, params, seed, until)
            csv_path = output_dir / f"run_{run_index:03d}.csv"
            write_csv(csv_path, rows)
            records.append(
                {
                    "run_id": run_index,
                    "seed": seed,
                    "parameters": params,
                    "csv": csv_path.name,
                    "final": rows[-1],
                }
            )
            run_index += 1

    summary = summarize_runs(config, records)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "run_count": len(records)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
