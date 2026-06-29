#!/usr/bin/env python3
"""Inspect common ABM source formats and emit a structural conversion summary."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


NETLOGO_SECTION = "@#$#@#$#@"
NETLOGO_WIDGETS = {
    "BUTTON",
    "SLIDER",
    "SWITCH",
    "CHOOSER",
    "INPUTBOX",
    "MONITOR",
    "PLOT",
    "TEXTBOX",
    "OUTPUT",
}


@dataclass
class SourceSummary:
    source_path: str
    source_type: str
    files: list[str] = field(default_factory=list)
    agents: list[dict[str, Any]] = field(default_factory=list)
    spaces: list[dict[str, Any]] = field(default_factory=list)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    procedures: list[dict[str, Any]] = field(default_factory=list)
    schedulers: list[dict[str, Any]] = field(default_factory=list)
    metrics: list[dict[str, Any]] = field(default_factory=list)
    visualization: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "source_type": self.source_type,
            "files": self.files,
            "agents": self.agents,
            "spaces": self.spaces,
            "parameters": self.parameters,
            "procedures": self.procedures,
            "schedulers": self.schedulers,
            "metrics": self.metrics,
            "visualization": self.visualization,
            "notes": self.notes,
        }


def unique_dicts(items: list[dict[str, Any]], key: str = "name") -> list[dict[str, Any]]:
    seen: set[Any] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        marker = item.get(key, json.dumps(item, sort_keys=True))
        if marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out


def clean_netlogo_block_values(values: str) -> list[str]:
    return [part for part in re.split(r"\s+", values.strip()) if part]


def inspect_netlogo(path: Path) -> SourceSummary:
    text = path.read_text(encoding="utf-8", errors="replace")
    sections = text.split(NETLOGO_SECTION)
    code = sections[0]
    summary = SourceSummary(
        source_path=str(path),
        source_type="netlogo",
        files=[str(path)],
        notes=[
            "NetLogo parsing is structural. Review setup/go procedures and widget defaults before conversion."
        ],
    )

    for match in re.finditer(
        r"(?im)^\s*(breed|directed-link-breed|undirected-link-breed)\s+\[([^\]]+)\]",
        code,
    ):
        breed_type = match.group(1)
        values = clean_netlogo_block_values(match.group(2))
        if values:
            summary.agents.append(
                {"name": values[0], "kind": breed_type, "singular": values[1:2] or None}
            )

    for owner in ("globals", "turtles-own", "patches-own", "links-own"):
        for match in re.finditer(rf"(?ims)^\s*{owner}\s+\[([^\]]+)\]", code):
            values = clean_netlogo_block_values(match.group(1))
            target = summary.parameters if owner == "globals" else summary.agents
            if owner == "globals":
                for value in values:
                    target.append({"name": value, "scope": owner})
            else:
                target.append({"name": owner, "kind": "state variables", "variables": values})

    for match in re.finditer(r"(?im)^\s*(to|to-report)\s+([A-Za-z0-9_-]+)", code):
        name = match.group(2)
        summary.procedures.append({"name": name, "kind": match.group(1)})
        if name in {"setup", "go", "step"}:
            summary.schedulers.append({"name": name, "kind": "conventional NetLogo procedure"})

    if any(word in code for word in ("patches", "pxcor", "pycor", "neighbors")):
        summary.spaces.append({"name": "patch grid", "kind": "NetLogo world"})
    if re.search(r"\blink[s]?\b|link-neighbors|create-links", code):
        summary.spaces.append({"name": "links", "kind": "network"})
    if re.search(r"\bplot\b|set-current-plot|histogram", code):
        summary.metrics.append({"name": "plots", "kind": "NetLogo plotting calls"})

    interface = NETLOGO_SECTION.join(sections[1:])
    lines = [line.strip() for line in interface.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if line in NETLOGO_WIDGETS:
            name = None
            for candidate in lines[index + 1 : index + 8]:
                if candidate and candidate not in NETLOGO_WIDGETS and not candidate.isdigit():
                    name = candidate
                    break
            summary.visualization.append({"kind": line.lower(), "name": name})
            if line in {"SLIDER", "SWITCH", "CHOOSER", "INPUTBOX"} and name:
                summary.parameters.append({"name": name, "scope": "interface widget", "kind": line})

    summary.agents = unique_dicts(summary.agents)
    summary.parameters = unique_dicts(summary.parameters)
    summary.procedures = unique_dicts(summary.procedures)
    summary.spaces = unique_dicts(summary.spaces)
    summary.metrics = unique_dicts(summary.metrics)
    summary.visualization = unique_dicts(summary.visualization, key="name")
    return summary


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)
    return ""


def string_keys_from_dict(node: ast.AST) -> list[str]:
    if not isinstance(node, ast.Dict):
        return []
    keys: list[str] = []
    for key in node.keys:
        if isinstance(key, ast.Constant) and isinstance(key.value, str):
            keys.append(key.value)
    return keys


def inspect_mesa(path: Path) -> SourceSummary:
    py_files = [path] if path.is_file() else sorted(path.rglob("*.py"))
    summary = SourceSummary(
        source_path=str(path),
        source_type="mesa",
        files=[str(file) for file in py_files],
        notes=[
            "Mesa parsing uses Python AST and class conventions. Dynamic factories or imports may require manual review."
        ],
    )

    for file_path in py_files:
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            summary.notes.append(f"Skipped {file_path}: Python parse error at line {exc.lineno}.")
            continue

        imports = {
            alias.asname or alias.name.split(".")[-1]: alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            {
                alias.asname or alias.name: f"{node.module}.{alias.name}" if node.module else alias.name
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom)
                for alias in node.names
            }
        )

        for node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
            bases = [dotted_name(base) for base in node.bases]
            resolved_bases = [imports.get(base, base) for base in bases]
            if any(base.endswith(".Model") or base == "Model" for base in bases + resolved_bases):
                summary.agents.append(
                    {
                        "name": node.name,
                        "kind": "Mesa Model",
                        "file": str(file_path),
                        "bases": bases,
                    }
                )
            if any(base.endswith(".Agent") or base == "Agent" for base in bases + resolved_bases):
                summary.agents.append(
                    {
                        "name": node.name,
                        "kind": "Mesa Agent",
                        "file": str(file_path),
                        "bases": bases,
                    }
                )

            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    if item.name in {"step", "advance", "setup", "__init__"}:
                        summary.procedures.append(
                            {
                                "name": f"{node.name}.{item.name}",
                                "kind": "Mesa method",
                                "file": str(file_path),
                            }
                        )
                    if item.name == "__init__":
                        for arg in item.args.args[1:]:
                            summary.parameters.append(
                                {
                                    "name": arg.arg,
                                    "scope": f"{node.name}.__init__",
                                    "file": str(file_path),
                                }
                            )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = dotted_name(node.func)
                if any(token in call_name for token in ("RandomActivation", "SimultaneousActivation", "StagedActivation")):
                    summary.schedulers.append({"name": call_name, "kind": "Mesa scheduler", "file": str(file_path)})
                if any(token in call_name for token in ("MultiGrid", "SingleGrid", "HexGrid", "ContinuousSpace")):
                    summary.spaces.append({"name": call_name, "kind": "Mesa space", "file": str(file_path)})
                if "NetworkGrid" in call_name:
                    summary.spaces.append({"name": call_name, "kind": "Mesa network", "file": str(file_path)})
                if call_name.endswith("DataCollector") or call_name == "DataCollector":
                    for keyword in node.keywords:
                        if keyword.arg in {"model_reporters", "agent_reporters", "tables"}:
                            for key in string_keys_from_dict(keyword.value):
                                summary.metrics.append(
                                    {
                                        "name": key,
                                        "kind": f"Mesa {keyword.arg}",
                                        "file": str(file_path),
                                    }
                                )

    summary.agents = unique_dicts(summary.agents)
    summary.parameters = unique_dicts(summary.parameters)
    summary.procedures = unique_dicts(summary.procedures)
    summary.schedulers = unique_dicts(summary.schedulers)
    summary.spaces = unique_dicts(summary.spaces)
    summary.metrics = unique_dicts(summary.metrics)
    return summary


def inspect_repast(path: Path) -> SourceSummary:
    java_files = [path] if path.is_file() else sorted(path.rglob("*.java"))
    config_files = [] if path.is_file() else sorted(
        p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in {".xml", ".rs", ".score"}
    )
    summary = SourceSummary(
        source_path=str(path),
        source_type="repast",
        files=[str(file) for file in java_files + config_files],
        notes=[
            "Repast parsing is text based. Inspect annotations, context builders, and scenario XML before conversion."
        ],
    )

    for file_path in java_files:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        package = re.search(r"(?m)^\s*package\s+([\w.]+)\s*;", text)
        package_name = package.group(1) if package else ""
        for match in re.finditer(r"(?m)^\s*(?:public\s+)?class\s+(\w+)([^{]*)\{", text):
            class_name = match.group(1)
            tail = match.group(2)
            kind = "Repast class"
            if "ContextBuilder" in tail:
                kind = "Repast ContextBuilder"
            summary.agents.append(
                {
                    "name": f"{package_name}.{class_name}" if package_name else class_name,
                    "kind": kind,
                    "file": str(file_path),
                }
            )

        for annotation in re.finditer(r"@ScheduledMethod\s*\(([^)]*)\)\s*(?:public|private|protected)?\s+\w+\s+(\w+)\s*\(", text, re.S):
            summary.schedulers.append(
                {
                    "name": annotation.group(2),
                    "kind": "Repast @ScheduledMethod",
                    "annotation": re.sub(r"\s+", " ", annotation.group(1)).strip(),
                    "file": str(file_path),
                }
            )

        for param in re.finditer(r"getParameters\(\)\.get(?:Value|Integer|Double|Boolean)?\(\s*\"([^\"]+)\"", text):
            summary.parameters.append({"name": param.group(1), "scope": "RunEnvironment parameters", "file": str(file_path)})

        for space_name in ("Grid", "ContinuousSpace", "Geography", "Network"):
            if re.search(rf"\b{space_name}\s*<|\b{space_name}Factory|\b{space_name}Builder", text):
                summary.spaces.append({"name": space_name, "kind": "Repast projection", "file": str(file_path)})

        if "DataSetBuilder" in text or "AggregateDataSource" in text:
            summary.metrics.append({"name": "dataset", "kind": "Repast data collection", "file": str(file_path)})

    for file_path in config_files:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        for name in re.findall(r"<parameter[^>]+name=[\"']([^\"']+)[\"']", text):
            summary.parameters.append({"name": name, "scope": file_path.name, "file": str(file_path)})
        if file_path.suffix.lower() in {".rs", ".score"}:
            summary.visualization.append({"name": file_path.name, "kind": "Repast scenario artifact", "file": str(file_path)})

    summary.agents = unique_dicts(summary.agents)
    summary.parameters = unique_dicts(summary.parameters)
    summary.schedulers = unique_dicts(summary.schedulers)
    summary.spaces = unique_dicts(summary.spaces)
    summary.metrics = unique_dicts(summary.metrics)
    summary.visualization = unique_dicts(summary.visualization)
    return summary


def detect_source_type(path: Path) -> str:
    if path.is_file() and path.suffix.lower() == ".nlogo":
        return "netlogo"
    if path.is_file() and path.suffix.lower() == ".py":
        return "mesa"
    if path.is_file() and path.suffix.lower() == ".java":
        return "repast"
    if path.is_dir():
        if list(path.rglob("*.nlogo")):
            return "netlogo-dir"
        java_text = "\n".join(
            file.read_text(encoding="utf-8", errors="replace")[:5000]
            for file in list(path.rglob("*.java"))[:20]
        )
        if "repast.simphony" in java_text or list(path.rglob("*.rs")) or list(path.rglob("*.score")):
            return "repast"
        py_text = "\n".join(
            file.read_text(encoding="utf-8", errors="replace")[:5000]
            for file in list(path.rglob("*.py"))[:20]
        )
        if "mesa" in py_text or "class Model" in py_text:
            return "mesa"
    return "unknown"


def inspect_source(path: Path, source_type: str = "auto") -> SourceSummary:
    detected = detect_source_type(path) if source_type == "auto" else source_type
    if detected == "netlogo-dir":
        nlogo_files = sorted(path.rglob("*.nlogo"))
        if not nlogo_files:
            raise ValueError(f"No .nlogo files found under {path}")
        return inspect_netlogo(nlogo_files[0])
    if detected == "netlogo":
        return inspect_netlogo(path)
    if detected == "mesa":
        return inspect_mesa(path)
    if detected == "repast":
        return inspect_repast(path)
    raise ValueError(f"Could not detect ABM source type for {path}")


def render_markdown(summary: SourceSummary) -> str:
    data = summary.to_dict()
    lines = [
        f"# ABM Source Inspection: {Path(summary.source_path).name}",
        "",
        f"- Source type: `{summary.source_type}`",
        f"- Files inspected: {len(summary.files)}",
    ]
    for field_name in ("agents", "spaces", "parameters", "procedures", "schedulers", "metrics", "visualization"):
        values = data[field_name]
        if not values:
            continue
        lines.extend(["", f"## {field_name.title()}"])
        for value in values:
            label = value.get("name") or value.get("kind") or json.dumps(value, sort_keys=True)
            details = ", ".join(f"{k}={v}" for k, v in value.items() if k != "name" and v)
            lines.append(f"- `{label}`" + (f" ({details})" if details else ""))
    if summary.notes:
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in summary.notes)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="NetLogo .nlogo, Repast Java project, or Mesa Python project")
    parser.add_argument(
        "--source-type",
        choices=["auto", "netlogo", "mesa", "repast"],
        default="auto",
        help="Override source type detection.",
    )
    parser.add_argument("--format", choices=["json", "markdown"], default="json")
    args = parser.parse_args()

    summary = inspect_source(args.source, args.source_type)
    if args.format == "markdown":
        print(render_markdown(summary), end="")
    else:
        print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
