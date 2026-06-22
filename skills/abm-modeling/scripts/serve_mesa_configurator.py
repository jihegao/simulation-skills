#!/usr/bin/env python3
"""Serve a local browser form for configuring and running a Mesa experiment."""

from __future__ import annotations

import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable
from urllib.parse import parse_qs


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8776
DEFAULT_MESA_INSTALL_DIR = ".abm-mesa-env"


class CompletedRun:
    def __init__(self, returncode: int, stdout: str, stderr: str):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Path to the Mesa model Python file.")
    parser.add_argument("--config", required=True, help="Path to the base experiment JSON config.")
    parser.add_argument(
        "--runner",
        default=str(Path(__file__).resolve().with_name("run_mesa_experiment.py")),
        help="Path to run_mesa_experiment.py.",
    )
    parser.add_argument("--output-root", default="/tmp/abm-mesa-configurator", help="Directory for run outputs.")
    parser.add_argument(
        "--install-dir",
        default=os.environ.get("ABM_MESA_INSTALL_DIR", DEFAULT_MESA_INSTALL_DIR),
        help="Optional Mesa virtualenv directory passed through to the runner.",
    )
    parser.add_argument(
        "--python",
        default=os.environ.get("ABM_MESA_PYTHON", sys.executable),
        help="Python executable used to invoke the runner.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="HTTP host.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="HTTP port.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_scalar(text: str):
    stripped = text.strip()
    if stripped == "":
        return ""
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered == "null":
        return None
    try:
        return int(stripped)
    except ValueError:
        pass
    try:
        return float(stripped)
    except ValueError:
        return stripped


def parse_value(text: str):
    stripped = text.strip()
    if stripped.startswith("[") or stripped.startswith("{"):
        return json.loads(stripped)
    if "," in stripped:
        return [parse_scalar(part) for part in stripped.split(",")]
    return parse_scalar(stripped)


def parse_seed_list(text: str) -> list[int]:
    parsed = parse_value(text)
    if parsed in ("", None):
        return []
    values = parsed if isinstance(parsed, list) else [parsed]
    return [int(value) for value in values]


def field_value(form: dict[str, str], name: str, default: str = "") -> str:
    value = form.get(name, default)
    if isinstance(value, list):
        return value[0] if value else default
    return value


_SAFE_NAME = re.compile(r"[^A-Za-z0-9_-]+")


def safe_experiment_name(name: str, default: str = "mesa_experiment") -> str:
    """Return a filesystem-safe run name.

    Strips path separators, dots, whitespace, and shell metacharacters so a
    submitted ``experiment_name`` can never escape ``output_root`` via traversal
    (e.g. ``../../etc``) or inject odd characters into the run directory path.
    """
    cleaned = _SAFE_NAME.sub("_", name.strip()).strip("_-")
    if not cleaned:
        return default
    return cleaned[:64]


def config_from_form(base_config: dict, form: dict[str, str]) -> dict:
    config = json.loads(json.dumps(base_config))
    base_name = config.get("experiment_name") or "mesa_experiment"
    experiment_name = field_value(form, "experiment_name", base_name).strip()
    config["experiment_name"] = safe_experiment_name(experiment_name, default=base_name)

    primary_metric = field_value(form, "primary_metric", config.get("primary_metric", "")).strip()
    if primary_metric:
        config["primary_metric"] = primary_metric

    steps_raw = field_value(form, "steps", str(config.get("steps", 1)))
    try:
        steps_value = int(steps_raw)
    except ValueError as exc:
        raise ValueError(f"steps must be an integer, got: {steps_raw!r}") from exc
    if steps_value < 1:
        raise ValueError("steps must be a positive integer")
    config["steps"] = steps_value

    config["seeds"] = parse_seed_list(
        field_value(form, "seeds", ",".join(str(seed) for seed in config.get("seeds", [])))
    )
    if not config["seeds"]:
        raise ValueError("at least one seed is required")

    # Only existing parameter keys may be updated; new keys cannot be injected.
    parameters = dict(config.get("parameters", {}))
    for key in list(parameters):
        field_name = f"param.{key}"
        if field_name in form:
            parameters[key] = parse_value(field_value(form, field_name))
    config["parameters"] = parameters
    return config


def format_value(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return "" if value is None else str(value)


def render_page(
    model_path: Path,
    config_path: Path,
    config: dict,
    result: dict | None = None,
    error: str | None = None,
) -> str:
    parameter_rows = []
    for name, value in config.get("parameters", {}).items():
        parameter_rows.append(
            "\n".join(
                [
                    '<label class="field">',
                    f"<span>{escape(name)}</span>",
                    (
                        f'<input name="param.{escape(name)}" value="{escape(format_value(value))}" '
                        'autocomplete="off">'
                    ),
                    "</label>",
                ]
            )
        )

    result_block = ""
    if result:
        summary = result.get("summary", {})
        result_block = f"""
        <section class="result">
          <h2>Run complete</h2>
          <p>Summary: <code>{escape(result.get("summary_path", ""))}</code></p>
          <pre>{escape(json.dumps(summary, indent=2, sort_keys=True))}</pre>
        </section>
        """
    elif error:
        result_block = f"""
        <section class="error">
          <h2>Run failed</h2>
          <pre>{escape(error)}</pre>
        </section>
        """

    seeds = ", ".join(str(seed) for seed in config.get("seeds", []))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mesa Experiment Configurator</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
      background: #f7f7f4;
      color: #202124;
    }}
    body {{ margin: 0; }}
    main {{ max-width: 920px; margin: 0 auto; padding: 32px 20px 48px; }}
    header {{ margin-bottom: 24px; }}
    h1 {{ font-size: 28px; margin: 0 0 8px; }}
    h2 {{ font-size: 20px; margin: 0 0 12px; }}
    p {{ margin: 0 0 10px; color: #51534d; }}
    code {{ background: #ecebe4; padding: 2px 5px; border-radius: 4px; }}
    form, .result, .error {{
      background: #ffffff;
      border: 1px solid #dad8ce;
      border-radius: 8px;
      padding: 18px;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .field {{ display: grid; gap: 6px; font-size: 14px; font-weight: 600; }}
    input {{
      font: inherit;
      font-weight: 400;
      min-width: 0;
      border: 1px solid #bbb8ad;
      border-radius: 6px;
      padding: 10px 11px;
    }}
    .actions {{ margin-top: 18px; display: flex; align-items: center; gap: 12px; }}
    button {{
      border: 0;
      border-radius: 6px;
      background: #245c4f;
      color: white;
      padding: 10px 14px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    pre {{ overflow: auto; background: #1f2328; color: #f6f8fa; padding: 14px; border-radius: 6px; }}
    .note {{ font-size: 13px; color: #646760; }}
    .result, .error {{ margin-top: 18px; }}
    .error {{ border-color: #d58989; }}
    @media (max-width: 720px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Mesa Experiment Configurator</h1>
    <p>Model: <code>{escape(str(model_path))}</code></p>
    <p>Base config: <code>{escape(str(config_path))}</code></p>
    <p class="note">Runs execute in Python through the Mesa runner. CSV/JSON outputs remain the evidence source.</p>
  </header>
  <form method="post" action="/run">
    <div class="grid">
      <label class="field">
        <span>experiment_name</span>
        <input name="experiment_name" value="{escape(str(config.get("experiment_name", "mesa_experiment")))}">
      </label>
      <label class="field">
        <span>steps</span>
        <input name="steps" value="{escape(str(config.get("steps", 1)))}" inputmode="numeric">
      </label>
      <label class="field">
        <span>seeds</span>
        <input name="seeds" value="{escape(seeds)}" autocomplete="off">
      </label>
      <label class="field">
        <span>primary_metric</span>
        <input name="primary_metric" value="{escape(str(config.get("primary_metric", "")))}">
      </label>
      {"".join(parameter_rows)}
    </div>
    <div class="actions">
      <button type="submit">Run experiment</button>
      <span class="note">Use comma-separated values for sweeps.</span>
    </div>
  </form>
  {result_block}
</main>
</body>
</html>
"""


def default_run_command(command: list[str], **kwargs) -> CompletedRun:
    completed = subprocess.run(command, **kwargs)
    return CompletedRun(completed.returncode, completed.stdout or "", completed.stderr or "")


def run_configured_experiment(
    *,
    model_path: Path,
    base_config_path: Path,
    runner_path: Path,
    output_root: Path,
    form: dict[str, str],
    python_executable: str,
    install_dir: Path | None,
    run_command: Callable[..., CompletedRun] = default_run_command,
) -> dict:
    base_config = load_json(base_config_path)
    config = config_from_form(base_config, form)
    run_dir = output_root / f"{int(time.time() * 1000)}-{config['experiment_name']}"
    output_dir = run_dir / "outputs"
    run_dir.mkdir(parents=True, exist_ok=True)
    config_path = run_dir / "experiment.json"
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")

    command = [
        python_executable,
        str(runner_path),
        "--model",
        str(model_path),
        "--config",
        str(config_path),
        "--output-dir",
        str(output_dir),
    ]
    if install_dir is not None:
        command.extend(["--install-dir", str(install_dir)])

    completed = run_command(command, text=True, capture_output=True, timeout=300)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout or f"Runner exited with {completed.returncode}")

    summary_path = output_dir / "summary.json"
    summary = load_json(summary_path)
    return {
        "config": config,
        "config_path": str(config_path),
        "output_dir": str(output_dir),
        "summary_path": str(summary_path),
        "summary": summary,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def flatten_form(body: bytes) -> dict[str, str]:
    parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


def make_handler(
    *,
    model_path: Path,
    base_config_path: Path,
    runner_path: Path,
    output_root: Path,
    python_executable: str,
    install_dir: Path | None,
):
    class MesaConfiguratorHandler(BaseHTTPRequestHandler):
        def send_html(self, html: str, status: int = 200) -> None:
            payload = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:
            if self.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            config = load_json(base_config_path)
            self.send_html(render_page(model_path, base_config_path, config))

        def do_POST(self) -> None:
            if self.path != "/run":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            form = flatten_form(self.rfile.read(length))
            try:
                result = run_configured_experiment(
                    model_path=model_path,
                    base_config_path=base_config_path,
                    runner_path=runner_path,
                    output_root=output_root,
                    form=form,
                    python_executable=python_executable,
                    install_dir=install_dir,
                )
                config = result["config"]
                html = render_page(model_path, base_config_path, config, result=result)
                self.send_html(html)
            except Exception as exc:  # noqa: BLE001 - display local run errors in the browser page.
                base_config = load_json(base_config_path)
                try:
                    config = config_from_form(base_config, form)
                except Exception:
                    config = base_config
                self.send_html(render_page(model_path, base_config_path, config, error=str(exc)), status=500)

        def log_message(self, format: str, *args) -> None:
            sys.stderr.write("configurator: " + (format % args) + "\n")

    return MesaConfiguratorHandler


def main() -> int:
    args = parse_args()
    model_path = Path(args.model).resolve()
    base_config_path = Path(args.config).resolve()
    runner_path = Path(args.runner).resolve()
    output_root = Path(args.output_root).resolve()
    install_dir = Path(args.install_dir).resolve() if args.install_dir else None
    output_root.mkdir(parents=True, exist_ok=True)

    handler = make_handler(
        model_path=model_path,
        base_config_path=base_config_path,
        runner_path=runner_path,
        output_root=output_root,
        python_executable=args.python,
        install_dir=install_dir,
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Mesa configurator listening at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping configurator.", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
