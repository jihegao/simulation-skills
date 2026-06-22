"""Generate a dependency-free HTML replay for the Air Defense Mesa model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from examples.air_defense_mesa.model import AirDefenseModel


def build_replay_payload(
    seed: int = 42,
    steps: int = 120,
    initial_aircraft: int = 8,
    aircraft_speed: float = 10.0,
    missile_speed: float = 20.0,
    radar_zone: float = 100.0,
    radar_max_missiles: int = 2,
) -> dict[str, Any]:
    model = AirDefenseModel(
        seed=seed,
        initial_aircraft=initial_aircraft,
        aircraft_speed=aircraft_speed,
        missile_speed=missile_speed,
        radar_zone=radar_zone,
        radar_max_missiles=radar_max_missiles,
    )
    frames = []
    for step in range(steps + 1):
        frame = model.agent_positions()
        frame["step"] = step
        frame["metrics"] = model.snapshot()
        frames.append(frame)
        if step < steps:
            model.step()
    return {
        "title": "Air Defense Mesa Replay",
        "params": {
            "seed": seed,
            "steps": steps,
            "initial_aircraft": initial_aircraft,
            "aircraft_speed": aircraft_speed,
            "missile_speed": missile_speed,
            "radar_zone": radar_zone,
            "radar_max_missiles": radar_max_missiles,
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
  <title>Air Defense Mesa Replay</title>
  <style>
    :root {{
      --paper: #f6f7f2;
      --ink: #1d2930;
      --muted: #65747c;
      --water: #dceaf0;
      --radar: #2f7f96;
      --asset: #263d35;
      --aircraft: #2c5f9e;
      --missile: #d34f35;
      --amber: #f0b84f;
      --rule: #cfd8d4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(280px, 340px) minmax(520px, 1fr);
      gap: 18px;
      padding: 18px;
    }}
    aside {{
      border-right: 1px solid var(--rule);
      padding-right: 18px;
    }}
    h1 {{
      margin: 0 0 14px;
      font-size: 24px;
      line-height: 1.1;
      letter-spacing: 0;
    }}
    .source {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin-bottom: 18px;
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0;
    }}
    button {{
      min-height: 34px;
      border: 1px solid #aebbb6;
      background: #ffffff;
      color: var(--ink);
      border-radius: 6px;
      font: inherit;
      cursor: pointer;
    }}
    button:hover {{ border-color: var(--radar); }}
    input[type="range"] {{ width: 100%; }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 16px;
    }}
    .metric {{
      border: 1px solid var(--rule);
      border-radius: 6px;
      padding: 9px;
      background: #ffffff;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
    }}
    .metric strong {{
      display: block;
      margin-top: 4px;
      font-size: 20px;
      font-weight: 650;
    }}
    main {{
      min-width: 0;
    }}
    #field {{
      width: 100%;
      max-height: calc(100vh - 36px);
      border: 1px solid var(--rule);
      border-radius: 6px;
      background: #f7f9f8;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    .key {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .swatch {{
      width: 10px;
      height: 10px;
      border-radius: 2px;
      display: inline-block;
    }}
    @media (max-width: 820px) {{
      .shell {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--rule); padding: 0 0 16px; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <h1>Air Defense Mesa Replay</h1>
      <div class="source">Behavioral Mesa reproduction of the local AnyLogic PLE Air Defense System. Frames are generated from Python model state.</div>
      <input id="frameSlider" type="range" min="0" max="0" value="0" aria-label="Frame">
      <div class="controls">
        <button id="back">Back</button>
        <button id="play">Play</button>
        <button id="forward">Step</button>
      </div>
      <div id="frameLabel" class="source"></div>
      <div class="metric-grid" id="metrics"></div>
      <div class="legend">
        <span class="key"><span class="swatch" style="background:var(--asset)"></span>asset</span>
        <span class="key"><span class="swatch" style="background:var(--aircraft)"></span>aircraft</span>
        <span class="key"><span class="swatch" style="background:var(--missile)"></span>missile</span>
        <span class="key"><span class="swatch" style="background:var(--amber)"></span>radar</span>
      </div>
    </aside>
    <main>
      <svg id="field" data-layer="battlefield" viewBox="0 0 720 460" role="img" aria-label="Air defense battlefield replay"></svg>
    </main>
  </div>
  <script>
    const REPLAY = {replay_json};
    const field = document.getElementById("field");
    const slider = document.getElementById("frameSlider");
    const label = document.getElementById("frameLabel");
    const metrics = document.getElementById("metrics");
    const playButton = document.getElementById("play");
    let frameIndex = 0;
    let timer = null;
    slider.max = String(REPLAY.frames.length - 1);

    function el(name, attrs = {{}}, text = "") {{
      const node = document.createElementNS("http://www.w3.org/2000/svg", name);
      for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
      if (text) node.textContent = text;
      return node;
    }}

    function metric(label, value) {{
      return `<div class="metric"><span>${{label}}</span><strong>${{value}}</strong></div>`;
    }}

    function draw(index) {{
      frameIndex = Math.max(0, Math.min(REPLAY.frames.length - 1, index));
      slider.value = String(frameIndex);
      const frame = REPLAY.frames[frameIndex];
      field.replaceChildren();
      field.appendChild(el("rect", {{x: 0, y: 0, width: 720, height: 460, fill: "#f7f9f8"}}));
      field.appendChild(el("rect", {{x: 0, y: 0, width: 178, height: 460, fill: "#dceaf0", opacity: 0.72}}));
      field.appendChild(el("text", {{x: 18, y: 28, fill: "#456170", "font-size": 12}}, "base / sea approach"));
      field.appendChild(el("text", {{x: 410, y: 28, fill: "#33413d", "font-size": 12}}, "protected asset cluster"));

      const radarZone = el("g", {{"data-layer": "radar-zone"}});
      for (const radar of frame.radars) {{
        radarZone.appendChild(el("circle", {{cx: radar.x, cy: radar.y, r: REPLAY.params.radar_zone, fill: "#6aa6b8", "fill-opacity": 0.09, stroke: "#357f96", "stroke-width": 1.5, "stroke-dasharray": "5 4"}}));
      }}
      field.appendChild(radarZone);

      const assets = el("g", {{"data-layer": "asset"}});
      for (const asset of frame.assets) {{
        const destroyed = asset.state === "destroyed";
        assets.appendChild(el("rect", {{x: asset.x - 5, y: asset.y - 5, width: 10, height: 10, rx: 1.5, fill: destroyed ? "#bb4b31" : "#263d35", stroke: destroyed ? "#7f2c1c" : "#10231f"}}));
      }}
      field.appendChild(assets);

      const radars = el("g", {{"data-layer": "radar"}});
      for (const radar of frame.radars) {{
        radars.appendChild(el("circle", {{cx: radar.x, cy: radar.y, r: 7, fill: "#f0b84f", stroke: "#755820", "stroke-width": 1.5}}));
        radars.appendChild(el("text", {{x: radar.x + 9, y: radar.y - 8, fill: "#755820", "font-size": 11}}, radar.state));
      }}
      field.appendChild(radars);

      const aircraft = el("g", {{"data-layer": "aircraft"}});
      for (const plane of frame.aircraft) {{
        const fill = plane.state === "destroyed" ? "#7a2d2a" : plane.state === "returning" ? "#8a6b35" : plane.state === "departed" ? "#9aa4aa" : "#2c5f9e";
        const points = `${{plane.x + 8}},${{plane.y}} ${{plane.x - 6}},${{plane.y - 5}} ${{plane.x - 3}},${{plane.y}} ${{plane.x - 6}},${{plane.y + 5}}`;
        aircraft.appendChild(el("polygon", {{points, fill, stroke: "#172232", "stroke-width": 1}}));
      }}
      field.appendChild(aircraft);

      const missiles = el("g", {{"data-layer": "missile"}});
      for (const missile of frame.missiles) {{
        missiles.appendChild(el("circle", {{cx: missile.x, cy: missile.y, r: 3.5, fill: "#d34f35", stroke: "#76271d", "stroke-width": 1}}));
      }}
      field.appendChild(missiles);

      label.textContent = `Frame ${{frameIndex}} / ${{REPLAY.frames.length - 1}}`;
      const m = frame.metrics;
      metrics.innerHTML = [
        metric("Assets destroyed", `${{m.assets_destroyed}} / ${{m.assets_total}}`),
        metric("Aircraft destroyed", m.aircraft_destroyed),
        metric("Missiles fired", m.missiles_fired),
        metric("Active missiles", m.active_missiles),
      ].join("");
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
      }}, 120);
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
    parser = argparse.ArgumentParser(description="Generate a static Air Defense replay HTML file.")
    parser.add_argument("--output", type=Path, default=Path("outputs/air_defense/replay.html"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--initial-aircraft", type=int, default=8)
    parser.add_argument("--aircraft-speed", type=float, default=10.0)
    parser.add_argument("--missile-speed", type=float, default=20.0)
    parser.add_argument("--radar-zone", type=float, default=100.0)
    parser.add_argument("--radar-max-missiles", type=int, default=2)
    args = parser.parse_args()

    payload = build_replay_payload(
        seed=args.seed,
        steps=args.steps,
        initial_aircraft=args.initial_aircraft,
        aircraft_speed=args.aircraft_speed,
        missile_speed=args.missile_speed,
        radar_zone=args.radar_zone,
        radar_max_missiles=args.radar_max_missiles,
    )
    write_replay_html(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
