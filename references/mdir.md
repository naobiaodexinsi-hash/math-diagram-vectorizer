# Math Diagram Intermediate Representation (MDIR) v1

MDIR is the editable source of truth. Coordinates use the cropped-source SVG
canvas: origin at top-left, x grows right, y grows down. Do not encode a visual
guess as a mathematical constraint.

```json
{
  "version": "1.0",
  "diagram_type": "geometry",
  "canvas": {"width": 600, "height": 400},
  "points": [
    {"id": "A", "x": 300, "y": 55, "role": "vertex", "confidence": 0.99}
  ],
  "segments": [
    {"id": "AB", "from": "A", "to": "B", "style": "solid", "arrow": "none", "confidence": 0.99}
  ],
  "circles": [{"id": "omega", "center": "O", "radius": 120, "confidence": 0.97}],
  "markers": [
    {"type": "right_angle", "vertex": "D", "leg_a": "A", "leg_b": "B", "confidence": 0.98}
  ],
  "labels": [
    {"text": "A", "point": "A", "placement": "upper", "dx": 0, "dy": -10, "confidence": 0.99}
  ],
  "warnings": []
}
```

Supported point roles are `vertex`, `intersection`, `on_segment`, `on_circle`,
`center`, and `free`. Supported segment styles are `solid`, `dashed`, and
`auxiliary`; arrows are `none`, `start`, `end`, or `both`.

Supported markers are `right_angle`, `equal_ticks`, `parallel`, and
`angle_arc`. Every marker retains `confidence`; a marker is evidence only when
it was visible in the source. A label can instead carry literal `x` and `y`.
Its `placement` is one of `upper`, `lower`, `left`, `right`, `upper-left`,
`upper-right`, `lower-left`, and `lower-right`.

`grid` is optional and has `x`, `y`, `width`, `height`, `cell`, and optional
`stroke`. It is an MVP extension; it must not be used to invent coordinates.

`paths` is a controlled extension for a visible curve whose semantics are not
yet in the MVP, such as a function-graph branch. Each entry has an `id`, a safe
SVG `d` command string, `stroke`, `width`, `style`, and `confidence`. It must
represent an observed curve only; do not use it to infer an unlabelled function.
