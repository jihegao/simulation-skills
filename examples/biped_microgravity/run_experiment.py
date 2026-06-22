"""Run load checks for a matchstick bridge structure."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from examples.biped_microgravity.model import MatchstickBridge


def run_experiment(config: dict[str, Any], output_dir: Path | str) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    load_cases = [float(value) for value in config.get("load_cases_n", [10.0, 18.0, 30.0])]
    panel_cases = [int(value) for value in config.get("panel_count_cases", [6])]

    rows: list[dict[str, Any]] = []
    replay_frames: list[dict[str, Any]] = []
    for load_n, panel_count in itertools.product(load_cases, panel_cases):
        model = MatchstickBridge(
            span_m=float(config.get("span_m", 0.60)),
            width_m=float(config.get("width_m", 0.10)),
            truss_depth_m=float(config.get("truss_depth_m", 0.12)),
            panel_count=panel_count,
            load_n=load_n,
            glue_joint_capacity_n=float(config.get("glue_joint_capacity_n", 16.0)),
            deflection_ratio_limit=float(config.get("deflection_ratio_limit", 250.0)),
        )
        evaluation = model.evaluate_load()
        rows.append(
            {
                "load_n": load_n,
                "panel_count": panel_count,
                "verdict": evaluation.verdict,
                "can_hold": evaluation.can_hold,
                "max_member_force_n": round(evaluation.max_member_force_n, 4),
                "max_member_utilization": round(evaluation.max_member_utilization, 4),
                "joint_utilization": round(evaluation.joint_utilization, 4),
                "midspan_deflection_m": round(evaluation.midspan_deflection_m, 6),
                "failure_modes": ";".join(evaluation.failure_modes),
            }
        )
        replay_frames.append(model.visualization_state())

    fieldnames = [
        "load_n",
        "panel_count",
        "verdict",
        "can_hold",
        "max_member_force_n",
        "max_member_utilization",
        "joint_utilization",
        "midspan_deflection_m",
        "failure_modes",
    ]
    with (target / "bridge_cases.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    hold_count = sum(1 for row in rows if row["can_hold"])
    summary = {
        "model": "Matchstick Warren-truss bridge quasi-static load check",
        "case_count": len(rows),
        "hold_count": hold_count,
        "fail_count": len(rows) - hold_count,
        "claim_boundary": (
            "Simplified structural envelope for matchstick bridge design; not a finite-element solver."
        ),
        "rows": rows,
    }
    (target / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (target / "replay.json").write_text(json.dumps({"frames": replay_frames}, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run matchstick bridge load checks.")
    parser.add_argument("--config", type=Path, default=Path("examples/biped_microgravity/experiment.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/biped_microgravity"))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    print(json.dumps(run_experiment(config, args.output_dir), indent=2))


if __name__ == "__main__":
    main()

