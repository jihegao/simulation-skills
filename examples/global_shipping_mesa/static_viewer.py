"""Generate a CesiumJS 3D globe replay for the global shipping model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from examples.global_shipping_mesa.model import GlobalShippingModel


def build_view_payload(
    seed: int = 21,
    steps: int = 120,
    ship_count: int = 8,
    initial_orders: int = 18,
    port_capacity_scale: float = 1.0,
    order_interval_hours: float = 8.0,
) -> dict[str, Any]:
    model = GlobalShippingModel(
        seed=seed,
        ship_count=ship_count,
        initial_orders=initial_orders,
        port_capacity_scale=port_capacity_scale,
        order_interval_hours=order_interval_hours,
    )
    frames = []
    for step in range(steps + 1):
        frame = model.visualization_state()
        frame["step"] = step
        frames.append(frame)
        if step < steps:
            model.step()
    return {
        "title": "Global Shipping 3D Globe",
        "source": {
            "model": "Mesa shell with SimPy port berth/crane resources",
            "gis": "Port latitude/longitude points are embedded in examples.global_shipping_mesa.model",
            "distance": "haversine_nm great-circle nautical miles",
            "claim_boundary": "Demonstration model for dispatch and port-congestion dynamics, not a calibrated shipping forecast.",
        },
        "params": {
            "seed": seed,
            "steps": steps,
            "ship_count": ship_count,
            "initial_orders": initial_orders,
            "port_capacity_scale": port_capacity_scale,
            "order_interval_hours": order_interval_hours,
        },
        "frames": frames,
    }


def write_viewer_html(path: Path | str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload_json = json.dumps(payload)
    local_cesium_root = target.parent / "cesium" / "Build" / "Cesium"
    if (local_cesium_root / "Cesium.js").exists():
        cesium_js = "cesium/Build/Cesium/Cesium.js"
        cesium_css = "cesium/Build/Cesium/Widgets/widgets.css"
    else:
        cesium_js = "https://unpkg.com/cesium@1.120.0/Build/Cesium/Cesium.js"
        cesium_css = "https://unpkg.com/cesium@1.120.0/Build/Cesium/Widgets/widgets.css"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <link href="{cesium_css}" rel="stylesheet">
  <script src="{cesium_js}"></script>
  <title>Global Shipping 3D Globe</title>
  <style>
    :root {{
      --water: #07151b;
      --ink: #d7e5e1;
      --muted: #86a09a;
      --line: rgba(154, 180, 172, .25);
      --panel: rgba(8, 22, 28, .82);
      --port: #f0c45f;
      --ship: #67d2c1;
      --order: #d96f5f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      overflow: hidden;
      background: #061116;
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: minmax(280px, 360px) 1fr minmax(290px, 360px);
      gap: 14px;
      padding: 14px;
    }}
    aside, .rail {{
      z-index: 2;
      border: 1px solid var(--line);
      background: var(--panel);
      backdrop-filter: blur(10px);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
      max-height: calc(100vh - 28px);
      overflow: auto;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 26px;
      line-height: 1.05;
      letter-spacing: 0;
      font-weight: 760;
    }}
    h2 {{
      margin: 18px 0 8px;
      font-size: 12px;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .source, .caption, .frame-label {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 12px 0;
    }}
    button {{
      min-height: 36px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, .06);
      color: var(--ink);
      border-radius: 6px;
      cursor: pointer;
      font: inherit;
    }}
    button:hover, button:focus-visible {{
      outline: none;
      border-color: var(--ship);
      box-shadow: 0 0 0 2px rgba(103, 210, 193, .18);
    }}
    input[type="range"] {{ width: 100%; accent-color: var(--ship); }}
    #cesiumContainer {{
      width: 100%;
      height: calc(100vh - 28px);
      min-height: 520px;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid rgba(154, 180, 172, .18);
    }}
    .cesium-viewer-bottom, .cesium-credit-lightbox-overlay {{ display: none !important; }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-top: 12px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: rgba(255,255,255,.045);
      padding: 9px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 11px;
    }}
    .metric strong {{
      display: block;
      margin-top: 3px;
      font-size: 18px;
      font-weight: 730;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 6px 3px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 650; }}
    .legend {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; color:var(--muted); font-size:12px; }}
    .key {{ display:inline-flex; align-items:center; gap:5px; }}
    .dot {{ width:10px; height:10px; border-radius:50%; display:inline-block; }}
    .log {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: 11px; line-height: 1.45; color: #bcd0cb; }}
    .log div {{ padding: 4px 0; border-bottom: 1px solid var(--line); }}
    @media (max-width: 980px) {{
      body {{ overflow: auto; }}
      .shell {{ grid-template-columns: 1fr; }}
      #cesiumContainer {{ height: 68vh; min-height: 460px; }}
      aside, .rail {{ max-height: none; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside>
      <h1>Global Shipping 3D Globe</h1>
      <div class="source">CesiumJS globe with WGS84 ports, draggable camera, daylight lighting, and shipping orders replayed from the Mesa/SimPy model.</div>
      <div class="controls">
        <button id="play">Play</button>
        <button id="pause">Pause</button>
        <button id="reset">Reset</button>
      </div>
      <input id="frame" type="range" min="0" max="0" value="0">
      <div id="frameLabel" class="frame-label"></div>
      <div class="legend">
        <span class="key"><span class="dot" style="background:var(--port)"></span>Port</span>
        <span class="key"><span class="dot" style="background:var(--ship)"></span>Ship</span>
        <span class="key"><span class="dot" style="background:var(--order)"></span>Open order</span>
      </div>
      <h2>Metrics</h2>
      <div id="metrics" class="metric-grid"></div>
      <h2>Assumptions</h2>
      <div class="caption">This is a compact operational demo, not a calibrated maritime forecast. Distances use haversine_nm; berth, crane, and yard constraints are synthetic. The globe uses Cesium NaturalEarth imagery without a Cesium ion token.</div>
    </aside>
    <main>
      <div id="cesiumContainer" aria-label="Cesium global shipping globe"></div>
    </main>
    <section class="rail">
      <h2>Port pressure</h2>
      <table id="ports"><thead><tr><th>Port</th><th>Queue</th><th>Pressure</th></tr></thead><tbody></tbody></table>
      <h2>Recent events</h2>
      <div id="events" class="log"></div>
    </section>
  </div>
  <script id="payload" type="application/json">{payload_json}</script>
  <script>
    const payload = JSON.parse(document.getElementById("payload").textContent);
    const frames = payload.frames;
    Cesium.Ion.defaultAccessToken = "";

    const viewer = new Cesium.Viewer("cesiumContainer", {{
      animation: false,
      baseLayer: false,
      baseLayerPicker: false,
      fullscreenButton: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      terrainProvider: new Cesium.EllipsoidTerrainProvider()
    }});
    window.__shippingCesiumViewer = viewer;
    viewer.clock.shouldAnimate = false;
    viewer.scene.globe.enableLighting = true;
    viewer.scene.globe.depthTestAgainstTerrain = false;
    viewer.scene.skyAtmosphere.show = true;
    viewer.scene.screenSpaceCameraController.enableRotate = true; // ScreenSpaceCameraController native drag
    viewer.scene.screenSpaceCameraController.enableTranslate = true;
    viewer.scene.screenSpaceCameraController.enableZoom = true;
    viewer.scene.screenSpaceCameraController.enableTilt = true;
    viewer.scene.screenSpaceCameraController.enableLook = true;
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#061116");
    document.body.dataset.cesiumReady = "true";

    (async () => {{
      const imageryProvider = await Cesium.TileMapServiceImageryProvider.fromUrl(
        Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
      );
      viewer.imageryLayers.addImageryProvider(imageryProvider);
    }})();

    const portEntities = new Map();
    const shipEntities = new Map();
    const orderEntities = new Map();
    let frameIndex = 0;
    let playing = false;
    let timer = null;

    function colorForPort(port) {{
      if (port.pressure > 1) return Cesium.Color.fromCssColorString("#d96f5f");
      if (port.pressure > 0.75) return Cesium.Color.fromCssColorString("#f0c45f");
      return Cesium.Color.fromCssColorString("#75c795");
    }}

    function cartesian(portOrPoint, height = 0) {{
      return Cesium.Cartesian3.fromDegrees(portOrPoint.lon, portOrPoint.lat, height);
    }}

    function addOrUpdatePort(port) {{
      let entity = portEntities.get(port.id);
      if (!entity) {{
        entity = viewer.entities.add({{
          id: `port-${{port.id}}`,
          name: port.name,
          position: cartesian(port, 0),
          point: {{
            pixelSize: 9,
            color: colorForPort(port),
            outlineColor: Cesium.Color.BLACK.withAlpha(0.65),
            outlineWidth: 1,
            heightReference: Cesium.HeightReference.NONE
          }},
          label: {{
            text: port.name,
            font: "12px Inter, sans-serif",
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(0, -18),
            scaleByDistance: new Cesium.NearFarScalar(1.0e6, 1.0, 1.6e7, 0.35)
          }}
        }});
        portEntities.set(port.id, entity);
      }}
      entity.point.pixelSize = 9 + Math.min(12, port.queue_depth * 2);
      entity.point.color = colorForPort(port);
      return entity;
    }}

    function addOrUpdateShip(ship) {{
      let entity = shipEntities.get(ship.id);
      if (!entity) {{
        entity = viewer.entities.add({{
          id: `ship-${{ship.id}}`,
          name: ship.id,
          position: Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat, 120000),
          point: {{
            pixelSize: 11,
            color: Cesium.Color.fromCssColorString("#67d2c1"),
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 1
          }},
          label: {{
            text: ship.id,
            font: "11px Inter, sans-serif",
            fillColor: Cesium.Color.fromCssColorString("#d7fff8"),
            outlineColor: Cesium.Color.BLACK,
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            pixelOffset: new Cesium.Cartesian2(0, 15),
            scaleByDistance: new Cesium.NearFarScalar(1.0e6, 1.0, 1.8e7, 0.25)
          }}
        }});
        shipEntities.set(ship.id, entity);
      }}
      entity.position = Cesium.Cartesian3.fromDegrees(ship.lon, ship.lat, 120000);
      return entity;
    }}

    function syncOrderRoutes(frame, portsById) {{
      const activeIds = new Set();
      frame.orders.filter(order => order.status !== "completed").slice(-42).forEach(order => {{
        const origin = portsById.get(order.origin);
        const destination = portsById.get(order.destination);
        if (!origin || !destination) return;
        activeIds.add(order.id);
        let entity = orderEntities.get(order.id);
        const active = order.status !== "open";
        const material = active
          ? Cesium.Color.fromCssColorString("#8aa7ff").withAlpha(0.75)
          : Cesium.Color.fromCssColorString("#d96f5f").withAlpha(0.34);
        if (!entity) {{
          entity = viewer.entities.add({{
            id: `order-${{order.id}}`,
            name: `${{order.id}} ${{origin.name}} to ${{destination.name}}`,
            polyline: {{
              positions: Cesium.Cartesian3.fromDegreesArray([
                origin.lon, origin.lat,
                destination.lon, destination.lat
              ]),
              width: active ? 2.2 : 1.2,
              arcType: Cesium.ArcType.GEODESIC,
              material
            }}
          }});
          orderEntities.set(order.id, entity);
        }}
        entity.polyline.width = active ? 2.2 : 1.2;
        entity.polyline.material = material;
      }});
      for (const [id, entity] of orderEntities) {{
        if (!activeIds.has(id)) {{
          viewer.entities.remove(entity);
          orderEntities.delete(id);
        }}
      }}
    }}

    function renderFrame(index) {{
      frameIndex = Math.max(0, Math.min(frames.length - 1, index));
      const frame = frames[frameIndex];
      const portsById = new Map(frame.ports.map(port => [port.id, port]));
      frame.ports.forEach(addOrUpdatePort);
      frame.ships.forEach(addOrUpdateShip);
      syncOrderRoutes(frame, portsById);

      document.getElementById("frame").value = String(frameIndex);
      document.getElementById("frameLabel").textContent = `Frame ${{frameIndex}} / ${{frames.length - 1}} · hour ${{frame.time_hours}}`;
      const m = frame.metrics;
      document.getElementById("metrics").innerHTML = [
        ["Completed", m.completed_orders],
        ["Open", m.open_orders],
        ["Avg queue", m.avg_port_queue],
        ["Avg wait h", m.avg_order_wait_hours],
        ["Cycle h", m.avg_cycle_hours],
        ["Empty share", m.empty_sailing_share]
      ].map(([label, value]) => `<div class="metric"><span>${{label}}</span><strong>${{value}}</strong></div>`).join("");
      document.querySelector("#ports tbody").innerHTML = frame.ports
        .slice()
        .sort((a, b) => b.pressure - a.pressure)
        .slice(0, 10)
        .map(port => `<tr><td>${{port.name}}</td><td>${{port.queue_depth}}</td><td>${{port.pressure}}</td></tr>`)
        .join("");
      document.getElementById("events").innerHTML = frame.events
        .map(event => `<div><strong>${{event.time_hours}}</strong> ${{event.message}}</div>`)
        .join("");
      window.__shippingCesiumState = {{
        frameIndex,
        entityCount: viewer.entities.values.length,
        url: location.href
      }};
      document.body.dataset.frameIndex = String(frameIndex);
      document.body.dataset.entityCount = String(viewer.entities.values.length);
    }}

    function advance() {{
      renderFrame((frameIndex + 1) % frames.length);
    }}

    document.getElementById("frame").max = String(frames.length - 1);
    document.getElementById("frame").addEventListener("input", event => renderFrame(Number(event.target.value)));
    document.getElementById("play").addEventListener("click", () => {{
      if (!playing) {{
        playing = true;
        timer = window.setInterval(advance, 420);
      }}
    }});
    document.getElementById("pause").addEventListener("click", () => {{
      playing = false;
      window.clearInterval(timer);
    }});
    document.getElementById("reset").addEventListener("click", () => renderFrame(0));

    renderFrame(0);
    viewer.camera.setView({{
      destination: Cesium.Cartesian3.fromDegrees(50, 16, 26500000),
      orientation: {{
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-90),
        roll: 0
      }}
    }});
    function updateCameraDataset() {{
      const cartographic = viewer.camera.positionCartographic;
      document.body.dataset.cameraLon = String(Cesium.Math.toDegrees(cartographic.longitude));
      document.body.dataset.cameraLat = String(Cesium.Math.toDegrees(cartographic.latitude));
      document.body.dataset.cameraHeight = String(Math.round(cartographic.height));
    }}
    viewer.camera.percentageChanged = 0.001;
    viewer.camera.changed.addEventListener(updateCameraDataset);
    updateCameraDataset();
  </script>
</body>
</html>
"""
    target.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a CesiumJS global shipping viewer.")
    parser.add_argument("--output", type=Path, default=Path("outputs/global_shipping/index.html"))
    parser.add_argument("--seed", type=int, default=21)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--ship-count", type=int, default=8)
    parser.add_argument("--initial-orders", type=int, default=18)
    parser.add_argument("--port-capacity-scale", type=float, default=1.0)
    parser.add_argument("--order-interval-hours", type=float, default=8.0)
    args = parser.parse_args()

    payload = build_view_payload(
        seed=args.seed,
        steps=args.steps,
        ship_count=args.ship_count,
        initial_orders=args.initial_orders,
        port_capacity_scale=args.port_capacity_scale,
        order_interval_hours=args.order_interval_hours,
    )
    write_viewer_html(args.output, payload)
    print(args.output)


if __name__ == "__main__":
    main()
