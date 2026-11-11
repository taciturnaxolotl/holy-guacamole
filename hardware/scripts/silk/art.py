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

def avocado(tilt=-14, pit_r=4.5, cross=True):
    body = unary_union([Point(0, 9.4).buffer(5.0, 96), Point(0, -0.8).buffer(8.4, 128)]).convex_hull   # Hass egg            # close the waist into a gentle concave neck
    skin = body.difference(body.buffer(-0.85))
    flesh_line = body.buffer(-1.6).exterior.buffer(0.14)     # thin line where the flesh pales near the skin
    pit = Point(0, 0).buffer(pit_r, 96)
    hl = LineString([(pit_r*0.68*math.cos(math.radians(a)), pit_r*0.68*math.sin(math.radians(a))) for a in range(105, 166, 5)]).buffer(0.32)
    cross_ = unary_union([LineString([(-1.4, 0), (1.4, 0)]).buffer(0.13), LineString([(0, -1.4), (0, 1.4)]).buffer(0.13), ring((0, 0), 0.75, 0.24)])
    pit = pit.difference(hl)
    if cross: pit = pit.difference(cross_)
    g = unary_union([skin, flesh_line.difference(Point(0, 0).buffer(pit_r+0.7)), pit])
    return affinity.rotate(g, tilt, origin=(0, 0)), affinity.rotate(body, tilt, origin=(0, 0))

def _common(bd, V):
    """bottom pieces every style shares (view frame): XT30 solder-side names, wordmark + credit, OSHW block"""
    G, labels = [], []
    for vx, top, bot in ((-13.8, 'BAT+', 'GND'), (13.8, 'VBAT', 'VBUS')):
        for y, t in ((-10.8, top), (-15.8, bot)):
            g, w = text(t, 0.8, 'xbold', align='r' if vx > 0 else 'l')
            labels.append(affinity.translate(_mid(g), vx - 2.35 if vx > 0 else vx + 2.35, y))
    h, wh = text('HOLY', 4.8, CHICLE, track=0.02); G.append(affinity.translate(h, 0, -27.0))
    gm, wg = text('GUACAMOLE', 3.4, CHICLE, track=0.02); gm = affinity.scale(gm, min(1, 32/wg), min(1, 32/wg), origin=(0, 0)); G.append(affinity.translate(gm, 0, -31.4))
    l1, _ = text('my favorite lil meltybrain  /  rev 2  /  nov 2026', 0.95, 'xbold', track=0.03); G.append(affinity.translate(l1, 0, -33.4))
    l2, _ = text('Kieran Klukas  /  dunkirk.sh/h/guac', 0.95, 'xbold', track=0.03); G.append(affinity.translate(l2, 0, -35.3))
    from oshw_logo import logo
    G.append(logo(7.2, (5.2, 32.6)))
    for k, t in enumerate(('OPEN', 'SOURCE', 'HARDWARE')):
        g, w = text(t, 0.85, 'xbold', track=0.06, align='l'); G.append(affinity.translate(g, 9.7, 34.1 - k*1.45))
    g, w = text('CERN-OHL-S-2.0', 0.8, 'xbold', track=0.02, align='l'); G.append(affinity.translate(g, 8.8, 29.15))   # tucked under the gear's curve
    return G, labels

def _avoid(bd, labels, extra=()):
    """view-frame keep-outs: pads, board texts, our labels"""
    exist = [Point(-tx, ty).buffer(sz*1.6) for txt, (tx, ty), sz, rot in bd.texts['B']]
    pads = affinity.scale(bd.pads['B'], -1, 1, origin=(0, 0)).buffer(0.7)
    return unary_union([pads] + exist + [l.buffer(0.6) for l in labels] + list(extra))

def bottom(bd, style='merged'):
    """returns geometry in BOARD coords for B.SilkS"""
    V = lambda x, y: (-x, y)                                     # board -> view
    G, labels = _common(bd, V)
    imus = {r: V(*p) for r, p, *_ in bd.fps if r in ('U4', 'U5', 'U6')}
    wordzone = box(-17, -37, 17, -21.5); oshw = box(0.5, 27.5, 19, 37.5)
    if style == 'swoosh':                                        # the first draft: avocado, swooshes, dashed radii
        av, body = avocado(); G.append(av); keep = body.buffer(1.2)
        sw = [dfm(x, 0.15) for x in (tapered_arc(16.4, -30, 30, 1.05), tapered_arc(15.0, 150, 206, 0.95), tapered_arc(13.0, 244, 298, 0.85))]; G += sw
        rings = unary_union([dashed_circle((0, 0), 12.0, 0.18, 0.7, 0.55), dashed_circle((0, 0), 18.0, 0.18, 0.7, 0.55)])
        for ref, (x, y) in imus.items():
            G += [ring((x, y), 1.75, 0.18), Point(x, y).buffer(0.32)]
        G.append(rings.difference(unary_union([keep] + [q.buffer(0.45) for q in sw] + [Point(p).buffer(2.4) for p in imus.values()] + [_avoid(bd, labels)])))
    elif style == 'clean':                                       # one big avocado, nothing else
        av, body = avocado(tilt=-8, pit_r=4.6, cross=False)
        G.append(affinity.scale(av, 1.08, 1.08, origin=(0, 0)))
    elif style in ('blueprint', 'merged'):                     # the sensor geometry as the hero
        av, body = avocado(tilt=-8, pit_r=4.6, cross=False)
        if style == 'merged':                                    # the clean avocado, smaller, inside the r 12 ring
            sc = 0.74; av = affinity.scale(av, sc, sc, origin=(0, 0)); body = affinity.scale(body, sc, sc, origin=(0, 0)); G.append(av)
            cross = unary_union([LineString([(-1.2, 0), (1.2, 0)]).buffer(0.1), LineString([(0, -1.2), (0, 1.2)]).buffer(0.1)])
            G[-1] = G[-1].difference(cross.buffer(0.12))         # spin-axis cross cut into the pit
        else:
            body = affinity.scale(body, 0.42, 0.42, origin=(0, 0)); G += [body.exterior.buffer(0.2), Point(0, 0).buffer(1.9)]
        hole = body.buffer(0.7)                                  # lines stop short of the avocado
        outline_v = affinity.scale(bd.outline, -1, 1, origin=(0, 0)).buffer(-0.5)
        ko = _avoid(bd, labels, [wordzone, oshw])
        lines = [ring((0, 0), 12.0, 0.15), ring((0, 0), 18.0, 0.15)]
        for k in range(24):                                      # 15 deg ticks outside r 18, long on the axes
            a = math.radians(k*15); L = 1.3 if k % 6 == 0 else 0.6
            lines.append(LineString([(18.3*math.cos(a), 18.3*math.sin(a)), ((18.3+L)*math.cos(a), (18.3+L)*math.sin(a))]).buffer(0.08))
        for k in range(72):                                      # 5 deg minor ticks inside r 12
            if k % 3 == 0: continue
            a = math.radians(k*5); lines.append(LineString([(11.75*math.cos(a), 11.75*math.sin(a)), (11.35*math.cos(a), 11.35*math.sin(a))]).buffer(0.07))
        lines += [LineString([(-20, 0), (20, 0)]).buffer(0.08), LineString([(0, -20), (0, 20)]).buffer(0.08)]
        tags = []
        chips = [Point(p).buffer(2.3) for p in imus.values()]
        M = lambda g: affinity.scale(g, -1, 1, origin=(0, 0))         # board -> view
        for ref, (x, y) in imus.items():
            # the chip as drawn on the top: real outline, pin-1 corner filled, its name inside, all the same way
            fp = bd.fp[ref]; own = unary_union([g for v in fp['pads'].values() for g in v])
            env = M(unary_union([q for q in (fp['fab'], own) if q and not q.is_empty]).minimum_rotated_rectangle).buffer(0.32, join_style=2)
            G.append(env.exterior.buffer(0.075))
            G.append(_corner_tri(env, M(_pad(bd, ref, '1')).centroid))
            # name turned along the ring like R12 / R18, centred in its box
            nm = _arc_text(_mid(text(ref, 0.85, 'xbold', track=0.04)[0]), math.hypot(x, y), math.atan2(y, x))
            tags.append(affinity.translate(nm, env.centroid.x - x, env.centroid.y - y))
            lines.append(LineString([(0, 0), (x, y)]).difference(env.buffer(0.3)).buffer(0.1))
        for r, ang in ((12, 45), (18, 45)):                      # ring names sit in a gap in their own ring, along it
            tags.append(_arc_text(_mid(text(f'R{r}', 0.85, 'xbold')[0]), r, math.radians(ang)))
        geo = unary_union(lines).difference(hole)
        G.append(geo.difference(unary_union([ko] + [q.buffer(0.35) for q in tags] + [Point(p).buffer(1.75) for p in imus.values()])))
        labels += tags
    elif style == 'pattern':                                     # wallpaper of little avocados
        av, body = avocado(tilt=0, pit_r=4.6, cross=False)
        icon = lambda t: affinity.rotate(unary_union([affinity.scale(body, 0.16, 0.16, origin=(0, 0)).exterior.buffer(0.11), Point(0, 0).buffer(0.62)]), t, origin=(0, 0))
        ko = _avoid(bd, labels, [wordzone.buffer(0.6), oshw.buffer(0.4)]).union(bd.outline.buffer(-0.8).symmetric_difference(bd.outline.buffer(5)) if False else Polygon())
        inside = affinity.scale(bd.outline.buffer(-1.0), -1, 1, origin=(0, 0))
        k = 0
        for j, y in enumerate(np.arange(-20.5, 37, 4.6)):
            for x in np.arange(-19 + (2.6 if j % 2 else 0), 20, 5.2):
                g = affinity.translate(icon(25 if (j + int(x)) % 2 else -25), x, y)
                if inside.contains(g) and not g.intersects(ko): G.append(g); k += 1
    G += labels
    g = unary_union(G)
    return affinity.scale(g, -1, 1, origin=(0, 0)), {}

CHICLE = 'Chicle-Regular.ttf'
# parts that get an assembly outline on the top (0402/0603 passives and the jumper are left bare)
PIN1 = ('U2', 'U4', 'U5', 'U6', 'U11')
OUTLINE = ('U1', 'U2', 'U4', 'U5', 'U6', 'U11', 'L1', 'C21', 'D2', 'Q1', 'J2', 'J4', 'J5')

class Placer:
    """greedy label placement on the top: every mark keeps 0.2 mm off exposed copper, stays off part bodies
    (courtyards) unless told otherwise, 0.15 mm off silk already placed, and inside the board."""
    def __init__(s, bd, side='F'):
        s.bd = bd; s.pads = bd.pads[side].buffer(0.2)
        # part bodies: the fab outline where the footprint has one, else the courtyard less its 0.25 margin
        s.body = {r: (fp['fab'] if fp['fab'] and not fp['fab'].is_empty else fp['crt'].buffer(-0.25)) for r, fp in bd.fp.items() if fp['side'] == side and fp['crt'] and not fp['crt'].is_empty and not r.startswith('H')}
        s.court = unary_union([g for g in s.body.values() if not g.is_empty])
        s.inside = bd.outline.buffer(-0.4); s.holes = unary_union([Point(h[0], h[1]).buffer(h[2]/2 + 0.6) for h in bd.holes])
        s.placed = []; s.G = []
        s.rvias = unary_union([Point(c).buffer(d/2 + 0.12) for c, d in bd.routed_vias])
        s.strict = True; s.over_vias = []     # pass 1 keeps off routed vias; pass 2 allows it and records where
    def free(s, g, allow_court=(), check_silk=True):
        if not s.inside.contains(g): return False
        if g.intersects(s.pads) or g.intersects(s.holes) or (s.strict and g.intersects(s.rvias)): return False
        crt = s.court
        if allow_court: crt = unary_union([g for r, g in s.body.items() if r not in allow_court and not g.is_empty])
        if g.intersects(crt): return False
        return not check_silk or not any(g.distance(p) < 0.15 for p in s.placed)
    def put(s, g, force=False, **kw):
        if force or s.free(g, **kw):
            s.G.append(g); s.placed.append(g)
            if not s.strict and g.intersects(s.rvias): s.over_vias.append(g)
            return True
        return False
    def passes(s):
        """iterate strict then relaxed; callers break out on success"""
        for st in (True, False):
            s.strict = st; yield st
        s.strict = True
    def first(s, geoms, **kw):
        """put the first geometry that fits, strict pass first"""
        geoms = list(geoms)
        for _ in s.passes():
            for g in geoms:
                if s.put(g, **kw): s.strict = True; return g
        return None
    def why(s, g):
        r = []
        if not s.inside.contains(g): r.append('edge')
        if g.intersects(s.pads): r.append('pad')
        if g.intersects(s.rvias): r.append('via')
        if g.intersects(s.holes): r.append('hole')
        r += [k for k, b in s.body.items() if not b.is_empty and g.intersects(b)]
        if any(g.distance(p) < 0.15 for p in s.placed): r.append('silk')
        return r
    def label(s, t, cands, cap=0.85, font='xbold', track=0.06, **kw):
        g0 = _mid(text(t, cap, font, track=track)[0])
        for _ in s.passes():
            for (x, y) in cands:
                g = affinity.translate(g0, x, y)
                if s.put(g, **kw): s.strict = True; return (x, y)
        print('  could not place', repr(t), s.why(affinity.translate(g0, *cands[0]))); return None

    def row(s, items, ys, cap, font='black', track=0, **kw):
        """tokens [(x, text)] on one shared midline: all placed at the same y, or none"""
        gs = [(x, _mid(text(t, cap, font, track=track)[0])) for x, t in items]
        for _ in s.passes():
            for y in ys:
                cand = [affinity.translate(g, x, y) for x, g in gs]
                if all(s.free(g, **kw) for g in cand) and all(a.distance(b) >= 0.15 for i, a in enumerate(cand) for b in cand[i+1:]):
                    for g in cand: s.put(g, force=True)
                    if not s.strict: s.over_vias += [g for g in cand if g.intersects(s.rvias)]
                    s.strict = True; return y
        print('  could not place row', [t for _, t in items], s.why(affinity.translate(gs[0][1], gs[0][0], ys[0]))); return None

def _corner_tri(env, p1, leg=1.05):
    """solid triangle filling the corner of a rectangle outline nearest pin 1, flush with the line's outer edge"""
    cs = list(env.exterior.coords)[:-1]; i = min(range(len(cs)), key=lambda j: Point(cs[j]).distance(p1)); k = cs[i]
    o = list(env.buffer(0.075, join_style=2).exterior.coords)[:-1]; kk = min(o, key=lambda q: Point(q).distance(Point(k)))
    def L(q):
        dx, dy = q[0] - k[0], q[1] - k[1]; n = math.hypot(dx, dy); return (kk[0] + dx/n*leg, kk[1] + dy/n*leg)
    return Polygon([kk, L(cs[i - 1]), L(cs[(i + 1) % len(cs)])])

def _arc_text(g, r, a):
    """text centred on radius r at angle a, turned to run along the circle and kept the right way up"""
    rot = math.degrees(a) - 90
    if math.cos(math.radians(rot)) < 0: rot += 180
    return affinity.translate(affinity.rotate(g, rot, origin=(0, 0)), r*math.cos(a), r*math.sin(a))

def _mid(g):
    """centre a glyph run on its own ink box, so + - and capitals share one midline"""
    x0, y0, x1, y1 = g.bounds; return affinity.translate(g, 0, -(y0 + y1)/2)

def _pad(bd, ref, num):
    return unary_union(bd.fp[ref]['pads'][num])

def _around(c, d, n=12, start=0):
    return [(c[0] + d*math.cos(math.radians(start + k*360/n)), c[1] + d*math.sin(math.radians(start + k*360/n))) for k in range(n)]

def top(bd):
    P = Placer(bd)
    # spin axis first; the U11 outline breaks around it
    crosses = [unary_union([LineString([(-a, 0), (a, 0)]).buffer(0.09), LineString([(0, -a), (0, a)]).buffer(0.09), ring((0, 0), 0.35, 0.16)]) for a in (0.9, 0.7, 0.55)]
    if not P.first(crosses, allow_court=('U11',)): print('  spin-axis mark does not fit', P.why(crosses[-1]))
    # assembly outlines: one thin, uniform line 0.15 outside each body that is worth lining up by eye
    for ref in OUTLINE:
        fp = bd.fp[ref]; own = unary_union([g for v in fp['pads'].values() for g in v])
        b = unary_union([x for x in (fp['fab'], own) if x and not x.is_empty])
        env = b.minimum_rotated_rectangle.buffer(0.32, join_style=2)          # clear of its own pads by ~0.25
        tri = None
        if ref in PIN1:                       # pin 1: fill the outline's corner nearest pad 1 with a solid triangle
            p1 = _pad(bd, ref, '1').centroid; cs = list(env.exterior.coords)[:-1]
            i = min(range(len(cs)), key=lambda j: Point(cs[j]).distance(p1)); k = cs[i]
            def leg(q, L=1.0):
                dx, dy = q[0] - k[0], q[1] - k[1]; n = math.hypot(dx, dy); return (k[0] + dx/n*L, k[1] + dy/n*L)
            o = env.buffer(0.075, join_style=2)                    # flush with the outer edge of the line
            ko = list(o.exterior.coords)[:-1]; kk = min(ko, key=lambda q: Point(q).distance(Point(k)))
            def leg2(q, L=1.05):
                dx, dy = q[0] - k[0], q[1] - k[1]; n = math.hypot(dx, dy); return (kk[0] + dx/n*L, kk[1] + dy/n*L)
            tri = Polygon([kk, leg2(cs[i - 1]), leg2(cs[(i + 1) % len(cs)])])
        line = env.exterior.buffer(0.075).difference(bd.pads['F'].buffer(0.2)).intersection(P.inside)
        if P.placed: line = line.difference(unary_union(P.placed).buffer(0.25))
        line = unary_union([p for p in getattr(line, 'geoms', [line]) if p.area > 0.06])   # no crumbs
        if not line.is_empty: P.put(line, force=True)
        if tri is not None:
            t = tri.difference(bd.pads['F'].buffer(0.2))
            if t.area > 0.12: P.put(t, force=True)
            else: print('  pin-1 triangle squeezed out for', ref)
    # connector bodies, drawn from their fab outline (keeps the XT30 chamfer = orientation)
    for ref in ('J6', 'J7'):    # XT30: the fab outline keeps the chamfer, which is the orientation key
        body = bd.fp[ref]['fab'].buffer(0.12)
        P.put(body.exterior.buffer(0.075).difference(bd.pads['F'].buffer(0.2)), force=True)
    # XT30 titles and pin names, inboard of each connector
    for ref, sgn, title, pins in (('J6', 1, 'BAT', ('+', '−')), ('J7', -1, 'SWITCH', ('VBAT', 'VBUS'))):
        cx = sgn*13.8
        P.label(title, [(cx, -6.75), (cx, -6.95), (cx - sgn*0.6, -6.75)], cap=1.05, font='black', track=0.08)
        for y, t in zip((-10.8, -15.8), pins):
            big = len(t) == 1; cap, fnt = (1.1, 'black') if big else (0.9, 'xbold')
            w = text(t, cap, fnt, track=0.06)[1]
            P.label(t, [(cx - sgn*(2.75 + 0.45 + w/2), y), (cx - sgn*(2.95 + 0.45 + w/2), y), (cx - sgn*(3.3 + w/2), y + 0.4)], cap=cap, font=fnt)
    # GH plugs: each pin named, vertical so the names fit the 1.25 mm pitch, then the plug's name
    for pins, toks, name, nx in (((-2.97, -1.72, -0.47, 0.78), ('GND', '5V', 'RX', 'TX'), 'RECEIVER', -1.1),
                                 ((6.62, 7.88, 9.12, 10.38), ('GND', 'CH1', 'CH2', 'GND'), 'ESC', 8.5)):
        done = False
        for _ in P.passes():
          for y in (-31.4, -31.6, -31.8):
            gs = [affinity.translate(affinity.rotate(_mid(text(t, 0.8, 'xbold', track=0.04)[0]), 90, origin=(0, 0)), x, 0) for x, t in zip(pins, toks)]
            top = max(g.bounds[3] for g in gs); cand = [affinity.translate(g, 0, y + 1.3 - top) for g in gs]
            if all(P.free(g) for g in cand) and all(a.distance(b) >= 0.15 for i, a in enumerate(cand) for b in cand[i+1:]):
                for g in cand: P.put(g, force=True)
                bottom = min(g.bounds[1] for g in cand); done = True; break
          if done: break
        P.strict = True
        if not done: print('  pin names do not fit for', name, P.why(cand[0])); bottom = -32.7
        P.label(name, [(nx, bottom - 0.95), (nx, bottom - 1.15), (nx + 0.4, bottom - 0.95), (nx - 0.4, bottom - 0.95)], cap=0.9, font='black', track=0.12)
    P.row([(15.0, '−'), (18.2, '+')], [-30.6, -30.8, -31.0], cap=0.95)
    P.label('PWR', [(16.6, -32.0), (16.4, -32.0), (16.6, -32.2)], cap=0.9, font='black', track=0.12)
    # heading-LED plug: + / − behind its pins, name beside
    xs = [_pad(bd, 'J2', n).centroid.x for n in ('1', '2')]
    y = P.row([(xs[0], '+'), (xs[1], '−')], [29.75, 30.05, 30.35], cap=0.95)
    P.label('LED', [(-17.5, y or 30.05), (-17.7, y or 30.05)], cap=0.9, font='black', track=0.12)
    # UVLO jumper: name each outer pad by the divider it selects
    if 'JP1' in bd.fp:
        for num, t in (('1', '3S'), ('3', '2S')):
            c = _pad(bd, 'JP1', num).centroid
            # the jumper is boxed in; stack the names on its axis, beyond the neighbours (3S = pad 1 = S end)
            sgn = -1 if num == '1' else 1
            P.label(t, [(c.x + dx, c.y + sgn*d) for d in (1.3, 1.6, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0) for dx in (0, 0.4, -0.4, 0.8)], cap=0.8)
    # C21 polymer tantalum: thick band on the anode (pad 1) end of its outline, the usual polarity mark
    fp = bd.fp['C21']; own = unary_union([g for v in fp['pads'].values() for g in v])
    env = unary_union([fp['fab'], own]).minimum_rotated_rectangle.buffer(0.32, join_style=2)
    cs = list(env.exterior.coords); p1 = _pad(bd, 'C21', '1').centroid
    segs = sorted((LineString([cs[i], cs[i+1]]) for i in range(len(cs)-1)), key=lambda l: l.centroid.distance(p1))
    band = segs[0].buffer(0.2, cap_style=2).intersection(env.buffer(0.2)).difference(bd.pads['F'].buffer(0.2))
    P.put(band, force=True)
    # wordmark in the free N strip (W of the USB notch), test-pad note in the S strip
    av, body = avocado(tilt=-10); b = affinity.scale(body, 0.235, 0.235, origin=(0, 0))
    mini = unary_union([b.difference(b.buffer(-0.34)), Point(0, 0).buffer(0.95)])
    P.put(affinity.translate(mini, -12.3, 33.75), force=True)
    h, wh = text('HOLY', 2.2, CHICLE, track=0.02); g2, wg = text('GUACAMOLE', 1.75, CHICLE, track=0.02)
    sc = min(1, 9.4/wg); h = affinity.scale(h, sc, sc, origin=(0, 0)); g2 = affinity.scale(g2, sc, sc, origin=(0, 0))
    P.put(affinity.translate(h, -4.9, 34.45), force=True); P.put(affinity.translate(g2, -4.9, 31.9), force=True)
    # middle of the front: a hazard placard in the free band between the ICs and the XT30s
    hz = hazard(16.0, 6.6)
    if not P.first(affinity.translate(hz, cx, cy) for cx, cy in ((0, -5.6), (-0.5, -5.6), (0.5, -5.6), (0, -5.3), (0, -5.9))):
        print('  hazard placard does not fit', P.why(affinity.translate(hz, 0, -5.6)))
    return unary_union(P.G)

def hazard(w, h):
    """hazard-stripe placard: stripe bands top and bottom, DANGEROUSLY AWESOME PCB in Bungee"""
    band = 0.95; G = [box(-w/2, -h/2, w/2, h/2).exterior.buffer(0.1)]
    stripes = unary_union([Polygon([(x, 0), (x + 0.55, 0), (x + 0.55 - band, band), (x - band, band)]) for x in np.arange(-w/2 - 1, w/2 + 2, 1.1)])
    for yb in (h/2 - band - 0.25, -h/2 + 0.25):
        G.append(affinity.translate(stripes, 0, yb).intersection(box(-w/2 + 0.25, yb, w/2 - 0.25, yb + band)))
    lines = ('DANGEROUSLY', 'AWESOME PCB'); cap = 1.35; gap = 0.65
    gs = [text(t, cap, 'Bungee-Regular.ttf', track=0.04) for t in lines]
    sc = min(1, (w - 1.6)/max(tw for _, tw in gs))
    for k, (t, tw) in enumerate(gs):
        yb = (cap*sc + gap)/2 - k*(cap*sc + gap) - cap*sc/2
        G.append(affinity.translate(affinity.scale(t, sc, sc, origin=(0, 0)), 0, yb))
    return dfm(unary_union(G), 0.15)

def dfm(g, wmin=0.16):
    """morphological opening: drop anything thinner than wmin (PCBWay silk min line 0.15)"""
    return g.buffer(-wmin/2, 32).buffer(wmin/2, 32).intersection(g.buffer(0.001))

DROP_TOP = 'all'   # every gr_text on F.SilkS is replaced
