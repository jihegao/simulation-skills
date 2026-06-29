"""Generate a browser replay for one BDI polarization simulation run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from examples.bdi_polarization_mesa.model import BDIPolarizationModel
from examples.bdi_polarization_mesa.opencode_sampler import load_behavior_samples


def _agent_rows(model: BDIPolarizationModel) -> list[dict[str, Any]]:
    rows = []
    for agent in model.bdi_agents:
        rows.append(
            {
                "id": agent.unique_id,
                "belief": round(agent.belief, 5),
                "intention": agent.last_intention,
                "isLlm": agent.is_llm_sampled,
                "sample": agent.llm_sample["name"] if agent.llm_sample else "rule_based",
                "alignment": round(agent.last_consumed_alignment, 5),
            }
        )
    return rows


def _frame(model: BDIPolarizationModel) -> dict[str, Any]:
    snapshot = model.snapshot()
    intention_counts = {"idle": 0, "support": 0, "share": 0, "mobilize": 0}
    for agent in model.bdi_agents:
        intention_counts[agent.last_intention] += 1
    return {
        "tick": int(snapshot["tick"]),
        "metrics": {key: round(float(value), 6) for key, value in snapshot.items()},
        "intentions": intention_counts,
        "agents": _agent_rows(model),
    }


def build_replay(config: dict[str, Any], output_dir: Path | str) -> dict[str, Any]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    parameters = dict(config.get("parameters", {}))
    for key, value in list(parameters.items()):
        if isinstance(value, list):
            parameters[key] = value[-1]
    steps = int(config.get("single_run", {}).get("steps", config.get("steps", 80)))
    seed = int(config.get("single_run", {}).get("seed", config.get("seeds", [11])[0]))
    single_params = dict(config.get("single_run", {}).get("parameters", {}))
    parameters.update(single_params)
    samples, sampling = load_behavior_samples(config.get("llm_sampling"), target)

    model = BDIPolarizationModel(seed=seed, llm_behavior_samples=samples, **parameters)
    frames = [_frame(model)]
    for _ in range(steps):
        model.step()
        frames.append(_frame(model))

    replay = {
        "model": "BDI Recommendation Polarization",
        "question": (
            "Single seeded replay of BDI agents exposed to recommender-ranked content "
            "and group-action feedback."
        ),
        "seed": seed,
        "steps": steps,
        "parameters": parameters,
        "llm_sampling": sampling,
        "llm_behavior_samples": samples,
        "frames": frames,
        "evidence_boundary": (
            "One seeded replay is useful for inspecting mechanism flow. Use batch "
            "summary outputs for stochastic claims."
        ),
    }
    (target / "single_run_replay.json").write_text(json.dumps(replay, indent=2), encoding="utf-8")
    return replay


def render_html(replay: dict[str, Any]) -> str:
    payload = json.dumps(replay, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>BDI Single Run Replay</title>
  <style>
    :root {{
      --paper: #f7f4ef;
      --ink: #1d2525;
      --muted: #697272;
      --line: #c9d0ca;
      --left: #2e6f9e;
      --right: #b64b3c;
      --llm: #7d4cc2;
      --panel: #ffffff;
      --action: #c98b2b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .shell {{
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      min-height: 100vh;
    }}
    aside {{
      border-right: 1px solid var(--line);
      padding: 24px;
      background: #ece8df;
    }}
    main {{
      padding: 24px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 30px;
      line-height: 1.05;
      letter-spacing: 0;
    }}
    .brief, .small {{
      color: var(--muted);
      line-height: 1.45;
      font-size: 13px;
    }}
    .controls {{
      display: grid;
      gap: 12px;
      margin: 24px 0;
    }}
    button {{
      border: 1px solid var(--ink);
      background: var(--ink);
      color: white;
      min-height: 38px;
      padding: 0 14px;
      cursor: pointer;
      font-weight: 650;
    }}
    button.secondary {{
      color: var(--ink);
      background: transparent;
    }}
    input[type="range"] {{
      width: 100%;
      accent-color: var(--ink);
    }}
    .tick {{
      display: flex;
      justify-content: space-between;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
      gap: 16px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      padding: 16px;
      min-width: 0;
    }}
    .panel h2 {{
      margin: 0 0 12px;
      font-size: 14px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: auto;
      background: #fbfaf7;
      border: 1px solid #e2e2dc;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }}
    .metric {{
      border-bottom: 1px solid var(--line);
      padding-bottom: 8px;
    }}
    .metric strong {{
      display: block;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 22px;
    }}
    .metric span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
      font-size: 12px;
      color: var(--muted);
    }}
    .swatch {{
      display: inline-block;
      width: 10px;
      height: 10px;
      margin-right: 5px;
      border-radius: 50%;
    }}
    .params {{
      margin-top: 20px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.5;
      color: #344040;
    }}
    @media (max-width: 920px) {{
      .shell {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--line); }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <h1>BDI single run replay</h1>
      <p class="brief">Inspect one seeded simulation: recommendations pull agents toward familiar content, group action injects amplified content, and a small sampled set uses opencode-derived behavior profiles.</p>
      <div class="controls">
        <button id="play">Play</button>
        <button id="reset" class="secondary">Reset</button>
        <input id="scrub" type="range" min="0" max="0" value="0">
        <div class="tick"><span id="tickLabel">tick 0</span><span id="stepLabel"></span></div>
      </div>
      <p class="small" id="boundary"></p>
      <div class="params" id="params"></div>
    </aside>
    <main>
      <div class="grid">
        <section class="panel">
          <h2>Agent belief field</h2>
          <canvas id="field" width="900" height="500"></canvas>
          <div class="legend">
            <span><i class="swatch" style="background: var(--left)"></i>negative belief</span>
            <span><i class="swatch" style="background: var(--right)"></i>positive belief</span>
            <span><i class="swatch" style="background: var(--llm)"></i>opencode sampled</span>
          </div>
        </section>
        <section class="panel">
          <h2>Current metrics</h2>
          <div class="metrics" id="metrics"></div>
          <canvas id="intentions" width="440" height="260"></canvas>
        </section>
        <section class="panel">
          <h2>Metric traces</h2>
          <canvas id="trace" width="900" height="300"></canvas>
        </section>
        <section class="panel">
          <h2>Sampled behavior profiles</h2>
          <div id="samples" class="small"></div>
        </section>
      </div>
    </main>
  </div>
  <script>
    const replay = {payload};
    const frames = replay.frames;
    let index = 0;
    let timer = null;
    const scrub = document.getElementById('scrub');
    const play = document.getElementById('play');
    const reset = document.getElementById('reset');
    scrub.max = String(frames.length - 1);
    document.getElementById('stepLabel').textContent = `${{frames.length}} frames`;
    document.getElementById('boundary').textContent = replay.evidence_boundary;
    document.getElementById('params').innerHTML = Object.entries(replay.parameters)
      .map(([key, value]) => `<div>${{key}} = ${{value}}</div>`).join('');
    document.getElementById('samples').innerHTML = replay.llm_behavior_samples
      .map(sample => `<p><strong>${{sample.name}}</strong><br>credulity ${{sample.credulity}}, activism ${{sample.activism}}, novelty ${{sample.novelty_bias}}, moderation ${{sample.moderation_bias}}</p>`)
      .join('');

    function canvas(id) {{
      const el = document.getElementById(id);
      return [el, el.getContext('2d')];
    }}
    function scale(value, a, b, c, d) {{
      return c + (value - a) * (d - c) / (b - a);
    }}
    function drawField(frame) {{
      const [el, ctx] = canvas('field');
      ctx.clearRect(0, 0, el.width, el.height);
      ctx.strokeStyle = '#c9d0ca';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(el.width / 2, 34);
      ctx.lineTo(el.width / 2, el.height - 34);
      ctx.stroke();
      ctx.fillStyle = '#697272';
      ctx.font = '12px ui-monospace, monospace';
      ctx.fillText('-1', 20, el.height - 14);
      ctx.fillText('0', el.width / 2 - 4, el.height - 14);
      ctx.fillText('+1', el.width - 42, el.height - 14);
      frame.agents.forEach((agent, i) => {{
        const x = scale(agent.belief, -1, 1, 34, el.width - 34);
        const band = i % 24;
        const y = 44 + band * ((el.height - 88) / 23);
        ctx.beginPath();
        ctx.fillStyle = agent.isLlm ? '#7d4cc2' : (agent.belief < 0 ? '#2e6f9e' : '#b64b3c');
        ctx.globalAlpha = agent.intention === 'mobilize' ? 0.96 : agent.intention === 'share' ? 0.76 : 0.55;
        ctx.arc(x, y, agent.isLlm ? 5.2 : 3.7, 0, Math.PI * 2);
        ctx.fill();
      }});
      ctx.globalAlpha = 1;
    }}
    function drawIntentions(frame) {{
      const [el, ctx] = canvas('intentions');
      ctx.clearRect(0, 0, el.width, el.height);
      const entries = Object.entries(frame.intentions);
      const max = Math.max(...entries.map(([, v]) => v), 1);
      entries.forEach(([name, value], i) => {{
        const y = 34 + i * 52;
        const w = scale(value, 0, max, 0, el.width - 150);
        ctx.fillStyle = name === 'mobilize' ? '#c98b2b' : '#647274';
        ctx.fillRect(112, y, w, 28);
        ctx.fillStyle = '#1d2525';
        ctx.font = '13px ui-monospace, monospace';
        ctx.fillText(name, 16, y + 19);
        ctx.fillText(String(value), 120 + w, y + 19);
      }});
    }}
    function drawTrace() {{
      const [el, ctx] = canvas('trace');
      ctx.clearRect(0, 0, el.width, el.height);
      const series = [
        ['polarization_index', '#b64b3c'],
        ['action_rate', '#c98b2b'],
        ['mean_recommendation_alignment', '#2e6f9e']
      ];
      ctx.strokeStyle = '#d8ded8';
      ctx.beginPath();
      ctx.moveTo(40, 26);
      ctx.lineTo(40, el.height - 32);
      ctx.lineTo(el.width - 20, el.height - 32);
      ctx.stroke();
      series.forEach(([metric, color]) => {{
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.beginPath();
        frames.forEach((frame, i) => {{
          const x = scale(i, 0, frames.length - 1, 42, el.width - 24);
          const y = scale(frame.metrics[metric], 0, 1, el.height - 34, 28);
          if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }});
        ctx.stroke();
      }});
      const cursorX = scale(index, 0, frames.length - 1, 42, el.width - 24);
      ctx.strokeStyle = '#1d2525';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(cursorX, 24);
      ctx.lineTo(cursorX, el.height - 30);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = '12px ui-monospace, monospace';
      ctx.fillStyle = '#1d2525';
      ctx.fillText('polarization', 52, 20);
      ctx.fillStyle = '#c98b2b';
      ctx.fillText('action', 164, 20);
      ctx.fillStyle = '#2e6f9e';
      ctx.fillText('alignment', 232, 20);
    }}
    function render() {{
      const frame = frames[index];
      scrub.value = String(index);
      document.getElementById('tickLabel').textContent = `tick ${{frame.tick}}`;
      const metrics = frame.metrics;
      document.getElementById('metrics').innerHTML = [
        ['Polarization', metrics.polarization_index],
        ['Extreme share', metrics.extreme_share],
        ['Action rate', metrics.action_rate],
        ['Alignment', metrics.mean_recommendation_alignment],
        ['Group actions', metrics.group_actions],
        ['Content pool', metrics.content_pool_size]
      ].map(([label, value]) => `<div class="metric"><strong>${{Number(value).toFixed(3)}}</strong><span>${{label}}</span></div>`).join('');
      drawField(frame);
      drawIntentions(frame);
      drawTrace();
    }}
    function stop() {{
      clearInterval(timer);
      timer = null;
      play.textContent = 'Play';
    }}
    play.addEventListener('click', () => {{
      if (timer) {{ stop(); return; }}
      play.textContent = 'Pause';
      timer = setInterval(() => {{
        index = index >= frames.length - 1 ? 0 : index + 1;
        render();
      }}, 180);
    }});
    reset.addEventListener('click', () => {{ stop(); index = 0; render(); }});
    scrub.addEventListener('input', event => {{ stop(); index = Number(event.target.value); render(); }});
    render();
  </script>
</body>
</html>
"""


def write_viewer(replay: dict[str, Any], output_path: Path | str) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_html(replay), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a single-run BDI polarization replay.")
    parser.add_argument("--config", type=Path, default=Path("examples/bdi_polarization_mesa/experiment.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/bdi_polarization_single"))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    replay = build_replay(config, args.output_dir)
    output = args.output or args.output_dir / "single_run_viewer.html"
    print(write_viewer(replay, output))


if __name__ == "__main__":
    main()
