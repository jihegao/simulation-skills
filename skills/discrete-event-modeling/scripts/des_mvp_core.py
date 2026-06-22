from __future__ import annotations

import copy
import csv
import json
import re
import textwrap
from pathlib import Path


SCHEMA = "des-agent-request/v0"
SESSION_SCHEMA = "des-agent-session/v0"


def parse_user_request(text: str) -> dict:
    normalized = text.lower()
    if _looks_like_repair_queue(normalized):
        return _repair_queue_request(text, normalized)
    if _looks_like_spares_inventory(normalized):
        return _spares_inventory_request(text, normalized)
    return {
        "schema": SCHEMA,
        "domain": "unsupported",
        "question": text,
        "horizon": None,
        "seeds": [],
        "parameters": {},
        "metrics": {},
        "assumptions": [],
        "missing_fields": ["domain"],
        "unsupported_reason": "The MVP supports repair queue and spare-parts inventory requests.",
    }


def parse_conversation_turn(text: str, previous_request: dict | None = None) -> dict:
    normalized = text.lower()
    if previous_request is None:
        return parse_user_request(text)

    if previous_request.get("domain") == "repair_queue":
        repairers = _repairer_followup(normalized)
        if repairers:
            updated = copy.deepcopy(previous_request)
            updated["question"] = text
            updated["parameters"]["repairers"] = repairers
            updated["resources"]["repairers"] = repairers
            updated["missing_fields"] = []
            updated.setdefault("assumptions", []).append("follow-up changed repairers from previous request")
            return updated
    if previous_request.get("domain") == "spares_inventory":
        reorder_points = _reorder_point_followup(normalized)
        if reorder_points:
            updated = copy.deepcopy(previous_request)
            updated["question"] = text
            updated["parameters"]["reorder_point"] = reorder_points
            updated["missing_fields"] = []
            updated.setdefault("assumptions", []).append("follow-up changed reorder_point from previous request")
            return updated

    request = parse_user_request(text)
    if request.get("domain") != "unsupported":
        return request

    request["missing_fields"] = ["followup"]
    request["unsupported_reason"] = "The follow-up could not be applied to the previous DES request."
    return request


def load_session(session_path: Path) -> dict:
    if not session_path.exists():
        return {"schema": SESSION_SCHEMA, "turns": [], "last_request": None, "last_run_dir": None}
    return json.loads(session_path.read_text(encoding="utf-8"))


def save_session(session_path: Path, session: dict) -> None:
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(session, indent=2, sort_keys=True), encoding="utf-8")


def append_session_turn(
    session: dict,
    *,
    user_text: str,
    request: dict,
    run_dir: Path,
    summary_path: Path,
    answer_path: Path,
) -> dict:
    updated = copy.deepcopy(session)
    updated.setdefault("schema", SESSION_SCHEMA)
    updated.setdefault("turns", [])
    turn = {
        "user_text": user_text,
        "domain": request.get("domain"),
        "request": request,
        "run_dir": str(run_dir),
        "summary": str(summary_path),
        "answer": str(answer_path),
    }
    updated["turns"].append(turn)
    updated["last_request"] = request
    updated["last_run_dir"] = str(run_dir)
    return updated


def generate_model_artifacts(request: dict, work_dir: Path) -> dict:
    if request.get("missing_fields"):
        raise ValueError(f"Cannot generate model with missing fields: {request['missing_fields']}")
    domain = request.get("domain")
    if domain not in {"repair_queue", "spares_inventory"}:
        raise ValueError(f"Unsupported MVP domain: {request.get('domain')}")

    work_dir.mkdir(parents=True, exist_ok=True)
    request_path = work_dir / "request.json"
    model_path = work_dir / "model.py"
    experiment_path = work_dir / "experiment.json"

    request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
    if domain == "repair_queue":
        template = "repair_queue"
        model_class = "RepairQueueModel"
        model_source = _repair_queue_model_source()
    else:
        template = "spares_inventory"
        model_class = "SparePartsInventoryModel"
        model_source = _spares_inventory_model_source()
    model_path.write_text(model_source, encoding="utf-8")
    experiment = {
        "experiment_name": f"des_mvp_{template}",
        "model_class": model_class,
        "until": request["horizon"]["value"],
        "seeds": request["seeds"],
        "primary_metric": request["metrics"]["primary"],
        "parameters": request["parameters"],
    }
    experiment_path.write_text(json.dumps(experiment, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "template": template,
        "request": str(request_path),
        "model": str(model_path),
        "experiment": str(experiment_path),
    }


def write_answer(summary: dict, request: dict, template: str, answer_path: Path) -> None:
    visuals = summary.get("visuals", {})
    topology_text = visuals.get("ascii_topology_text", "")
    chart_text = visuals.get("metrics_chart_text", "")
    primary_metric = request["metrics"]["primary"]
    metric = summary.get("metrics", {}).get(primary_metric, {})
    effects = summary.get("parameter_effects", {})
    effect_lines = []
    for parameter, values in effects.items():
        rendered = ", ".join(f"{value}: {result:.4f}" for value, result in values.items())
        effect_lines.append(f"- {parameter}: {rendered}")
    if not effect_lines:
        effect_lines.append("- No parameter sweep effects were reported.")

    seeds = ", ".join(str(seed) for seed in summary.get("seeds", []))
    if template == "repair_queue":
        mechanism = (
            "- In this repair queue model, tighter repair capacity increases waiting when "
            "arrivals overlap with occupied repairers; adding repairers reduces queue pressure "
            "when service time consumes a high share of available capacity."
        )
    else:
        mechanism = (
            "- In this spare-parts inventory model, demand consumes on-hand stock and "
            "stockouts occur when replenishment lead time leaves the system below demand. "
            "Higher reorder points can improve immediate service level by placing orders sooner."
        )

    body = [
        f"# DES MVP Result: {template}",
        "",
        f"Experiment question: {request['question']}",
        f"Template: {template}",
        f"Runs: {summary.get('run_count')} seeded SimPy runs",
        f"Seeds: {seeds}",
        f"Horizon: {summary.get('until')} simulated minutes",
        "",
        "Primary metric:",
        (
            f"- {primary_metric}: mean {metric.get('mean', 0.0):.4f}, "
            f"range {metric.get('min', 0.0):.4f} to {metric.get('max', 0.0):.4f}"
        ),
        "",
        "Parameter effects:",
        *effect_lines,
        "",
        "ASCII topology:",
        "```text",
        topology_text,
        "```",
        "",
        "Metric chart:",
        "```text",
        chart_text,
        "```",
        "",
        "Artifact paths:",
        f"- ASCII topology: {visuals.get('ascii_topology', '')}",
        f"- Metrics chart: {visuals.get('metrics_chart', '')}",
        f"- Chart CSV: {visuals.get('chart_csv', '')}",
        "",
        "Mechanism:",
        mechanism,
        "",
        "Assumptions and limits:",
        *[f"- {item}" for item in request.get("assumptions", [])],
        (
            "- Results are simulation evidence under the encoded event rules; this MVP result "
            "does not prove external-world causality without calibration and sensitivity checks."
        ),
        "",
    ]
    answer_path.write_text("\n".join(body), encoding="utf-8")


def build_ascii_topology(request: dict) -> str:
    if request.get("domain") == "repair_queue":
        repairers = ",".join(str(value) for value in request["parameters"].get("repairers", []))
        return "\n".join(
            [
                "[Arrivals]",
                f"  mean interval: {request['parameters']['arrival_interval'][0]} min",
                "      |",
                "      v",
                "[Queue] ---> [Repairers]",
                f"              capacity sweep: {repairers}",
                "      |",
                "      v",
                "[Completed repairs]",
            ]
        )
    reorder_points = ",".join(str(value) for value in request["parameters"].get("reorder_point", []))
    return "\n".join(
        [
            "[Demand]",
            f"  mean interval: {request['parameters']['demand_interval'][0]} hr",
            "      |",
            "      v",
            "[On-hand stock] -- below reorder point --> [Replenishment order]",
            f"      |                                  reorder sweep: {reorder_points}",
            "      v",
            "[Filled demand or stockout]",
        ]
    )


def build_metrics_chart(summary: dict, request: dict) -> str:
    primary_metric = request.get("metrics", {}).get("primary") or summary.get("primary_metric") or "metric"
    effects = summary.get("parameter_effects", {})
    if not effects:
        return f"{primary_metric}: no parameter sweep effects reported"
    parameter, values = next(iter(effects.items()))
    numeric_values = [(str(value), float(metric)) for value, metric in values.items()]
    max_value = max((metric for _, metric in numeric_values), default=0.0)
    scale = max_value / 32.0 if max_value > 0 else 1.0
    lines = [f"{primary_metric} by {parameter}"]
    for value, metric in numeric_values:
        bar = "#" * max(1, int(round(metric / scale))) if metric > 0 else ""
        lines.append(f"{parameter}={value:<8} | {bar} {metric:.4f}")
    return "\n".join(lines)


def write_visual_artifacts(run_dir: Path, summary: dict, request: dict, template: str) -> dict:
    del template
    run_dir.mkdir(parents=True, exist_ok=True)
    topology_text = build_ascii_topology(request)
    chart_text = build_metrics_chart(summary, request)
    topology_path = run_dir / "ascii_topology.txt"
    chart_path = run_dir / "metrics_chart.txt"
    csv_path = run_dir / "chart.csv"
    topology_path.write_text(topology_text, encoding="utf-8")
    chart_path.write_text(chart_text, encoding="utf-8")

    primary_metric = request.get("metrics", {}).get("primary") or "metric"
    effects = summary.get("parameter_effects", {})
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["parameter", "value", "metric", "mean"])
        for parameter, values in effects.items():
            for value, metric in values.items():
                writer.writerow([parameter, value, primary_metric, metric])

    return {
        "ascii_topology": str(topology_path),
        "metrics_chart": str(chart_path),
        "chart_csv": str(csv_path),
        "ascii_topology_text": topology_text,
        "metrics_chart_text": chart_text,
    }


def _looks_like_repair_queue(text: str) -> bool:
    return any(word in text for word in ["repair", "server", "service"]) and any(
        word in text for word in ["arrive", "arrival", "jobs", "queue", "repairers"]
    )


def _looks_like_spares_inventory(text: str) -> bool:
    return any(word in text for word in ["spare", "stock", "inventory", "reorder"]) and any(
        word in text for word in ["demand", "part", "parts", "stockout"]
    )


def _repair_queue_request(original: str, normalized: str) -> dict:
    arrival_interval = _number_before_unit(normalized, ["minute", "minutes", "min"]) or 18.0
    horizon_hours = _number_before_unit(normalized, ["hour", "hours", "hr"])
    horizon = int((horizon_hours or 24.0) * 60)
    repairers = _repairer_sweep(normalized)
    assumptions = [
        "repair_time_mean defaults to 45.0 minutes",
        "repair_time_sigma defaults to 9.0 minutes",
        "monitor_interval defaults to 120.0 minutes",
    ]
    return {
        "schema": SCHEMA,
        "domain": "repair_queue",
        "question": original,
        "horizon": {"value": horizon, "unit": "minute"},
        "seeds": [11, 22],
        "entities": ["repair_jobs", "repairers"],
        "arrivals": {"process": "exponential", "mean_interval": arrival_interval, "unit": "minute"},
        "resources": {"repairers": repairers},
        "processes": {"repair_time": "normal_positive", "unit": "minute"},
        "parameters": {
            "arrival_interval": [arrival_interval],
            "repair_time_mean": [45.0],
            "repair_time_sigma": [9.0],
            "repairers": repairers,
            "monitor_interval": [120.0],
        },
        "metrics": {
            "primary": "average_wait",
            "secondary": ["completed_repairs", "repairer_utilization"],
        },
        "assumptions": assumptions,
        "missing_fields": [],
    }


def _spares_inventory_request(original: str, normalized: str) -> dict:
    demand_interval = _number_before_unit(normalized, ["hour", "hours", "hr"]) or 12.0
    horizon_days = _number_before_unit(normalized, ["day", "days"])
    horizon = int((horizon_days or 30.0) * 24)
    reorder_points = _sweep_after_phrase(normalized, "reorder point") or [10, 20]
    return {
        "schema": SCHEMA,
        "domain": "spares_inventory",
        "question": original,
        "horizon": {"value": horizon, "unit": "hour"},
        "seeds": [11, 22],
        "entities": ["part_demands", "on_hand_stock", "replenishment_orders"],
        "arrivals": {"process": "exponential", "mean_interval": demand_interval, "unit": "hour"},
        "resources": {"stock": "container"},
        "processes": {"replenishment": "reorder_point_policy", "lead_time_unit": "hour"},
        "parameters": {
            "demand_interval": [demand_interval],
            "initial_stock": [40],
            "reorder_point": reorder_points,
            "order_quantity": [40],
            "lead_time": [72.0],
            "monitor_interval": [24.0],
        },
        "metrics": {
            "primary": "service_level",
            "secondary": ["stockouts", "orders_placed", "stock_level"],
        },
        "assumptions": [
            "initial_stock defaults to 40 parts",
            "order_quantity defaults to 40 parts",
            "lead_time defaults to 72.0 hours",
            "monitor_interval defaults to 24.0 hours",
        ],
        "missing_fields": [],
    }


def _number_before_unit(text: str, units: list[str]) -> float | None:
    unit_pattern = "|".join(re.escape(unit) for unit in units)
    match = re.search(rf"(\d+(?:\.\d+)?)\s*(?:{unit_pattern})\b", text)
    if not match:
        return None
    return float(match.group(1))


def _repairer_sweep(text: str) -> list[int]:
    if re.search(r"\bone\s+and\s+two\s+repairers\b", text) or re.search(r"\b1\s+and\s+2\s+repairers\b", text):
        return [1, 2]
    match = re.search(r"(\d+)\s+repairers?", text)
    if match:
        return [int(match.group(1))]
    return [1]


def _repairer_followup(text: str) -> list[int] | None:
    match = re.search(r"repairers?\s+(?:to|=)\s+(\d+)\s+(?:and|or|vs|versus|,)\s+(\d+)", text)
    if match:
        return [int(match.group(1)), int(match.group(2))]
    match = re.search(r"repairers?\s+(?:to|=)\s+(\d+)", text)
    if match:
        return [int(match.group(1))]
    return None


def _reorder_point_followup(text: str) -> list[int] | None:
    return _sweep_after_phrase(text, "reorder point") or _single_after_phrase(text, "reorder point")


def _single_after_phrase(text: str, phrase: str) -> list[int] | None:
    match = re.search(rf"{re.escape(phrase)}\s+(?:to|=)\s+(\d+)", text)
    if not match:
        return None
    return [int(match.group(1))]


def _sweep_after_phrase(text: str, phrase: str) -> list[int] | None:
    match = re.search(rf"{re.escape(phrase)}\s+(\d+)\s+(?:and|or|vs|versus|,)\s+(\d+)", text)
    if not match:
        return None
    return [int(match.group(1)), int(match.group(2))]


def _repair_queue_model_source() -> str:
    return textwrap.dedent(
        '''
        from __future__ import annotations

        import random

        import simpy


        class RepairQueueModel:
            def __init__(
                self,
                *,
                arrival_interval: float = 18.0,
                repair_time_mean: float = 45.0,
                repair_time_sigma: float = 9.0,
                repairers: int = 1,
                monitor_interval: float = 120.0,
                seed: int | None = None,
            ) -> None:
                self.arrival_interval = float(arrival_interval)
                self.repair_time_mean = float(repair_time_mean)
                self.repair_time_sigma = float(repair_time_sigma)
                self.repairers = int(repairers)
                self.monitor_interval = float(monitor_interval)
                self.rng = random.Random(seed)
                self.env = simpy.Environment()
                self.crew = simpy.Resource(self.env, capacity=self.repairers)
                self.arrivals = 0
                self.completed_repairs = 0
                self.waits: list[float] = []
                self.busy_time = 0.0
                self.rows: list[dict] = []

            def run(self, until: float) -> list[dict]:
                self.env.process(self._arrival_process(until))
                self.env.process(self._monitor(until))
                self.rows.append(self._snapshot())
                self.env.run(until=until)
                if not self.rows or self.rows[-1]["time"] < until:
                    self.rows.append(self._snapshot(time=until))
                return self.rows

            def _arrival_process(self, until: float):
                while self.env.now < until:
                    delay = self.rng.expovariate(1.0 / self.arrival_interval)
                    yield self.env.timeout(delay)
                    if self.env.now < until:
                        self.arrivals += 1
                        self.env.process(self._repair_job())

            def _repair_job(self):
                arrival_time = self.env.now
                with self.crew.request() as request:
                    yield request
                    self.waits.append(self.env.now - arrival_time)
                    repair_time = max(0.1, self.rng.gauss(self.repair_time_mean, self.repair_time_sigma))
                    self.busy_time += repair_time
                    yield self.env.timeout(repair_time)
                    self.completed_repairs += 1

            def _monitor(self, until: float):
                while self.env.now < until:
                    yield self.env.timeout(self.monitor_interval)
                    self.rows.append(self._snapshot())

            def _snapshot(self, *, time: float | None = None) -> dict:
                now = self.env.now if time is None else time
                average_wait = sum(self.waits) / len(self.waits) if self.waits else 0.0
                utilization = min(1.0, self.busy_time / max(1.0, now * self.repairers))
                return {
                    "time": round(now, 3),
                    "arrivals": self.arrivals,
                    "completed_repairs": self.completed_repairs,
                    "queue_depth": len(self.crew.queue),
                    "average_wait": round(average_wait, 3),
                    "repairer_utilization": round(utilization, 4),
                }
        '''
    ).lstrip()


def _spares_inventory_model_source() -> str:
    return textwrap.dedent(
        '''
        from __future__ import annotations

        import random

        import simpy


        class SparePartsInventoryModel:
            def __init__(
                self,
                *,
                demand_interval: float = 12.0,
                initial_stock: int = 40,
                reorder_point: int = 15,
                order_quantity: int = 40,
                lead_time: float = 72.0,
                monitor_interval: float = 24.0,
                seed: int | None = None,
            ) -> None:
                self.demand_interval = float(demand_interval)
                self.initial_stock = int(initial_stock)
                self.reorder_point = int(reorder_point)
                self.order_quantity = int(order_quantity)
                self.lead_time = float(lead_time)
                self.monitor_interval = float(monitor_interval)
                self.rng = random.Random(seed)
                self.env = simpy.Environment()
                capacity = max(1, self.initial_stock + self.order_quantity * 4)
                self.stock = simpy.Container(self.env, capacity=capacity, init=self.initial_stock)
                self.demands = 0
                self.filled_demands = 0
                self.stockouts = 0
                self.orders_placed = 0
                self.order_in_transit = False
                self.rows: list[dict] = []

            def run(self, until: float) -> list[dict]:
                self.env.process(self._demand_process(until))
                self.env.process(self._monitor(until))
                self.rows.append(self._snapshot())
                self.env.run(until=until)
                if not self.rows or self.rows[-1]["time"] < until:
                    self.rows.append(self._snapshot(time=until))
                return self.rows

            def _demand_process(self, until: float):
                while self.env.now < until:
                    yield self.env.timeout(self.rng.expovariate(1.0 / self.demand_interval))
                    if self.env.now < until:
                        self.demands += 1
                        if self.stock.level >= 1:
                            yield self.stock.get(1)
                            self.filled_demands += 1
                        else:
                            self.stockouts += 1
                        self._maybe_order()

            def _maybe_order(self) -> None:
                if self.order_in_transit:
                    return
                if self.stock.level <= self.reorder_point:
                    self.order_in_transit = True
                    self.orders_placed += 1
                    self.env.process(self._replenish())

            def _replenish(self):
                yield self.env.timeout(self.lead_time)
                room = self.stock.capacity - self.stock.level
                yield self.stock.put(min(self.order_quantity, room))
                self.order_in_transit = False
                self._maybe_order()

            def _monitor(self, until: float):
                while self.env.now < until:
                    yield self.env.timeout(self.monitor_interval)
                    self.rows.append(self._snapshot())

            def _snapshot(self, *, time: float | None = None) -> dict:
                service_level = self.filled_demands / self.demands if self.demands else 1.0
                return {
                    "time": round(self.env.now if time is None else time, 3),
                    "stock_level": round(self.stock.level, 3),
                    "demands": self.demands,
                    "filled_demands": self.filled_demands,
                    "stockouts": self.stockouts,
                    "orders_placed": self.orders_placed,
                    "service_level": round(service_level, 4),
                }
        '''
    ).lstrip()
