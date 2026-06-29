"""Write a small HTML viewer for BDI polarization experiment summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def render_html(summary: dict) -> str:
    rows = []
    for scenario, metrics in summary["aggregate_metrics"].items():
        rows.append(
            "<tr>"
            f"<td>{scenario}</td>"
            f"<td>{metrics['polarization_index_mean']:.3f}</td>"
            f"<td>{metrics['extreme_share_mean']:.3f}</td>"
            f"<td>{metrics['action_rate_mean']:.3f}</td>"
            f"<td>{metrics['mean_recommendation_alignment_mean']:.3f}</td>"
            "</tr>"
        )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>BDI Polarization Summary</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #172026; }}
    table {{ border-collapse: collapse; min-width: 760px; }}
    th, td {{ border: 1px solid #d8dee4; padding: 8px 10px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #f4f6f8; }}
    .note {{ max-width: 860px; line-height: 1.45; color: #4b5563; }}
  </style>
</head>
<body>
  <h1>BDI Polarization Summary</h1>
  <p class="note">{summary["question"]}</p>
  <table>
    <thead>
      <tr>
        <th>Scenario</th>
        <th>Polarization</th>
        <th>Extreme Share</th>
        <th>Action Rate</th>
        <th>Recommendation Alignment</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <p class="note">{summary["evidence_boundary"]}</p>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Render BDI polarization summary HTML.")
    parser.add_argument("--summary", type=Path, default=Path("outputs/bdi_polarization/summary.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/bdi_polarization/viewer.html"))
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_html(summary), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()

