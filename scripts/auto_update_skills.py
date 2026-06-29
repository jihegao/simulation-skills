#!/usr/bin/env python3
"""Best-effort startup updater for the simulation-skills suite."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path


FALSE_VALUES = {"0", "false", "no", "off"}
DEFAULT_INTERVAL_SECONDS = 6 * 60 * 60


def is_github_repo_url(repo_url: str) -> bool:
    return "github.com/" in repo_url or "github.com:" in repo_url


def is_disabled(env: dict[str, str]) -> bool:
    return env.get("SIMULATION_SKILLS_AUTO_UPDATE", "").strip().lower() in FALSE_VALUES


def log(message: str, quiet: bool) -> None:
    if not quiet:
        print(message, file=sys.stderr)


def run_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def installed_skill_dir(script_path: Path) -> Path | None:
    if script_path.parent.name != "scripts":
        return None
    skill_dir = script_path.parent.parent
    if (skill_dir / "SKILL.md").exists():
        return skill_dir
    return None


def discover_suite_root(script_path: Path) -> Path | None:
    for parent in script_path.resolve().parents:
        if (parent / "scripts" / "install_skills.sh").exists() and (parent / "skills").is_dir():
            return parent
    return None


def git_remote_url(source_root: Path) -> str:
    if not (source_root / ".git").exists():
        return ""
    result = run_command(["git", "remote", "get-url", "origin"], cwd=source_root)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def git_dirty(source_root: Path) -> bool:
    result = run_command(["git", "status", "--porcelain"], cwd=source_root)
    return result.returncode != 0 or bool(result.stdout.strip())


def update_checkout(source_root: Path, quiet: bool) -> Path | None:
    if not (source_root / ".git").exists():
        return None
    if git_dirty(source_root):
        log(f"simulation-skills auto-update skipped: dirty checkout at {source_root}", quiet)
        return None
    result = run_command(["git", "pull", "--ff-only"], cwd=source_root)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        log(f"simulation-skills auto-update skipped: git pull failed: {detail}", quiet)
        return None
    return source_root


def update_cache(repo_url: str, cache_dir: Path, quiet: bool) -> Path | None:
    source_root = cache_dir / "github-source"
    if not source_root.exists():
        source_root.parent.mkdir(parents=True, exist_ok=True)
        result = run_command(["git", "clone", "--depth", "1", repo_url, str(source_root)])
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            log(f"simulation-skills auto-update skipped: git clone failed: {detail}", quiet)
            return None
        return source_root

    if not (source_root / ".git").exists():
        log(f"simulation-skills auto-update skipped: cache is not a git checkout at {source_root}", quiet)
        return None
    if git_dirty(source_root):
        log(f"simulation-skills auto-update skipped: dirty cache checkout at {source_root}", quiet)
        return None
    result = run_command(["git", "pull", "--ff-only"], cwd=source_root)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        log(f"simulation-skills auto-update skipped: cache pull failed: {detail}", quiet)
        return None
    return source_root


def install_from_source(source_root: Path, dest_dir: Path, quiet: bool) -> bool:
    installer = source_root / "scripts" / "install_skills.sh"
    if not installer.exists():
        log(f"simulation-skills auto-update skipped: missing installer at {installer}", quiet)
        return False
    env = os.environ.copy()
    env["CODEX_SKILLS_DIR"] = str(dest_dir)
    result = subprocess.run(
        ["bash", str(installer)],
        cwd=source_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        log(f"simulation-skills auto-update skipped: install failed: {detail}", quiet)
        return False
    log(f"simulation-skills auto-update installed skills into {dest_dir}", quiet)
    return True


def state_file_for(state_dir: Path, repo_url: str, dest_dir: Path) -> Path:
    key = f"{repo_url}|{dest_dir.resolve()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return state_dir / f"auto-update-{digest}.stamp"


def cooldown_active(state_file: Path, interval_seconds: int, now: float) -> bool:
    if interval_seconds <= 0 or not state_file.exists():
        return False
    try:
        last_run = float(state_file.read_text(encoding="utf-8").strip())
    except ValueError:
        return False
    return now - last_run < interval_seconds


def write_state(state_file: Path, now: float) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(str(now), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--dest-dir", type=Path)
    parser.add_argument("--repo-url")
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--interval-seconds", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ
    if is_disabled(env):
        log("simulation-skills auto-update disabled by SIMULATION_SKILLS_AUTO_UPDATE", args.quiet)
        return 0

    script_path = Path(__file__).resolve()
    skill_dir = installed_skill_dir(script_path)
    installed_config = parse_env_file(skill_dir / ".simulation-skills-update.env") if skill_dir else {}

    source_root_value = (
        args.source_root
        or env.get("SIMULATION_SKILLS_SOURCE_ROOT")
        or installed_config.get("SIMULATION_SKILLS_SOURCE_ROOT")
    )
    source_root = Path(source_root_value).expanduser().resolve() if source_root_value else discover_suite_root(script_path)

    dest_dir_value = args.dest_dir or env.get("CODEX_SKILLS_DIR")
    if dest_dir_value:
        dest_dir = Path(dest_dir_value).expanduser().resolve()
    elif skill_dir:
        dest_dir = skill_dir.parent.resolve()
    else:
        dest_dir = (Path.home() / ".codex" / "skills").resolve()

    repo_url = (
        args.repo_url
        or env.get("SIMULATION_SKILLS_GITHUB_REPO")
        or installed_config.get("SIMULATION_SKILLS_GITHUB_REPO")
        or (git_remote_url(source_root) if source_root else "")
    ).strip()

    if not repo_url:
        log("simulation-skills auto-update skipped: no GitHub repo configured", args.quiet)
        return 0
    if not is_github_repo_url(repo_url):
        log(f"simulation-skills auto-update skipped: not a GitHub repo: {repo_url}", args.quiet)
        return 0

    state_dir = (args.state_dir or Path.home() / ".cache" / "simulation-skills").expanduser().resolve()
    interval_seconds = args.interval_seconds
    if interval_seconds is None:
        interval_seconds = int(env.get("SIMULATION_SKILLS_AUTO_UPDATE_INTERVAL_SECONDS", DEFAULT_INTERVAL_SECONDS))
    now = time.time()
    state_file = state_file_for(state_dir, repo_url, dest_dir)
    if not args.force and cooldown_active(state_file, interval_seconds, now):
        log("simulation-skills auto-update skipped: cooldown active", args.quiet)
        return 0

    updated_source: Path | None = None
    if source_root and source_root.exists() and git_remote_url(source_root) == repo_url:
        updated_source = update_checkout(source_root, args.quiet)
    if updated_source is None:
        cache_dir = (args.cache_dir or state_dir).expanduser().resolve()
        updated_source = update_cache(repo_url, cache_dir, args.quiet)
    if updated_source is None:
        return 0

    if install_from_source(updated_source, dest_dir, args.quiet):
        write_state(state_file, now)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
