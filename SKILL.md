---
name: math-diagram-vectorizer
description: High-fidelity semantic reconstruction of uploaded math diagrams into editable SVG. Use for requests such as "重绘几何图", "vectorize this worksheet diagram", "redraw a coordinate graph", or faithfully recreating a geometry or coordinate diagram from a worksheet, scan, or screenshot. Do not use for ordinary photo tracing.
---

# Math Diagram Vectorizer

Create a faithful, editable SVG from a local plane-geometry or coordinate
diagram. Preserve the original source; include surrounding text only when it is
part of the figure. Default to `faithful`; use `clean` or `editable` only when
the user requests those modes.

## Fast path — clear, supported diagram

1. **Precheck before reading references or rendering.** An ordinary photo,
   complex solid, or unsupported task is out of scope. An unreadable crop,
   label, marker, or arrow is a STOP: ask for a clearer image or confirmation;
   do not write a guessed MDIR.
2. Read [MDIR](references/mdir.md), author `diagram.json` against the exact
   source canvas, and record every visible point, segment, label, and marker;
   infer no unmarked relation. Then render once:

   ```bash
   python3 scripts/math_vectorize.py SOURCE --mdir diagram.json \
     --mode faithful --output OUTPUT_ROOT --refinement 0
   ```

3. Read `report.json`; inspect `diagram.png` and `overlay.png`. When all
   validations pass and neither reveals a discrepancy, deliver `diagram.svg`,
   `diagram.png`, `report.json`, and MDIR for later edits.

## Escalate only on a trigger

- **Unclear boundary:** run `python3 scripts/math_vectorize.py SOURCE
  --prepare --output OUTPUT_ROOT`; inspect `crop_report.json` and explicitly
  choose the original or reviewed `cropped_source.png` before authoring MDIR.
- **Low-resolution, cropped, or second-pass source:** also read
  [validation notes](references/validation.md).
- **Reported or visible mismatch:** change only the supported MDIR field,
  inspect the overlay, then rerun with `--refinement 1`; use
  `--refinement 2` only for one final report-supported correction. Stop after
  three renders or when the source limits certainty.
- **MDIR, SVG, PNG, overlay, or Geometry DSL failure:** correct the reported
  defect. If it remains unresolved, do not deliver an unvalidated SVG; return
  MDIR and the exact failure.

## Non-negotiable boundaries

- Never pixel-trace, embed the raster, pathify labels, infer unmarked
  parallel/perpendicular/equal/midpoint/similarity relations, or upload images.
- Do not extend this release to full function recognition, Word/PPT
  replacement, TikZ, or GeoGebra.
