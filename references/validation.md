# Validation and refinement

The overlay is diagnostic, not a pixel-similarity gate. Scan noise, JPEG
artifacts, and antialiasing are expected differences. Use it to examine:

- omitted or extra main lines, circles, markers, and labels;
- large displacement of vertices, circle centres, or label quadrants;
- changed dash style, arrow direction, or crop boundaries.

The local validator rejects raster `<image>` nodes, external URLs, scripts,
filters, and SVGs without editable geometry. `report.json` also records MDIR
counts, live-text counts, render status, crop caution, confidence warnings, and
the Geometry DSL diagnostic result.

Only refine a report-supported discrepancy. Stop after three total renders or
when remaining ambiguity is source-limited; tell the user which label or mark
needs confirmation instead of silently changing it.
