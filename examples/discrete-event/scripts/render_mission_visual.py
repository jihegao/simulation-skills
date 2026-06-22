"""Create a simple static HTML visualization from a simulation run CSV."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def _read_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _build_html(
    run_path: Path,
    sample_rows: List[Dict[str, str]],
    mission_rows: List[Dict[str, str]],
    summary_rows: List[Dict[str, str]],
) -> str:
    summary = summary_rows[0] if summary_rows else {}
    sample_payload = [
        {
            "time": _safe_float(r.get("time", "0"), 0.0),
            "sample_idle": _safe_float(r.get("sample_idle", "0"), 0.0),
            "sample_mission": _safe_float(r.get("sample_mission", "0"), 0.0),
            "sample_pm": _safe_float(r.get("sample_pm", "0"), 0.0),
            "sample_repair": _safe_float(r.get("sample_repair", "0"), 0.0),
        }
        for r in sample_rows
    ]
    mission_payload = [
        {
            "time": _safe_float(r.get("time", "0"), 0.0),
            "mission_id": int(float(r.get("mission_id", "0"))),
            "aircraft_id": int(float(r.get("aircraft_id", "-1"))),
            "plan_start": _safe_float(r.get("plan_start", "0"), 0.0),
            "mission_dispatched": int(float(r.get("mission_dispatched", "0"))),
            "mission_success": int(float(r.get("mission_success", "0"))),
            "mission_result": r.get("mission_result", ""),
            "task_time": _safe_float(r.get("task_time", "0"), 0.0),
        }
        for r in mission_rows
    ]
    failure_payload = [
        {
            "time": _safe_float(r.get("time", "0"), 0.0),
            "aircraft_id": int(float(r.get("aircraft_id", "-1"))),
            "mission_id": int(float(r.get("mission_id", "0"))),
            "mission_id_text": str(r.get("mission_id", "")),
            "mission_result": r.get("mission_result", ""),
            "task_time": _safe_float(r.get("task_time", "0"), 0.0),
        }
        for r in mission_rows
        if str(r.get("mission_result", "")).lower() == "failed"
        or int(float(r.get("mission_success", "0"))) == 0
    ]

    mission_table_rows = "".join(
        [
            "<tr>"
            f"<td>{int(m['mission_id'])}</td>"
            f"<td>{float(m['time']):.2f}</td>"
            f"<td>{float(m['plan_start']):.2f}</td>"
            f"<td>{int(m['aircraft_id'])}</td>"
            f"<td>{m['mission_result']}</td>"
            f"<td>{float(m['task_time']):.3f}</td>"
            "</tr>"
            for m in mission_payload[:200]
        ]
    )

    sample_table_rows = "".join(
        [
            "<tr>"
            f"<td>{float(r['time']):.2f}</td>"
            f"<td>{float(r.get('sample_idle', 0.0)):.0f}</td>"
            f"<td>{float(r.get('sample_mission', 0.0)):.0f}</td>"
            f"<td>{float(r.get('sample_pm', 0.0)):.0f}</td>"
            f"<td>{float(r.get('sample_repair', 0.0)):.0f}</td>"
            "</tr>"
            for r in sample_rows[:300]
        ]
    )

    sample_json = json.dumps(sample_payload, ensure_ascii=False)
    mission_json = json.dumps(mission_payload, ensure_ascii=False)
    failure_json = json.dumps(failure_payload, ensure_ascii=False)
    summary_json = json.dumps(summary, ensure_ascii=False)
    return f"""
    <!doctype html>
    <html>
    <head>
      <meta charset='utf-8'/>
      <title>飞机保障任务仿真可视化</title>
      <style>
        body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 24px; background: #f6f7fb; color: #1b1f2a; }}
        h1 {{ margin: 0 0 4px; }}
        .card {{ background: #fff; border: 1px solid #d9deea; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; }}
        .metric {{ background: #f9fbff; border: 1px solid #d5def2; padding: 8px 10px; border-radius: 6px; }}
        .chart {{ width: 100%; min-height: 340px; margin-bottom: 10px; }}
        .legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin: 8px 0 4px; font-size: 13px; }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; }}
        .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; }}
        th, td {{ border-bottom: 1px solid #e7ecf6; padding: 6px; text-align: left; font-size: 13px; }}
        th {{ background: #eef2fb; }}
      </style>
    </head>
    <body>
      <h1>飞机保障任务仿真可视化</h1>
      <div class="card">
        <div>数据文件: {run_path}</div>
      </div>
      <div class="card grid">
        <div class="metric"><strong>计划任务总数:</strong> {summary.get("summary_planned_missions", 0)}</div>
        <div class="metric"><strong>实际出动:</strong> {summary.get("summary_dispatched_missions", 0)}</div>
        <div class="metric"><strong>任务可靠度:</strong> {summary.get("summary_mission_reliability", 0)}</div>
        <div class="metric"><strong>出动率:</strong> {summary.get("summary_sortie_rate", 0)}</div>
        <div class="metric"><strong>出动后成功率:</strong> {summary.get("summary_success_when_dispatched", 0)}</div>
        <div class="metric"><strong>PM 次数:</strong> {summary.get("summary_pm_events", 0)}</div>
        <div class="metric"><strong>修复次数:</strong> {summary.get("summary_repair_events", 0)}</div>
        <div class="metric"><strong>备件短缺次数:</strong> {summary.get("summary_part_shortage_events", 0)}</div>
      </div>
      <div class="card">
        <h3>任务事件</h3>
        <table>
          <thead><tr><th>任务ID</th><th>时间</th><th>计划时间</th><th>飞机ID</th><th>结果</th><th>任务时长</th></tr></thead>
          <tbody>{mission_table_rows}</tbody>
        </table>
      </div>
      <div class="card">
        <h3>空闲机 / 在修机（二维轨迹）</h3>
        <div class="legend">
          <span class="legend-item"><span class="dot" style="background:#4e79a7"></span>空闲机</span>
          <span class="legend-item"><span class="dot" style="background:#e15759"></span>在修机</span>
        </div>
        <div id="stateChart" class="chart"></div>
      </div>
      <div class="card">
        <h3>失败事件时间线</h3>
        <div id="failureTimeline" class="chart"></div>
      </div>
      <div class="card">
        <h3>采样轨迹（前 300 条）</h3>
        <table>
          <thead><tr><th>时间</th><th>空闲机</th><th>任务中</th><th>PM中</th><th>修复中</th></tr></thead>
          <tbody>{sample_table_rows}</tbody>
        </table>
      </div>
      <script type="application/json" id="mission-summary">{summary_json}</script>
      <script type="application/json" id="mission-samples">{sample_json}</script>
      <script type="application/json" id="mission-failures">{failure_json}</script>
      <script>
        (function() {{
          const samples = JSON.parse(document.getElementById("mission-samples").textContent || "[]");
          const failures = JSON.parse(document.getElementById("mission-failures").textContent || "[]");
          const ns = "http://www.w3.org/2000/svg";

          function makeLinePath(data, xScale, yScale, key) {{
            return data.map((d, i) =>
              (i === 0 ? "M " : "L ") + xScale(d.time).toFixed(2) + " " + yScale(d[key]).toFixed(2)
            ).join(" ");
          }}

          function buildStateChart(containerId) {{
            const el = document.getElementById(containerId);
            if (!samples || samples.length === 0) {{
              el.textContent = "无采样数据";
              return;
            }}
            const width = Math.max(640, el.clientWidth || 900);
            const height = 300;
            const pad = {{ left: 60, right: 18, top: 20, bottom: 36 }};
            const w = width - pad.left - pad.right;
            const h = height - pad.top - pad.bottom;
            const data = samples.slice().sort((a, b) => a.time - b.time);
            const xMin = data[0].time;
            const xMax = data[data.length - 1].time;
            const yMax = Math.max(1, Math.max(...data.map(d => Math.max(d.sample_idle, d.sample_repair))));

            const svg = document.createElementNS(ns, "svg");
            svg.setAttribute("viewBox", "0 0 " + width + " " + height);
            svg.setAttribute("width", "100%");
            svg.setAttribute("height", String(height));
            el.appendChild(svg);

            function xScale(t) {{
              return pad.left + ((t - xMin) / (xMax - xMin || 1)) * w;
            }}
            function yScale(v) {{
              return pad.top + h - (v / yMax) * h;
            }}

            const frame = document.createElementNS(ns, "rect");
            frame.setAttribute("x", String(pad.left));
            frame.setAttribute("y", String(pad.top));
            frame.setAttribute("width", String(w));
            frame.setAttribute("height", String(h));
            frame.setAttribute("fill", "none");
            frame.setAttribute("stroke", "#c8d0e4");
            svg.appendChild(frame);

            for (let i = 0; i <= 5; i += 1) {{
              const y = pad.top + (h / 5) * i;
              const value = (yMax * (1 - i / 5)).toFixed(0);
              const l = document.createElementNS(ns, "line");
              l.setAttribute("x1", String(pad.left));
              l.setAttribute("x2", String(width - pad.right));
              l.setAttribute("y1", String(y));
              l.setAttribute("y2", String(y));
              l.setAttribute("stroke", "#d8dfef");
              svg.appendChild(l);
              const t = document.createElementNS(ns, "text");
              t.setAttribute("x", String(pad.left - 8));
              t.setAttribute("y", String(y + 4));
              t.setAttribute("fill", "#445");
              t.setAttribute("font-size", "11");
              t.setAttribute("text-anchor", "end");
              t.textContent = value;
              svg.appendChild(t);
            }}
            for (let i = 0; i <= 6; i += 1) {{
              const x = pad.left + (w / 6) * i;
              const value = (xMin + ((xMax - xMin) * (i / 6))).toFixed(1);
              const l = document.createElementNS(ns, "line");
              l.setAttribute("x1", String(x));
              l.setAttribute("x2", String(x));
              l.setAttribute("y1", String(pad.top));
              l.setAttribute("y2", String(height - pad.bottom));
              l.setAttribute("stroke", "#d8dfef");
              svg.appendChild(l);
              const t = document.createElementNS(ns, "text");
              t.setAttribute("x", String(x));
              t.setAttribute("y", String(height - pad.bottom + 18));
              t.setAttribute("fill", "#445");
              t.setAttribute("font-size", "11");
              t.setAttribute("text-anchor", "middle");
              t.textContent = value;
              svg.appendChild(t);
            }}

            const idlePath = document.createElementNS(ns, "path");
            idlePath.setAttribute("d", makeLinePath(data, xScale, yScale, "sample_idle"));
            idlePath.setAttribute("fill", "none");
            idlePath.setAttribute("stroke", "#4e79a7");
            idlePath.setAttribute("stroke-width", "2");
            svg.appendChild(idlePath);

            const repairPath = document.createElementNS(ns, "path");
            repairPath.setAttribute("d", makeLinePath(data, xScale, yScale, "sample_repair"));
            repairPath.setAttribute("fill", "none");
            repairPath.setAttribute("stroke", "#e15759");
            repairPath.setAttribute("stroke-width", "2");
            svg.appendChild(repairPath);
          }}

          function buildFailureTimeline(containerId) {{
            const el = document.getElementById(containerId);
            if (!failures || failures.length === 0) {{
              el.textContent = "无失败事件";
              t.textContent = value;
              svg.appendChild(t);
            }}
            const width = Math.max(640, el.clientWidth || 900);
            const height = 260;
            const pad = {{ left: 70, right: 18, top: 22, bottom: 24 }};
            const w = width - pad.left - pad.right;
            const h = height - pad.top - pad.bottom;

            const aircraftIds = Array.from(new Set(failures.map((f) => f.aircraft_id))).sort((a, b) => a - b);
            const xMin = Math.min(...failures.map((f) => f.time));
            const xMax = Math.max(...failures.map((f) => f.time));
            const yPos = (aid) => aircraftIds.length <= 1
              ? pad.top + h / 2
              : pad.top + (aircraftIds.indexOf(aid) / (aircraftIds.length - 1)) * h;
            const xScale = (t) => pad.left + ((t - xMin) / (xMax - xMin || 1)) * w;

            const svg = document.createElementNS(ns, "svg");
            svg.setAttribute("viewBox", "0 0 " + width + " " + height);
            svg.setAttribute("width", "100%");
            svg.setAttribute("height", String(height));
            el.appendChild(svg);

            for (let i = 0; i < aircraftIds.length; i++) {{
              const y = pad.top + (h / Math.max(aircraftIds.length - 1, 1)) * i;
              const l = document.createElementNS(ns, "line");
              l.setAttribute("x1", String(pad.left));
              l.setAttribute("x2", String(width - pad.right));
              l.setAttribute("y1", String(y));
              l.setAttribute("y2", String(y));
              l.setAttribute("stroke", "#d9dfef");
              l.setAttribute("stroke-width", "1");
              svg.appendChild(l);
              const lab = document.createElementNS(ns, "text");
              lab.setAttribute("x", String(pad.left - 8));
              lab.setAttribute("y", String(y + 4));
              lab.setAttribute("font-size", "11");
              lab.setAttribute("text-anchor", "end");
              lab.setAttribute("fill", "#445");
              lab.textContent = "A" + aircraftIds[i];
              svg.appendChild(lab);
            }}

            for (let i = 0; i <= 6; i += 1) {{
              const x = pad.left + (w / 6) * i;
              const value = (xMin + ((xMax - xMin) * (i / 6))).toFixed(1);
              const l = document.createElementNS(ns, "line");
              l.setAttribute("x1", String(x));
              l.setAttribute("x2", String(x));
              l.setAttribute("y1", String(pad.top));
              l.setAttribute("y2", String(height - pad.bottom));
              l.setAttribute("stroke", "#d8dfef");
              svg.appendChild(l);
              const t = document.createElementNS(ns, "text");
              t.setAttribute("x", String(x));
              t.setAttribute("y", String(height - 4));
              t.setAttribute("fill", "#445");
              t.setAttribute("font-size", "11");
              t.setAttribute("text-anchor", "middle");
              t.textContent = value;
              svg.appendChild(t);
            }}

            failures.sort((a, b) => a.time - b.time).forEach((f) => {{
              const x = xScale(f.time);
              const y = yPos(f.aircraft_id);
              const l = document.createElementNS(ns, "line");
              l.setAttribute("x1", String(x));
              l.setAttribute("x2", String(x));
              l.setAttribute("y1", String(pad.top));
              l.setAttribute("y2", String(height - pad.bottom));
              l.setAttribute("stroke", "#e15759");
              l.setAttribute("opacity", "0.5");
              svg.appendChild(l);

              const c = document.createElementNS(ns, "circle");
              c.setAttribute("cx", String(x));
              c.setAttribute("cy", String(y));
              c.setAttribute("r", "5");
              c.setAttribute("fill", "#e15759");
              c.setAttribute("stroke", "#fff");
              c.setAttribute("stroke-width", "1");
              svg.appendChild(c);

              const t = document.createElementNS(ns, "text");
              t.setAttribute("x", String(x + 6));
              t.setAttribute("y", String(Math.max(pad.top + 10, y - 8)));
              t.setAttribute("font-size", "10");
              t.setAttribute("fill", "#703233");
              t.textContent = "M" + f.mission_id_text + " @ " + f.time.toFixed(2) + "h";
              svg.appendChild(t);
            }});
          }}

          buildStateChart("stateChart");
          buildFailureTimeline("failureTimeline");
        }})();
      </script>
    </body>
    </html>
    """


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a simple HTML visual artifact for one mission run.")
    parser.add_argument("--run-csv", required=True, help="Path to run_*.csv generated by run_simpy_experiment.py")
    parser.add_argument(
        "--out-html",
        default=None,
        help="Optional output HTML path. Defaults to <run>.mission_visual.html",
    )
    args = parser.parse_args()

    run_csv = Path(args.run_csv).resolve()
    if not run_csv.exists():
        raise FileNotFoundError(f"run csv not found: {run_csv}")

    rows = _read_rows(run_csv)
    sample_rows = [r for r in rows if int(float(r.get("kind", "0"))) == 2]
    mission_rows = [r for r in rows if int(float(r.get("kind", "0"))) in (1, 5)]
    summary_rows = [r for r in rows if int(float(r.get("kind", "0"))) == 3]
    out_path = Path(args.out_html) if args.out_html else run_csv.with_suffix(".mission_visual.html")
    out_path.write_text(_build_html(run_csv, sample_rows, mission_rows, summary_rows), encoding="utf-8")
    print(json.dumps({"output_html": str(out_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
