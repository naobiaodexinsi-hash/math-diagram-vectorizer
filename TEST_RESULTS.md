# Test results

Run date: 2026-08-29

## Automated checks

| Check | Result |
|---|---|
| Skill structure validation | PASS |
| Python unit and integration tests | PASS — 5 tests |
| MDIR reference, marker, grid, and SVG tests | PASS |
| SVG-to-PNG local render | PASS — `@resvg/resvg-js` |
| macOS Quick Look SVG thumbnail | PASS |

## Degraded-fixture integration runs

Each fixture is rendered to a 2200-pixel-long-edge PNG, overlaid against its
source, XML-validated, and compiled through the pinned Geometry DSL diagnostic.

| Fixture | SVG | PNG | Overlay | Geometry DSL | Visual inspection |
|---|---|---|---|---|---|
| Triangle + altitude + right angle | PASS | PASS | PASS | PASS | PASS |
| Circle + radii + chord + central angle | PASS | PASS | PASS | PASS | PASS |
| Similar-figure layout + parallel/equal markers | PASS | PASS | PASS | PASS | PASS |
| Grid + triangle | PASS | PASS | PASS | PASS | PASS |
| Ordinary triangle | PASS | PASS | PASS | PASS | PASS |

The fixture sources simulate low resolution, JPEG compression, blur, and
grayscale/rotation. Their MDIR is deliberately known, so these tests validate
the deterministic rendering, validation, and refinement artifacts rather than
claiming OCR accuracy.

## Mode and crop checks

- `--prepare` created a conservative crop suggestion at confidence 0.72 and
  preserved the source when MDIR had already been authored.
- `clean` and `editable` both produced valid SVG, PNG, overlay, MDIR, and
  Geometry DSL diagnostic artifacts.

## Remaining acceptance work

No user-owned real worksheet image was supplied in this task. Before claiming
the target 70–80% real-world coverage, run the installed Skill on at least three
user-provided scans/screenshots and retain their job reports. Office-suite
insertion (Word, WPS, PowerPoint, Illustrator, and Inkscape) also remains a
manual target-version check; it has not been claimed as automatically tested.
