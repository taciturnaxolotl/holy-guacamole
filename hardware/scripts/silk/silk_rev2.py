"""Silkscreen art for the rev-2 carrier: draws it, writes it into the board as filled gr_poly items, renders previews.

usage (from hardware/):  python3 scripts/silk/silk_rev2.py guac.kicad_pcb [--preview-only]
needs: shapely, fonttools, pillow (fonts are vendored in scripts/silk/fonts, OFL)

Idempotent: every item it writes has a uuid starting 5a17a127-, and a rerun deletes those first. It also replaces
the old top-side RX / ESC / wordmark / SWD texts (art.DROP_TOP) with its own. Run it after any change that moves
pads near the art, then refill zones and rerun DRC in KiCad.
  bottom: avocado with the pit on the spin axis, swooshes, dashed accel radii r 12 / 18 with U4-U6 markers,
          XT30 solder-side net labels, wordmark, credit + dunkirk.sh/h/guac
  top:    GH pin rows (- + R T / - 1 2 -), RX / ESC, mini logo + wordmark, test-pad note
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


def top_items(txt):
    """yield (start, end) spans of top-level s-expressions inside (kicad_pcb ...)"""
    depth, start, i, n, instr = 0, None, 0, len(txt), False
    while i < n:
        c = txt[i]
        if instr:
            if c == '\\': i += 1
            elif c == '"': instr = False
        elif c == '"': instr = True
        elif c == '(':
            depth += 1
            if depth == 2: start = i
        elif c == ')':
            if depth == 2: yield start, i + 1
            depth -= 1
        i += 1


def strip(txt, drop_texts=()):
    """remove our gr_poly items and the replaced top-side gr_texts"""
    cut = []
    for a, b in top_items(txt):
        item = txt[a:b]
        if item.startswith('(gr_poly') and f'(uuid "{TAG}-' in item: cut.append((a, b))
        elif item.startswith('(gr_text'):
            m = re.match(r'\(gr_text "((?:[^"\\]|\\.)*)"', item)
            if m and m.group(1) in drop_texts and '"F.SilkS"' in item: cut.append((a, b))
    for a, b in reversed(cut):
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
    txt = strip(open(pcb).read(), art.DROP_TOP)
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
        im = render(bd, side, art=G[side], ppm=40, drop=art.DROP_TOP)
        im.save(os.path.join(out, f'silk_{name}.png'))
    if preview_only: print('previews in', out); return
    items, k = [], 0
    for side, layer in (('F', 'F.SilkS'), ('B', 'B.SilkS')):
        for p in no_holes(G[side]):
            items.append(sexpr(p, layer, k)); k += 1
    i = txt.rindex('\t(embedded_fonts')
    txt = txt[:i] + ''.join(items) + txt[i:]
    open(pcb, 'w').write(txt)
    print(f'wrote {k} silk polygons ({sum(1 for s in items if "B.SilkS" in s)} bottom); previews in {out}')


if __name__ == '__main__':
    main()
