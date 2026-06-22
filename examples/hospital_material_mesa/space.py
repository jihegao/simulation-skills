"""2D space extraction from the AnyLogic hospital material-handling `.alp`.

The parser reads AnyLogic XML markup only. It intentionally ignores 3D `.dae`
resources and extracts the level-floor 2D environment used by the Mesa view.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
import xml.etree.ElementTree as ET

from examples.hospital_material_mesa.model import FLOOR_LEVELS


DEFAULT_ALP_PATH = Path(
    "/Users/Shared/AnyLogic 8 PLE/eclipse/plugins/"
    "com.anylogic.examples_8.9.0.202404161223/models/"
    "Material Handling in Hospital/Material Handling in Hospital.alp"
)


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float


@dataclass(frozen=True)
class Bounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


@dataclass(frozen=True)
class PathMarkup:
    name: str
    points: tuple[Point2D, ...]
    closed: bool = False


@dataclass(frozen=True)
class RectMarkup:
    name: str
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class NodeMarkup:
    name: str
    x: float
    y: float


@dataclass(frozen=True)
class LiftMarkup:
    name: str
    x: float
    y: float
    width: float
    depth: float


@dataclass
class LevelSpace:
    name: str
    walls: list[PathMarkup] = field(default_factory=list)
    polylines: list[PathMarkup] = field(default_factory=list)
    rectangles: list[RectMarkup] = field(default_factory=list)
    nodes: list[NodeMarkup] = field(default_factory=list)
    lifts: list[LiftMarkup] = field(default_factory=list)
    bounds: Bounds = Bounds(0.0, 0.0, 1.0, 1.0)


@dataclass
class HospitalSpace:
    levels: dict[str, LevelSpace]


def _text(element: ET.Element, name: str, default: str = "") -> str:
    child = element.find(name)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def _float_text(element: ET.Element, name: str, default: float = 0.0) -> float:
    text = _text(element, name)
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def _unit_value(element: ET.Element, name: str, default: float) -> float:
    child = element.find(name)
    if child is None:
        return default
    value = child.find("Value")
    if value is None or value.text is None:
        return default
    try:
        return float(value.text.strip())
    except ValueError:
        return default


def _points(element: ET.Element, origin_x: float, origin_y: float) -> tuple[Point2D, ...]:
    points: list[Point2D] = []
    points_element = element.find("Points")
    if points_element is None:
        return tuple(points)
    for point in points_element.findall("Point"):
        points.append(Point2D(origin_x + _float_text(point, "X"), origin_y + _float_text(point, "Y")))
    return tuple(points)


def _expand_bounds(existing: list[Point2D], level: LevelSpace) -> None:
    for wall in level.walls:
        existing.extend(wall.points)
    for polyline in level.polylines:
        existing.extend(polyline.points)
    for rect in level.rectangles:
        existing.extend(
            [
                Point2D(rect.x, rect.y),
                Point2D(rect.x + rect.width, rect.y + rect.height),
            ]
        )
    for node in level.nodes:
        existing.append(Point2D(node.x, node.y))
    for lift in level.lifts:
        existing.extend([Point2D(lift.x, lift.y), Point2D(lift.x + lift.width, lift.y + lift.depth)])


def _set_bounds(level: LevelSpace) -> None:
    points: list[Point2D] = []
    _expand_bounds(points, level)
    if not points:
        level.bounds = Bounds(0.0, 0.0, 1.0, 1.0)
        return
    level.bounds = Bounds(
        min(point.x for point in points),
        min(point.y for point in points),
        max(point.x for point in points),
        max(point.y for point in points),
    )


def _parse_markup(level: LevelSpace, element: ET.Element, offset_x: float = 0.0, offset_y: float = 0.0) -> None:
    tag = element.tag
    if tag == "Level" and _text(element, "Name") != level.name:
        return

    own_x = _float_text(element, "X")
    own_y = _float_text(element, "Y")
    current_x = offset_x + own_x
    current_y = offset_y + own_y

    if tag == "Wall":
        points = _points(element, current_x, current_y)
        if len(points) >= 2:
            level.walls.append(PathMarkup(_text(element, "Name", "wall"), points, _text(element, "Closed") == "true"))
        return
    if tag == "Polyline":
        points = _points(element, current_x, current_y)
        if len(points) >= 2:
            level.polylines.append(
                PathMarkup(_text(element, "Name", "polyline"), points, _text(element, "Closed") == "true")
            )
        return
    if tag == "Rectangle":
        width = _float_text(element, "Width")
        height = _float_text(element, "Height")
        if width > 0 and height > 0:
            level.rectangles.append(RectMarkup(_text(element, "Name", "rectangle"), current_x, current_y, width, height))
        return
    if tag == "PointNode":
        level.nodes.append(NodeMarkup(_text(element, "Name", "node"), current_x, current_y))
        return
    if tag == "Lift":
        level.lifts.append(
            LiftMarkup(
                _text(element, "Name", "lift"),
                current_x,
                current_y,
                _unit_value(element, "Width", 20.0) * 10.0,
                _unit_value(element, "Depth", 20.0) * 10.0,
            )
        )
        return

    child_offset_x = current_x if tag == "Group" else offset_x
    child_offset_y = current_y if tag == "Group" else offset_y
    for child in element:
        _parse_markup(level, child, child_offset_x, child_offset_y)


def _parse_file(path_text: str) -> HospitalSpace:
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"AnyLogic hospital model not found: {path}")
    root = ET.parse(path).getroot()
    expected = set(FLOOR_LEVELS)
    levels: dict[str, LevelSpace] = {}

    for element in root.iter("Level"):
        name = _text(element, "Name")
        if name not in expected or name in levels:
            continue
        level = LevelSpace(name=name)
        for child in element:
            _parse_markup(level, child)
        _set_bounds(level)
        levels[name] = level

    ordered = {name: levels[name] for name in FLOOR_LEVELS if name in levels}
    return HospitalSpace(levels=ordered)


@lru_cache(maxsize=4)
def _parse_cached(path_text: str) -> HospitalSpace:
    return _parse_file(path_text)


def parse_hospital_space(path: Path | str = DEFAULT_ALP_PATH) -> HospitalSpace:
    """Parse the AnyLogic `.alp` 2D floor markup into lightweight view data."""
    return _parse_cached(str(Path(path)))
