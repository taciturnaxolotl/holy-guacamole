"""Silkscreen art for the rev-2 carrier. Bottom art is authored in the view-from-below frame (vx = -x) and mirrored into board coords."""
import math, numpy as np
from shapely.geometry import Point, Polygon, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from glyphs import text

def tapered_arc(r, a0, a1, wmax, n=80, skew=0.35):
    """comet-like swoosh: width rises fast then tails off (skew moves the fat end toward a1)."""
    out, inn = [], []
    for k in range(n+1):
        t = k/n; a = math.radians(a0 + (a1-a0)*t)
        w = wmax*math.sin(math.pi*min(1, t**(1-skew) if skew else t))**0.9
        out.append(((r+w/2)*math.cos(a), (r+w/2)*math.sin(a))); inn.append(((r-w/2)*math.cos(a), (r-w/2)*math.sin(a)))
    return Polygon(out + inn[::-1]).buffer(0)

def ring(c, r, w): return Point(c).buffer(r+w/2).difference(Point(c).buffer(r-w/2))

def dashed_circle(c, r, w, dash, gap, phase=0):
    L = 2*math.pi*r; n = int(L/(dash+gap)); out = []
    for k in range(n):
        a0 = phase + k*(dash+gap)/r; a1 = a0 + dash/r
        pts = [(c[0]+r*math.cos(a0+(a1-a0)*j/6), c[1]+r*math.sin(a0+(a1-a0)*j/6)) for j in range(7)]
        out.append(LineString(pts).buffer(w/2))
    return unary_union(out)

def avocado(tilt=-14, pit_r=4.5):
    body = unary_union([Point(0, 8.2).buffer(5.2, 96), Point(0, -0.8).buffer(8.9, 128)])
    body = body.buffer(5.0, 64).buffer(-5.0, 64)            # close the waist into a gentle concave neck
    skin = body.difference(body.buffer(-0.85))
    flesh_line = body.buffer(-1.6).exterior.buffer(0.14)     # thin line where the flesh pales near the skin
    pit = Point(0, 0).buffer(pit_r, 96)
    hl = LineString([(pit_r*0.68*math.cos(math.radians(a)), pit_r*0.68*math.sin(math.radians(a))) for a in range(105, 166, 5)]).buffer(0.32)
    cross = unary_union([LineString([(-1.4, 0), (1.4, 0)]).buffer(0.13), LineString([(0, -1.4), (0, 1.4)]).buffer(0.13), ring((0, 0), 0.75, 0.24)])
    pit = pit.difference(hl).difference(cross)
    g = unary_union([skin, flesh_line.difference(Point(0, 0).buffer(pit_r+0.7)), pit])
    return affinity.rotate(g, tilt, origin=(0, 0)), affinity.rotate(body, tilt, origin=(0, 0))

def bottom(bd):
    """returns geometry in BOARD coords for B.SilkS"""
    V = lambda x, y: (-x, y)                                     # board -> view
    G = []
    av, body = avocado(); G.append(av)
    keep = body.buffer(1.2)
    imus = {r: V(*p) for r, p, *_ in bd.fps if r in ('U4', 'U5', 'U6')}
    # spin swooshes (no direction: the bot spins either way)
    sw = [tapered_arc(16.4, -30, 30, 1.05), tapered_arc(15.0, 150, 206, 0.95), tapered_arc(13.0, 244, 298, 0.85)]
    sw = [dfm(x, 0.15) for x in sw]; G += sw
    # sensor map: dashed accel radii, ticks at each IMU
    rings = unary_union([dashed_circle((0, 0), 12.0, 0.18, 0.7, 0.55), dashed_circle((0, 0), 18.0, 0.18, 0.7, 0.55)])
    labels = []
    clear = [keep] + [s.buffer(0.45) for s in sw] + [Point(p).buffer(2.4) for p in imus.values()]
    for ref, (x, y) in imus.items():
        a = math.atan2(y, x); r = math.hypot(x, y)
        G.append(ring((x, y), 1.75, 0.18))
        G.append(Point(x, y).buffer(0.32))
        lab, w = text(ref, 0.85, 'xbold')
        lx, ly = (x + 2.9*math.cos(a), y + 2.9*math.sin(a))
        if ref == 'U6': lx, ly = x + 0.2, y + 2.6
        if ref == 'U5': lx, ly = x + 2.9, y - 0.45
        if ref == 'U4': lx, ly = x - 0.2, y + 2.55
        labels.append(affinity.translate(lab, lx, ly - 0.42))
    # XT30 solder-side labels (bottom of J6 = view x -13.8, J7 = +13.8)
    for vx, top, bot in ((-13.8, 'BAT+', 'GND'), (13.8, 'VBAT', 'VBUS')):
        for y, t in ((-10.8, top), (-15.8, bot)):
            g, w = text(t, 0.8, 'xbold', align='r' if vx > 0 else 'l')
            labels.append(affinity.translate(g, vx - 2.35 if vx > 0 else vx + 2.35, y - 0.4))
    exist = [Point(-tx, ty).buffer(sz*1.6) for txt, (tx, ty), sz, rot in bd.texts['B']]   # board labels (GND/CLK/DIO/VBAT), view frame
    pads = affinity.scale(bd.pads['B'], -1, 1, origin=(0, 0)).buffer(0.7)
    G += labels
    G.append(rings.difference(unary_union(clear + [l.buffer(0.6) for l in labels] + exist + [pads])))
    # wordmark
    h, wh = text('HOLY', 4.4, 'blacki', track=0.02); G.append(affinity.translate(h, 0, -27.0))
    gm, wg = text('GUACAMOLE', 2.75, 'blacki', track=0.04); G.append(affinity.translate(gm, 0, -31.2))
    l1, _ = text('1 LB MELTYBRAIN  ·  REV 2  ·  2026', 0.8, 'xbold', track=0.08); G.append(affinity.translate(l1, 0, -33.4))
    l2, _ = text('KIERAN KLUKAS  ·  dunkirk.sh/h/guac', 0.8, 'xbold', track=0.08); G.append(affinity.translate(l2, 0, -35.3))
    # underline swoosh under HOLY
    G.append(dfm(affinity.translate(tapered_arc(40, 262.5, 277.5, 0.55, skew=0.0), 0, 40-28.0), 0.15))
    # OSHW logo + licence, view NE of the notch (board NW corner)
    from oshw_logo import logo
    G.append(logo(7.2, (5.2, 32.6)))
    for k, t in enumerate(('OPEN', 'SOURCE', 'HARDWARE')):
        g, w = text(t, 0.85, 'xbold', track=0.06, align='l'); G.append(affinity.translate(g, 9.7, 34.1 - k*1.45))
    g, w = text('CERN-OHL-S-2.0', 0.8, 'xbold', track=0.04, align='l'); G.append(affinity.translate(g, 9.7, 29.15))
    g = unary_union(G)
    return affinity.scale(g, -1, 1, origin=(0, 0)), {}

def top(bd):
    G = []
    # pin rows under the S-facing GH connectors
    for pins, toks in (((-2.97, -1.72, -0.47, 0.78), ('−', '+', 'R', 'T')), ((6.62, 7.88, 9.12, 10.38), ('−', '1', '2', '−'))):
        for x, t in zip(pins, toks):
            g, w = text(t, 1.0, 'black'); G.append(affinity.translate(g, x, -31.15))
    for x, t in ((-1.1, 'RX'), (8.5, 'ESC')):
        g, w = text(t, 0.85, 'xbold', track=0.1); G.append(affinity.translate(g, x, -32.55))
    # wordmark + mini avocado
    av, body = avocado(tilt=-14); b = affinity.scale(body, 0.15, 0.15, origin=(0, 0))
    mini = unary_union([b.difference(b.buffer(-0.3)), Point(0, 0).buffer(0.62)])
    wm, ww = text('HOLY GUACAMOLE', 1.45, 'blacki', track=0.03)
    tot = ww + 3.6; x0 = -tot/2
    G.append(affinity.translate(mini, x0 + 1.4, -34.55 + 0.72))
    G.append(affinity.translate(wm, x0 + 3.6 + ww/2, -34.55))
    s2, _ = text('SWD + VBAT TEST PADS ON THE BOTTOM', 0.8, 'xbold', track=0.06); G.append(affinity.translate(s2, 0, -36.35))
    return unary_union(G)

def dfm(g, wmin=0.16):
    """morphological opening: drop anything thinner than wmin (PCBWay silk min line 0.15)"""
    return g.buffer(-wmin/2, 32).buffer(wmin/2, 32).intersection(g.buffer(0.001))

DROP_TOP = {'RX', 'ESC', 'HOLY GUACAMOLE rev2', 'SWD/VBAT pads on bottom'}
