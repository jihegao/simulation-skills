"""Solara visualization for the Mesa Air Defense model."""

from __future__ import annotations

import html

import solara

from examples.air_defense_mesa.model import AirDefenseModel, distance2


FIELD_WIDTH = 720
FIELD_HEIGHT = 460


def _circle(cx: float, cy: float, radius: float, attrs: str) -> str:
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius:.1f}" {attrs} />'


def _label(x: float, y: float, text: str, color: str = "#28313f") -> str:
    safe_text = html.escape(text)
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" fill="{color}" '
        'font-family="Inter, Arial, sans-serif" font-size="11">'
        f"{safe_text}</text>"
    )


def render_battlefield_svg(model: AirDefenseModel) -> str:
    """Render the current model state as an inspection-oriented SVG."""
    parts = [
        f'<svg viewBox="0 0 {FIELD_WIDTH} {FIELD_HEIGHT}" width="100%" '
        'style="background:#f7f9f8;border:1px solid #d5dde1;border-radius:6px" '
        'xmlns="http://www.w3.org/2000/svg">',
        '<rect x="0" y="0" width="720" height="460" fill="#f7f9f8" />',
        '<rect x="0" y="0" width="178" height="460" fill="#dceaf0" opacity="0.7" />',
        _label(18, 28, "base / sea approach", "#456170"),
        _label(410, 28, "protected asset cluster", "#33413d"),
    ]

    parts.append('<g data-layer="radar-zone">')
    for radar in model.radars:
        parts.append(
            _circle(
                radar.x,
                radar.y,
                radar.zone,
                'fill="#6aa6b8" fill-opacity="0.09" stroke="#357f96" '
                'stroke-width="1.5" stroke-dasharray="5 4"',
            )
        )
    parts.append("</g>")

    parts.append('<g data-layer="asset">')
    for asset in model.assets:
        fill = "#263d35" if asset.state == "normal" else "#bb4b31"
        stroke = "#10231f" if asset.state == "normal" else "#7f2c1c"
        parts.append(
            f'<rect x="{asset.x - 5:.1f}" y="{asset.y - 5:.1f}" width="10" height="10" '
            f'rx="1.5" fill="{fill}" stroke="{stroke}" />'
        )
    parts.append("</g>")

    parts.append('<g data-layer="radar">')
    for radar in model.radars:
        parts.append(_circle(radar.x, radar.y, 7, 'fill="#f0b84f" stroke="#755820" stroke-width="1.5"'))
        parts.append(_label(radar.x + 9, radar.y - 8, f"{len(radar.missiles)}/{radar.max_missiles}", "#755820"))
    parts.append("</g>")

    parts.append('<g data-layer="aircraft">')
    for aircraft in model.aircrafts:
        if aircraft.state == "destroyed":
            fill = "#7a2d2a"
        elif aircraft.state == "returning":
            fill = "#8a6b35"
        elif aircraft.state == "departed":
            fill = "#9aa4aa"
        else:
            fill = "#2c5f9e"
        points = (
            f"{aircraft.x + 8:.1f},{aircraft.y:.1f} "
            f"{aircraft.x - 6:.1f},{aircraft.y - 5:.1f} "
            f"{aircraft.x - 3:.1f},{aircraft.y:.1f} "
            f"{aircraft.x - 6:.1f},{aircraft.y + 5:.1f}"
        )
        parts.append(f'<polygon points="{points}" fill="{fill}" stroke="#172232" stroke-width="1" />')
        if aircraft.state == "flying" and aircraft.target.is_alive():
            ground_dist = distance2((aircraft.x, aircraft.y), (aircraft.target.x, aircraft.target.y))
            parts.append(
                f'<line x1="{aircraft.x:.1f}" y1="{aircraft.y:.1f}" '
                f'x2="{aircraft.target.x:.1f}" y2="{aircraft.target.y:.1f}" '
                'stroke="#5f7180" stroke-width="0.7" stroke-dasharray="3 3" opacity="0.65" />'
            )
            parts.append(_label(aircraft.x + 9, aircraft.y + 13, f"{ground_dist:.0f}", "#5f7180"))
    parts.append("</g>")

    parts.append('<g data-layer="missile">')
    for missile in model.missiles:
        parts.append(_circle(missile.x, missile.y, 3.5, 'fill="#d34f35" stroke="#76271d" stroke-width="1"'))
        parts.append(
            f'<line x1="{missile.radar.x:.1f}" y1="{missile.radar.y:.1f}" '
            f'x2="{missile.x:.1f}" y2="{missile.y:.1f}" '
            'stroke="#d34f35" stroke-width="1" opacity="0.7" />'
        )
    parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)


def _new_model(seed: int, aircraft_speed: float, missile_speed: float, radar_zone: float, radar_max_missiles: int, initial_aircraft: int) -> AirDefenseModel:
    return AirDefenseModel(
        seed=seed,
        aircraft_speed=aircraft_speed,
        missile_speed=missile_speed,
        radar_zone=radar_zone,
        radar_max_missiles=radar_max_missiles,
        initial_aircraft=initial_aircraft,
    )


@solara.component
def Page() -> None:
    seed, set_seed = solara.use_state(42)
    aircraft_speed, set_aircraft_speed = solara.use_state(10.0)
    missile_speed, set_missile_speed = solara.use_state(20.0)
    radar_zone, set_radar_zone = solara.use_state(100.0)
    radar_max_missiles, set_radar_max_missiles = solara.use_state(2)
    initial_aircraft, set_initial_aircraft = solara.use_state(6)
    model, set_model = solara.use_state(_new_model(seed, aircraft_speed, missile_speed, radar_zone, radar_max_missiles, initial_aircraft))
    render_tick, set_render_tick = solara.use_state(0)

    def reset() -> None:
        set_model(_new_model(seed, aircraft_speed, missile_speed, radar_zone, radar_max_missiles, initial_aircraft))
        set_render_tick(render_tick + 1)

    def step_once() -> None:
        model.step()
        set_render_tick(render_tick + 1)

    def run_twenty() -> None:
        for _ in range(20):
            model.step()
        set_render_tick(render_tick + 1)

    metrics = model.snapshot()
    solara.Title("Mesa Air Defense")
    with solara.Column(gap="14px", style="font-family: Inter, Arial, sans-serif; color: #1f2a32;"):
        solara.Markdown("## Mesa Air Defense")
        with solara.Row(gap="10px"):
            solara.Button("Step", on_click=step_once)
            solara.Button("Run 20", on_click=run_twenty)
            solara.Button("Reset", on_click=reset)
        with solara.Row(gap="18px"):
            with solara.Column(style="min-width: 270px; max-width: 320px;"):
                solara.SliderInt("Seed", value=seed, min=1, max=999, on_value=set_seed)
                solara.SliderInt("Initial aircraft", value=initial_aircraft, min=1, max=20, on_value=set_initial_aircraft)
                solara.SliderFloat("Aircraft speed", value=aircraft_speed, min=1, max=30, step=1, on_value=set_aircraft_speed)
                solara.SliderFloat("Missile speed", value=missile_speed, min=1, max=40, step=1, on_value=set_missile_speed)
                solara.SliderFloat("Radar zone", value=radar_zone, min=30, max=180, step=5, on_value=set_radar_zone)
                solara.SliderInt("Missiles per radar", value=radar_max_missiles, min=0, max=5, on_value=set_radar_max_missiles)
                solara.Markdown(
                    "\n".join(
                        [
                            f"- Time: `{metrics['time_days']:.2f}` days",
                            f"- Assets destroyed: `{metrics['assets_destroyed']}` / `{metrics['assets_total']}`",
                            f"- Aircraft destroyed: `{metrics['aircraft_destroyed']}`",
                            f"- Missiles fired: `{metrics['missiles_fired']}`",
                            f"- Active missiles: `{metrics['active_missiles']}`",
                        ]
                    )
                )
            with solara.Column(style="flex: 1; min-width: 520px;"):
                solara.HTML(tag="div", unsafe_innerHTML=render_battlefield_svg(model))
