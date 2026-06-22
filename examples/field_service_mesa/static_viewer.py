"""Generate a dependency-free HTML replay for the Field Service Mesa model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from examples.field_service_mesa.model import FieldServiceModel


def build_replay_payload(
    seed: int = 42,
    steps: int = 120,
    equipment_count: int = 100,
    service_capacity: int = 3,
    replace_old_equipment: bool = False,
    normal_failure_rate: float = 0.03,
) -> dict[str, Any]:
    model = FieldServiceModel(
        seed=seed,
        equipment_count=equipment_count,
        service_capacity=service_capacity,
        replace_old_equipment=replace_old_equipment,
        normal_failure_rate=normal_failure_rate,
    )
    frames = []
    for step in range(steps + 1):
        frame = model.visualization_state()
        frame["step"] = step
        frame["metrics"] = model.snapshot()
        frame["events"] = list(model.event_log[-14:])
        frames.append(frame)
        if step < steps:
            model.step()
    return {
        "title": "Field Service Mesa Replay",
        "source": {
            "anylogic_model": "Field Service.alp",
            "time_unit": "Day",
            "claim_boundary": "Behavioral Mesa reproduction; not an AnyLogic runtime import.",
        },
        "params": {
            "seed": seed,
            "steps": steps,
            "equipment_count": equipment_count,
            "service_capacity": service_capacity,
            "replace_old_equipment": replace_old_equipment,
            "normal_failure_rate": normal_failure_rate,
        },
        "frames": frames,
    }


def write_replay_html(path: Path | str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    replay_json = json.dumps(payload)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Field Service Mesa Replay</title>
  <style>
    :root {{
      --paper: #f4f6f1;
      --ink: #1f2926;
      --muted: #66736e;
      --line: #c8d0ca;
      --yard: #e7ece4;
      --road: #b9c3bc;
      --base: #293d42;
      --working: #2f86a6;
      --due: #d6a437;
      --failed: #c94f3d;
      --service: #2f8b62;
      --crew: #513f93;
      --profit: #1c6f5a;
      --queue: #b95d3b;
      --panel: #ffffff;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(270px, 330px) minmax(520px, 1fr) minmax(300px, 380px);
      gap: 16px;
      padding: 16px;
    }}
    aside, .right-rail {{
      min-width: 0;
    }}
    aside {{
      border-right: 1px solid var(--line);
      padding-right: 16px;
    }}
    .right-rail {{
      border-left: 1px solid var(--line);
      padding-left: 16px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 25px;
      line-height: 1.05;
      letter-spacing: 0;
      font-weight: 760;
    }}
    h2 {{
      margin: 0 0 8px;
      font-size: 13px;
      letter-spacing: 0;
      text-transform: uppercase;
      color: #52645e;
    }}
    .source, .frame-label, .caption {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0 8px;
    }}
    button {{
      min-height: 36px;
      border: 1px solid #aeb9b2;
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      font: inherit;
      cursor: pointer;
    }}
    button:hover, button:focus-visible {{
      border-color: var(--crew);
      outline: none;
      box-shadow: 0 0 0 2px rgba(81, 63, 147, 0.15);
    }}
    input[type="range"] {{
      width: 100%;
      accent-color: var(--crew);
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 14px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px;
      background: var(--panel);
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
    }}
    .metric strong {{
      display: block;
      margin-top: 3px;
      font-size: 20px;
      font-weight: 720;
    }}
    main {{
      min-width: 0;
    }}
    #field {{
      width: 100%;
      max-height: calc(100vh - 32px);
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #eef2ec;
    }}
    .chart {{
      width: 100%;
      height: 150px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      margin-bottom: 12px;
    }}
    .log {{
      height: min(300px, 34vh);
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #101715;
      color: #d9e7df;
      padding: 8px;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
    }}
    .log div {{
      border-bottom: 1px solid rgba(217, 231, 223, 0.11);
      padding: 4px 0;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .key {{
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }}
    .swatch {{
      width: 10px;
      height: 10px;
      border-radius: 2px;
      display: inline-block;
    }}
    @media (max-width: 1040px) {{
      .shell {{
        grid-template-columns: minmax(260px, 320px) 1fr;
      }}
      .right-rail {{
        grid-column: 1 / -1;
        border-left: 0;
        border-top: 1px solid var(--line);
        padding: 14px 0 0;
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }}
      .log-wrap {{ grid-column: 1 / -1; }}
    }}
    @media (max-width: 740px) {{
      .shell {{ grid-template-columns: 1fr; }}
      aside {{
        border-right: 0;
        border-bottom: 1px solid var(--line);
        padding: 0 0 14px;
      }}
      .right-rail {{ display: block; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <h1>Field Service Mesa Replay</h1>
      <div class="source">Mobile crews handle high-priority failures before preventive maintenance. Profit combines equipment revenue, crew cost, and work cost.</div>
      <input id="frameSlider" type="range" min="0" max="0" value="0" aria-label="Frame">
      <div class="controls">
        <button id="back">Back</button>
        <button id="play">Play</button>
        <button id="forward">Step</button>
      </div>
      <div id="frameLabel" class="frame-label"></div>
      <div class="metric-grid" id="metrics"></div>
      <div class="legend">
        <span class="key"><span class="swatch" style="background:var(--working)"></span>working</span>
        <span class="key"><span class="swatch" style="background:var(--due)"></span>queued</span>
        <span class="key"><span class="swatch" style="background:var(--failed)"></span>failed</span>
        <span class="key"><span class="swatch" style="background:var(--service)"></span>in service</span>
        <span class="key"><span class="swatch" style="background:var(--crew)"></span>crew</span>
      </div>
    </aside>
    <main>
      <svg id="field" data-layer="situation-animation" viewBox="0 0 610 510" role="img" aria-label="Field service situation animation"></svg>
    </main>
    <section class="right-rail" aria-label="Metrics and log">
      <div>
        <h2>Profit trajectory</h2>
        <svg id="profitChart" class="chart" data-chart="profit" viewBox="0 0 360 150" role="img" aria-label="Profit over time"></svg>
      </div>
      <div>
        <h2>Request queues</h2>
        <svg id="queueChart" class="chart" data-chart="queues" viewBox="0 0 360 150" role="img" aria-label="Service and maintenance queues"></svg>
      </div>
      <div class="log-wrap">
        <h2>Dispatch log</h2>
        <div id="eventLog" class="log" data-panel="event-log" role="log" aria-label="Event log"></div>
      </div>
    </section>
  </div>
  <script>
    const REPLAY = {replay_json};
    const field = document.getElementById("field");
    const profitChart = document.getElementById("profitChart");
    const queueChart = document.getElementById("queueChart");
    const slider = document.getElementById("frameSlider");
    const label = document.getElementById("frameLabel");
    const metrics = document.getElementById("metrics");
    const eventLog = document.getElementById("eventLog");
    const playButton = document.getElementById("play");
    let frameIndex = 0;
    let timer = null;
    slider.max = String(REPLAY.frames.length - 1);

    function svgEl(name, attrs = {{}}, text = "") {{
      const node = document.createElementNS("http://www.w3.org/2000/svg", name);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      if (text) node.textContent = text;
      return node;
    }}

    function metric(label, value) {{
      return `<div class="metric"><span>${{label}}</span><strong>${{value}}</strong></div>`;
    }}

    function formatMoney(value) {{
      const abs = Math.abs(value);
      if (abs >= 1000000) return `${{value < 0 ? "-" : ""}}$${{(abs / 1000000).toFixed(1)}}M`;
      if (abs >= 1000) return `${{value < 0 ? "-" : ""}}$${{Math.round(abs / 1000)}}k`;
      return `$${{Math.round(value)}}`;
    }}

    function equipmentColor(unit) {{
      if (unit.state === "failed") return "#c94f3d";
      if (unit.state === "repair" || unit.state === "maintenance" || unit.state === "replacement") return "#2f8b62";
      if (unit.maintenance_requested === "true") return "#d6a437";
      return "#2f86a6";
    }}

    function drawField(frame) {{
      field.replaceChildren();
      field.appendChild(svgEl("rect", {{x: 0, y: 0, width: 610, height: 510, fill: "#eef2ec"}}));
      field.appendChild(svgEl("rect", {{x: 0, y: 420, width: 610, height: 90, fill: "#dde5dc"}}));
      field.appendChild(svgEl("rect", {{x: 0, y: 0, width: 86, height: 510, fill: "#d8dfd8"}}));
      field.appendChild(svgEl("path", {{d: "M60 455 C180 360 260 260 390 170 S540 80 610 45", fill: "none", stroke: "#b9c3bc", "stroke-width": 10, "stroke-linecap": "round", opacity: 0.9}}));
      field.appendChild(svgEl("rect", {{x: 24, y: 430, width: 70, height: 48, rx: 5, fill: "#293d42"}}));
      field.appendChild(svgEl("text", {{x: 31, y: 458, fill: "#ffffff", "font-size": 12}}, "base"));

      const links = svgEl("g", {{"data-layer": "dispatch-routes"}});
      for (const crew of frame.crews) {{
        if (crew.equipment_unit) {{
          const unit = frame.equipment.find(item => item.id === crew.equipment_unit);
          if (unit) {{
            links.appendChild(svgEl("line", {{x1: crew.x, y1: crew.y, x2: unit.x + 5, y2: unit.y + 5, stroke: "#513f93", "stroke-width": 1.5, "stroke-dasharray": "4 5", opacity: 0.7}}));
          }}
        }}
      }}
      field.appendChild(links);

      const equipment = svgEl("g", {{"data-layer": "equipment"}});
      for (const unit of frame.equipment) {{
        equipment.appendChild(svgEl("rect", {{x: unit.x - 4, y: unit.y - 4, width: 8, height: 8, rx: 1.5, fill: equipmentColor(unit), stroke: "#1f2926", "stroke-width": 0.8}}));
      }}
      field.appendChild(equipment);

      const crews = svgEl("g", {{"data-layer": "service-crews"}});
      for (const crew of frame.crews) {{
        crews.appendChild(svgEl("circle", {{cx: crew.x, cy: crew.y, r: 7, fill: "#513f93", stroke: "#f4f6f1", "stroke-width": 2}}));
        crews.appendChild(svgEl("text", {{x: crew.x + 9, y: crew.y - 7, fill: "#332b63", "font-size": 10}}, crew.task_type || crew.state));
      }}
      field.appendChild(crews);
    }}

    function chartLine(svg, values, color, minValue, maxValue) {{
      const pad = 18;
      const width = 360 - pad * 2;
      const height = 150 - pad * 2;
      const span = Math.max(1, maxValue - minValue);
      const points = values.map((value, index) => {{
        const x = pad + (values.length <= 1 ? 0 : (index / (values.length - 1)) * width);
        const y = pad + height - ((value - minValue) / span) * height;
        return `${{x.toFixed(1)}},${{y.toFixed(1)}}`;
      }}).join(" ");
      svg.appendChild(svgEl("polyline", {{points, fill: "none", stroke: color, "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round"}}));
    }}

    function drawCharts(index) {{
      const frames = REPLAY.frames.slice(0, index + 1);
      const profits = frames.map(frame => frame.metrics.profit);
      const service = frames.map(frame => frame.metrics.service_queue);
      const maintenance = frames.map(frame => frame.metrics.maintenance_queue);
      const profitMin = Math.min(...profits, 0);
      const profitMax = Math.max(...profits, 1);
      const queueMax = Math.max(...service, ...maintenance, 1);

      profitChart.replaceChildren();
      profitChart.appendChild(svgEl("rect", {{x: 0, y: 0, width: 360, height: 150, fill: "#ffffff"}}));
      profitChart.appendChild(svgEl("line", {{x1: 18, y1: 122, x2: 342, y2: 122, stroke: "#c8d0ca"}}));
      chartLine(profitChart, profits, "#1c6f5a", profitMin, profitMax);
      profitChart.appendChild(svgEl("text", {{x: 18, y: 22, fill: "#66736e", "font-size": 11}}, `profit ${{formatMoney(profits[profits.length - 1])}}`));

      queueChart.replaceChildren();
      queueChart.appendChild(svgEl("rect", {{x: 0, y: 0, width: 360, height: 150, fill: "#ffffff"}}));
      queueChart.appendChild(svgEl("line", {{x1: 18, y1: 122, x2: 342, y2: 122, stroke: "#c8d0ca"}}));
      chartLine(queueChart, service, "#b95d3b", 0, queueMax);
      chartLine(queueChart, maintenance, "#d6a437", 0, queueMax);
      queueChart.appendChild(svgEl("text", {{x: 18, y: 22, fill: "#66736e", "font-size": 11}}, "red repair queue / gold maintenance queue"));
    }}

    function draw(index) {{
      frameIndex = Math.max(0, Math.min(REPLAY.frames.length - 1, index));
      slider.value = String(frameIndex);
      const frame = REPLAY.frames[frameIndex];
      drawField(frame);
      drawCharts(frameIndex);
      label.textContent = `Day ${{Math.round(frame.metrics.time_days)}} / ${{REPLAY.frames.length - 1}}`;
      const m = frame.metrics;
      metrics.innerHTML = [
        metric("Profit", formatMoney(m.profit)),
        metric("Working", `${{m.working}} / ${{m.equipment_total}}`),
        metric("Repair queue", m.service_queue),
        metric("Busy crews", `${{m.busy_crews}} / ${{REPLAY.params.service_capacity}}`),
        metric("Failures", m.failures_observed),
        metric("Replacements", m.replacements_completed),
      ].join("");
      eventLog.innerHTML = frame.events.length
        ? frame.events.map(event => `<div><strong>day ${{event.time}}</strong> ${{event.message}}</div>`).join("")
        : "<div>No dispatch events yet.</div>";
      eventLog.scrollTop = eventLog.scrollHeight;
    }}

    function togglePlay() {{
      if (timer) {{
        clearInterval(timer);
        timer = null;
        playButton.textContent = "Play";
        return;
      }}
      playButton.textContent = "Pause";
      timer = setInterval(() => {{
        if (frameIndex >= REPLAY.frames.length - 1) {{
          clearInterval(timer);
          timer = null;
          playButton.textContent = "Play";
        }} else {{
          draw(frameIndex + 1);
        }}
      }}, 140);
    }}

    document.getElementById("back").addEventListener("click", () => draw(frameIndex - 1));
    document.getElementById("forward").addEventListener("click", () => draw(frameIndex + 1));
    playButton.addEventListener("click", togglePlay);
    slider.addEventListener("input", event => draw(Number(event.target.value)));
    draw(0);
  </script>
</body>
</html>
"""
    target.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a static Field Service replay HTML file.")
    parser.add_argument("--output", type=Path, default=Path("outputs/field_service/replay.html"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--equipment-count", type=int, default=100)
    parser.add_argument("--service-capacity", type=int, default=3)
    parser.add_argument("--replace-old-equipment", action="store_true")
    parser.add_argument("--normal-failure-rate", type=float, default=0.03)
    args = parser.parse_args()

    payload = build_replay_payload(
        seed=args.seed,
        steps=args.steps,
        equipment_count=args.equipment_count,
        service_capacity=args.service_capacity,
        replace_old_equipment=args.replace_old_equipment,
        normal_failure_rate=args.normal_failure_rate,
    )
    write_replay_html(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
