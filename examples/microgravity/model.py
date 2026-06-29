"""Quasi-static matchstick bridge structure model.

The model represents a small Warren-truss bridge made from matchstick-like
members. It checks a simplified structural envelope: chord axial force,
diagonal shear force, support reaction at glued joints, and midspan deflection.
This is a classroom-scale structural approximation, not a finite-element
solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot


Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class Node:
    name: str
    position: Vector3
    support: bool = False


@dataclass(frozen=True)
class Member:
    name: str
    start: str
    end: str
    kind: str
    diameter_m: float = 0.0022
    tensile_capacity_n: float = 36.0
    compressive_capacity_n: float = 24.0

    def length_m(self, nodes: dict[str, Node]) -> float:
        a = nodes[self.start].position
        b = nodes[self.end].position
        return hypot(hypot(a[0] - b[0], a[1] - b[1]), a[2] - b[2])


@dataclass(frozen=True)
class BridgeEvaluation:
    can_hold: bool
    load_n: float
    span_m: float
    max_member_force_n: float
    max_member_utilization: float
    max_joint_reaction_n: float
    joint_utilization: float
    midspan_deflection_m: float
    deflection_limit_m: float
    failure_modes: list[str]

    @property
    def verdict(self) -> str:
        return "holds_load" if self.can_hold else "fails_load"


class MatchstickBridge:
    """Small matchstick Warren-truss bridge with simplified load checks."""

    def __init__(
        self,
        span_m: float = 0.60,
        width_m: float = 0.10,
        truss_depth_m: float = 0.12,
        panel_count: int = 6,
        load_n: float = 18.0,
        glue_joint_capacity_n: float = 16.0,
        deflection_ratio_limit: float = 250.0,
    ) -> None:
        if panel_count < 2:
            raise ValueError("panel_count must be at least 2")
        self.span_m = span_m
        self.width_m = width_m
        self.truss_depth_m = truss_depth_m
        self.panel_count = panel_count
        self.load_n = load_n
        self.glue_joint_capacity_n = glue_joint_capacity_n
        self.deflection_ratio_limit = deflection_ratio_limit
        self.nodes, self.members = self._build_warren_truss()

    def _build_warren_truss(self) -> tuple[dict[str, Node], list[Member]]:
        nodes: dict[str, Node] = {}
        members: list[Member] = []
        dx = self.span_m / self.panel_count
        side_y = (-self.width_m / 2.0, self.width_m / 2.0)

        for side_name, y in (("left", side_y[0]), ("right", side_y[1])):
            for i in range(self.panel_count + 1):
                x = i * dx
                bottom = f"{side_name}_bottom_{i}"
                top = f"{side_name}_top_{i}"
                nodes[bottom] = Node(bottom, (x, y, 0.0), support=i in {0, self.panel_count})
                nodes[top] = Node(top, (x, y, self.truss_depth_m))
                if i > 0:
                    members.append(Member(f"{side_name}_bottom_chord_{i}", f"{side_name}_bottom_{i-1}", bottom, "bottom_chord"))
                    members.append(Member(f"{side_name}_top_chord_{i}", f"{side_name}_top_{i-1}", top, "top_chord"))
                members.append(Member(f"{side_name}_vertical_{i}", bottom, top, "vertical", compressive_capacity_n=18.0))
            for i in range(self.panel_count):
                if i % 2 == 0:
                    start, end = f"{side_name}_bottom_{i}", f"{side_name}_top_{i+1}"
                else:
                    start, end = f"{side_name}_top_{i}", f"{side_name}_bottom_{i+1}"
                members.append(Member(f"{side_name}_diagonal_{i}", start, end, "diagonal", tensile_capacity_n=30.0, compressive_capacity_n=20.0))

        for i in range(self.panel_count + 1):
            members.append(Member(f"deck_tie_{i}", f"left_bottom_{i}", f"right_bottom_{i}", "deck_tie", tensile_capacity_n=28.0))
            members.append(Member(f"top_tie_{i}", f"left_top_{i}", f"right_top_{i}", "top_tie", tensile_capacity_n=24.0))
        return nodes, members

    def _member_force_estimates(self) -> dict[str, float]:
        half_trusses = 2.0
        max_moment = self.load_n * self.span_m / 4.0
        chord_force = max_moment / max(self.truss_depth_m, 0.001) / half_trusses
        end_shear = self.load_n / 2.0 / half_trusses
        diagonal_force = end_shear / max(1.0, self.panel_count / 2.0)
        vertical_force = self.load_n / (self.panel_count + 1) / half_trusses
        deck_tie_force = self.load_n / (self.panel_count + 1)
        forces: dict[str, float] = {}
        for member in self.members:
            if member.kind in {"top_chord", "bottom_chord"}:
                forces[member.name] = chord_force
            elif member.kind == "diagonal":
                forces[member.name] = diagonal_force
            elif member.kind == "vertical":
                forces[member.name] = vertical_force
            elif member.kind == "deck_tie":
                forces[member.name] = deck_tie_force
            else:
                forces[member.name] = deck_tie_force * 0.4
        return forces

    def _estimate_deflection(self) -> float:
        # Effective beam stiffness from separated top/bottom chord pairs.
        elastic_modulus_pa = 9.0e9
        match_area_m2 = 3.14159 * (0.0022 / 2.0) ** 2
        chord_count = 4
        effective_i = chord_count * match_area_m2 * (self.truss_depth_m / 2.0) ** 2
        distributed_load_n_per_m = self.load_n / self.span_m
        return 5.0 * distributed_load_n_per_m * self.span_m**4 / (384.0 * elastic_modulus_pa * effective_i)

    def evaluate_load(self) -> BridgeEvaluation:
        forces = self._member_force_estimates()
        max_force = max(forces.values())
        max_utilization = 0.0
        for member in self.members:
            capacity = member.compressive_capacity_n if member.kind == "top_chord" else member.tensile_capacity_n
            max_utilization = max(max_utilization, forces[member.name] / capacity)

        support_count = sum(1 for node in self.nodes.values() if node.support)
        max_joint_reaction = self.load_n / max(support_count, 1)
        joint_utilization = max_joint_reaction / self.glue_joint_capacity_n
        deflection = self._estimate_deflection()
        deflection_limit = self.span_m / self.deflection_ratio_limit

        failure_modes: list[str] = []
        if max_utilization > 1.0:
            failure_modes.append("member_capacity_exceeded")
        if joint_utilization > 1.0:
            failure_modes.append("glue_joint_capacity_exceeded")
        if deflection > deflection_limit:
            failure_modes.append("deflection_limit_exceeded")

        return BridgeEvaluation(
            can_hold=not failure_modes,
            load_n=self.load_n,
            span_m=self.span_m,
            max_member_force_n=max_force,
            max_member_utilization=max_utilization,
            max_joint_reaction_n=max_joint_reaction,
            joint_utilization=joint_utilization,
            midspan_deflection_m=deflection,
            deflection_limit_m=deflection_limit,
            failure_modes=failure_modes,
        )

    def visualization_state(self) -> dict[str, object]:
        evaluation = self.evaluate_load()
        forces = self._member_force_estimates()
        return {
            "nodes": [
                {"name": node.name, "position": node.position, "support": node.support}
                for node in self.nodes.values()
            ],
            "members": [
                {
                    "name": member.name,
                    "start": member.start,
                    "end": member.end,
                    "kind": member.kind,
                    "force_n": forces[member.name],
                    "length_m": member.length_m(self.nodes),
                }
                for member in self.members
            ],
            "evaluation": {
                "verdict": evaluation.verdict,
                "can_hold": evaluation.can_hold,
                "load_n": evaluation.load_n,
                "span_m": evaluation.span_m,
                "max_member_force_n": evaluation.max_member_force_n,
                "max_member_utilization": evaluation.max_member_utilization,
                "max_joint_reaction_n": evaluation.max_joint_reaction_n,
                "joint_utilization": evaluation.joint_utilization,
                "midspan_deflection_m": evaluation.midspan_deflection_m,
                "deflection_limit_m": evaluation.deflection_limit_m,
                "failure_modes": evaluation.failure_modes,
            },
        }
