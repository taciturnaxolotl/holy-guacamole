"""Silkscreen art for the rev-2 carrier: draws it, writes it into the board as filled gr_poly items, renders previews.

usage (from hardware/):  uv run --with shapely --with fonttools --with pillow python3 scripts/silk/silk_rev2.py guac.kicad_pcb [--preview-only]
(fonts are vendored in scripts/silk/fonts, OFL; route_best_rev2.sh runs this for you)

Idempotent: every item it writes has a uuid starting 5a17a127-, and a rerun deletes those first. It also replaces
the old top-side RX / ESC / wordmark / SWD texts (art.DROP_TOP) with its own. Run it after any change that moves
pads near the art, then refill zones and rerun DRC in KiCad.
  bottom: avocado with the pit on the spin axis, swooshes, dashed accel radii r 12 / 18 with U4-U6 markers,
          XT30 solder-side net labels, Chicle wordmark, credit + dunkirk.sh/h/guac, OSHW logo + licence
  top:    replaces KiCad's footprint outlines with a minimal set: XT30 bodies (chamfer = orientation) and pin
          names, GH pin rows, LED +/-, pin-1 dots, cathode bars, C21 +, spin-axis mark, wordmark
"""
import os, re, sys, tempfile
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import split, unary_union
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import art
from board import Board, render, OX, OY
from PIL import Image

TAG = '5a17a127'
PAD_CLR, EDGE_CLR = 0.2, 0.25       # silk to exposed copper / to board edge


def top_items(txt, level=2, lo=0, hi=None):
    """yield (start, end) spans of s-expressions at nesting `level` (2 = items inside (kicad_pcb ...))"""
    depth, start, i, n, instr = 0, None, lo, len(txt) if hi is None else hi, False
    while i < n:
        c = txt[i]
        if instr:
            if c == '\\': i += 1
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c == '(':
            depth += 1
            if depth == level: start = i
        elif c == ')':
            if depth == level: yield start, i + 1
            depth -= 1
        i += 1


FP_SILK = ('(fp_line', '(fp_arc', '(fp_circle', '(fp_rect', '(fp_poly', '(fp_text')


def strip(txt):
    """remove our gr_poly items, every top-side gr_text, and the footprints' own F.SilkS graphics and texts
    (KiCad's outlines; 'update footprints from library' brings them back, so rerun this after one)"""
    cut = []
    for a, b in top_items(txt):
        item = txt[a:b]
        if item.startswith('(gr_poly') and f'(uuid "{TAG}-' in item: cut.append((a, b))
        elif item.startswith('(gr_text') and '(layer "F.SilkS")' in item: cut.append((a, b))
        elif item.startswith('(footprint'):
            for c, d in top_items(txt, 1, a + 1, b - 1):
                sub = txt[c:d]
                if sub.startswith(FP_SILK) and '(layer "F.SilkS")' in sub: cut.append((c, d))
    for a, b in sorted(cut, reverse=True):
        j = txt.rfind('\n', 0, a); txt = txt[:j] + txt[b:]
    return txt


def no_holes(g):
    """KiCad gr_poly has no holes: split through each hole until every piece is simple"""
    out, todo = [], list(getattr(g, 'geoms', [g]))
    while todo:
        p = todo.pop()
        if p.geom_type != 'Polygon' or p.area < 1e-4: continue
        if not p.interiors: out.append(p); continue
        cx = p.interiors[0].centroid.x + 1e-4; y0, y1 = p.bounds[1] - 1, p.bounds[3] + 1
        for q in split(p, LineString([(cx, y0), (cx, y1)])).geoms: todo.append(q)
    return out


def sexpr(poly, layer, k):
    pts = list(poly.exterior.coords)[:-1]
    xy = ' '.join(f'(xy {OX + x:.4f} {OY - y:.4f})' for x, y in pts)
    return (f'\t(gr_poly\n\t\t(pts {xy})\n\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n\t\t(fill yes)\n'
            f'\t\t(layer "{layer}")\n\t\t(uuid "{TAG}-0000-4000-8000-{k:012x}")\n\t)\n')


def main():
    pcb = sys.argv[1]; preview_only = '--preview-only' in sys.argv
    txt = strip(open(pcb).read())
    with tempfile.NamedTemporaryFile('w', suffix='.kicad_pcb', delete=False) as f: f.write(txt); clean = f.name
    bd = Board(clean); os.unlink(clean)
    B, info = art.bottom(bd); T = art.top(bd)
    G = {}
    for side, g in (('B', B), ('F', T)):
        g = g.difference(bd.pads[side].buffer(PAD_CLR)).intersection(bd.outline.buffer(-EDGE_CLR))
        G[side] = art.dfm(g, 0.12).simplify(0.004)      # drop crumbs the pad clipping leaves behind
    out = os.path.join(os.path.dirname(os.path.abspath(pcb)), '..', 'docs', 'silk')
    os.makedirs(out, exist_ok=True)
    for side, name in (('F', 'top'), ('B', 'bottom')):
        im = render(bd, side, art=G[side], ppm=40)
        im.save(os.path.join(out, f'silk_{name}.png'))
    if preview_only: print('previews in', out); return
    items, k = [], 0
    for side, layer in (('F', 'F.SilkS'), ('B', 'B.SilkS')):
        for p in no_holes(G[side]):
            items.append(sexpr(p, layer, k)); k += 1
    i = txt.rindex('\t(embedded_fonts')
    txt = txt[:i] + ''.join(items) + txt[i:]
    open(pcb, 'w').write(txt)
    import clear_vias                     # then get the stitching vias out from under it
    D, moves, drops = clear_vias.plan(pcb); clear_vias.apply(pcb, moves, drops)
    print(f'stitching vias under silk: {len(moves)} moved, {len(drops)} dropped')
    print(f'wrote {k} silk polygons ({sum(1 for s in items if "B.SilkS" in s)} bottom); previews in {out}')


if __name__ == '__main__':
    main()
