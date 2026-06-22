"""Generate a self-contained legacy JavaScript Field Service app."""

from __future__ import annotations

import argparse
from pathlib import Path


LEGACY_APP_HTML = r"""<!doctype html>
<html lang="en" data-runtime="legacy-js">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Field Service Legacy JS</title>
  <style>
    :root {
      --paper: #f4f6f1;
      --ink: #1f2926;
      --muted: #66736e;
      --line: #c8d0ca;
      --panel: #ffffff;
      --working: #2f86a6;
      --queued: #d6a437;
      --failed: #c94f3d;
      --service: #2f8b62;
      --crew: #513f93;
      --profit: #1c6f5a;
      --queue: #b95d3b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .shell {
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(290px, 350px) minmax(560px, 1fr) minmax(320px, 400px);
      gap: 16px;
      padding: 16px;
    }
    aside {
      border-right: 1px solid var(--line);
      padding-right: 16px;
    }
    .right-rail {
      border-left: 1px solid var(--line);
      padding-left: 16px;
    }
    h1 {
      margin: 0 0 10px;
      font-size: 25px;
      line-height: 1.06;
      letter-spacing: 0;
    }
    h2 {
      margin: 0 0 8px;
      font-size: 13px;
      letter-spacing: 0;
      text-transform: uppercase;
      color: #52645e;
    }
    .source, label, .readout {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }
    .controls {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
      margin: 14px 0;
    }
    button {
      min-height: 36px;
      border: 1px solid #aeb9b2;
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      font: inherit;
      cursor: pointer;
    }
    button:hover, button:focus-visible {
      border-color: var(--crew);
      outline: none;
      box-shadow: 0 0 0 2px rgba(81, 63, 147, 0.15);
    }
    .field {
      display: grid;
      gap: 10px;
      margin-top: 16px;
    }
    label {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 8px;
      align-items: center;
    }
    input[type="range"] {
      grid-column: 1 / -1;
      width: 100%;
      accent-color: var(--crew);
    }
    input[type="checkbox"] { accent-color: var(--crew); }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 14px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px;
      background: var(--panel);
    }
    .metric span {
      display: block;
      color: var(--muted);
      font-size: 12px;
    }
    .metric strong {
      display: block;
      margin-top: 3px;
      font-size: 20px;
      font-weight: 720;
    }
    main { min-width: 0; }
    #situation {
      width: 100%;
      max-height: calc(100vh - 32px);
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #eef2ec;
    }
    .chart {
      width: 100%;
      height: 150px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      margin-bottom: 12px;
    }
    .log {
      height: min(320px, 36vh);
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #101715;
      color: #d9e7df;
      padding: 8px;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
    }
    .log div {
      border-bottom: 1px solid rgba(217, 231, 223, 0.11);
      padding: 4px 0;
    }
    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 10px;
      color: var(--muted);
      font-size: 12px;
    }
    .key {
      display: inline-flex;
      align-items: center;
      gap: 5px;
    }
    .swatch {
      width: 10px;
      height: 10px;
      border-radius: 2px;
      display: inline-block;
    }
    @media (max-width: 1060px) {
      .shell { grid-template-columns: minmax(290px, 350px) 1fr; }
      .right-rail {
        grid-column: 1 / -1;
        border-left: 0;
        border-top: 1px solid var(--line);
        padding: 14px 0 0;
      }
    }
    @media (max-width: 760px) {
      .shell { grid-template-columns: 1fr; }
      aside {
        border-right: 0;
        border-bottom: 1px solid var(--line);
        padding: 0 0 14px;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <h1>Field Service Legacy JS</h1>
      <div class="source">Vanilla JavaScript browser model: mobile service crews repair, maintain, and replace revenue-generating equipment.</div>
      <div class="controls">
        <button id="step">Step</button>
        <button id="run30">Run 30</button>
        <button id="startStop">Start</button>
        <button id="reset">Reset</button>
      </div>
      <div class="field">
        <label>Seed <output id="seedValue">42</output><input id="seed" type="range" min="1" max="999" value="42"></label>
        <label>Equipment <output id="equipmentValue">100</output><input id="equipmentCount" type="range" min="20" max="150" value="100"></label>
        <label>Service crews <output id="crewValue">3</output><input id="serviceCapacity" type="range" min="1" max="8" value="3"></label>
        <label>Failure rate <output id="failureValue">0.030</output><input id="failureRate" type="range" min="0" max="0.1" step="0.005" value="0.03"></label>
        <label>Step delay (s) <output id="delayValue">0.25</output><input id="stepDelay" type="range" min="0.05" max="1" step="0.05" value="0.25"></label>
        <label style="display:flex;justify-content:space-between"><span>Replace old equipment</span><input id="replaceOld" type="checkbox"></label>
      </div>
      <div class="metric-grid" id="metrics"></div>
      <div class="legend">
        <span class="key"><span class="swatch" style="background:var(--working)"></span>working</span>
        <span class="key"><span class="swatch" style="background:var(--queued)"></span>queued</span>
        <span class="key"><span class="swatch" style="background:var(--failed)"></span>failed</span>
        <span class="key"><span class="swatch" style="background:var(--service)"></span>in service</span>
        <span class="key"><span class="swatch" style="background:var(--crew)"></span>crew</span>
      </div>
    </aside>
    <main>
      <svg id="situation" data-layer="situation-animation" viewBox="0 0 610 510" role="img" aria-label="Field service situation animation"></svg>
    </main>
    <section class="right-rail" aria-label="Metrics and log">
      <h2>Profit trajectory</h2>
      <svg id="profitChart" class="chart" data-chart="profit" viewBox="0 0 360 150" role="img" aria-label="Profit over time"></svg>
      <h2>Request queues</h2>
      <svg id="queueChart" class="chart" data-chart="queues" viewBox="0 0 360 150" role="img" aria-label="Service and maintenance queues"></svg>
      <h2>Dispatch log</h2>
      <div id="eventLog" class="log" data-panel="event-log" role="log" aria-label="Event log"></div>
    </section>
  </div>
  <script>
  (function () {
    var WIDTH = 610;
    var HEIGHT = 510;
    var HOME = { x: 60, y: 455 };
    var model = null;
    var timer = null;
    var history = [];

    function Lcg(seed) {
      this.state = seed % 2147483647;
      if (this.state <= 0) this.state += 2147483646;
    }
    Lcg.prototype.next = function () {
      this.state = this.state * 16807 % 2147483647;
      return (this.state - 1) / 2147483646;
    };
    Lcg.prototype.uniform = function (min, max) {
      return min + (max - min) * this.next();
    };

    function byId(id) { return document.getElementById(id); }
    function num(id) { return Number(byId(id).value); }
    function dist(a, b) {
      var dx = a.x - b.x;
      var dy = a.y - b.y;
      return Math.sqrt(dx * dx + dy * dy);
    }
    function moveToward(pos, target, speed) {
      var d = dist(pos, target);
      if (d === 0 || speed <= 0) return { x: pos.x, y: pos.y };
      var ratio = Math.min(1, speed / d);
      return { x: pos.x + (target.x - pos.x) * ratio, y: pos.y + (target.y - pos.y) * ratio };
    }
    function money(value) {
      var sign = value < 0 ? "-" : "";
      var abs = Math.abs(value);
      if (abs >= 1000000) return sign + "$" + (abs / 1000000).toFixed(1) + "M";
      if (abs >= 1000) return sign + "$" + Math.round(abs / 1000) + "k";
      return sign + "$" + Math.round(abs);
    }
    function svgEl(name, attrs, text) {
      var node = document.createElementNS("http://www.w3.org/2000/svg", name);
      var key;
      attrs = attrs || {};
      for (key in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, key)) node.setAttribute(key, attrs[key]);
      }
      if (text) node.textContent = text;
      return node;
    }
    function log(message) {
      model.events.push({ time: model.time, message: message });
      if (model.events.length > 250) model.events = model.events.slice(model.events.length - 250);
    }

    function initModel() {
      var seed = num("seed");
      var equipmentCount = num("equipmentCount");
      var serviceCapacity = num("serviceCapacity");
      var normalFailureRate = num("failureRate");
      var rng = new Lcg(seed);
      var equipment = [];
      var cols = Math.ceil(Math.sqrt(equipmentCount));
      var rows = Math.ceil(equipmentCount / cols);
      var xGap = (WIDTH - 150) / Math.max(1, cols);
      var yGap = (HEIGHT - 120) / Math.max(1, rows);
      var i;
      for (i = 0; i < equipmentCount; i += 1) {
        var col = i % cols;
        var row = Math.floor(i / cols);
        equipment.push({
          id: "unit-" + i,
          x: Math.max(95, Math.min(WIDTH - 20, 130 + (col + 0.5) * xGap + rng.uniform(-8, 8))),
          y: Math.max(25, Math.min(HEIGHT - 25, 50 + (row + 0.5) * yGap + rng.uniform(-8, 8))),
          state: "working",
          assignedCrewId: "",
          maintenanceRequested: false,
          requestTime: null,
          timeLastReplacement: 0,
          timeLastMaintenance: rng.uniform(-90, 0)
        });
      }
      var crews = [];
      for (i = 0; i < serviceCapacity; i += 1) {
        crews.push({
          id: "crew-" + i,
          x: HOME.x,
          y: HOME.y,
          state: "idle",
          equipmentUnit: null,
          taskType: "",
          workRemaining: 0,
          travelTarget: { x: HOME.x, y: HOME.y }
        });
      }
      model = {
        rng: rng,
        equipment: equipment,
        crews: crews,
        serviceRequests: [],
        maintenanceRequests: [],
        normalFailureRate: normalFailureRate,
        replaceOldEquipment: byId("replaceOld").checked,
        crewSpeed: 75,
        maintenancePeriod: 90,
        repairTypicalTime: 5,
        maintenanceMeanTime: 3,
        replacementMeanTime: 12,
        replacementProbability: 0.1,
        mtcePeriodsToReplace: 5,
        dailyRevenuePerUnit: 400,
        serviceCrewCostPerDay: 1000,
        repairCost: 1000,
        maintenanceCost: 600,
        replacementCost: 10000,
        time: 0,
        revenue: 0,
        workCost: 0,
        crewCost: 0,
        failuresObserved: 0,
        repairsCompleted: 0,
        maintenanceCompleted: 0,
        replacementsCompleted: 0,
        events: []
      };
      history = [snapshot()];
      render();
    }

    function age(unit) { return Math.max(0, model.time - unit.timeLastReplacement); }
    function maintenanceOverdue(unit) { return model.time - unit.timeLastMaintenance >= model.maintenancePeriod; }
    function failureProbability(unit) {
      var timeSinceMaintenance = Math.max(0, model.time - unit.timeLastMaintenance);
      var overdueFactor = Math.max(1, timeSinceMaintenance / Math.max(1, model.maintenancePeriod));
      var ageFactor = Math.max(1, age(unit) / Math.max(1, 3 * model.maintenancePeriod));
      var rate = model.normalFailureRate * overdueFactor * ageFactor;
      return Math.max(0, Math.min(0.95, 1 - Math.exp(-rate)));
    }
    function crewHandling(unit) {
      var i;
      for (i = 0; i < model.crews.length; i += 1) {
        if (model.crews[i].equipmentUnit === unit) return true;
      }
      return false;
    }
    function requestService(unit) {
      var mtceIndex = model.maintenanceRequests.indexOf(unit);
      if (mtceIndex >= 0) model.maintenanceRequests.splice(mtceIndex, 1);
      if (model.serviceRequests.indexOf(unit) >= 0 || crewHandling(unit)) return;
      unit.state = "failed";
      unit.requestTime = model.time;
      unit.maintenanceRequested = false;
      model.serviceRequests.push(unit);
      model.failuresObserved += 1;
      log(unit.id + " failed and requested repair");
    }
    function requestMaintenance(unit) {
      if (model.serviceRequests.indexOf(unit) >= 0 || model.maintenanceRequests.indexOf(unit) >= 0 || crewHandling(unit)) return;
      unit.maintenanceRequested = true;
      unit.requestTime = model.time;
      model.maintenanceRequests.push(unit);
      log(unit.id + " requested preventive maintenance");
    }
    function getRequest() {
      if (model.serviceRequests.length) return { unit: model.serviceRequests.shift(), taskType: "repair" };
      return { unit: model.maintenanceRequests.shift(), taskType: "maintenance" };
    }
    function dispatchIdleCrews() {
      var i;
      for (i = 0; i < model.crews.length; i += 1) {
        var crew = model.crews[i];
        if (crew.state !== "idle" || (!model.serviceRequests.length && !model.maintenanceRequests.length)) continue;
        var request = getRequest();
        crew.equipmentUnit = request.unit;
        crew.taskType = request.taskType;
        crew.travelTarget = { x: request.unit.x + 5, y: request.unit.y + 5 };
        crew.state = "driving_to_work";
        request.unit.assignedCrewId = crew.id;
        log(crew.id + " dispatched to " + request.unit.id + " for " + request.taskType);
      }
    }
    function startWork(crew) {
      var unit = crew.equipmentUnit;
      if (!unit) return;
      if (crew.taskType === "repair") {
        var replace = model.rng.next() < model.replacementProbability;
        if (model.replaceOldEquipment && age(unit) >= model.mtcePeriodsToReplace * model.maintenancePeriod) replace = true;
        if (replace) {
          crew.taskType = "replacement";
          unit.state = "replacement";
          crew.workRemaining = Math.max(1, model.replacementMeanTime);
        } else {
          unit.state = "repair";
          crew.workRemaining = Math.max(1, model.repairTypicalTime);
        }
      } else {
        unit.state = "maintenance";
        crew.workRemaining = Math.max(1, model.maintenanceMeanTime);
      }
      crew.state = "working";
      log(crew.id + " started " + crew.taskType + " on " + unit.id);
    }
    function finishWork(crew) {
      var unit = crew.equipmentUnit;
      if (!unit) return;
      unit.state = "working";
      unit.assignedCrewId = "";
      unit.requestTime = null;
      unit.maintenanceRequested = false;
      if (crew.taskType === "replacement") {
        unit.timeLastReplacement = model.time;
        unit.timeLastMaintenance = model.time;
        model.workCost += model.replacementCost;
        model.replacementsCompleted += 1;
      } else if (crew.taskType === "maintenance") {
        unit.timeLastMaintenance = model.time;
        model.workCost += model.maintenanceCost;
        model.maintenanceCompleted += 1;
      } else {
        unit.timeLastMaintenance = model.time;
        model.workCost += model.repairCost;
        model.repairsCompleted += 1;
      }
      log(crew.id + " finished " + crew.taskType + " on " + unit.id);
      crew.equipmentUnit = null;
      crew.taskType = "";
      crew.workRemaining = 0;
      crew.travelTarget = { x: HOME.x, y: HOME.y };
      crew.state = "driving_home";
    }
    function stepCrew(crew) {
      if (crew.state === "idle") return;
      if (crew.state === "driving_to_work") {
        var next = moveToward({ x: crew.x, y: crew.y }, crew.travelTarget, model.crewSpeed);
        crew.x = next.x; crew.y = next.y;
        if (dist({ x: crew.x, y: crew.y }, crew.travelTarget) <= 0.001) startWork(crew);
      } else if (crew.state === "working") {
        crew.workRemaining -= 1;
        if (crew.workRemaining <= 0) finishWork(crew);
      } else if (crew.state === "driving_home") {
        var homeward = moveToward({ x: crew.x, y: crew.y }, HOME, model.crewSpeed);
        crew.x = homeward.x; crew.y = homeward.y;
        if (dist({ x: crew.x, y: crew.y }, HOME) <= 0.001) {
          crew.state = "idle";
          log(crew.id + " returned to base");
        }
      }
    }
    function stepModel() {
      var i;
      var working = 0;
      for (i = 0; i < model.equipment.length; i += 1) if (model.equipment[i].state === "working") working += 1;
      model.revenue += working * model.dailyRevenuePerUnit;
      model.crewCost += model.crews.length * model.serviceCrewCostPerDay;
      for (i = 0; i < model.equipment.length; i += 1) {
        var unit = model.equipment[i];
        if (unit.state !== "working" || crewHandling(unit)) continue;
        if (maintenanceOverdue(unit)) requestMaintenance(unit);
        if (model.rng.next() < failureProbability(unit)) requestService(unit);
      }
      dispatchIdleCrews();
      for (i = 0; i < model.crews.length; i += 1) stepCrew(model.crews[i]);
      dispatchIdleCrews();
      model.time += 1;
      history.push(snapshot());
      if (history.length > 300) history.shift();
      render();
    }
    function snapshot() {
      var states = { working: 0, failed: 0, repair: 0, maintenance: 0, replacement: 0 };
      var busy = 0;
      var i;
      for (i = 0; i < model.equipment.length; i += 1) states[model.equipment[i].state] += 1;
      for (i = 0; i < model.crews.length; i += 1) {
        if (model.crews[i].state === "driving_to_work" || model.crews[i].state === "working") busy += 1;
      }
      return {
        time: model.time,
        equipmentTotal: model.equipment.length,
        working: states.working,
        failed: states.failed,
        repairing: states.repair,
        maintenance: states.maintenance,
        replacement: states.replacement,
        serviceQueue: model.serviceRequests.length,
        maintenanceQueue: model.maintenanceRequests.length,
        busyCrews: busy,
        revenue: model.revenue,
        workCost: model.workCost,
        crewCost: model.crewCost,
        profit: model.revenue - model.workCost - model.crewCost,
        failuresObserved: model.failuresObserved,
        repairsCompleted: model.repairsCompleted,
        maintenanceCompleted: model.maintenanceCompleted,
        replacementsCompleted: model.replacementsCompleted
      };
    }
    function equipmentColor(unit) {
      if (unit.state === "failed") return "#c94f3d";
      if (unit.state === "repair" || unit.state === "maintenance" || unit.state === "replacement") return "#2f8b62";
      if (unit.maintenanceRequested) return "#d6a437";
      return "#2f86a6";
    }
    function renderSituation() {
      var svg = byId("situation");
      var i;
      svg.replaceChildren();
      svg.appendChild(svgEl("rect", { x: 0, y: 0, width: WIDTH, height: HEIGHT, fill: "#eef2ec" }));
      svg.appendChild(svgEl("rect", { x: 0, y: 420, width: WIDTH, height: 90, fill: "#dde5dc" }));
      svg.appendChild(svgEl("rect", { x: 0, y: 0, width: 86, height: HEIGHT, fill: "#d8dfd8" }));
      svg.appendChild(svgEl("path", { d: "M60 455 C180 360 260 260 390 170 S540 80 610 45", fill: "none", stroke: "#b9c3bc", "stroke-width": 10, "stroke-linecap": "round", opacity: 0.9 }));
      svg.appendChild(svgEl("rect", { x: 24, y: 430, width: 70, height: 48, rx: 5, fill: "#293d42" }));
      svg.appendChild(svgEl("text", { x: 31, y: 458, fill: "#fff", "font-size": 12 }, "base"));
      var routes = svgEl("g", { "data-layer": "dispatch-routes" });
      for (i = 0; i < model.crews.length; i += 1) {
        var crew = model.crews[i];
        if (crew.equipmentUnit) {
          routes.appendChild(svgEl("line", { x1: crew.x, y1: crew.y, x2: crew.equipmentUnit.x + 5, y2: crew.equipmentUnit.y + 5, stroke: "#513f93", "stroke-width": 1.5, "stroke-dasharray": "4 5", opacity: 0.7 }));
        }
      }
      svg.appendChild(routes);
      var units = svgEl("g", { "data-layer": "equipment" });
      for (i = 0; i < model.equipment.length; i += 1) {
        var unit = model.equipment[i];
        units.appendChild(svgEl("rect", { x: unit.x - 4, y: unit.y - 4, width: 8, height: 8, rx: 1.5, fill: equipmentColor(unit), stroke: "#1f2926", "stroke-width": 0.8 }));
      }
      svg.appendChild(units);
      var crews = svgEl("g", { "data-layer": "service-crews" });
      for (i = 0; i < model.crews.length; i += 1) {
        var c = model.crews[i];
        crews.appendChild(svgEl("circle", { cx: c.x, cy: c.y, r: 7, fill: "#513f93", stroke: "#f4f6f1", "stroke-width": 2 }));
        crews.appendChild(svgEl("text", { x: c.x + 9, y: c.y - 7, fill: "#332b63", "font-size": 10 }, c.taskType || c.state));
      }
      svg.appendChild(crews);
    }
    function metric(label, value) {
      return '<div class="metric"><span>' + label + '</span><strong>' + value + '</strong></div>';
    }
    function renderMetrics() {
      var m = snapshot();
      byId("metrics").innerHTML = [
        metric("Time", Math.round(m.time) + " d"),
        metric("Profit", money(m.profit)),
        metric("Working", m.working + " / " + m.equipmentTotal),
        metric("Repair queue", m.serviceQueue),
        metric("Busy crews", m.busyCrews + " / " + model.crews.length),
        metric("Failures", m.failuresObserved)
      ].join("");
    }
    function chartLine(svg, values, color, minValue, maxValue) {
      var pad = 18;
      var width = 360 - pad * 2;
      var height = 150 - pad * 2;
      var span = Math.max(1, maxValue - minValue);
      var points = [];
      var i;
      for (i = 0; i < values.length; i += 1) {
        var x = pad + (values.length <= 1 ? 0 : (i / (values.length - 1)) * width);
        var y = pad + height - ((values[i] - minValue) / span) * height;
        points.push(x.toFixed(1) + "," + y.toFixed(1));
      }
      svg.appendChild(svgEl("polyline", { points: points.join(" "), fill: "none", stroke: color, "stroke-width": 2.5, "stroke-linejoin": "round", "stroke-linecap": "round" }));
    }
    function renderCharts() {
      var profitChart = byId("profitChart");
      var queueChart = byId("queueChart");
      var profits = [];
      var service = [];
      var maintenance = [];
      var i;
      for (i = 0; i < history.length; i += 1) {
        profits.push(history[i].profit);
        service.push(history[i].serviceQueue);
        maintenance.push(history[i].maintenanceQueue);
      }
      var profitMin = Math.min.apply(null, profits.concat([0]));
      var profitMax = Math.max.apply(null, profits.concat([1]));
      var queueMax = Math.max.apply(null, service.concat(maintenance).concat([1]));
      profitChart.replaceChildren();
      profitChart.appendChild(svgEl("rect", { x: 0, y: 0, width: 360, height: 150, fill: "#fff" }));
      profitChart.appendChild(svgEl("line", { x1: 18, y1: 122, x2: 342, y2: 122, stroke: "#c8d0ca" }));
      chartLine(profitChart, profits, "#1c6f5a", profitMin, profitMax);
      profitChart.appendChild(svgEl("text", { x: 18, y: 22, fill: "#66736e", "font-size": 11 }, "profit " + money(profits[profits.length - 1])));
      queueChart.replaceChildren();
      queueChart.appendChild(svgEl("rect", { x: 0, y: 0, width: 360, height: 150, fill: "#fff" }));
      queueChart.appendChild(svgEl("line", { x1: 18, y1: 122, x2: 342, y2: 122, stroke: "#c8d0ca" }));
      chartLine(queueChart, service, "#b95d3b", 0, queueMax);
      chartLine(queueChart, maintenance, "#d6a437", 0, queueMax);
      queueChart.appendChild(svgEl("text", { x: 18, y: 22, fill: "#66736e", "font-size": 11 }, "red repair queue / gold maintenance queue"));
    }
    function renderLog() {
      var events = model.events.slice(Math.max(0, model.events.length - 14));
      byId("eventLog").innerHTML = events.length ? events.map(function (event) {
        return "<div><strong>day " + event.time + "</strong> " + event.message + "</div>";
      }).join("") : "<div>No dispatch events yet.</div>";
      byId("eventLog").scrollTop = byId("eventLog").scrollHeight;
    }
    function renderReadouts() {
      byId("seedValue").textContent = byId("seed").value;
      byId("equipmentValue").textContent = byId("equipmentCount").value;
      byId("crewValue").textContent = byId("serviceCapacity").value;
      byId("failureValue").textContent = Number(byId("failureRate").value).toFixed(3);
      byId("delayValue").textContent = Number(byId("stepDelay").value).toFixed(2);
    }
    function render() {
      renderReadouts();
      renderSituation();
      renderMetrics();
      renderCharts();
      renderLog();
    }
    function stop() {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
      byId("startStop").textContent = "Start";
    }
    function start() {
      stop();
      byId("startStop").textContent = "Stop";
      timer = setInterval(stepModel, Math.max(50, num("stepDelay") * 1000));
    }
    byId("step").onclick = function () { stepModel(); };
    byId("run30").onclick = function () {
      var i;
      for (i = 0; i < 30; i += 1) stepModel();
    };
    byId("startStop").onclick = function () {
      if (timer) stop();
      else start();
    };
    byId("reset").onclick = function () {
      stop();
      initModel();
    };
    ["seed", "equipmentCount", "serviceCapacity", "failureRate", "replaceOld"].forEach(function (id) {
      byId(id).onchange = function () {
        stop();
        initModel();
      };
      byId(id).oninput = renderReadouts;
    });
    byId("stepDelay").oninput = function () {
      renderReadouts();
      if (timer) start();
    };
    initModel();
  }());
  </script>
</body>
</html>
"""


def build_legacy_app_html() -> str:
    return LEGACY_APP_HTML


def write_legacy_app(path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_legacy_app_html(), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="Write the Field Service legacy JavaScript app.")
    parser.add_argument("--output", type=Path, default=Path("outputs/field_service/index.html"))
    args = parser.parse_args()
    print(write_legacy_app(args.output))


if __name__ == "__main__":
    main()
