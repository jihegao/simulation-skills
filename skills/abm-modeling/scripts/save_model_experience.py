#!/usr/bin/env python3
"""Save a compact private experience record for a completed Mesa model."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


SCHEMA_VERSION = 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to the Mesa model Python file.")
    parser.add_argument("--config", required=True, help="Path to the experiment JSON config.")
    parser.add_argument("--summary", required=True, help="Path to runner summary.json.")
    parser.add_argument(
        "--output-root",
        default=".mesa-abm-experience",
        help="Private local experience store root.",
    )
    parser.add_argument(
        "--notes",
        default="",
        help="Short lessons, pitfalls, or reuse guidance from the completed model.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def require_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise SystemExit(f"{label} does not exist or is not a file: {path}")
    return resolved


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "mesa-model"


def relative_to_cwd(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def primary_metric(summary: dict, config: dict) -> str | None:
    configured = config.get("primary_metric")
    metrics = summary.get("metrics", {})
    if configured in metrics:
        return configured
    if metrics:
        return sorted(metrics)[0]
    return None


def compact_metrics(summary: dict, metric_name: str | None) -> dict:
    metrics = summary.get("metrics", {})
    if metric_name and metric_name in metrics:
        return {metric_name: metrics[metric_name]}
    return metrics


def build_compressed_experience(
    summary: dict,
    config: dict,
    metric_name: str | None,
    notes: str,
) -> str:
    experiment = summary.get("experiment") or config.get("experiment_name") or "Mesa experiment"
    model_class = summary.get("model_class") or config.get("model_class") or "Mesa model"
    steps = summary.get("steps", config.get("steps"))
    run_count = summary.get("run_count", 0)
    metric_text = "no numeric primary metric"
    metric_summary = compact_metrics(summary, metric_name)
    if metric_name and metric_summary.get(metric_name):
        stats = metric_summary[metric_name]
        metric_text = (
            f"{metric_name} mean {stats.get('mean')} "
            f"with range {stats.get('min')} to {stats.get('max')}"
        )
    parts = [
        f"Built {model_class} for {experiment}.",
        f"Ran {run_count} Mesa runs for {steps} steps; observed {metric_text}.",
    ]
    effects = summary.get("parameter_effects", {})
    if effects:
        varied = ", ".join(sorted(effects))
        parts.append(f"Reusable comparison dimension(s): {varied}.")
    if notes:
        parts.append(notes.strip())
    parts.append(
        "Reuse only as model-building experience; external-world claims still require calibration."
    )
    return " ".join(part for part in parts if part)


def build_card(model_path: Path, config_path: Path, summary_path: Path, notes: str) -> dict:
    config = load_json(config_path)
    summary = load_json(summary_path)
    metric_name = primary_metric(summary, config)
    compressed = build_compressed_experience(summary, config, metric_name, notes)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "model_name": model_path.stem,
        "model_path": relative_to_cwd(model_path),
        "config_path": relative_to_cwd(config_path),
        "summary_path": relative_to_cwd(summary_path),
        "experiment": summary.get("experiment") or config.get("experiment_name"),
        "framework": summary.get("framework", "mesa"),
        "model_class": summary.get("model_class") or config.get("model_class"),
        "steps": summary.get("steps", config.get("steps")),
        "run_count": summary.get("run_count", 0),
        "seeds": summary.get("seeds", config.get("seeds", [])),
        "primary_metric": metric_name,
        "metric_summary": compact_metrics(summary, metric_name),
        "parameter_effects": summary.get("parameter_effects", {}),
        "compressed_experience": compressed,
        "assumptions_and_limits": [
            "This record summarizes encoded Mesa model behavior, not calibrated external causality.",
            "Raw run outputs remain outside the private experience card.",
        ],
        "reusable_patterns": [notes.strip()] if notes.strip() else [],
        "pitfalls": [],
        "next_time": [
            "Start from the saved model/config paths when building a similar Mesa model.",
            "Run fresh seeded evidence before reusing any result claim.",
        ],
    }


def write_markdown(path: Path, card: dict) -> None:
    lines = [
        f"# {card['experiment']} Experience",
        "",
        f"- Model: `{card['model_class']}`",
        f"- Framework: `{card['framework']}`",
        f"- Runs: {card['run_count']}",
        f"- Steps: {card['steps']}",
        f"- Primary metric: `{card['primary_metric']}`",
        "",
        "## Compressed Experience",
        "",
        card["compressed_experience"],
        "",
        "## Evidence Pointers",
        "",
        f"- Model path: `{card['model_path']}`",
        f"- Config path: `{card['config_path']}`",
        f"- Summary path: `{card['summary_path']}`",
        "",
        "## Limits",
        "",
        "- Local private user data; do not publish unless the user explicitly asks.",
        "- This is reusable modeling experience, not proof of real-world causality.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    model_path = require_file(Path(args.model), "Model")
    config_path = require_file(Path(args.config), "Config")
    summary_path = require_file(Path(args.summary), "Summary")
    output_root = Path(args.output_root).resolve()
    models_dir = output_root / "models"
    summaries_dir = output_root / "summaries"
    models_dir.mkdir(parents=True, exist_ok=True)
    summaries_dir.mkdir(parents=True, exist_ok=True)

    card = build_card(model_path, config_path, summary_path, args.notes)
    slug = slugify(card.get("experiment") or card["model_name"])
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_name = f"{timestamp}-{slug}"
    card_path = models_dir / f"{base_name}.json"
    summary_md_path = summaries_dir / f"{base_name}.md"
    index_path = output_root / "index.jsonl"

    card_path.write_text(json.dumps(card, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(summary_md_path, card)
    index_entry = {
        "created_at": card["created_at"],
        "experiment": card["experiment"],
        "model_class": card["model_class"],
        "card": relative_to_cwd(card_path),
        "summary_markdown": relative_to_cwd(summary_md_path),
        "primary_metric": card["primary_metric"],
    }
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(index_entry, sort_keys=True) + "\n")

    print(
        json.dumps(
            {
                "card": str(card_path),
                "summary_markdown": str(summary_md_path),
                "index": str(index_path),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
