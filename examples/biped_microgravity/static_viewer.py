"""Write a Three.js + cannon-es viewer for the matchstick bridge model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from examples.biped_microgravity.model import MatchstickBridge


def build_view_payload(load_n: float = 18.0, panel_count: int = 6) -> dict[str, Any]:
    return {
        "title": "火柴棍桥梁物理仿真",
        "claim_boundary": (
            "Three.js renders the bridge; cannon-es simulates the payload body and contact. "
            "Bridge capacity remains a simplified structural envelope, not a finite-element solver."
        ),
        "state": MatchstickBridge(load_n=load_n, panel_count=panel_count).visualization_state(),
    }


def write_viewer_html(path: Path | str, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload_json = json.dumps(payload)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>火柴棍桥梁物理仿真</title>
  <style>
    :root {{
      --paper: #f4f0e7;
      --ink: #232628;
      --muted: #6c6d68;
      --line: #cbc3b4;
      --load: #b84339;
      --ok: #2f7651;
      --danger: #b94b43;
      --panel: #fffdfa;
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
      grid-template-columns: minmax(280px, 360px) minmax(460px, 1fr);
      gap: 18px;
      padding: 18px;
    }}
    aside {{
      border-right: 1px solid var(--line);
      padding-right: 18px;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 26px;
      line-height: 1.08;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 18px 0 8px;
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0;
      color: var(--muted);
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      padding: 10px;
      min-height: 76px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
    }}
    .metric strong {{
      display: block;
      margin-top: 6px;
      font-size: 20px;
    }}
    .verdict {{
      display: inline-block;
      border-radius: 6px;
      padding: 7px 9px;
      margin-bottom: 10px;
      color: #fff;
      background: var(--danger);
      font-weight: 700;
    }}
    .verdict.ok {{ background: var(--ok); }}
    .controls {{
      display: grid;
      grid-template-columns: 1fr;
      gap: 8px;
      margin: 0 0 12px;
    }}
    button {{
      min-height: 38px;
      border: 1px solid #9e7a55;
      border-radius: 6px;
      background: #fff7ea;
      color: var(--ink);
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover, button:focus-visible {{
      border-color: var(--load);
      outline: none;
      box-shadow: 0 0 0 2px rgba(184, 67, 57, 0.14);
    }}
    .viewport {{
      position: relative;
      width: 100%;
      height: calc(100vh - 36px);
      min-height: 520px;
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
      background: linear-gradient(#fffdf8, #ebe6da);
    }}
    .viewport canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    ul {{
      margin: 8px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .note {{
      margin-top: 14px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
    }}
    @media (max-width: 820px) {{
      .shell {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--line); padding: 0 0 14px; }}
      .viewport {{ height: 62vh; min-height: 420px; }}
    }}
  </style>
  <script type="importmap">
    {{
      "imports": {{
        "three": "https://unpkg.com/three@0.165.0/build/three.module.js",
        "three/addons/": "https://unpkg.com/three@0.165.0/examples/jsm/",
        "cannon-es": "https://cdn.jsdelivr.net/npm/cannon-es@0.20.0/dist/cannon-es.js"
      }}
    }}
  </script>
</head>
<body>
  <div class="shell">
    <aside data-panel="bridge-metrics">
      <h1>火柴棍桥梁物理仿真</h1>
      <div id="verdict" class="verdict"></div>
      <div class="controls">
        <button id="addPayload" type="button" data-action="add-payload">Add payload +5N</button>
      </div>
      <div class="metric-grid">
        <div class="metric"><span>Point load</span><strong id="load"></strong></div>
        <div class="metric"><span>Member utilization</span><strong id="memberUtil"></strong></div>
        <div class="metric"><span>Joint utilization</span><strong id="jointUtil"></strong></div>
        <div class="metric"><span>Midspan deflection</span><strong id="deflection"></strong></div>
      </div>
      <h2>Failure modes</h2>
      <ul id="failures"></ul>
      <h2>Joint force color</h2>
      <ul>
        <li><span style="color:#2f6fb0">blue</span>: low</li>
        <li><span style="color:#d6a12d">amber</span>: medium</li>
        <li><span style="color:#b84339">red</span>: high</li>
      </ul>
      <p class="note" id="boundary"></p>
    </aside>
    <main data-panel="bridge-structure">
      <div id="scene" class="viewport" data-layer="threejs-cannon-bridge"></div>
    </main>
  </div>
  <script type="module">
    import * as THREE from "three";
    import {{ OrbitControls }} from "three/addons/controls/OrbitControls.js";
    import * as CANNON from "cannon-es";

    const payload = {payload_json};
    const state = payload.state;
    const evaluation = state.evaluation;
    const baseLoad = evaluation.load_n;
    let currentLoad = baseLoad;
    const container = document.getElementById("scene");
    const nodes = new Map(state.nodes.map(node => [node.name, node]));
    const nodeBaseForces = new Map(state.nodes.map(node => [node.name, 0]));
    for (const member of state.members) {{
      nodeBaseForces.set(member.start, nodeBaseForces.get(member.start) + member.force_n);
      nodeBaseForces.set(member.end, nodeBaseForces.get(member.end) + member.force_n);
    }}
    const maxBaseNodeForce = Math.max(...nodeBaseForces.values());
    const colors = {{
      chord: 0x5b3822,
      diagonal: 0xb57438,
      tie: 0x8d6a4a,
      jointLow: 0x2f6fb0,
      jointMid: 0xd6a12d,
      jointHigh: 0xb84339,
      support: 0x2f7651,
      payload: 0xb84339
    }};

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf6f0e4);
    const camera = new THREE.PerspectiveCamera(45, 1, 0.01, 20);
    camera.position.set(0.55, 0.42, 0.72);
    const renderer = new THREE.WebGLRenderer({{ antialias: true }});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.target.set(0, 0.06, 0);
    controls.update();

    scene.add(new THREE.HemisphereLight(0xfffbef, 0xb7aa98, 2.1));
    const keyLight = new THREE.DirectionalLight(0xffffff, 2.2);
    keyLight.position.set(0.5, 1.3, 0.8);
    keyLight.castShadow = true;
    scene.add(keyLight);
    const grid = new THREE.GridHelper(1.1, 12, 0xd0c7b8, 0xe2dace);
    grid.position.y = -0.035;
    scene.add(grid);

    const world = new CANNON.World({{ gravity: new CANNON.Vec3(0, -9.82, 0) }});
    world.broadphase = new CANNON.SAPBroadphase(world);
    world.allowSleep = true;
    const groundBody = new CANNON.Body({{ mass: 0, shape: new CANNON.Plane() }});
    groundBody.quaternion.setFromEuler(-Math.PI / 2, 0, 0);
    groundBody.position.set(0, -0.04, 0);
    world.addBody(groundBody);
    const deckBody = new CANNON.Body({{
      mass: 0,
      shape: new CANNON.Box(new CANNON.Vec3(evaluation.span_m / 2, 0.012, 0.085)),
      position: new CANNON.Vec3(0, 0.135, 0)
    }});
    world.addBody(deckBody);

    function toThree(position) {{
      return new THREE.Vector3(position[0] - evaluation.span_m / 2, position[2], position[1]);
    }}
    function memberColor(kind) {{
      if (kind.includes("chord")) return colors.chord;
      if (kind.includes("diagonal") || kind.includes("vertical")) return colors.diagonal;
      return colors.tie;
    }}
    function jointForceRatio(nodeName) {{
      return (nodeBaseForces.get(nodeName) || 0) * (currentLoad / baseLoad) / maxBaseNodeForce;
    }}
    function jointColor(nodeName) {{
      const ratio = jointForceRatio(nodeName);
      if (ratio >= 1.05) return colors.jointHigh;
      if (ratio >= 0.62) return colors.jointMid;
      return colors.jointLow;
    }}
    function createCylinderBetween(start, end, radius, material) {{
      const direction = new THREE.Vector3().subVectors(end, start);
      const length = direction.length();
      const geometry = new THREE.CylinderGeometry(radius, radius, length, 12);
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.copy(start).add(end).multiplyScalar(0.5);
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      scene.add(mesh);
      return mesh;
    }}

    const memberMeshes = [];
    const materialCache = new Map();
    function materialFor(hex) {{
      if (!materialCache.has(hex)) {{
        materialCache.set(hex, new THREE.MeshStandardMaterial({{ color: hex, roughness: 0.68, metalness: 0.02 }}));
      }}
      return materialCache.get(hex);
    }}
    for (const member of state.members) {{
      const start = toThree(nodes.get(member.start).position);
      const end = toThree(nodes.get(member.end).position);
      const mesh = createCylinderBetween(start, end, 0.0048, materialFor(memberColor(member.kind)));
      memberMeshes.push({{ mesh, member }});
    }}

    const jointMeshes = new Map();
    const jointGeometry = new THREE.SphereGeometry(0.012, 18, 18);
    for (const node of state.nodes) {{
      const material = new THREE.MeshStandardMaterial({{ color: jointColor(node.name), roughness: 0.45 }});
      const mesh = new THREE.Mesh(jointGeometry, material);
      mesh.position.copy(toThree(node.position));
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      scene.add(mesh);
      jointMeshes.set(node.name, mesh);
      if (node.support) {{
        const support = new THREE.Mesh(
          new THREE.ConeGeometry(0.022, 0.035, 4),
          new THREE.MeshStandardMaterial({{ color: colors.support, roughness: 0.65, transparent: true, opacity: 0.72 }})
        );
        support.position.copy(mesh.position).add(new THREE.Vector3(0, -0.026, 0));
        support.rotation.y = Math.PI / 4;
        scene.add(support);
      }}
    }}

    const payloadGeometry = new THREE.SphereGeometry(0.03, 24, 24);
    const payloadMaterial = new THREE.MeshStandardMaterial({{ color: colors.payload, roughness: 0.35 }});
    const payloadMesh = new THREE.Mesh(payloadGeometry, payloadMaterial);
    payloadMesh.castShadow = true;
    scene.add(payloadMesh);
    let payloadBody;
    function resetPayloadBody() {{
      if (payloadBody) world.removeBody(payloadBody);
      payloadBody = new CANNON.Body({{
        mass: Math.max(0.05, currentLoad / 9.82),
        shape: new CANNON.Sphere(0.03),
        position: new CANNON.Vec3(0, 0.34, 0)
      }});
      payloadBody.linearDamping = 0.25;
      payloadBody.angularDamping = 0.5;
      world.addBody(payloadBody);
    }}
    resetPayloadBody();

    const arrowGroup = new THREE.Group();
    const arrowMaterial = new THREE.MeshStandardMaterial({{ color: colors.payload, roughness: 0.4 }});
    const arrowShaft = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.09, 12), arrowMaterial);
    const arrowHead = new THREE.Mesh(new THREE.ConeGeometry(0.016, 0.034, 18), arrowMaterial);
    arrowShaft.position.y = 0.045;
    arrowHead.position.y = -0.02;
    arrowHead.rotation.x = Math.PI;
    arrowGroup.add(arrowShaft, arrowHead);
    scene.add(arrowGroup);

    function currentEvaluation() {{
      const ratio = currentLoad / baseLoad;
      const memberUtil = evaluation.max_member_utilization * ratio;
      const jointUtil = evaluation.joint_utilization * ratio;
      const deflection = evaluation.midspan_deflection_m * ratio;
      const failures = [];
      if (memberUtil > 1) failures.push("member_capacity_exceeded");
      if (jointUtil > 1) failures.push("glue_joint_capacity_exceeded");
      if (deflection > evaluation.deflection_limit_m) failures.push("deflection_limit_exceeded");
      return {{
        load_n: currentLoad,
        can_hold: failures.length === 0,
        verdict: failures.length === 0 ? "holds_load" : "fails_load",
        max_member_utilization: memberUtil,
        joint_utilization: jointUtil,
        midspan_deflection_m: deflection,
        failure_modes: failures
      }};
    }}
    function format(value, unit, digits = 2) {{
      return `${{Number(value).toFixed(digits)}} ${{unit}}`;
    }}
    function updateMetrics(view) {{
      document.getElementById("verdict").textContent = view.verdict.replace("_", " ");
      document.getElementById("verdict").classList.toggle("ok", view.can_hold);
      document.getElementById("load").textContent = format(view.load_n, "N", 1);
      document.getElementById("memberUtil").textContent = format(view.max_member_utilization * 100, "%", 0);
      document.getElementById("jointUtil").textContent = format(view.joint_utilization * 100, "%", 0);
      document.getElementById("deflection").textContent = format(view.midspan_deflection_m * 1000, "mm", 2);
      const failures = document.getElementById("failures");
      failures.replaceChildren();
      for (const mode of view.failure_modes.length ? view.failure_modes : ["none"]) {{
        const item = document.createElement("li");
        item.textContent = mode;
        failures.appendChild(item);
      }}
      for (const [name, mesh] of jointMeshes) {{
        mesh.material.color.setHex(jointColor(name));
      }}
      const ratio = currentLoad / baseLoad;
      for (const item of memberMeshes) {{
        const scale = Math.min(1.9, 1 + item.member.force_n * ratio / 25);
        item.mesh.scale.set(scale, 1, scale);
      }}
    }}
    document.getElementById("boundary").textContent = payload.claim_boundary;
    document.getElementById("addPayload").addEventListener("click", () => {{
      currentLoad += 5;
      resetPayloadBody();
      updateMetrics(currentEvaluation());
    }});
    function resize() {{
      const rect = container.getBoundingClientRect();
      camera.aspect = rect.width / rect.height;
      camera.updateProjectionMatrix();
      renderer.setSize(rect.width, rect.height, false);
    }}
    window.addEventListener("resize", resize);
    resize();
    updateMetrics(currentEvaluation());
    function animate() {{
      world.step(1 / 60);
      payloadMesh.position.copy(payloadBody.position);
      payloadMesh.quaternion.copy(payloadBody.quaternion);
      arrowGroup.position.set(payloadBody.position.x, payloadBody.position.y + 0.12, payloadBody.position.z);
      controls.update();
      renderer.render(scene, camera);
      requestAnimationFrame(animate);
    }}
    animate();
  </script>
</body>
</html>
"""
    target.write_text(html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a Three.js matchstick bridge structure viewer.")
    parser.add_argument("--output", type=Path, default=Path("outputs/biped_microgravity/viewer.html"))
    parser.add_argument("--load", type=float, default=18.0)
    parser.add_argument("--panel-count", type=int, default=6)
    args = parser.parse_args()
    write_viewer_html(args.output, build_view_payload(args.load, args.panel_count))
    print(args.output)


if __name__ == "__main__":
    main()
