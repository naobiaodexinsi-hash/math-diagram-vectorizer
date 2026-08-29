#!/usr/bin/env python3
"""Local execution backend for the Math Diagram Vectorizer Codex skill."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "src"))
from mdir import MDIRError, load_mdir, render_svg, to_geometry_dsl, validate_svg  # noqa: E402


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_source(source: Path, destination: Path) -> Image.Image:
    with Image.open(source) as original:
        image = original.convert("RGBA")
        image.save(destination)
        return image.copy()


def crop_suggestion(image: Image.Image) -> dict[str, Any]:
    """Suggest, but never silently apply, a conservative foreground crop."""
    gray = image.convert("L")
    pixels = gray.load()
    width, height = gray.size
    xs, ys = [], []
    for y in range(height):
        for x in range(width):
            if pixels[x, y] < 230:
                xs.append(x)
                ys.append(y)
    if not xs:
        return {"applied": False, "confidence": 0.0, "reason": "no foreground detected", "box": [0, 0, width, height]}
    margin = max(12, round(min(width, height) * 0.04))
    left, top = max(0, min(xs) - margin), max(0, min(ys) - margin)
    right, bottom = min(width, max(xs) + margin + 1), min(height, max(ys) + margin + 1)
    crop_area = (right - left) * (bottom - top)
    source_area = width * height
    if crop_area >= source_area * 0.85:
        return {"applied": False, "confidence": 0.3, "reason": "foreground occupies most of the source; preserve full image", "box": [0, 0, width, height]}
    return {"applied": True, "confidence": 0.72, "reason": "conservative foreground bounding box; inspect before analysis", "box": [left, top, right, bottom]}


def make_job_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    stem = datetime.now().strftime("job_%Y%m%d_%H%M%S_%f")
    directory = root / stem
    directory.mkdir()
    return directory


def run(command: list[str], cwd: Path | None = None) -> dict[str, Any]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {"command": command, "returncode": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


def analysis_from_mdir(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagram_type": doc.get("diagram_type", "geometry"),
        "objects": {key: doc.get(key, []) for key in ("points", "segments", "circles", "paths", "markers", "labels")},
        "warnings": doc.get("warnings", []),
        "source": "Codex visual analysis normalized to MDIR",
    }


def prepare(args: argparse.Namespace) -> int:
    output_root = Path(args.output).expanduser().resolve() if args.output else SKILL_ROOT / "output"
    job = make_job_dir(output_root)
    source = Path(args.source).expanduser().resolve()
    image = normalize_source(source, job / "source.png")
    suggestion = crop_suggestion(image)
    if suggestion["applied"]:
        image.crop(tuple(suggestion["box"])).save(job / "cropped_source.png")
    else:
        shutil.copy2(job / "source.png", job / "cropped_source.png")
    write_json(job / "crop_report.json", suggestion)
    print(job)
    return 0


def vectorize(args: argparse.Namespace) -> int:
    if args.refinement < 0 or args.refinement > 2:
        raise MDIRError("--refinement must be from 0 to 2 (three renders maximum)")
    output_root = Path(args.output).expanduser().resolve() if args.output else SKILL_ROOT / "output"
    job = make_job_dir(output_root)
    source_path = Path(args.source).expanduser().resolve()
    document = load_mdir(Path(args.mdir).expanduser().resolve())
    image = normalize_source(source_path, job / "source.png")
    suggestion = crop_suggestion(image)
    # During a full run the MDIR coordinates are already relative to the image
    # chosen by the skill. Preserve it to avoid corrupting the reference frame.
    shutil.copy2(job / "source.png", job / "cropped_source.png")
    if suggestion["applied"]:
        suggestion["reason"] += "; not applied after MDIR creation; use --prepare before visual analysis"
        suggestion["applied"] = False

    write_json(job / "diagram.json", document)
    write_json(job / "diagram_analysis.json", analysis_from_mdir(document))
    svg_path = job / "diagram.svg"
    svg_path.write_text(render_svg(document, args.mode), encoding="utf-8")
    svg_validation = validate_svg(svg_path)

    geom_path = job / "diagram.geom"
    geom_path.write_text(to_geometry_dsl(document), encoding="utf-8")
    geometry_check = run(["node", "scripts/validate_geometry.mjs", str(geom_path)], SKILL_ROOT / "third_party" / "geometry-dsl")

    png_path = job / "diagram.png"
    render_result = run(["node", str(SKILL_ROOT / "scripts" / "render_svg.mjs"), str(svg_path), str(png_path), str(args.png_long_edge)])
    if render_result["returncode"] != 0:
        raise RuntimeError(render_result["stderr"] or render_result["stdout"] or "SVG PNG render failed")
    metrics_path = job / "overlay_metrics.json"
    overlay_result = run([sys.executable, str(SKILL_ROOT / "scripts" / "compare_overlay.py"), str(job / "cropped_source.png"), str(png_path), str(job / "overlay.png"), "--metrics", str(metrics_path)])
    if overlay_result["returncode"] != 0:
        raise RuntimeError(overlay_result["stderr"] or overlay_result["stdout"] or "overlay creation failed")
    overlay_metrics = json.loads(metrics_path.read_text(encoding="utf-8"))

    low_confidence = []
    for kind in ("points", "segments", "circles", "paths", "markers", "labels"):
        for item in document.get(kind, []):
            if float(item.get("confidence", 1.0)) < 0.75:
                label = item.get("id") or item.get("text") or item.get("type") or kind
                low_confidence.append({"object": str(label), "kind": kind, "confidence": item.get("confidence")})
    warnings = list(document.get("warnings", []))
    if low_confidence:
        warnings.append("low-confidence elements retained without inferred correction")
    if suggestion["confidence"] < 0.75:
        warnings.append("crop should be reviewed before the next image-analysis pass")
    report = {
        "diagram_type": document.get("diagram_type", "geometry"),
        "mode": args.mode,
        "detected_objects": {key: len(document.get(key, [])) for key in ("points", "segments", "circles", "paths", "markers", "labels")},
        "confidence_warnings": low_confidence,
        "warnings": warnings,
        "refinement_count": args.refinement,
        "validation_result": {
            "svg": {"passed": True, **svg_validation},
            "png_render": {"passed": True, "backend": "@resvg/resvg-js"},
            "overlay": {"passed": True, **overlay_metrics},
            "geometry_dsl_diagnostic": {"passed": geometry_check["returncode"] == 0, **geometry_check},
            "crop": suggestion,
        },
    }
    write_json(job / "report.json", report)
    if not args.debug:
        # All required artifacts are intentionally retained; --debug is reserved
        # for later verbose internal tracing without changing user-visible files.
        pass
    print(job)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an MDIR math diagram into editable SVG, PNG, overlay, and report.")
    parser.add_argument("source", help="source raster image")
    parser.add_argument("--mdir", help="Codex-authored MDIR JSON")
    parser.add_argument("--mode", choices=("faithful", "clean", "editable"), default="faithful")
    parser.add_argument("--output", help="directory that will receive a new job directory")
    parser.add_argument("--prepare", action="store_true", help="only normalize and conservatively crop before Codex visual analysis")
    parser.add_argument("--refinement", type=int, default=0)
    parser.add_argument("--png-long-edge", type=int, default=2200)
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    try:
        if args.prepare:
            return prepare(args)
        if not args.mdir:
            parser.error("--mdir is required unless --prepare is used; the Codex Skill creates it from visual analysis")
        return vectorize(args)
    except (MDIRError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
