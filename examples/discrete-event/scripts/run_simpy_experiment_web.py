"""Tiny local web console for submitting SimPy experiment parameters."""

from __future__ import annotations

import argparse
import copy
import datetime
import json
import html
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from run_simpy_experiment import _read_json, run_experiments_from_config


def _safe_float(raw: str, default: float) -> float:
    try:
        return float(raw)
    except Exception:
        return default


def _safe_int(raw: str, default: int) -> int:
    try:
        return int(raw)
    except Exception:
        return default


def _safe_values(raw: str) -> list[float]:
    values = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(float(token))
        except ValueError:
            pass
    return values


def _render_page(config_path: Path, status_html: str | None = None) -> str:
    cfg = _read_json(config_path)
    defaults = cfg.get("fixed_parameters", {})
    default_run = cfg.get("default_run", {})
    sweep = cfg.get("sweep", {})

    fields = {
        "seed": default_run.get("seed", 2026),
        "horizon": default_run.get("horizon", 240),
        "sample_interval": default_run.get("sample_interval", 2),
        "arrival_mean": defaults.get("arrival_mean", 12.0),
        "service_time_mean": defaults.get("service_time_mean", 18.0),
        "maintenance_bays": defaults.get("maintenance_bays", 2),
        "technicians": defaults.get("technicians", 3),
        "support_equipments": defaults.get("support_equipments", 2),
        "initial_parts": defaults.get("initial_parts", 18),
        "parts_capacity": defaults.get("parts_capacity", 60),
        "parts_reorder_point": defaults.get("parts_reorder_point", 8),
        "parts_reorder_qty": defaults.get("parts_reorder_qty", 25),
        "parts_lead_time_mean": defaults.get("parts_lead_time_mean", 14.0),
        "runs_per_value": sweep.get("runs_per_value", 2),
        "seed_start": sweep.get("seed_start", 3000),
        "sweep_param": sweep.get("param", "arrival_mean"),
        "sweep_values": ", ".join(str(v) for v in sweep.get("values", [10.0, 14.0, 20.0])),
    }

    alert_html = ""
    if status_html:
        alert_html = f"<div class='status'>{status_html}</div>"

    return f"""
    <html>
    <head>
      <meta charset='utf-8'/>
      <title>DES Config Console</title>
      <style>
        body {{ font-family: Arial, sans-serif; padding: 24px; background: #f6f8fb; }}
        .status {{ background: #eef6ff; border: 1px solid #aac0dd; padding: 12px; margin-bottom: 20px; }}
        .grid {{ max-width: 900px; display: grid; gap: 10px; grid-template-columns: 1fr 1fr; }}
        label {{ display: block; font-size: 14px; margin-top: 8px; }}
        .field input {{ width: 100%; padding: 8px; }}
        .full {{ grid-column: 1 / 3; }}
        button {{ margin-top: 14px; padding: 10px 16px; }}
      </style>
    </head>
    <body>
      <h2>飞机保障离散事件实验配置</h2>
      <p>填写参数后提交，将触发实验并在页面返回关键结果摘要。</p>
      {alert_html}
      <form method='POST' action='/run'>
        <div class='grid'>
          <div class='field'><label>随机种子起点 seed</label><input name='seed' value='{fields['seed']}'/></div>
          <div class='field'><label>模拟时长 horizon</label><input name='horizon' value='{fields['horizon']}'/></div>
          <div class='field'><label>采样间隔 sample_interval</label><input name='sample_interval' value='{fields['sample_interval']}'/></div>
          <div class='field'><label>任务平均到达间隔 (更小表示更密集)</label><input name='arrival_mean' value='{fields['arrival_mean']}'/></div>
          <div class='field'><label>平均维修时长</label><input name='service_time_mean' value='{fields['service_time_mean']}'/></div>
          <div class='field'><label>维修机位</label><input name='maintenance_bays' value='{fields['maintenance_bays']}'/></div>
          <div class='field'><label>技师数量</label><input name='technicians' value='{fields['technicians']}'/></div>
          <div class='field'><label>保障设备数量</label><input name='support_equipments' value='{fields['support_equipments']}'/></div>
          <div class='field'><label>初始备件库存</label><input name='initial_parts' value='{fields['initial_parts']}'/></div>
          <div class='field'><label>库存上限</label><input name='parts_capacity' value='{fields['parts_capacity']}'/></div>
          <div class='field'><label>再订货阈值</label><input name='parts_reorder_point' value='{fields['parts_reorder_point']}'/></div>
          <div class='field'><label>每次补货数量</label><input name='parts_reorder_qty' value='{fields['parts_reorder_qty']}'/></div>
          <div class='field'><label>补货提前期平均</label><input name='parts_lead_time_mean' value='{fields['parts_lead_time_mean']}'/></div>
          <div class='field'><label>每个参数值重复次数</label><input name='runs_per_value' value='{fields['runs_per_value']}'/></div>
          <div class='field'><label>seed_start</label><input name='seed_start' value='{fields['seed_start']}'/></div>
          <div class='field'><label>扫描参数（固定为 arrival_mean / 可改名）</label><input name='sweep_param' value='{fields['sweep_param']}'/></div>
          <div class='field full'><label>扫描取值（用逗号分隔）</label><input name='sweep_values' value='{fields['sweep_values']}'/></div>
        </div>
        <button type='submit'>运行实验</button>
      </form>
    </body>
    </html>
    """


def _render_result_page(data: dict) -> str:
    output_dir = Path(data["output_dir"])
    status = f"结果写入: {html.escape(str(output_dir))}"
    summary = data.get("summary", [])
    rows = []
    for row in summary:
        rows.append(
            "<tr>"
            f"<td>{row.get('setting')}</td>"
            f"<td>{row.get('value')}</td>"
            f"<td>{row.get('run_id')}</td>"
            f"<td>{row.get('seed')}</td>"
            f"<td>{row.get('completed')}</td>"
            f"<td>{row.get('mean_queue_wait',0.0):.3f}</td>"
            f"<td>{row.get('mean_task_time',0.0):.3f}</td>"
            f"<td>{row.get('avg_bay_util',0.0):.3f}</td>"
            f"<td>{row.get('avg_bay_queue',0.0):.3f}</td>"
            f"<td>{row.get('stockout_events',0)}</td>"
            f"<td>{row.get('reorders',0)}</td>"
            "</tr>"
        )

    return f"""
    <html>
    <head>
      <meta charset='utf-8'/>
      <title>实验完成</title>
      <style>
        body {{ font-family: Arial, sans-serif; padding: 24px; background: #f6f8fb; }}
        table {{ border-collapse: collapse; background: #fff; width: 100%; max-width: 1200px; }}
        th, td {{ border: 1px solid #d9d9d9; padding: 8px; text-align: right; }}
        th {{ background: #efefef; }}
      </style>
    </head>
    <body>
      <h2>实验已完成</h2>
      <p>{status}</p>
      <p>汇总文件: <a href='/artifact/{html.escape(data['summary_csv'].split('/')[-1])}'>{html.escape(data['summary_csv'])}</a></p>
      <table>
        <tr>
          <th>sweep</th><th>value</th><th>run_id</th><th>seed</th><th>completed</th>
          <th>mean_queue_wait</th><th>mean_task_time</th><th>avg_bay_util</th><th>avg_bay_queue</th>
          <th>stockout_events</th><th>reorders</th>
        </tr>
        {''.join(rows)}
      </table>
      <p><a href='/'>返回设置页</a></p>
    </body>
    </html>
    """


class Handler(BaseHTTPRequestHandler):
    server_version = "des-experiment-web/0.1"

    def do_GET(self) -> None:
        if self.path == "/":
            page = _render_page(self.server.config_path)
            self._send(page.encode("utf-8"), 200, "text/html; charset=utf-8")
            return
        if self.path.startswith("/artifact/"):
            name = Path(self.path.replace("/artifact/", "", 1))
            file_path = self.server.result_dir / name
            if not file_path.exists():
                self._send(b"artifact not found", 404, "text/plain; charset=utf-8")
                return
            content = file_path.read_bytes()
            ctype = "application/json" if name.suffix == ".json" else "text/csv"
            self._send(content, 200, ctype)
            return
        self._send(b"not found", 404, "text/plain; charset=utf-8")

    def do_POST(self) -> None:
        if self.path != "/run":
            self._send(b"not found", 404, "text/plain; charset=utf-8")
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        values = parse_qs(body)
        get = lambda k, default="": values.get(k, [default])[0]

        config = _read_json(self.server.config_path)
        fixed = copy.deepcopy(config.get("fixed_parameters", {}))
        fixed["arrival_mean"] = _safe_float(get("arrival_mean"), float(fixed.get("arrival_mean", 12.0)))
        fixed["service_time_mean"] = _safe_float(get("service_time_mean"), float(fixed.get("service_time_mean", 18.0)))
        fixed["parts_per_task_mean"] = fixed.get("parts_per_task_mean", 1.6)
        fixed["maintenance_bays"] = _safe_int(get("maintenance_bays"), int(fixed.get("maintenance_bays", 2)))
        fixed["technicians"] = _safe_int(get("technicians"), int(fixed.get("technicians", 3)))
        fixed["support_equipments"] = _safe_int(get("support_equipments"), int(fixed.get("support_equipments", 2)))
        fixed["initial_parts"] = _safe_int(get("initial_parts"), int(fixed.get("initial_parts", 18)))
        fixed["parts_capacity"] = _safe_int(get("parts_capacity"), int(fixed.get("parts_capacity", 60)))
        fixed["parts_reorder_point"] = _safe_int(get("parts_reorder_point"), int(fixed.get("parts_reorder_point", 8)))
        fixed["parts_reorder_qty"] = _safe_int(get("parts_reorder_qty"), int(fixed.get("parts_reorder_qty", 25)))
        fixed["parts_lead_time_mean"] = _safe_float(
            get("parts_lead_time_mean"), float(fixed.get("parts_lead_time_mean", 14.0))
        )

        default_run = config.get("default_run", {}).copy()
        default_run["seed"] = _safe_int(get("seed"), int(default_run.get("seed", 2026)))
        default_run["horizon"] = _safe_float(get("horizon"), float(default_run.get("horizon", 240)))
        default_run["sample_interval"] = _safe_float(get("sample_interval"), float(default_run.get("sample_interval", 2)))

        sweep_param = get("sweep_param", "arrival_mean")
        sweep_values = _safe_values(get("sweep_values"))
        runs_per_value = _safe_int(get("runs_per_value"), int(config.get("sweep", {}).get("runs_per_value", 2)))
        seed_start = _safe_int(get("seed_start"), int(config.get("sweep", {}).get("seed_start", default_run["seed"])))

        runtime_config = {
            "model_path": config["model_path"],
            "model_class": config["model_class"],
            "default_run": default_run,
            "fixed_parameters": fixed,
            "sweep": {
                "param": sweep_param,
                "values": sweep_values,
                "runs_per_value": runs_per_value,
                "seed_start": seed_start,
            },
        }

        # each run is isolated into timestamped folder
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        result_root = self.server.output_root / stamp
        result_root.mkdir(parents=True, exist_ok=True)
        self.server.result_dir = result_root

        try:
            result = run_experiments_from_config(runtime_config, result_root, None)
            result["summary_csv"] = f"/artifact/{Path(result['summary_csv']).name}"
            page = _render_result_page(result)
            self._send(page.encode("utf-8"), 200, "text/html; charset=utf-8")
        except Exception as exc:
            page = _render_page(
                self.server.config_path,
                status_html=f"<strong>运行失败</strong>：{html.escape(repr(exc))}",
            )
            self._send(page.encode("utf-8"), 500, "text/html; charset=utf-8")

    def _send(self, content: bytes, code: int, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


class ConsoleServer(ThreadingHTTPServer):
    config_path: Path
    output_root: Path
    result_dir: Path


def main() -> int:
    parser = argparse.ArgumentParser(description="DES experiment web console")
    parser.add_argument("--config", required=True, help="Path to base experiment JSON file")
    parser.add_argument("--port", type=int, default=8780, help="Listen port")
    parser.add_argument("--output-dir", default="./des-web-output", help="Experiment output root")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    output_root = Path(args.output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if "model_path" in _read_json(config_path):
        cfg_model = _read_json(config_path)
        model_path = Path(cfg_model["model_path"])
        if not model_path.is_absolute():
            _resolved_model = str((config_path.parent / model_path).resolve())
            cfg_model["model_path"] = _resolved_model
            config_path = Path(config_path.with_name(config_path.name))

    server = ConsoleServer(("127.0.0.1", args.port), Handler)
    server.config_path = config_path
    server.output_root = output_root
    print(f"open http://127.0.0.1:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
