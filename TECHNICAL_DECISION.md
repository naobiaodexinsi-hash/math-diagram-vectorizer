# Technical decision record

Date: 2026-08-29

## Reference review

| Project | Inspected revision | Useful capability | Not used | Reuse decision |
|---|---:|---|---|---|
| `ivanfxia-sketch/cell-lct-macos` | `70df3551ba8b9f051aa205decddfb97103bdb471` | Fresh job directory, untouched source retention, live-text SVG checks, completion gate | Illustrator bridge, Keychain/API work, paid external vectorization | Design only |
| `anounman/mathwriter-diagrams` | `47da959a50d4bc1cb592b76f8bd8c6623237b6c3` | Structured primitive and local validation split | Hand-drawn CS style, raster-only output | Design only; no LICENSE was present, so no code is copied |
| `shand001/geometry-dsl` | `c7ee10030c175acad792ba82b53af540f2b578f8` | Deterministic geometry parser, marks, SVG/PNG renderer, machine-readable validation loop | Its automatic visual layout as the final reference-matching renderer | Pinned local runtime subset and semantic diagnostic compiler |

## License decision

The first and third repositories include MIT licenses. Their code may be
copied or modified only with the original copyright and license notice.
Mathwriter Diagrams had no license at the pinned revision; this project does
not include its code. Geometry DSL is retained intact under `third_party/` and
its MIT license is preserved. Project-authored files remain all rights reserved.

## Architecture

```text
source raster -> safe crop -> Codex visual analysis -> MDIR
             -> editable SVG renderer -> high-resolution PNG -> overlay/report
             -> Geometry DSL diagnostic validation -> bounded refinement
```

MDIR, not SVG, is the editable asset. The SVG renderer is deliberately small
and direct so source-relative coordinates and label offsets remain faithful.
Geometry DSL independently compiles a generated semantic shadow (`diagram.geom`)
to catch invalid object references and provide a portable diagnostic. This
avoids changing a source figure merely to fit a generic auto-layout engine.
