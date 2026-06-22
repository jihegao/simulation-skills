#!/usr/bin/env python3
"""Run the DES agent-swarm MVP from user language to SimPy outputs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

import des_mvp_core


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request_text", help="Natural-language DES modeling request, or 'chat' for stdin chat mode.")
    parser.add_argument(
        "--output-root",
        default="outputs/des_mvp",
        help="Root directory for generated run artifacts.",
    )
    parser.add_argument(
        "--install-dir",
        help="Optional virtualenv directory passed to the SimPy runner for dependency bootstrapping.",
    )
    parser.add_argument("--run-id", help="Optional stable run id. Defaults to a UTC timestamp.")
    parser.add_argument("--session-file", help="Optional session.json path for continuing conversations.")
    return parser.parse_args()


def run_turn(
    *,
    request_text: str,
    output_root: Path,
    install_dir: str | None = None,
    run_id: str | None = None,
    session_file: Path | None = None,
) -> tuple[int, dict]:
    base_run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id, run_dir = allocate_run_dir(output_root, base_run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    session = None
    previous_request = None
    if session_file is not None:
        session = des_mvp_core.load_session(session_file)
        previous_request = session.get("last_request")

    request = des_mvp_core.parse_conversation_turn(request_text, previous_request)
    if request.get("missing_fields"):
        request_path = run_dir / "request.json"
        request_path.write_text(json.dumps(request, indent=2, sort_keys=True), encoding="utf-8")
        return 2, {
            "run_dir": str(run_dir),
            "request": str(request_path),
            "domain": request["domain"],
            "missing_fields": request["missing_fields"],
            "unsupported_reason": request.get("unsupported_reason"),
            "session": str(session_file) if session_file else None,
        }

    artifacts = des_mvp_core.generate_model_artifacts(request, run_dir)
    runner = Path(__file__).resolve().parent / "run_simpy_experiment.py"
    command = [
        sys.executable,
        str(runner),
        "--model",
        artifacts["model"],
        "--config",
        artifacts["experiment"],
        "--output-dir",
        str(run_dir),
    ]
    if install_dir:
        command.extend(["--install-dir", str(Path(install_dir).resolve())])

    completed = subprocess.run(command, text=True, capture_output=True)
    (run_dir / "runner_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "runner_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (run_dir / "runner_command.json").write_text(json.dumps(command, indent=2), encoding="utf-8")
    if completed.returncode != 0:
        return completed.returncode, {
            "run_dir": str(run_dir),
            "domain": request["domain"],
            "template": artifacts["template"],
            "runner_returncode": completed.returncode,
            "runner_stderr": str(run_dir / "runner_stderr.txt"),
            "session": str(session_file) if session_file else None,
        }

    summary_path = run_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    visual_artifacts = des_mvp_core.write_visual_artifacts(run_dir, summary, request, artifacts["template"])
    summary["visuals"] = visual_artifacts
    answer_path = run_dir / "answer.md"
    des_mvp_core.write_answer(summary, request, artifacts["template"], answer_path)

    if session_file is not None and session is not None:
        session = des_mvp_core.append_session_turn(
            session,
            user_text=request_text,
            request=request,
            run_dir=run_dir,
            summary_path=summary_path,
            answer_path=answer_path,
        )
        des_mvp_core.save_session(session_file, session)

    return 0, {
        "run_dir": str(run_dir),
        "request": artifacts["request"],
        "model": artifacts["model"],
        "experiment": artifacts["experiment"],
        "summary": str(summary_path),
        "answer": str(answer_path),
        "domain": request["domain"],
        "template": artifacts["template"],
        "run_count": summary["run_count"],
        "ascii_topology": visual_artifacts["ascii_topology"],
        "metrics_chart": visual_artifacts["metrics_chart"],
        "chart_csv": visual_artifacts["chart_csv"],
        "session": str(session_file) if session_file else None,
    }


def allocate_run_dir(output_root: Path, base_run_id: str) -> tuple[str, Path]:
    root = output_root.resolve()
    candidate_id = base_run_id
    candidate = root / candidate_id
    suffix = 1
    while candidate.exists():
        candidate_id = f"{base_run_id}-{suffix:03d}"
        candidate = root / candidate_id
        suffix += 1
    return candidate_id, candidate


def main() -> int:
    args = parse_args()
    if args.request_text == "chat":
        return run_chat(args)
    code, payload = run_turn(
        request_text=args.request_text,
        output_root=Path(args.output_root),
        install_dir=args.install_dir,
        run_id=args.run_id,
        session_file=Path(args.session_file) if args.session_file else None,
    )
    stream = sys.stdout if code == 0 or code == 2 else sys.stderr
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)
    return code


def run_chat(args: argparse.Namespace) -> int:
    session_file = Path(args.session_file) if args.session_file else Path(args.output_root) / "session.json"
    output_root = Path(args.output_root)
    exit_code = 0
    for raw_line in sys.stdin:
        request_text = raw_line.strip()
        if not request_text:
            continue
        if request_text.lower() in {"exit", "quit"}:
            break
        code, payload = run_turn(
            request_text=request_text,
            output_root=output_root,
            install_dir=args.install_dir,
            run_id=None,
            session_file=session_file,
        )
        print(json.dumps(payload, sort_keys=True), flush=True)
        if code != 0:
            exit_code = code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
