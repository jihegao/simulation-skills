"""Solara tiled 2D visualization for Hospital Material Handling Mesa."""

from __future__ import annotations

import html

import solara

from examples.hospital_material_mesa.model import (
    ACTIVE_MISSION_TYPES,
    FLOOR_LEVELS,
    MISSION_COLORS,
    HospitalMaterialHandlingModel,
)
from examples.hospital_material_mesa.space import HospitalSpace, LevelSpace, parse_hospital_space


def _bar(value: float, color: str, width: int = 120) -> str:
    clamped = max(0.0, min(1.0, value))
    filled = max(1, int(width * clamped))
    return (
        f'<svg width="{width}" height="8" viewBox="0 0 {width} 8" role="img">'
        f'<rect x="0" y="0" width="{width}" height="8" fill="#e4e8e5" rx="2"/>'
        f'<rect x="0" y="0" width="{filled}" height="8" fill="{color}" rx="2"/>'
        "</svg>"
    )


def _scale_point(level: LevelSpace, x: float, y: float, width: float, height: float) -> tuple[float, float]:
    bounds = level.bounds
    scale = min(width / max(1.0, bounds.width), height / max(1.0, bounds.height))
    pad_x = (width - bounds.width * scale) / 2
    pad_y = (height - bounds.height * scale) / 2
    return (pad_x + (x - bounds.min_x) * scale, pad_y + (y - bounds.min_y) * scale)


def _render_level_svg(level: LevelSpace, carts_html: str, agvs_html: str) -> str:
    width = 210.0
    height = 118.0
    parts = [
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" width="100%" height="118" '
        'data-space-source="alp-2d-markup" xmlns="http://www.w3.org/2000/svg">',
        '<rect x="0" y="0" width="210" height="118" fill="#f8faf8" />',
    ]
    for rect in level.rectangles[:28]:
        x, y = _scale_point(level, rect.x, rect.y, width, height)
        x2, y2 = _scale_point(level, rect.x + rect.width, rect.y + rect.height, width, height)
        parts.append(
            f'<rect data-layer="space-rect" x="{min(x, x2):.1f}" y="{min(y, y2):.1f}" '
            f'width="{abs(x2 - x):.1f}" height="{abs(y2 - y):.1f}" fill="#e5ece7" '
            'stroke="#d0d9d3" stroke-width="0.6" />'
        )
    for polyline in level.polylines[:24]:
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_scale_point(level, p.x, p.y, width, height) for p in polyline.points))
        parts.append(
            f'<polyline data-layer="space-polyline" points="{points}" fill="none" stroke="#c6d1ca" '
            'stroke-width="1" stroke-linejoin="round" />'
        )
    for wall in level.walls[:80]:
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_scale_point(level, p.x, p.y, width, height) for p in wall.points))
        parts.append(
            f'<polyline data-layer="wall" points="{points}" fill="none" stroke="#5c6762" '
            'stroke-width="1.1" stroke-linejoin="round" />'
        )
    for lift in level.lifts[:10]:
        x, y = _scale_point(level, lift.x, lift.y, width, height)
        x2, y2 = _scale_point(level, lift.x + lift.width, lift.y + lift.depth, width, height)
        parts.append(
            f'<rect data-layer="lift" x="{min(x, x2):.1f}" y="{min(y, y2):.1f}" '
            f'width="{max(3.5, abs(x2 - x)):.1f}" height="{max(3.5, abs(y2 - y)):.1f}" '
            'fill="#f3c766" stroke="#8a6d24" stroke-width="0.8" />'
        )
    for node in level.nodes[:36]:
        x, y = _scale_point(level, node.x, node.y, width, height)
        title = html.escape(node.name)
        parts.append(
            f'<circle data-layer="node" data-node-name="{title}" cx="{x:.1f}" cy="{y:.1f}" r="2.1" '
            'fill="#2f6f90"><title>'
            f"{title}</title></circle>"
        )
    parts.append(
        '<foreignObject x="4" y="92" width="202" height="22">'
        '<div xmlns="http://www.w3.org/1999/xhtml" class="hm-overlay">'
        f"{carts_html}{agvs_html}</div></foreignObject>"
    )
    parts.append("</svg>")
    return "".join(parts)


def _floor_grid(model: HospitalMaterialHandlingModel, space: HospitalSpace | None = None) -> str:
    if space is None:
        space = parse_hospital_space()
    waiting = model.waiting_counts_by_mission()
    active = model.active_counts_by_mission()
    rows = []
    for floor in FLOOR_LEVELS:
        carts = [cart for cart in model.pending_carts if cart.origin_floor == floor]
        agvs = [agv for agv in model.agvs if agv.current_floor == floor]
        cart_marks = "".join(
            f'<span class="hm-chip" style="background:{MISSION_COLORS[cart.mission]}">{cart.mission[0]}</span>'
            for cart in carts[:8]
        )
        agv_marks = "".join('<span class="hm-agv">AGV</span>' for _ in agvs[:4])
        if floor in space.levels:
            floor_body = _render_level_svg(space.levels[floor], cart_marks, agv_marks)
        else:
            floor_body = f'<div class="hm-floor-content">{cart_marks}{agv_marks}</div>'
        rows.append(
            '<div class="hm-floor" data-layer="floor">'
            f'<div class="hm-floor-name">{html.escape(floor)}</div>'
            f"{floor_body}"
            "</div>"
        )
    totals = " ".join(f"{mission}: {waiting[mission]} wait / {active[mission]} active" for mission in ACTIVE_MISSION_TYPES)
    return (
        '<section class="hm-panel" data-panel="floor-grid">'
        "<h3>All-floor 2D view</h3>"
        f'<div class="hm-subtle">{html.escape(totals)}</div>'
        '<div class="hm-floor-grid">'
        + "".join(rows)
        + "</div></section>"
    )


def _agv_status(model: HospitalMaterialHandlingModel) -> str:
    rows = []
    for agv in model.agvs:
        mission = agv.current_mission or "idle"
        color = MISSION_COLORS.get(mission, "#78828a")
        rows.append(
            "<tr>"
            f"<td>{html.escape(agv.unique_id)}</td>"
            f"<td>{html.escape(agv.current_floor)}</td>"
            f'<td><span class="hm-dot" style="background:{color}"></span>{html.escape(mission)}</td>'
            f"<td>{agv.remaining_seconds:.0f}s</td>"
            "</tr>"
        )
    return (
        '<section class="hm-panel" data-panel="agv-status">'
        "<h3>AGV fleet</h3>"
        '<table><thead><tr><th>AGV</th><th>floor</th><th>mission</th><th>remaining</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></section>"
    )


def _mission_queues(model: HospitalMaterialHandlingModel) -> str:
    waiting = model.waiting_counts_by_mission()
    active = model.active_counts_by_mission()
    rows = []
    for mission in ACTIVE_MISSION_TYPES:
        generated = model.generated_counts[mission]
        completed = model.completed_counts[mission]
        rows.append(
            "<tr>"
            f'<td><span class="hm-dot" style="background:{MISSION_COLORS[mission]}"></span>{mission.lower()}</td>'
            f"<td>{generated}</td><td>{waiting[mission]}</td><td>{active[mission]}</td><td>{completed}</td>"
            "</tr>"
        )
    return (
        '<section class="hm-panel" data-panel="mission-queues">'
        "<h3>Mission queues</h3>"
        '<table><thead><tr><th>mission</th><th>generated</th><th>waiting</th><th>active</th><th>complete</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></section>"
    )


def _performance(model: HospitalMaterialHandlingModel) -> str:
    snapshot = model.snapshot()
    station = model.station_utilization()
    station_rows = "".join(
        f'<div class="hm-meter"><span>{html.escape(name.replace("_", " "))}</span>{_bar(value, "#4f7f72")}</div>'
        for name, value in station.items()
    )
    log_rows = "".join(
        f'<li><span>{event["time_seconds"]:.0f}s</span> {html.escape(str(event["message"]))}</li>'
        for event in model.event_log[-8:]
    )
    return (
        '<section class="hm-panel" data-panel="performance">'
        "<h3>Performance</h3>"
        f'<div class="hm-kpis"><div><b>{snapshot["agv_utilization"] * 100:.1f}%</b><span>AGV utilization</span></div>'
        f'<div><b>{snapshot["waste_station_queue"]}</b><span>waste station queue</span></div>'
        f'<div><b>{snapshot["avg_meal_wait_seconds"]:.0f}s</b><span>meal wait</span></div></div>'
        f'<div class="hm-stations">{station_rows}</div>'
        f'<ol class="hm-log">{log_rows}</ol>'
        "</section>"
    )


def render_tiled_views(model: HospitalMaterialHandlingModel, space: HospitalSpace | None = None) -> str:
    """Render multiple 2D inspection views as one tiled HTML surface."""
    if space is None:
        space = parse_hospital_space()
    styles = """
    <style>
    .hm-wrap{font-family:Inter,Arial,sans-serif;color:#1f2a32}
    .hm-grid{display:grid;grid-template-columns:repeat(2,minmax(360px,1fr));gap:12px;align-items:start}
    .hm-panel{border:1px solid #d8dedb;border-radius:6px;background:#fbfcfb;padding:12px;min-height:220px}
    .hm-panel h3{font-size:15px;margin:0 0 8px 0;font-weight:650}
    .hm-subtle{font-size:12px;color:#61706a;margin-bottom:8px}
    .hm-floor-grid{display:grid;grid-template-columns:repeat(2,minmax(260px,1fr));gap:8px}
    .hm-floor{min-height:154px;border:1px solid #d9dfdc;background:#f4f7f5;border-radius:4px;padding:6px}
    .hm-floor-name{font-size:11px;color:#56635e;margin-bottom:5px}
    .hm-overlay{display:flex;gap:3px;align-items:center;overflow:hidden}
    .hm-chip,.hm-agv{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:18px;
      border-radius:3px;color:white;font-size:10px;margin:0 3px 3px 0}
    .hm-agv{background:#344c5a}
    table{width:100%;border-collapse:collapse;font-size:12px}
    th,td{text-align:left;border-bottom:1px solid #e5e9e7;padding:5px 4px}
    th{color:#5f6d67;font-weight:600}
    .hm-dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}
    .hm-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}
    .hm-kpis div{background:#f1f4f2;border-radius:4px;padding:8px}
    .hm-kpis b{display:block;font-size:16px}
    .hm-kpis span{font-size:11px;color:#5e6b65}
    .hm-meter{display:flex;justify-content:space-between;gap:8px;align-items:center;font-size:11px;margin:6px 0}
    .hm-log{font-size:11px;color:#46534e;margin:10px 0 0 0;padding-left:18px;max-height:90px;overflow:auto}
    .hm-log span{color:#7a8781}
    @media(max-width:900px){.hm-grid{grid-template-columns:1fr}.hm-floor-grid{grid-template-columns:1fr}}
    </style>
    """
    return (
        f'<div class="hm-wrap">{styles}<div class="hm-grid">'
        + _floor_grid(model, space)
        + _agv_status(model)
        + _mission_queues(model)
        + _performance(model)
        + "</div></div>"
    )


def _new_model(seed: int, agv_count: int, demand_scale: float, initial_hour: float) -> HospitalMaterialHandlingModel:
    return HospitalMaterialHandlingModel(
        seed=seed,
        agv_count=agv_count,
        demand_scale=demand_scale,
        initial_time_seconds=initial_hour * 60 * 60,
        step_seconds=300,
    )


@solara.component
def Page() -> None:
    seed, set_seed = solara.use_state(42)
    agv_count, set_agv_count = solara.use_state(10)
    demand_scale, set_demand_scale = solara.use_state(1.0)
    initial_hour, set_initial_hour = solara.use_state(6.0)
    model, set_model = solara.use_state(_new_model(seed, agv_count, demand_scale, initial_hour))
    render_tick, set_render_tick = solara.use_state(0)

    def reset() -> None:
        set_model(_new_model(seed, agv_count, demand_scale, initial_hour))
        set_render_tick(render_tick + 1)

    def step_once() -> None:
        model.step()
        set_render_tick(render_tick + 1)

    def run_one_hour() -> None:
        for _ in range(12):
            model.step()
        set_render_tick(render_tick + 1)

    snapshot = model.snapshot()
    solara.Title("Mesa Hospital Material Handling")
    with solara.Column(gap="12px", style="font-family: Inter, Arial, sans-serif; color: #1f2a32;"):
        solara.Markdown("## Mesa Hospital Material Handling")
        with solara.Row(gap="10px"):
            solara.Button("Step", on_click=step_once)
            solara.Button("Run 1h", on_click=run_one_hour)
            solara.Button("Reset", on_click=reset)
        with solara.Row(gap="18px"):
            with solara.Column(style="min-width: 260px; max-width: 320px;"):
                solara.SliderInt("Seed", value=seed, min=1, max=999, on_value=set_seed)
                solara.SliderInt("AGVs", value=agv_count, min=1, max=20, on_value=set_agv_count)
                solara.SliderFloat("Demand scale", value=demand_scale, min=0.25, max=3.0, step=0.25, on_value=set_demand_scale)
                solara.SliderFloat("Initial hour", value=initial_hour, min=0.0, max=23.5, step=0.5, on_value=set_initial_hour)
                solara.Markdown(
                    "\n".join(
                        [
                            f"- Time: `{snapshot['time_hours']:.2f}` h",
                            f"- Busy AGVs: `{snapshot['busy_agvs']}` / `{snapshot['agv_count']}`",
                            f"- Pending carts: `{snapshot['pending_carts']}`",
                            f"- Waste station queue: `{snapshot['waste_station_queue']}`",
                        ]
                    )
                )
            with solara.Column(style="flex:1; min-width: 720px;"):
                solara.HTML(tag="div", unsafe_innerHTML=render_tiled_views(model))
