"""Generate a self-contained global warming system-dynamics page."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import DEFAULT_SCENARIOS, checkpoint_summary, run_default_scenarios


def build_global_warming_html() -> str:
    rows_by_scenario = run_default_scenarios()
    payload = {
        "scenarios": [scenario.__dict__ for scenario in DEFAULT_SCENARIOS],
        "rowsByScenario": rows_by_scenario,
        "checkpoints": checkpoint_summary(rows_by_scenario),
    }
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return HTML_TEMPLATE.replace("__MODEL_DATA__", data_json)


def write_global_warming_page(target: str | Path) -> Path:
    output = Path(target)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_global_warming_html(), encoding="utf-8")
    return output


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN" data-model="global-warming-system-dynamics">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>全球变暖系统动力学模型</title>
  <style>
    :root {
      --ice: #eef7f3;
      --ink: #17211f;
      --muted: #5b6a67;
      --panel: #ffffff;
      --line: #bfd0ca;
      --ocean: #22577a;
      --green: #2f8f6f;
      --amber: #c17a2f;
      --red: #b23a48;
      --deep: #0f2d3a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        linear-gradient(90deg, rgba(34,87,122,0.10) 1px, transparent 1px),
        linear-gradient(0deg, rgba(34,87,122,0.08) 1px, transparent 1px),
        var(--ice);
      background-size: 48px 48px;
      color: var(--ink);
      font-family: "Avenir Next", "Segoe UI", system-ui, sans-serif;
    }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(300px, 380px) minmax(0, 1fr);
    }
    .controls {
      border-right: 1px solid var(--line);
      padding: 22px;
      background: rgba(255,255,255,0.74);
      backdrop-filter: blur(8px);
    }
    h1 {
      margin: 0 0 10px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(30px, 5vw, 58px);
      line-height: 0.95;
      letter-spacing: 0;
    }
    .subtitle, .source, .note, label {
      color: var(--muted);
      line-height: 1.55;
      font-size: 14px;
    }
    .signature {
      margin: 20px 0;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, #fff, #e7f0ec);
      height: 210px;
      position: relative;
      overflow: hidden;
    }
    .signature svg { width: 100%; height: 100%; display: block; }
    .knob {
      margin: 18px 0;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
    }
    input[type="range"] {
      grid-column: 1 / -1;
      width: 100%;
      accent-color: var(--ocean);
    }
    .scenario-buttons {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 18px 0;
    }
    button {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
      font: inherit;
    }
    button[aria-pressed="true"] {
      border-color: var(--deep);
      box-shadow: inset 0 -3px 0 var(--accent, var(--ocean));
      font-weight: 700;
    }
    button:focus-visible, input:focus-visible {
      outline: 2px solid var(--ocean);
      outline-offset: 2px;
    }
    .source {
      border-top: 1px solid var(--line);
      margin-top: 18px;
      padding-top: 14px;
    }
    .source a { color: var(--deep); }
    main {
      padding: 22px;
      display: grid;
      gap: 14px;
      align-content: start;
    }
    .topline {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }
    .metric, .chart-panel, .table-panel, .claim, .sd-panel {
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.86);
      border-radius: 8px;
    }
    .metric {
      min-height: 92px;
      padding: 12px;
    }
    .metric span, th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
    }
    .metric strong {
      display: block;
      margin-top: 6px;
      font-size: 26px;
      line-height: 1;
    }
    .chart-panel, .table-panel, .claim, .sd-panel { padding: 14px; }
    h2 {
      margin: 0 0 10px;
      font-size: 15px;
      letter-spacing: 0;
    }
    .chart {
      width: 100%;
      height: 330px;
      display: block;
      background: #f9fcfb;
      border: 1px solid #d8e4df;
      border-radius: 6px;
    }
    .sd-panel {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
      gap: 14px;
      align-items: stretch;
    }
    .sd-canvas {
      width: 100%;
      min-height: 320px;
      display: block;
      background:
        radial-gradient(circle at 20% 35%, rgba(34,87,122,0.08), transparent 26%),
        #f9fcfb;
      border: 1px solid #d8e4df;
      border-radius: 6px;
    }
    .equation-panel {
      display: grid;
      gap: 10px;
      align-content: start;
    }
    .equation {
      border: 1px solid #dbe6e2;
      border-radius: 6px;
      background: #fff;
      padding: 10px;
    }
    .equation span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      margin-bottom: 4px;
    }
    .equation code {
      white-space: normal;
      color: var(--deep);
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
    }
    .grid-two {
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.9fr);
      gap: 14px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      border-bottom: 1px solid #dbe6e2;
      padding: 8px 6px;
      text-align: right;
    }
    th:first-child, td:first-child { text-align: left; }
    .claim {
      display: grid;
      gap: 10px;
    }
    .claim strong { color: var(--deep); }
    .badge {
      display: inline-flex;
      align-items: center;
      width: fit-content;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      color: var(--muted);
      font-size: 12px;
      background: #fff;
    }
    @media (max-width: 980px) {
      .shell { grid-template-columns: 1fr; }
      .controls { border-right: 0; border-bottom: 1px solid var(--line); }
      .topline { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid-two, .sd-panel { grid-template-columns: 1fr; }
    }
    @media (max-width: 560px) {
      .topline, .scenario-buttons { grid-template-columns: 1fr; }
      main, .controls { padding: 14px; }
      .chart { height: 260px; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside class="controls">
      <h1>全球变暖系统动力学模型</h1>
      <p class="subtitle">把排放、CO2 浓度、辐射强迫和温度响应放进一个可检查的 stock-flow 模型，用三条排放路径给出 2030、2035、2040 的短中期预测。</p>
      <div class="signature" aria-label="CO2 stock-flow glyph">
        <svg id="stockFlowGlyph" viewBox="0 0 360 210" role="img"></svg>
      </div>
      <div class="scenario-buttons" id="scenarioButtons"></div>
      <label class="knob">气候敏感度 ECS <output id="ecsValue">3.0°C</output><input id="ecs" type="range" min="2.0" max="4.5" value="3.0" step="0.1"></label>
      <label class="knob">温度响应滞后 <output id="lagValue">40 年</output><input id="lag" type="range" min="25" max="70" value="40" step="1"></label>
      <label class="knob">初始温度异常 <output id="tempValue">1.34°C</output><input id="initialTemp" type="range" min="1.15" max="1.55" value="1.34" step="0.01"></label>
      <p class="source">
        基线口径：NOAA 2025 年全球温度比 1850-1900 年高约 1.34°C；NASA/GISTEMP 2025 年低于 2024 年但仍为前三高温年；Global Carbon Project 预计 2025 年化石 CO2 排放继续创新高。来源：
        <a href="https://www.ncei.noaa.gov/news/global-climate-202513">NOAA 2025</a>,
        <a href="https://data.giss.nasa.gov/gistemp/">NASA GISTEMP</a>,
        <a href="https://globalcarbonbudget.org/">Global Carbon Budget</a>.
      </p>
    </aside>
    <main>
      <section class="topline" id="metrics" aria-label="Scenario metrics"></section>
      <section class="sd-panel" data-panel="sd-model-visualization" aria-label="System dynamics model visualization">
        <div>
          <h2>SD 模型结构：stocks、flows 与反馈回路</h2>
          <svg id="sdModelChart" class="sd-canvas" data-chart="sd-stock-flow" viewBox="0 0 760 320" role="img" aria-label="System dynamics stock and flow diagram"></svg>
        </div>
        <div>
          <h2>当前方程读数</h2>
          <div id="equationPanel" class="equation-panel" data-panel="sd-equations"></div>
        </div>
      </section>
      <section class="grid-two">
        <div class="chart-panel">
          <h2>温度路径与 1.5°C 阈值</h2>
          <svg id="temperatureChart" class="chart" data-chart="temperature-path" viewBox="0 0 760 330" role="img" aria-label="Temperature anomaly projections"></svg>
        </div>
        <div class="table-panel">
          <h2>可检验预测检查点</h2>
          <table data-table="prediction-checkpoints">
            <thead><tr><th>年份</th><th>温度</th><th>CO2</th><th>排放</th></tr></thead>
            <tbody id="checkpointRows"></tbody>
          </table>
        </div>
      </section>
      <section class="grid-two">
        <div class="chart-panel">
          <h2>CO2 stock 累积</h2>
          <svg id="co2Chart" class="chart" data-chart="co2-stock" viewBox="0 0 760 330" role="img" aria-label="CO2 concentration projections"></svg>
        </div>
        <div class="claim" id="claims" data-panel="prediction-claims"></div>
      </section>
    </main>
  </div>
  <script id="modelData" type="application/json">__MODEL_DATA__</script>
  <script>
    const modelData = JSON.parse(document.getElementById("modelData").textContent);
    const START_YEAR = 2025;
    const END_YEAR = 2040;
    const PREINDUSTRIAL_CO2_PPM = 278.0;
    const GTCO2_PER_PPM = 7.82;
    const FORCING_PER_DOUBLING = 3.71;
    let selectedScenario = "baseline";

    function simulateScenario(scenario, settings) {
      let co2Ppm = 424.6;
      let emissions = 42.2;
      let temperature = settings.initialTemp;
      let nonCo2Forcing = scenario.non_co2_forcing_2025;
      const feedbackGain = settings.ecs / FORCING_PER_DOUBLING;
      const rows = [];
      for (let year = START_YEAR; year <= END_YEAR; year += 1) {
        const co2Forcing = 5.35 * Math.log(co2Ppm / PREINDUSTRIAL_CO2_PPM);
        const forcing = co2Forcing + nonCo2Forcing;
        const equilibriumTemperature = feedbackGain * forcing;
        rows.push({
          year,
          scenario: scenario.key,
          scenarioName: scenario.name,
          emissionsGtco2: emissions,
          co2Ppm,
          forcing,
          temperatureC: temperature,
          equilibriumTemperatureC: equilibriumTemperature,
          warmingRate: (equilibriumTemperature - temperature) / settings.lag
        });
        emissions *= 1 + scenario.annual_emissions_change;
        co2Ppm += emissions * scenario.airborne_fraction / GTCO2_PER_PPM;
        nonCo2Forcing += scenario.non_co2_forcing_change;
        temperature += (equilibriumTemperature - temperature) / settings.lag;
      }
      return rows;
    }

    function settings() {
      return {
        ecs: Number(document.getElementById("ecs").value),
        lag: Number(document.getElementById("lag").value),
        initialTemp: Number(document.getElementById("initialTemp").value)
      };
    }

    function allRows(currentSettings) {
      const map = {};
      for (const scenario of modelData.scenarios) {
        map[scenario.key] = simulateScenario(scenario, currentSettings);
      }
      return map;
    }

    function scale(value, domainMin, domainMax, rangeMin, rangeMax) {
      return rangeMin + ((value - domainMin) / (domainMax - domainMin)) * (rangeMax - rangeMin);
    }

    function drawLineChart(svgId, rowsByScenario, field, domain, unit, threshold) {
      const svg = document.getElementById(svgId);
      const width = 760;
      const height = 330;
      const pad = { left: 54, right: 24, top: 22, bottom: 38 };
      svg.innerHTML = "";
      const yTicks = 5;
      for (let i = 0; i <= yTicks; i += 1) {
        const value = domain[0] + (domain[1] - domain[0]) * i / yTicks;
        const y = scale(value, domain[0], domain[1], height - pad.bottom, pad.top);
        svg.insertAdjacentHTML("beforeend", `<line x1="${pad.left}" y1="${y}" x2="${width-pad.right}" y2="${y}" stroke="#d8e4df"/><text x="12" y="${y+4}" font-size="12" fill="#5b6a67">${value.toFixed(field === "co2Ppm" ? 0 : 2)}${unit}</text>`);
      }
      for (let year = START_YEAR; year <= END_YEAR; year += 5) {
        const x = scale(year, START_YEAR, END_YEAR, pad.left, width - pad.right);
        svg.insertAdjacentHTML("beforeend", `<line x1="${x}" y1="${pad.top}" x2="${x}" y2="${height-pad.bottom}" stroke="#edf4f1"/><text x="${x}" y="${height-12}" text-anchor="middle" font-size="12" fill="#5b6a67">${year}</text>`);
      }
      if (threshold) {
        const y = scale(threshold, domain[0], domain[1], height - pad.bottom, pad.top);
        svg.insertAdjacentHTML("beforeend", `<line x1="${pad.left}" y1="${y}" x2="${width-pad.right}" y2="${y}" stroke="#b23a48" stroke-dasharray="6 6"/><text x="${width-pad.right-6}" y="${y-7}" text-anchor="end" font-size="12" fill="#b23a48">1.5°C</text>`);
      }
      for (const scenario of modelData.scenarios) {
        const rows = rowsByScenario[scenario.key];
        const points = rows.map(row => {
          const x = scale(row.year, START_YEAR, END_YEAR, pad.left, width - pad.right);
          const y = scale(row[field], domain[0], domain[1], height - pad.bottom, pad.top);
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(" ");
        const active = scenario.key === selectedScenario;
        svg.insertAdjacentHTML("beforeend", `<polyline points="${points}" fill="none" stroke="${scenario.color}" stroke-width="${active ? 4 : 2}" opacity="${active ? 1 : 0.45}"/>`);
        const last = rows[rows.length - 1];
        const lx = scale(last.year, START_YEAR, END_YEAR, pad.left, width - pad.right);
        const ly = scale(last[field], domain[0], domain[1], height - pad.bottom, pad.top);
        svg.insertAdjacentHTML("beforeend", `<circle cx="${lx}" cy="${ly}" r="${active ? 5 : 3}" fill="${scenario.color}"/><text x="${lx-6}" y="${ly-9}" text-anchor="end" font-size="12" fill="${scenario.color}">${scenario.name}</text>`);
      }
    }

    function drawGlyph(row, scenario) {
      const svg = document.getElementById("stockFlowGlyph");
      const fill = scenario.color;
      const ppmLevel = Math.min(1, (row.co2Ppm - 410) / 45);
      const tempLevel = Math.min(1, (row.temperatureC - 1.2) / 0.7);
      svg.innerHTML = `
        <rect x="32" y="${150 - ppmLevel * 70}" width="96" height="${ppmLevel * 70 + 26}" fill="${fill}" opacity="0.20"/>
        <rect x="32" y="54" width="96" height="122" fill="none" stroke="#22577a" stroke-width="2"/>
        <text x="80" y="44" text-anchor="middle" font-size="13" fill="#17211f">CO2 stock</text>
        <path d="M137 116 C184 88 194 88 236 116" fill="none" stroke="${fill}" stroke-width="4"/>
        <polygon points="235,110 250,116 235,122" fill="${fill}"/>
        <circle cx="285" cy="116" r="${32 + tempLevel * 24}" fill="${fill}" opacity="0.18" stroke="${fill}" stroke-width="3"/>
        <text x="285" y="112" text-anchor="middle" font-size="22" fill="#17211f">${row.temperatureC.toFixed(2)}°C</text>
        <text x="285" y="133" text-anchor="middle" font-size="12" fill="#5b6a67">surface response</text>
        <text x="80" y="192" text-anchor="middle" font-size="13" fill="#5b6a67">${row.co2Ppm.toFixed(0)} ppm</text>
        <text x="190" y="82" text-anchor="middle" font-size="12" fill="#5b6a67">${row.forcing.toFixed(2)} W/m²</text>`;
    }

    function drawSDModel(row, scenario, currentSettings) {
      const svg = document.getElementById("sdModelChart");
      const active = scenario.color;
      const airborneGtco2 = row.emissionsGtco2 * scenario.airborne_fraction;
      const uptakeGtco2 = row.emissionsGtco2 - airborneGtco2;
      const heatGap = row.equilibriumTemperatureC - row.temperatureC;
      const co2Level = Math.min(1, Math.max(0, (row.co2Ppm - 420) / 65));
      const tempLevel = Math.min(1, Math.max(0, (row.temperatureC - 1.2) / 0.85));
      svg.innerHTML = `
        <defs>
          <marker id="arrowActive" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="${active}"/>
          </marker>
          <marker id="arrowMuted" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#78918a"/>
          </marker>
        </defs>
        <text x="28" y="32" font-size="13" font-weight="700" fill="#17211f">${scenario.name} · 2040 年状态</text>
        <rect x="230" y="78" width="150" height="94" rx="4" fill="#fff" stroke="#22577a" stroke-width="2"/>
        <rect x="230" y="${152 - co2Level * 62}" width="150" height="${20 + co2Level * 62}" fill="${active}" opacity="0.18"/>
        <text x="305" y="110" text-anchor="middle" font-size="14" font-weight="700" fill="#17211f">大气 CO2</text>
        <text x="305" y="133" text-anchor="middle" font-size="22" fill="#17211f">${row.co2Ppm.toFixed(0)} ppm</text>
        <text x="305" y="154" text-anchor="middle" font-size="12" fill="#5b6a67">stock</text>
        <path d="M70 126 H214" fill="none" stroke="${active}" stroke-width="4" marker-end="url(#arrowActive)"/>
        <text x="142" y="103" text-anchor="middle" font-size="12" fill="#17211f">排放流入</text>
        <text x="142" y="120" text-anchor="middle" font-size="12" fill="#5b6a67">${row.emissionsGtco2.toFixed(1)} GtCO2/年</text>
        <path d="M305 178 C305 236 170 238 118 202" fill="none" stroke="#78918a" stroke-width="3" marker-end="url(#arrowMuted)"/>
        <text x="210" y="242" text-anchor="middle" font-size="12" fill="#5b6a67">陆地/海洋吸收 ${uptakeGtco2.toFixed(1)} GtCO2/年</text>
        <path d="M392 126 H510" fill="none" stroke="${active}" stroke-width="3" marker-end="url(#arrowActive)"/>
        <text x="452" y="103" text-anchor="middle" font-size="12" fill="#17211f">辐射强迫</text>
        <text x="452" y="120" text-anchor="middle" font-size="12" fill="#5b6a67">${row.forcing.toFixed(2)} W/m²</text>
        <circle cx="604" cy="126" r="${38 + tempLevel * 18}" fill="${active}" opacity="0.16" stroke="${active}" stroke-width="3"/>
        <text x="604" y="120" text-anchor="middle" font-size="14" font-weight="700" fill="#17211f">温度响应</text>
        <text x="604" y="143" text-anchor="middle" font-size="21" fill="#17211f">${row.temperatureC.toFixed(2)}°C</text>
        <text x="604" y="166" text-anchor="middle" font-size="12" fill="#5b6a67">stock</text>
        <path d="M612 72 C552 34 450 38 372 76" fill="none" stroke="#b23a48" stroke-width="2" stroke-dasharray="7 6" marker-end="url(#arrowMuted)"/>
        <text x="492" y="34" text-anchor="middle" font-size="12" fill="#b23a48">R1: 变暖削弱自然碳汇风险</text>
        <path d="M584 205 C500 266 360 266 287 183" fill="none" stroke="#22577a" stroke-width="2" stroke-dasharray="7 6" marker-end="url(#arrowMuted)"/>
        <text x="448" y="286" text-anchor="middle" font-size="12" fill="#22577a">B1: 减排路径降低后续流入</text>
        <line x1="526" y1="188" x2="680" y2="188" stroke="#d8e4df"/>
        <text x="604" y="212" text-anchor="middle" font-size="12" fill="#5b6a67">热惯性缺口 ${heatGap.toFixed(2)}°C / ${currentSettings.lag} 年</text>`;
    }

    function updateEquationPanel(row, scenario, currentSettings) {
      const airborneGtco2 = row.emissionsGtco2 * scenario.airborne_fraction;
      const uptakeGtco2 = row.emissionsGtco2 - airborneGtco2;
      const co2Delta = airborneGtco2 / GTCO2_PER_PPM;
      const tempDelta = row.warmingRate;
      document.getElementById("equationPanel").innerHTML = `
        <div class="equation"><span>CO2 stock 更新</span><code>CO2(t+1) = CO2(t) + 排放 × 空气留存率 / 7.82 = +${co2Delta.toFixed(2)} ppm/年</code></div>
        <div class="equation"><span>碳汇流出</span><code>吸收 = 排放 × (1 - 空气留存率) = ${uptakeGtco2.toFixed(1)} GtCO2/年</code></div>
        <div class="equation"><span>辐射强迫</span><code>F = 5.35 × ln(CO2 / 278) + 非 CO2 强迫 = ${row.forcing.toFixed(2)} W/m²</code></div>
        <div class="equation"><span>温度响应 stock</span><code>T(t+1) = T(t) + (T_eq - T) / 滞后年数 = ${tempDelta >= 0 ? "+" : ""}${tempDelta.toFixed(3)}°C/年</code></div>
        <div class="equation"><span>当前调参</span><code>ECS=${currentSettings.ecs.toFixed(1)}°C, 响应滞后=${currentSettings.lag} 年, 初始温度=${currentSettings.initialTemp.toFixed(2)}°C</code></div>`;
    }

    function update() {
      const currentSettings = settings();
      document.getElementById("ecsValue").textContent = `${currentSettings.ecs.toFixed(1)}°C`;
      document.getElementById("lagValue").textContent = `${currentSettings.lag} 年`;
      document.getElementById("tempValue").textContent = `${currentSettings.initialTemp.toFixed(2)}°C`;
      const rowsByScenario = allRows(currentSettings);
      const scenario = modelData.scenarios.find(item => item.key === selectedScenario);
      const rows = rowsByScenario[selectedScenario];
      const y2040 = rows.find(row => row.year === 2040);
      const y2030 = rows.find(row => row.year === 2030);
      const y2035 = rows.find(row => row.year === 2035);
      drawGlyph(y2040, scenario);
      drawSDModel(y2040, scenario, currentSettings);
      updateEquationPanel(y2040, scenario, currentSettings);
      drawLineChart("temperatureChart", rowsByScenario, "temperatureC", [1.2, 2.05], "°", 1.5);
      drawLineChart("co2Chart", rowsByScenario, "co2Ppm", [420, 485], " ppm");
      document.getElementById("metrics").innerHTML = `
        <div class="metric"><span>当前场景</span><strong>${scenario.name}</strong></div>
        <div class="metric"><span>2030 温度异常</span><strong>${y2030.temperatureC.toFixed(2)}°C</strong></div>
        <div class="metric"><span>2035 温度异常</span><strong>${y2035.temperatureC.toFixed(2)}°C</strong></div>
        <div class="metric"><span>2040 CO2 浓度</span><strong>${y2040.co2Ppm.toFixed(0)} ppm</strong></div>`;
      document.getElementById("checkpointRows").innerHTML = [2030, 2035, 2040].map(year => {
        const row = rows.find(item => item.year === year);
        return `<tr><td>${year}</td><td>${row.temperatureC.toFixed(2)}°C</td><td>${row.co2Ppm.toFixed(0)} ppm</td><td>${row.emissionsGtco2.toFixed(1)} GtCO2/年</td></tr>`;
      }).join("");
      const thresholdYear = rows.find(row => row.temperatureC >= 1.5)?.year || "2040 后";
      document.getElementById("claims").innerHTML = `
        <span class="badge">模型结论，可复算</span>
        <div><strong>短期：</strong>到 2030 年，${scenario.name} 场景给出 ${y2030.temperatureC.toFixed(2)}°C，主要由已累积 CO2 stock 和温度响应滞后决定。</div>
        <div><strong>中期：</strong>到 2035 年，该场景为 ${y2035.temperatureC.toFixed(2)}°C；若使用当前所选路径，1.5°C 年均阈值在 ${thresholdYear} 附近被触及。</div>
        <div><strong>可检验性：</strong>每年更新三项观测即可复核：全球 CO2 ppm、全球 CO2 排放、相对 1850-1900 的温度异常。若 2030 年观测温度偏离本页同场景超过约 0.15°C，应重新校准 ECS、非 CO2 强迫和海洋热吸收滞后。</div>
        <p class="note">证据边界：本页比较政策路径和阈值风险，不模拟 ENSO、气溶胶细分、区域反馈、冰盖动力学或极端天气频率。</p>`;
    }

    function setup() {
      document.getElementById("scenarioButtons").innerHTML = modelData.scenarios.map(scenario => `<button style="--accent:${scenario.color}" data-scenario="${scenario.key}" aria-pressed="${scenario.key === selectedScenario}">${scenario.name}</button>`).join("");
      document.getElementById("scenarioButtons").addEventListener("click", event => {
        const button = event.target.closest("button[data-scenario]");
        if (!button) return;
        selectedScenario = button.dataset.scenario;
        document.querySelectorAll("button[data-scenario]").forEach(item => item.setAttribute("aria-pressed", String(item.dataset.scenario === selectedScenario)));
        update();
      });
      ["ecs", "lag", "initialTemp"].forEach(id => document.getElementById(id).addEventListener("input", update));
      update();
    }
    setup();
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="examples/global_warming_system_dynamics/index.html",
        help="Path to write the self-contained page.",
    )
    args = parser.parse_args()
    output = write_global_warming_page(args.output)
    print(output)


if __name__ == "__main__":
    main()
