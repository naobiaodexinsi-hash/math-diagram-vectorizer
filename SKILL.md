---
name: math-diagram-vectorizer
description: Reconstruct math diagrams as editable SVG with semantic inventory, geometry checks, uncertainty gates, and layered deliverables. Use for faithful worksheet, scan, or screenshot redraws; not ordinary photo tracing.
---

# Math Diagram Vectorizer

Create a faithful, editable SVG from a local plane-geometry or coordinate
diagram. Preserve the source; default to `faithful`.

## Fast path — clear, supported diagram

1. **Precheck.** A photo, complex solid, unsupported task, unreadable crop,
   label, marker, or arrow is a STOP; ask for a clearer source or confirmation.
2. **Semantic inventory before drawing.** Write `semantic.json` with points,
   lines, circles(`center`, `radius`, `through`), relations(`perpendicular`,
   `parallel`, `intersect`, `midpoint`, `angle_bisector`, `tangent`), and
   annotations(`text`, `angle`, `shade`, `arrow`). Record every visible item.
   Relations
   carry `status: verified|inferred|待确认` and
   `evidence: marker|geometry|none`; unreadable ones use `待确认关系`. Then
   read [MDIR](references/mdir.md), author `diagram.json`, and infer no
   unmarked relation while drawing:

   ```bash
   python3 scripts/math_vectorize.py SOURCE --mdir diagram.json \
     --mode faithful --output OUTPUT_ROOT --refinement 0
   ```

3. Read `report.json`; inspect `diagram.png` and `overlay.png`. Deliver
   `semantic.json`, `diagram.svg`, and `check_report.md` only when valid; keep
   MDIR, PNG, overlay, Geometry DSL diagnostics, and `report.json` alongside.
   Separate verified relations, visual inferences, and pending items.

## Escalate only on a trigger

- Unclear boundary: run `--prepare`, inspect `crop_report.json`, and choose a
  crop before authoring MDIR.
- Low-resolution, cropped, or second-pass source: read
  [validation notes](references/validation.md).
- Mismatch: change only the supported MDIR field; use refinements `1` then `2`
  only for report-supported corrections. Stop after three total renders.
- Any renderer failure: fix it or return the exact failure; never deliver an
  unvalidated SVG.

## Mathematical constraint check

After rendering, compare `semantic.json` coordinates with MDIR and record
measurements in `check_report.md`:

- collinearity: normalized cross-product error ≤ 0.02;
- perpendicularity/parallelism: angle error ≤ 2°;
- point-on-circle: radial error ≤ `max(2 px, 1% of radius)`;
- tangent: point-on-circle passes and tangent–radius angle error ≤ 2°;
- midpoint/equal-length/equal-angle marks: paired measurements agree within
  `max(2 px, 1% of the reference)`.

A pass proves coordinate consistency only, not that a visual guess is a given
fact. A failed check blocks delivery until corrected or marked `待确认`.

## Failure branches

| If this happens | Do this | Do not do this |
|---|---|---|
| Low resolution/occlusion | Mark `待确认`; 🔴 STOP | Invent a point, mark, or label |
| Relation is unclear | Write `待确认关系`; omit it from MDIR | Default to a relation |
| Labels overlap | Reposition labels only; rerender | Move a geometric point |
| Renderer fails | Use visible structure/live labels; rerun | Deliver unvalidated SVG |
| Constraint fails | Repair from evidence and rerun, or report mismatch | Hide it or force coordinates |

## 🔴 Red-light blacklist

- Do not guess hidden conditions from visual appearance.
- Do not call an approximately perpendicular pair a known perpendicular pair.
- Do not treat sketch proportions as mathematical proportions.
- Do not move a key point for beauty or encode an unprovided equilateral,
  isosceles, tangent, midpoint, parallel, perpendicular, equal-length, or
  equal-angle relation as certain.
- Do not pixel-trace, embed the raster, pathify labels, upload images, or replace
  semantic geometry with one giant path.

Do not extend this release to full function recognition, Word/PPT replacement,
TikZ, or GeoGebra.
