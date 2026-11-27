# Viewer and README renders: build sources

`../holy-guacamole.html` is built from these. Everything runs from this folder, after `concept_v33.py` has written its
`v33m_*.step` / `.stl` set (default prefix `../../scripts/v33m_`, override with `SRC=<prefix>`).

**Offline viewer**
1. `python3 fine_stl.py` — fine meshes of the four printed parts (`v33m_{lower,upper,top,bot}fine.stl`)
2. `python3 pack33.py` — decimate + pack every mesh into `geo.b64` / `meta.json`
3. `python3 build_page.py` — inline `../../harness/harness.js`, the meta and the geometry into `template.html` → `holy-guacamole.html` (copy it up a folder)

**README renders** (Onshape look: Phong + headlight, screen-space silhouette and crease edges, hatched section caps, real alpha)
1. `python3 pack_hi.py && python3 build_page.py hi` → `page_hi.html` (full-resolution geometry)
2. For each shot list: `SHOTS=$PWD/h.json node onshape_shots.mjs $PWD/page_hi.html os` (also `ex.json`, `dw.json`, `sec.json`, `g.json`). Needs Playwright + Chromium.
3. `python3 mk_exploded.py`, `python3 mk_drawing.py` (callouts and the dimensioned sheet; `annot.py` holds the shared drawing helpers), `python3 wiring.py && node svg2png.mjs $PWD/os/wiring.svg $PWD/os/wiring.png 1810 1090`

Renders come out at 2×, trimmed, then halved. The finished set is in `docs/img/`.
