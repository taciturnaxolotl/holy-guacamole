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

def bottom(bd, style='swoosh'):
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
    elif style == 'blueprint':                                   # the sensor geometry as the hero
        av, body = avocado(tilt=-8, pit_r=4.6, cross=False); b = affinity.scale(body, 0.42, 0.42, origin=(0, 0))
        G += [b.exterior.buffer(0.2), Point(0, 0).buffer(1.9)]
        ko = _avoid(bd, labels, [wordzone, oshw])
        lines = [ring((0, 0), 12.0, 0.15), ring((0, 0), 18.0, 0.15)]
        for k in range(24):                                      # 15 deg ticks on r 18, long on the axes
            a = math.radians(k*15); L = 1.4 if k % 6 == 0 else 0.7
            lines.append(LineString([(18.3*math.cos(a), 18.3*math.sin(a)), ((18.3+L)*math.cos(a), (18.3+L)*math.sin(a))]).buffer(0.08))
        lines += [LineString([(-19.5, 0), (-5.6, 0)]).buffer(0.08), LineString([(5.6, 0), (19.5, 0)]).buffer(0.08),
                  LineString([(0, -19.5), (0, -6.6)]).buffer(0.08), LineString([(0, 7.2), (0, 19.5)]).buffer(0.08)]
        for ref, (x, y) in imus.items():
            rot = -bd.fp[ref]['rot']                             # mirrored frame
            chip = affinity.rotate(box(-1.5, -1.25, 1.5, 1.25), rot, origin=(0, 0))
            G.append(affinity.translate(chip.exterior.buffer(0.09), x, y))
            G.append(affinity.translate(affinity.rotate(Point(-1.0, 0.75).buffer(0.25), rot, origin=(0, 0)), x, y))
            lines.append(LineString([(0, 0), (x, y)]).difference(Point(0, 0).buffer(6.0)).difference(Point(x, y).buffer(2.2)).buffer(0.08))
            r = math.hypot(x, y); lab = f'{ref}  r{r:.0f}'
            g = _mid(text(lab, 0.8, 'xbold', track=0.04)[0]); a = math.atan2(y, x)
            for d in (3.6, 4.4, 5.2):
                cand = affinity.translate(g, x + d*math.cos(a), y + d*math.sin(a) + (1.4 if abs(math.sin(a)) < 0.3 else 0))
                if not cand.intersects(ko) and bd.outline.buffer(-0.5).contains(affinity.scale(cand, -1, 1, origin=(0, 0))): labels.append(cand); break
        for r, ang in ((12, 52), (18, 63)):
            g = _mid(text(f'R{r}', 0.8, 'xbold')[0]); c = (r*math.cos(math.radians(ang)), r*math.sin(math.radians(ang)))
            labels.append(affinity.translate(g, *c)); lines.append(Point(c).buffer(1.2))   # (cut below)
        cut = _avoid(bd, [l for l in labels], [wordzone, oshw]).union(unary_union([Point(-12*math.cos(math.radians(-52)), 0).buffer(0)]))
        geo = unary_union([l for l in lines if l.area < 50 or True])
        R = unary_union([affinity.translate(_mid(text(f'R{r}', 0.8, 'xbold')[0]), r*math.cos(math.radians(a)), r*math.sin(math.radians(a))).buffer(0.35) for r, a in ((12, 52), (18, 63))])
        G.append(geo.difference(cut).difference(R).difference(Point(0, 0).buffer(0)))
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
    def free(s, g, allow_court=(), check_silk=True):
        if not s.inside.contains(g): return False
        if g.intersects(s.pads) or g.intersects(s.holes): return False
        crt = s.court
        if allow_court: crt = unary_union([g for r, g in s.body.items() if r not in allow_court and not g.is_empty])
        if g.intersects(crt): return False
        return not check_silk or not any(g.distance(p) < 0.15 for p in s.placed)
    def put(s, g, force=False, **kw):
        if force or s.free(g, **kw): s.G.append(g); s.placed.append(g); return True
        return False
    def why(s, g):
        r = []
        if not s.inside.contains(g): r.append('edge')
        if g.intersects(s.pads): r.append('pad')
        if g.intersects(s.holes): r.append('hole')
        r += [k for k, b in s.body.items() if not b.is_empty and g.intersects(b)]
        if any(g.distance(p) < 0.15 for p in s.placed): r.append('silk')
        return r
    def label(s, t, cands, cap=0.85, font='xbold', track=0.06, **kw):
        g0 = _mid(text(t, cap, font, track=track)[0])
        for (x, y) in cands:
            g = affinity.translate(g0, x, y)
            if s.put(g, **kw): return (x, y)
        print('  could not place', repr(t), s.why(affinity.translate(g0, *cands[0]))); return None

    def row(s, items, ys, cap, font='black', track=0, **kw):
        """tokens [(x, text)] on one shared midline: all placed at the same y, or none"""
        gs = [(x, _mid(text(t, cap, font, track=track)[0])) for x, t in items]
        for y in ys:
            cand = [affinity.translate(g, x, y) for x, g in gs]
            if all(s.free(g, **kw) for g in cand) and all(a.distance(b) >= 0.15 for i, a in enumerate(cand) for b in cand[i+1:]):
                for g in cand: s.put(g, force=True)
                return y
        print('  could not place row', [t for _, t in items], s.why(affinity.translate(gs[0][1], gs[0][0], ys[0]))); return None

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
    for a in (0.9, 0.7, 0.55):
        cross = unary_union([LineString([(-a, 0), (a, 0)]).buffer(0.09), LineString([(0, -a), (0, a)]).buffer(0.09), ring((0, 0), 0.35, 0.16)])
        if P.put(cross, allow_court=('U11',)): break
    else: print('  spin-axis mark does not fit', P.why(cross))
    # assembly outlines: one thin, uniform line 0.15 outside each body that is worth lining up by eye
    for ref in OUTLINE:
        fp = bd.fp[ref]; own = unary_union([g for v in fp['pads'].values() for g in v])
        b = unary_union([x for x in (fp['fab'], own) if x and not x.is_empty])
        env = b.minimum_rotated_rectangle.buffer(0.32, join_style=2)          # clear of its own pads by ~0.25
        line = env.exterior.buffer(0.075).difference(bd.pads['F'].buffer(0.2)).intersection(P.inside)
        if P.placed: line = line.difference(unary_union(P.placed).buffer(0.25))
        line = unary_union([p for p in getattr(line, 'geoms', [line]) if p.area > 0.06])   # no crumbs
        if not line.is_empty: P.put(line, force=True)
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
    # GH pin rows under the S-facing plugs, then their names
    for pins, toks in (((-2.97, -1.72, -0.47, 0.78), ('−', '+', 'R', 'T')), ((6.62, 7.88, 9.12, 10.38), ('−', '1', '2', '−'))):
        P.row(list(zip(pins, toks)), [-30.6, -30.8, -31.0], cap=0.95)
    P.row([(15.0, '−'), (18.2, '+')], [-30.6, -30.8, -31.0], cap=0.95)
    P.row([(-1.1, 'RX'), (8.5, 'ESC')], [-32.0, -32.2], cap=0.9, track=0.12)
    P.label('PWR', [(16.6, -32.0), (16.4, -32.0), (16.6, -32.2)], cap=0.9, font='black', track=0.12)
    # heading-LED plug: + / − behind its pins, name beside
    xs = [_pad(bd, 'J2', n).centroid.x for n in ('1', '2')]
    y = P.row([(xs[0], '+'), (xs[1], '−')], [29.75, 30.05, 30.35], cap=0.95)
    P.label('LED', [(-17.5, y or 30.05), (-17.7, y or 30.05)], cap=0.9, font='black', track=0.12)
    # UVLO jumper: name each outer pad by the divider it selects
    for num, t in (('1', '3S'), ('3', '2S')):
        c = _pad(bd, 'JP1', num).centroid
        # the jumper is boxed in; stack the names on its axis, beyond the neighbours (3S = pad 1 = S end)
        sgn = -1 if num == '1' else 1
        P.label(t, [(c.x + dx, c.y + sgn*d) for d in (1.3, 1.6, 2.0, 2.4, 2.8, 3.2, 3.6, 4.0) for dx in (0, 0.4, -0.4, 0.8)], cap=0.8)
    # polarity / pin 1, only where an orientation can go wrong
    for ref in ('U2', 'U4', 'U5', 'U6', 'U11'):
        fp = bd.fp[ref]; c = Point(fp['at']); p1 = _pad(bd, ref, '1').centroid
        dx, dy = p1.x - c.x, p1.y - c.y; L = math.hypot(dx, dy) or 1
        for d in (0.55, 0.7, 0.85, 1.0, 1.2):
            if P.put(Point(p1.x + dx/L*d, p1.y + dy/L*d).buffer(0.22), allow_court=(ref,)): break
        else:   # boxed in by its own outline: let the dot sit on the outline instead
            for d in (0.55, 0.7, 0.85, 1.0, 1.2):
                if P.put(Point(p1.x + dx/L*d, p1.y + dy/L*d).buffer(0.24), allow_court=(ref,), check_silk=False): break
            else: print('  no pin-1 dot for', ref)
    for ref in ('D3', 'D4', 'D5', 'D6'):                 # SOD-523 pad 1 = cathode: bar on the cathode end
        k = _pad(bd, ref, '1'); a = _pad(bd, ref, '2').centroid; x0, y0, x1, y1 = k.bounds
        bx = x0 - 0.35 if k.centroid.x < a.x else x1 + 0.35
        (P.put(box(bx - 0.1, k.centroid.y - 0.55, bx + 0.1, k.centroid.y + 0.55), allow_court=(ref,)) or
         P.put(box(bx - 0.1, y1 + 0.25, bx + 0.1, y1 + 0.85), allow_court=(ref,)) or
         P.put(box(bx - 0.1, y0 - 0.85, bx + 0.1, y0 - 0.25), allow_court=(ref,)) or print('  no cathode bar', ref, P.why(box(bx - 0.1, k.centroid.y - 0.55, bx + 0.1, k.centroid.y + 0.55))))
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
    P.label('REV 2', [(-4.9, 30.5), (-4.9, 30.3), (-6.5, 30.5), (-3.3, 30.5)], cap=0.8, font='xbold', track=0.1)
    s2, _ = text('SWD + VBAT TEST PADS ON THE BOTTOM', 0.8, 'xbold', track=0.06); P.put(affinity.translate(s2, 0, -35.7), force=True)
    return unary_union(P.G)

def dfm(g, wmin=0.16):
    """morphological opening: drop anything thinner than wmin (PCBWay silk min line 0.15)"""
    return g.buffer(-wmin/2, 32).buffer(wmin/2, 32).intersection(g.buffer(0.001))

DROP_TOP = 'all'   # every gr_text on F.SilkS is replaced
