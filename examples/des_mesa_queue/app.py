"""Solara visualization for a SimPy DES queue wrapped as a Mesa model."""

from __future__ import annotations

import html

import solara

from examples.des_mesa_queue.model import CustomerServiceDesMesaModel


def _bar(value: float, color: str, width: int = 128) -> str:
    clamped = max(0.0, min(1.0, value))
    return (
        f'<svg width="{width}" height="8" viewBox="0 0 {width} 8" role="img">'
        f'<rect width="{width}" height="8" rx="2" fill="#e2e8e4"/>'
        f'<rect width="{int(width * clamped)}" height="8" rx="2" fill="{color}"/></svg>'
    )


def render_queue_dashboard(model: CustomerServiceDesMesaModel) -> str:
    state = model.visualization_state()
    metrics = model.snapshot()
    waiting_jobs = state["waiting_jobs"]
    servers = state["servers"]
    completed = state["recent_completed"]
    events = state["events"]

    queue_chips = "".join(
        '<span class="dmq-job" title="'
        f'{html.escape(job["id"])} waited {job["wait_minutes"]} min">{html.escape(job["id"])}</span>'
        for job in waiting_jobs
    )
    if not queue_chips:
        queue_chips = '<span class="dmq-empty">queue empty</span>'

    server_cards = "".join(
        '<div class="dmq-server" data-server-state="busy">'
        if server["busy"]
        else '<div class="dmq-server" data-server-state="idle">'
        f'<b>{html.escape(server["id"])}</b>'
        f'<span>{html.escape(str(server["job_id"] or "idle"))}</span>'
        f'<small>{server["remaining_minutes"]} min left</small>'
        f'{_bar(1.0 if server["busy"] else 0.0, "#4e7f77")}'
        "</div>"
        for server in servers
    )
    completed_rows = "".join(
        f'<tr><td>{html.escape(job["id"])}</td><td>{html.escape(str(job["server_id"]))}</td>'
        f'<td>{job["system_minutes"]}</td></tr>'
        for job in completed
    )
    log_rows = "".join(
        f'<li><span>{event["time_minutes"]:.1f}</span> {html.escape(str(event["message"]))}</li>'
        for event in events
    )

    return f"""
    <div class="dmq-wrap">
      <style>
        .dmq-wrap{{font-family:Inter,Arial,sans-serif;color:#1f2a32}}
        .dmq-grid{{display:grid;grid-template-columns:minmax(360px,1.2fr) minmax(300px,.8fr);gap:12px;align-items:start}}
        .dmq-panel{{border:1px solid #d3dbd7;border-radius:6px;background:#fbfcfb;padding:12px;min-height:160px}}
        .dmq-panel h3{{font-size:15px;margin:0 0 8px 0;font-weight:650}}
        .dmq-flow{{display:grid;grid-template-columns:1fr auto 1.1fr auto .8fr;gap:8px;align-items:center;margin-top:8px}}
        .dmq-lane{{min-height:110px;border:1px solid #dce4df;background:#f3f7f4;border-radius:5px;padding:8px}}
        .dmq-arrow{{color:#68766f;font-size:22px}}
        .dmq-job{{display:inline-flex;align-items:center;justify-content:center;min-width:52px;height:26px;margin:3px;padding:0 6px;border-radius:4px;background:#476f90;color:white;font-size:11px}}
        .dmq-empty{{display:inline-block;color:#6f7c76;font-size:12px;margin:6px}}
        .dmq-servers{{display:grid;grid-template-columns:repeat(2,minmax(130px,1fr));gap:8px}}
        .dmq-server{{border:1px solid #d4dcd8;border-radius:5px;background:#fff;padding:8px;display:grid;gap:4px}}
        .dmq-server[data-server-state="busy"]{{border-color:#719b92;background:#f0f8f5}}
        .dmq-server b{{font-size:13px}} .dmq-server span,.dmq-server small{{font-size:12px;color:#596960}}
        .dmq-kpis{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}}
        .dmq-kpi{{background:#f0f4f1;border:1px solid #dbe3de;border-radius:5px;padding:8px}}
        .dmq-kpi b{{display:block;font-size:18px}} .dmq-kpi span{{font-size:11px;color:#66736d}}
        table{{width:100%;border-collapse:collapse;font-size:12px}} th,td{{padding:5px;border-bottom:1px solid #e3e9e5;text-align:left}}
        .dmq-log{{font-size:11px;color:#46534e;margin:0;padding-left:18px;max-height:130px;overflow:auto}} .dmq-log span{{color:#7b8982}}
        @media(max-width:920px){{.dmq-grid{{grid-template-columns:1fr}}.dmq-flow{{grid-template-columns:1fr}}.dmq-arrow{{display:none}}}}
      </style>
      <div class="dmq-grid">
        <section class="dmq-panel" data-panel="des-flow">
          <h3>DES event flow</h3>
          <div class="dmq-flow">
            <div class="dmq-lane" data-layer="arrival-source">Arrival source<br><b>{metrics["arrivals"]}</b> generated</div>
            <div class="dmq-arrow">-&gt;</div>
            <div class="dmq-lane" data-layer="waiting-queue">{queue_chips}</div>
            <div class="dmq-arrow">-&gt;</div>
            <div class="dmq-lane dmq-servers" data-layer="service-resource">{server_cards}</div>
          </div>
        </section>
        <section class="dmq-panel" data-panel="metrics">
          <h3>Metrics</h3>
          <div class="dmq-kpis">
            <div class="dmq-kpi"><b>{metrics["time_minutes"]}</b><span>sim minutes</span></div>
            <div class="dmq-kpi"><b>{metrics["waiting"]}</b><span>waiting</span></div>
            <div class="dmq-kpi"><b>{metrics["completed"]}</b><span>completed</span></div>
            <div class="dmq-kpi"><b>{metrics["server_utilization"] * 100:.1f}%</b><span>server utilization</span></div>
          </div>
        </section>
        <section class="dmq-panel" data-panel="recent-completions">
          <h3>Recent completions</h3>
          <table><thead><tr><th>job</th><th>server</th><th>system min</th></tr></thead><tbody>{completed_rows}</tbody></table>
        </section>
        <section class="dmq-panel" data-panel="event-log">
          <h3>Event log</h3>
          <ol class="dmq-log">{log_rows}</ol>
        </section>
      </div>
    </div>
    """


def _new_model(
    seed: int,
    server_count: int,
    arrival_rate_per_hour: float,
    mean_service_minutes: float,
    patience_minutes: float,
) -> CustomerServiceDesMesaModel:
    return CustomerServiceDesMesaModel(
        seed=seed,
        server_count=server_count,
        arrival_rate_per_hour=arrival_rate_per_hour,
        mean_service_minutes=mean_service_minutes,
        patience_minutes=patience_minutes,
        step_minutes=1.0,
    )


@solara.component
def Page() -> None:
    seed, set_seed = solara.use_state(7)
    server_count, set_server_count = solara.use_state(2)
    arrival_rate, set_arrival_rate = solara.use_state(10.0)
    service_minutes, set_service_minutes = solara.use_state(8.0)
    patience_minutes, set_patience_minutes = solara.use_state(20.0)
    model, set_model = solara.use_state(_new_model(seed, server_count, arrival_rate, service_minutes, patience_minutes))
    render_tick, set_render_tick = solara.use_state(0)

    def reset() -> None:
        set_model(_new_model(seed, server_count, arrival_rate, service_minutes, patience_minutes))
        set_render_tick(render_tick + 1)

    def step_once() -> None:
        model.step()
        set_render_tick(render_tick + 1)

    def run_thirty() -> None:
        for _ in range(30):
            model.step()
        set_render_tick(render_tick + 1)

    metrics = model.snapshot()
    solara.Title("Mesa DES Queue")
    with solara.Column(gap="14px", style="font-family: Inter, Arial, sans-serif; color: #1f2a32;"):
        solara.Markdown("## Mesa DES Queue")
        with solara.Row(gap="10px"):
            solara.Button("Step", on_click=step_once)
            solara.Button("Run 30", on_click=run_thirty)
            solara.Button("Reset", on_click=reset)
        with solara.Row(gap="18px"):
            with solara.Column(style="min-width: 270px; max-width: 330px;"):
                solara.SliderInt("Seed", value=seed, min=1, max=999, on_value=set_seed)
                solara.SliderInt("Servers", value=server_count, min=1, max=6, on_value=set_server_count)
                solara.SliderFloat("Arrivals per hour", value=arrival_rate, min=2, max=30, step=1, on_value=set_arrival_rate)
                solara.SliderFloat("Mean service minutes", value=service_minutes, min=2, max=20, step=1, on_value=set_service_minutes)
                solara.SliderFloat("Patience minutes", value=patience_minutes, min=1, max=45, step=1, on_value=set_patience_minutes)
                solara.Markdown(
                    "\n".join(
                        [
                            f"- Time: `{metrics['time_minutes']}` minutes",
                            f"- Arrivals: `{metrics['arrivals']}`",
                            f"- Waiting: `{metrics['waiting']}`",
                            f"- Completed: `{metrics['completed']}`",
                            f"- Abandoned: `{metrics['abandoned']}`",
                            f"- Avg wait: `{metrics['avg_wait_minutes']}` minutes",
                        ]
                    )
                )
            with solara.Column(style="flex: 1; min-width: 520px;"):
                solara.HTML(tag="div", unsafe_innerHTML=render_queue_dashboard(model))

