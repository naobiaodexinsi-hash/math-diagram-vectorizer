#!/usr/bin/env python3
"""Create a source-versus-rendered diagnostic overlay without judging scan noise."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("rendered", type=Path)
    parser.add_argument("overlay", type=Path)
    parser.add_argument("--metrics", type=Path)
    args = parser.parse_args()
    source_rgba = Image.open(args.source).convert("RGBA")
    rendered_rgba = Image.open(args.rendered).convert("RGBA")
    source_rgba = source_rgba.resize(rendered_rgba.size, Image.Resampling.LANCZOS)
    # SVG output intentionally has a transparent background. Flatten both sides
    # onto white only for comparison; otherwise transparent pixels read as black.
    def white_preview(image: Image.Image) -> Image.Image:
        preview = Image.new("RGBA", image.size, "white")
        preview.alpha_composite(image)
        return preview
    source = white_preview(source_rgba)
    rendered = white_preview(rendered_rgba)
    overlay = Image.blend(source, rendered, 0.5)
    args.overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.save(args.overlay)
    source_gray = source.convert("L")
    rendered_gray = rendered.convert("L")
    diff = ImageChops.difference(source_gray, rendered_gray)
    histogram = diff.histogram()
    mean_difference = sum(index * count for index, count in enumerate(histogram)) / max(1, sum(histogram))
    payload = {"overlay_size": list(rendered.size), "mean_pixel_difference": round(mean_difference, 3), "note": "diagnostic only; scan noise and antialiasing are expected"}
    if args.metrics:
        args.metrics.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
