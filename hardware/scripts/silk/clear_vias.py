"""Move GND stitching vias out from under the silkscreen (or drop them when there is nowhere to go).

A stitching via is a GND via with no track ending on it. Each one under silk on either side moves to the
nearest spot within MAX_MOVE that is clear of silk on both sides, keeps the board's clearance to every
other-net track / pad / via on all four layers, stays out of every non-GND zone fill (so it never punches
a hole in a power pour), keeps hole-to-hole and edge rules, and is not too close to another stitch via.
Routed vias are left alone: the silk placer keeps labels off them instead.

usage (from hardware/): python3 scripts/silk/clear_vias.py guac.kicad_pcb    (silk_rev2.py runs it for you)
then refill zones in KiCad and rerun DRC.
"""
import math, os, re, sys
from collections import Counter
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import affinity
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'review'))
from kpcb import load
from board import Board, T

CLR, HOLE2HOLE, EDGE, SILK_CLR, STITCH_GAP, MAX_MOVE = 0.205, 0.3, 0.5, 0.15, 1.0, 3.0
LAYERS = ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu')


def pad_poly(p):
    x, y = T(p['x'], p['y']); w, h = p['w'], p['h']
    g = Point(0, 0).buffer(w/2) if p['shape'] == 'circle' else box(-w/2, -h/2, w/2, h/2)
    return affinity.translate(affinity.rotate(g, p.get('rot', 0) or 0, origin=(0, 0)), x, y)


def plan(pcb):
    D = load(pcb); bd = Board(pcb)
    silk = unary_union([bd.silk['F'], bd.silk['B']])
    ends = Counter((round(e[0], 3), round(e[1], 3)) for s in D['seg'] for e in (s['a'], s['b']))
    def is_stitch(v): return v['net'] == 'GND' and ends[(round(v['p'][0], 3), round(v['p'][1], 3))] == 0
    # other-net copper on every layer (a through via touches all four)
    foreign = []
    for s in D['seg']:
        if s['net'] != 'GND' and s['layer'] in LAYERS: foreign.append(LineString([T(*s['a']), T(*s['b'])]).buffer(s['w']/2))
    for f in D['fp']:
        for p in f['pads']:
            if p['net'] != 'GND' and any(l in LAYERS or l == '*.Cu' for l in p['layers']): foreign.append(pad_poly(p))
    for v in D['via']:
        if v['net'] != 'GND': foreign.append(Point(T(*v['p'])).buffer(v['d']/2))
    for z in D['zone']:
        if z['net'] != 'GND':
            for L, pts in z['fills']:
                if L in LAYERS and len(pts) > 2: foreign.append(Polygon([T(*q) for q in pts]).buffer(0))
    foreign = unary_union(foreign)
    drills = [Point(h[0], h[1]).buffer(h[2]/2) for h in bd.holes]
    inside = bd.outline
    vias = [dict(v, c=T(*v['p'])) for v in D['via']]
    stitch = [v for v in vias if is_stitch(v)]
    moves, drops = [], []
    placed = [Point(v['c']) for v in vias if not is_stitch(v)]          # routed vias are fixed
    keep = [v for v in stitch if not Point(v['c']).buffer(v['d']/2 + SILK_CLR).intersects(silk)]
    placed += [Point(v['c']) for v in keep]
    for v in stitch:
        r = v['d']/2; c = Point(v['c'])
        if not c.buffer(r + SILK_CLR).intersects(silk): continue
        def ok(p):
            q = Point(p)
            if not inside.buffer(-(EDGE + r)).contains(q): return False
            if q.buffer(r + SILK_CLR).intersects(silk): return False
            if q.buffer(r + CLR).intersects(foreign): return False
            if any(q.distance(d) < HOLE2HOLE + v['drill']/2 for d in drills): return False
            if any(q.distance(o) < STITCH_GAP for o in placed): return False
            return True
        best = None
        for k in range(1, int(MAX_MOVE/0.1) + 1):                         # rings of growing radius, 24 bearings each
            d = k*0.1
            for j in range(24):
                a = 2*math.pi*j/24; p = (v['c'][0] + d*math.cos(a), v['c'][1] + d*math.sin(a))
                if ok(p): best = p; break
            if best: break
        if best: moves.append((v, best)); placed.append(Point(best))
        else: drops.append(v)
    return D, moves, drops


def apply(pcb, moves, drops):
    """edit the via blocks in place, matched by position (to 1 um) so number formatting never matters"""
    txt = open(pcb).read()
    blocks = [(m.start(), m.end(), float(m.group(1)), float(m.group(2))) for m in re.finditer(r'\n\t\(via\s+\(at ([-\d.]+) ([-\d.]+)\).*?\n\t\)', txt, re.S)]
    def find(v):
        for blk in blocks:
            if abs(blk[2] - v['p'][0]) < 1e-3 and abs(blk[3] - v['p'][1]) < 1e-3: return blk
        print('  could not find via at', v['p'])
    edits = []
    for v, (x, y) in moves:
        blk = find(v)
        if blk: edits.append((blk, re.sub(r'\(at [-\d.]+ [-\d.]+\)', f'(at {x + 80.0:.4f} {65.5 - y:.4f})', txt[blk[0]:blk[1]], count=1)))
    for v in drops:
        blk = find(v)
        if blk: edits.append((blk, ''))
    for (a, b, *_), new in sorted(edits, key=lambda e: -e[0][0]): txt = txt[:a] + new + txt[b:]
    open(pcb, 'w').write(txt)


if __name__ == '__main__':
    pcb = sys.argv[1]; D, moves, drops = plan(pcb)
    apply(pcb, moves, drops)
    print(f'stitching vias under silk: {len(moves)} moved (max {max([math.dist(v["c"], p) for v, p in moves] or [0]):.2f} mm), {len(drops)} dropped')
