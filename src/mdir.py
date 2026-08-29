"""MDIR validation, SVG generation, and Geometry DSL diagnostic conversion."""
from __future__ import annotations

import html
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

FORBIDDEN_SVG = {"image", "script", "foreignObject", "iframe", "object", "embed", "filter"}
EDITABLE_SVG = {"path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text"}
URL_PATTERN = re.compile(r"(?:https?|file):|data:image", re.I)
SVG_PATH_PATTERN = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9,.\s+\-Ee]+$")
PLACEMENTS = {
    "upper": (0, -1), "lower": (0, 1), "left": (-1, 0), "right": (1, 0),
    "upper-left": (-1, -1), "upper-right": (1, -1),
    "lower-left": (-1, 1), "lower-right": (1, 1),
}


class MDIRError(ValueError):
    pass


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise MDIRError(f"{field} must be a finite number")
    return float(value)


def _list(doc: dict[str, Any], field: str) -> list[dict[str, Any]]:
    value = doc.get(field, [])
    if not isinstance(value, list):
        raise MDIRError(f"{field} must be a list")
    if not all(isinstance(item, dict) for item in value):
        raise MDIRError(f"{field} entries must be objects")
    return value


def validate_mdir(doc: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(doc, dict):
        raise MDIRError("MDIR root must be an object")
    if str(doc.get("version", "1.0")) != "1.0":
        raise MDIRError("only MDIR version 1.0 is supported")
    canvas = doc.get("canvas")
    if not isinstance(canvas, dict):
        raise MDIRError("canvas is required")
    width, height = _number(canvas.get("width"), "canvas.width"), _number(canvas.get("height"), "canvas.height")
    if width <= 0 or height <= 0:
        raise MDIRError("canvas dimensions must be positive")

    points = _list(doc, "points")
    point_ids: set[str] = set()
    for point in points:
        ident = point.get("id")
        if not isinstance(ident, str) or not ident.strip() or ident in point_ids:
            raise MDIRError("each point needs a unique non-empty id")
        point_ids.add(ident)
        _number(point.get("x"), f"point {ident}.x")
        _number(point.get("y"), f"point {ident}.y")
        _confidence(point, f"point {ident}")

    segments = _list(doc, "segments")
    segment_ids: set[str] = set()
    for index, segment in enumerate(segments):
        ident = str(segment.get("id", f"segment_{index + 1}"))
        if ident in segment_ids:
            raise MDIRError(f"duplicate segment id: {ident}")
        segment_ids.add(ident)
        if segment.get("from") not in point_ids or segment.get("to") not in point_ids:
            raise MDIRError(f"segment {ident} references an unknown point")
        if segment.get("from") == segment.get("to"):
            raise MDIRError(f"segment {ident} has identical endpoints")
        if segment.get("style", "solid") not in {"solid", "dashed", "auxiliary"}:
            raise MDIRError(f"segment {ident} has unsupported style")
        if segment.get("arrow", "none") not in {"none", "start", "end", "both"}:
            raise MDIRError(f"segment {ident} has unsupported arrow")
        _confidence(segment, f"segment {ident}")

    for index, circle in enumerate(_list(doc, "circles")):
        ident = str(circle.get("id", f"circle_{index + 1}"))
        if circle.get("center") not in point_ids:
            raise MDIRError(f"circle {ident} references an unknown center")
        radius = _number(circle.get("radius"), f"circle {ident}.radius")
        if radius <= 0:
            raise MDIRError(f"circle {ident} radius must be positive")
        _confidence(circle, f"circle {ident}")

    for index, path in enumerate(_list(doc, "paths")):
        ident = str(path.get("id", f"path_{index + 1}"))
        d = path.get("d")
        if not isinstance(d, str) or not d.strip() or not SVG_PATH_PATTERN.fullmatch(d):
            raise MDIRError(f"path {ident} needs a safe SVG path d attribute")
        _confidence(path, f"path {ident}")

    grid = doc.get("grid")
    if grid is not None:
        if not isinstance(grid, dict):
            raise MDIRError("grid must be an object")
        for field, default in (("x", 0), ("y", 0), ("width", width), ("height", height), ("cell", None)):
            number = _number(grid.get(field, default), f"grid.{field}")
            if field in {"width", "height", "cell"} and number <= 0:
                raise MDIRError(f"grid.{field} must be positive")

    for label in _list(doc, "labels"):
        if not isinstance(label.get("text"), str) or not label["text"]:
            raise MDIRError("every label needs non-empty text")
        if "point" in label and label["point"] not in point_ids:
            raise MDIRError(f"label {label['text']!r} references an unknown point")
        if "point" not in label:
            _number(label.get("x"), f"label {label['text']!r}.x")
            _number(label.get("y"), f"label {label['text']!r}.y")
        if label.get("placement", "upper") not in PLACEMENTS:
            raise MDIRError(f"label {label['text']!r} has unsupported placement")
        _confidence(label, f"label {label['text']}")

    for marker in _list(doc, "markers"):
        kind = marker.get("type")
        if kind not in {"right_angle", "equal_ticks", "parallel", "angle_arc"}:
            raise MDIRError(f"unsupported marker type: {kind}")
        if kind == "right_angle":
            for key in ("vertex", "leg_a", "leg_b"):
                if marker.get(key) not in point_ids:
                    raise MDIRError(f"right_angle marker references unknown {key}")
        if kind in {"equal_ticks", "parallel"}:
            ids = marker.get("segments")
            if not isinstance(ids, list) or not ids or any(item not in segment_ids for item in ids):
                raise MDIRError(f"{kind} marker needs known segments")
        if kind == "angle_arc":
            for key in ("vertex", "start", "end"):
                if marker.get(key) not in point_ids:
                    raise MDIRError(f"angle_arc marker references unknown {key}")
        _confidence(marker, f"marker {kind}")
    return doc


def _confidence(item: dict[str, Any], field: str) -> None:
    value = item.get("confidence", 1.0)
    value = _number(value, f"{field}.confidence")
    if not 0 <= value <= 1:
        raise MDIRError(f"{field}.confidence must be between 0 and 1")


def load_mdir(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MDIRError(f"cannot read MDIR: {exc}") from exc
    return validate_mdir(doc)


def point_map(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {point["id"]: point for point in doc.get("points", [])}


def _fmt(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _tag(name: str, **attrs: Any) -> str:
    clean = " ".join(f'{key}="{html.escape(str(value), quote=True)}"' for key, value in attrs.items() if value is not None)
    return f"<{name} {clean}/>"


def _segment_style(segment: dict[str, Any], mode: str) -> dict[str, str]:
    width = float(segment.get("width", 1.8 if mode == "faithful" else 2.0))
    if segment.get("style") == "auxiliary":
        width = min(width, 1.5)
    result = {"stroke": str(segment.get("stroke", "#000000")), "stroke-width": _fmt(width), "fill": "none", "stroke-linecap": "round"}
    if segment.get("style") == "dashed":
        result["stroke-dasharray"] = str(segment.get("dasharray", "6 4"))
    arrow = segment.get("arrow", "none")
    if arrow in {"start", "both"}:
        result["marker-start"] = "url(#arrow)"
    if arrow in {"end", "both"}:
        result["marker-end"] = "url(#arrow)"
    return result


def _unit(origin: dict[str, Any], target: dict[str, Any]) -> tuple[float, float]:
    dx, dy = float(target["x"]) - float(origin["x"]), float(target["y"]) - float(origin["y"])
    length = math.hypot(dx, dy)
    if length == 0:
        return 0.0, 0.0
    return dx / length, dy / length


def _right_angle(marker: dict[str, Any], points: dict[str, dict[str, Any]]) -> str:
    vertex, leg_a, leg_b = points[marker["vertex"]], points[marker["leg_a"]], points[marker["leg_b"]]
    ux, uy = _unit(vertex, leg_a)
    vx, vy = _unit(vertex, leg_b)
    size = float(marker.get("size", 11))
    p1 = (float(vertex["x"]) + ux * size, float(vertex["y"]) + uy * size)
    p2 = (p1[0] + vx * size, p1[1] + vy * size)
    p3 = (float(vertex["x"]) + vx * size, float(vertex["y"]) + vy * size)
    return _tag("polyline", points=" ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in (p1, p2, p3)), fill="none", stroke=marker.get("stroke", "#000000"), **{"stroke-width": marker.get("width", "1.5"), "stroke-linejoin": "miter"})


def _ticks(marker: dict[str, Any], segment_lookup: dict[str, dict[str, Any]], points: dict[str, dict[str, Any]]) -> list[str]:
    output: list[str] = []
    count = int(marker.get("count", 1))
    spacing = float(marker.get("spacing", 4))
    size = float(marker.get("size", 7))
    for seg_id in marker["segments"]:
        segment = segment_lookup[seg_id]
        a, b = points[segment["from"]], points[segment["to"]]
        ux, uy = _unit(a, b)
        mid_x, mid_y = (float(a["x"]) + float(b["x"])) / 2, (float(a["y"]) + float(b["y"])) / 2
        for index in range(count):
            shift = (index - (count - 1) / 2) * spacing
            cx, cy = mid_x + ux * shift, mid_y + uy * shift
            px, py = -uy * size / 2, ux * size / 2
            output.append(_tag("line", x1=_fmt(cx - px), y1=_fmt(cy - py), x2=_fmt(cx + px), y2=_fmt(cy + py), stroke=marker.get("stroke", "#000000"), **{"stroke-width": marker.get("width", "1.4")}))
    return output


def _parallel(marker: dict[str, Any], segment_lookup: dict[str, dict[str, Any]], points: dict[str, dict[str, Any]]) -> list[str]:
    output: list[str] = []
    count = int(marker.get("count", 1))
    for seg_id in marker["segments"]:
        segment = segment_lookup[seg_id]
        a, b = points[segment["from"]], points[segment["to"]]
        ux, uy = _unit(a, b)
        for index in range(count):
            t = 0.5 + (index - (count - 1) / 2) * 0.09
            cx = float(a["x"]) + (float(b["x"]) - float(a["x"])) * t
            cy = float(a["y"]) + (float(b["y"]) - float(a["y"])) * t
            length = float(marker.get("size", 9))
            px, py = -uy * length / 2, ux * length / 2
            output.append(_tag("line", x1=_fmt(cx - px - ux * 2), y1=_fmt(cy - py - uy * 2), x2=_fmt(cx + px + ux * 2), y2=_fmt(cy + py + uy * 2), stroke=marker.get("stroke", "#000000"), **{"stroke-width": marker.get("width", "1.4")}))
    return output


def _angle_arc(marker: dict[str, Any], points: dict[str, dict[str, Any]]) -> str:
    vertex, start, end = points[marker["vertex"]], points[marker["start"]], points[marker["end"]]
    radius = float(marker.get("radius", 18))
    ux, uy = _unit(vertex, start)
    vx, vy = _unit(vertex, end)
    sx, sy = float(vertex["x"]) + ux * radius, float(vertex["y"]) + uy * radius
    ex, ey = float(vertex["x"]) + vx * radius, float(vertex["y"]) + vy * radius
    cross = ux * vy - uy * vx
    sweep = 1 if cross > 0 else 0
    d = f"M {_fmt(sx)} {_fmt(sy)} A {_fmt(radius)} {_fmt(radius)} 0 0 {sweep} {_fmt(ex)} {_fmt(ey)}"
    return _tag("path", d=d, fill="none", stroke=marker.get("stroke", "#000000"), **{"stroke-width": marker.get("width", "1.3")})


def render_svg(doc: dict[str, Any], mode: str = "faithful") -> str:
    validate_mdir(doc)
    canvas = doc["canvas"]
    width, height = float(canvas["width"]), float(canvas["height"])
    points = point_map(doc)
    segments = doc.get("segments", [])
    segment_lookup = {str(segment.get("id", f"segment_{index + 1}")): segment for index, segment in enumerate(segments)}
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(width)}" height="{_fmt(height)}" viewBox="0 0 {_fmt(width)} {_fmt(height)}" role="img">',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="context-stroke"/></marker></defs>',
    ]
    grid = doc.get("grid")
    if isinstance(grid, dict):
        cell = float(grid.get("cell", 20))
        gx, gy = float(grid.get("x", 0)), float(grid.get("y", 0))
        gw, gh = float(grid.get("width", width)), float(grid.get("height", height))
        stroke = grid.get("stroke", "#b8b8b8")
        for x in _frange(gx, gx + gw + .01, cell):
            parts.append(_tag("line", x1=_fmt(x), y1=_fmt(gy), x2=_fmt(x), y2=_fmt(gy + gh), stroke=stroke, **{"stroke-width": "0.6"}))
        for y in _frange(gy, gy + gh + .01, cell):
            parts.append(_tag("line", x1=_fmt(gx), y1=_fmt(y), x2=_fmt(gx + gw), y2=_fmt(y), stroke=stroke, **{"stroke-width": "0.6"}))
    for circle in doc.get("circles", []):
        center = points[circle["center"]]
        parts.append(_tag("circle", cx=_fmt(center["x"]), cy=_fmt(center["y"]), r=_fmt(circle["radius"]), fill="none", stroke=circle.get("stroke", "#000000"), **{"stroke-width": _fmt(circle.get("width", 1.8))}))
    for path in doc.get("paths", []):
        path_style = {"fill": "none", "stroke": path.get("stroke", "#000000"), "stroke-width": _fmt(path.get("width", 1.8)), "stroke-linecap": "round", "stroke-linejoin": "round"}
        if path.get("style") == "dashed":
            path_style["stroke-dasharray"] = str(path.get("dasharray", "6 4"))
        parts.append(_tag("path", d=path["d"], **path_style))
    for segment in segments:
        start, end = points[segment["from"]], points[segment["to"]]
        parts.append(_tag("line", x1=_fmt(start["x"]), y1=_fmt(start["y"]), x2=_fmt(end["x"]), y2=_fmt(end["y"]), **_segment_style(segment, mode)))
    for marker in doc.get("markers", []):
        if marker["type"] == "right_angle":
            parts.append(_right_angle(marker, points))
        elif marker["type"] == "equal_ticks":
            parts.extend(_ticks(marker, segment_lookup, points))
        elif marker["type"] == "parallel":
            parts.extend(_parallel(marker, segment_lookup, points))
        elif marker["type"] == "angle_arc":
            parts.append(_angle_arc(marker, points))
    for point in doc.get("points", []):
        if point.get("visible", True):
            parts.append(_tag("circle", cx=_fmt(point["x"]), cy=_fmt(point["y"]), r=_fmt(point.get("size", 1.8)), fill=point.get("stroke", "#000000")))
    label_size = 16 if mode == "faithful" else 15
    for label in doc.get("labels", []):
        if "point" in label:
            base = points[label["point"]]
            dx, dy = PLACEMENTS[label.get("placement", "upper")]
            x = float(base["x"]) + dx * float(label.get("distance", 11)) + float(label.get("dx", 0))
            y = float(base["y"]) + dy * float(label.get("distance", 11)) + float(label.get("dy", 0))
        else:
            x, y = float(label["x"]), float(label["y"])
        text = html.escape(label["text"])
        family = html.escape(str(label.get("font_family", "Arial, Helvetica, sans-serif")), quote=True)
        style = html.escape(str(label.get("font_style", "normal")), quote=True)
        parts.append(f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-family="{family}" font-style="{style}" font-size="{_fmt(label.get("size", label_size))}" text-anchor="{html.escape(label.get("anchor", "middle"), quote=True)}" dominant-baseline="central" fill="{html.escape(str(label.get("fill", "#000000")), quote=True)}">{text}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _frange(start: float, stop: float, step: float):
    if step <= 0:
        raise MDIRError("grid cell must be positive")
    value = start
    while value <= stop:
        yield value
        value += step


def validate_svg(path: Path) -> dict[str, int]:
    root = ET.parse(path).getroot()
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise MDIRError("SVG root must be <svg>")
    geometry = text = 0
    for node in root.iter():
        name = node.tag.rsplit("}", 1)[-1]
        if name in FORBIDDEN_SVG:
            raise MDIRError(f"forbidden SVG element <{name}>")
        if name in EDITABLE_SVG:
            geometry += 1
        if name == "text":
            text += 1
        if any(URL_PATTERN.search(value) for value in node.attrib.values()):
            raise MDIRError("external URL or embedded raster is forbidden")
    if geometry == 0:
        raise MDIRError("SVG has no editable geometry")
    return {"geometry_elements": geometry, "live_text_elements": text}


def to_geometry_dsl(doc: dict[str, Any]) -> str:
    """Create a deliberately conservative semantic shadow for Geometry DSL."""
    validate_mdir(doc)
    lines = ["# Generated semantic diagnostic; MDIR remains the source of truth."]
    for point in doc.get("points", []):
        name = _dsl_name(point["id"])
        lines.append(f"{name} = point({_fmt(point['x'])}, {_fmt(-float(point['y']))}, visible=false)")
    for index, segment in enumerate(doc.get("segments", []), 1):
        name = _dsl_name(str(segment.get("id", f"S{index}")))
        style = ", dashed=true" if segment.get("style") == "dashed" else ""
        lines.append(f"{name} = line({_dsl_name(segment['from'])}, {_dsl_name(segment['to'])}, kind=segment{style})")
    for index, circle in enumerate(doc.get("circles", []), 1):
        name = _dsl_name(str(circle.get("id", f"C{index}")))
        lines.append(f"{name} = circle({_dsl_name(circle['center'])}, {_fmt(circle['radius'])})")
    return "\n".join(lines) + "\n"


def _dsl_name(value: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not clean or clean[0].isdigit() or clean in {"left", "right", "parallel", "circle", "line", "start", "end"}:
        clean = "obj_" + clean
    return clean
