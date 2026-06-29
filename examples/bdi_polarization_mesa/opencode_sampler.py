"""Sample BDI behavior profiles through the local opencode CLI."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


FALLBACK_BEHAVIOR_SAMPLES: tuple[dict[str, float | str], ...] = (
    {
        "name": "bridge_builder",
        "credulity": 0.32,
        "activism": 0.18,
        "novelty_bias": 0.28,
        "moderation_bias": 0.45,
    },
    {
        "name": "identity_defender",
        "credulity": 0.58,
        "activism": 0.55,
        "novelty_bias": 0.12,
        "moderation_bias": -0.25,
    },
    {
        "name": "outrage_amplifier",
        "credulity": 0.66,
        "activism": 0.72,
        "novelty_bias": 0.2,
        "moderation_bias": -0.55,
    },
)


def _prompt(sample_count: int) -> str:
    return f"""
You are creating synthetic BDI behavior profiles for a social simulation.
Return only one JSON object, no markdown.
Schema:
{{
  "samples": [
    {{
      "name": "short_snake_case_label",
      "credulity": 0.0,
      "activism": 0.0,
      "novelty_bias": 0.0,
      "moderation_bias": 0.0
    }}
  ]
}}
Generate {sample_count} diverse profiles. Numeric ranges:
credulity 0.15 to 0.85, activism 0.05 to 0.85, novelty_bias -0.2 to 0.5,
moderation_bias -0.7 to 0.7. The samples should include at least one
moderating profile and one conflict-amplifying profile.
""".strip()


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)
    direct = cleaned.strip()
    try:
        return json.loads(direct)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise ValueError("opencode output did not contain a JSON object")
    return json.loads(match.group(0))


def _coerce_sample(raw: dict[str, Any], index: int) -> dict[str, float | str]:
    def number(name: str, low: float, high: float) -> float:
        value = float(raw[name])
        return max(low, min(high, value))

    name = str(raw.get("name") or f"opencode_sample_{index}").strip().lower()
    name = re.sub(r"[^a-z0-9_]+", "_", name).strip("_") or f"opencode_sample_{index}"
    return {
        "name": name,
        "credulity": number("credulity", 0.15, 0.85),
        "activism": number("activism", 0.05, 0.85),
        "novelty_bias": number("novelty_bias", -0.2, 0.5),
        "moderation_bias": number("moderation_bias", -0.7, 0.7),
    }


def _validate_samples(payload: dict[str, Any], sample_count: int) -> list[dict[str, float | str]]:
    raw_samples = payload.get("samples")
    if not isinstance(raw_samples, list) or not raw_samples:
        raise ValueError("opencode JSON must contain a non-empty samples list")
    samples = [_coerce_sample(raw, index) for index, raw in enumerate(raw_samples[:sample_count], start=1)]
    if len(samples) < sample_count:
        fallback = list(FALLBACK_BEHAVIOR_SAMPLES)
        samples.extend(fallback[: sample_count - len(samples)])
    return samples


def sample_with_opencode(
    sample_count: int,
    model: str | None = None,
    timeout_seconds: int = 90,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    opencode_path: str | None = None,
) -> list[dict[str, float | str]]:
    executable = opencode_path or shutil.which("opencode")
    if executable is None:
        raise RuntimeError("opencode CLI was not found on PATH")
    command = [executable, "run"]
    if model:
        command.extend(["--model", model])
    command.append(_prompt(sample_count))
    result = runner(command, text=True, capture_output=True, timeout=timeout_seconds, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"opencode exited with {result.returncode}: {stderr}")
    payload = _extract_json(result.stdout)
    return _validate_samples(payload, sample_count)


def load_behavior_samples(
    sampling_config: dict[str, Any] | None,
    output_dir: Path,
) -> tuple[list[dict[str, float | str]], dict[str, Any]]:
    config = dict(sampling_config or {})
    mode = str(config.get("mode", "fallback"))
    sample_count = int(config.get("sample_count", len(FALLBACK_BEHAVIOR_SAMPLES)))
    cache_path = Path(config.get("cache_path", output_dir / "opencode_behavior_samples.json"))
    if not cache_path.is_absolute():
        cache_path = output_dir / cache_path

    if cache_path.exists() and mode in {"opencode", "cache"}:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return _validate_samples(payload, sample_count), {
            "mode": mode,
            "source": "cache",
            "cache_path": str(cache_path),
        }

    if mode == "opencode":
        try:
            samples = sample_with_opencode(
                sample_count=sample_count,
                model=config.get("model"),
                timeout_seconds=int(config.get("timeout_seconds", 90)),
            )
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps({"samples": samples}, indent=2), encoding="utf-8")
            return samples, {"mode": mode, "source": "opencode", "cache_path": str(cache_path)}
        except Exception as exc:
            samples = list(FALLBACK_BEHAVIOR_SAMPLES[:sample_count])
            return samples, {
                "mode": mode,
                "source": "fallback_after_opencode_error",
                "error": str(exc),
                "cache_path": str(cache_path),
            }

    samples = list(FALLBACK_BEHAVIOR_SAMPLES[:sample_count])
    return samples, {"mode": mode, "source": "fallback", "cache_path": str(cache_path)}
