"""Board geometry for silkscreen work + a realistic render (mask / copper / ENIG / silk).
Coordinates: board frame, x right, y north (y = 65.5 - Y_kicad, x = X_kicad - 80). Bottom renders are viewed from below (mirrored x)."""
import sys, math, numpy as np
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'review'))
from kpcb import parse, find, one
from shapely.geometry import Polygon, LineString, Point, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont
PCB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'guac.kicad_pcb')
OX, OY = 80.0, 65.5
def T(x, y): return (float(x) - OX, OY - float(y))

def arc_pts(s, m, e, n=24):
    (x1, y1), (x2, y2), (x3, y3) = s, m, e
    d = 2*(x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2))
    if abs(d) < 1e-9: return [s, e]
    ux = ((x1*x1+y1*y1)*(y2-y3)+(x2*x2+y2*y2)*(y3-y1)+(x3*x3+y3*y3)*(y1-y2))/d
    uy = ((x1*x1+y1*y1)*(x3-x2)+(x2*x2+y2*y2)*(x1-x3)+(x3*x3+y3*y3)*(x2-x1))/d
    r = math.hypot(x1-ux, y1-uy); a1 = math.atan2(y1-uy, x1-ux); a2 = math.atan2(y2-uy, x2-ux); a3 = math.atan2(y3-uy, x3-ux)
    def norm(a): return a % (2*math.pi)
    ccw = norm(a2-a1) < norm(a3-a1); span = norm(a3-a1) if ccw else -norm(a1-a3)
    return [(ux+r*math.cos(a1+span*k/n), uy+r*math.sin(a1+span*k/n)) for k in range(n+1)]

def width(g):
    w = one(g, 'width') or (one(one(g, 'stroke'), 'width') if one(g, 'stroke') else None)
    return float(w[1]) if w else 0.12

def gshape(g, xf):
    """KiCad graphic item -> shapely geometry in board frame. xf maps local (x,y kicad) -> board frame."""
    k = g[0][3:] if g[0].startswith('fp_') else g[0][3:]
    w = width(g)
    filled = one(g, 'fill') and one(g, 'fill')[1] in ('solid', 'yes')
    if k == 'line': return LineString([xf(*one(g, 'start')[1:3]), xf(*one(g, 'end')[1:3])]).buffer(w/2, cap_style=1)
    if k == 'arc':
        p = arc_pts(xf(*one(g, 'start')[1:3]), xf(*one(g, 'mid')[1:3]), xf(*one(g, 'end')[1:3])); return LineString(p).buffer(w/2)
    if k == 'circle':
        c = xf(*one(g, 'center')[1:3]); e = xf(*one(g, 'end')[1:3]); r = math.dist(c, e)
        return Point(c).buffer(r + w/2) if filled else Point(c).buffer(r).boundary.buffer(w/2)
    if k == 'rect':
        a = one(g, 'start')[1:3]; b = one(g, 'end')[1:3]
        pts = [xf(a[0], a[1]), xf(b[0], a[1]), xf(b[0], b[1]), xf(a[0], b[1])]
        return Polygon(pts).buffer(w/2) if filled else LineString(pts + [pts[0]]).buffer(w/2)
    if k == 'poly':
        pts = [xf(*q[1:3]) for q in one(g, 'pts') if q[0] == 'xy']
        P = Polygon(pts).buffer(0)
        return P.buffer(w/2) if (filled or filled is None) else LineString(pts + [pts[0]]).buffer(w/2)
    return None

def pad_shape(p, fx, fy, fr):
    pa = one(p, 'at'); px, py = float(pa[1]), float(pa[2]); pr = float(pa[3]) if len(pa) > 3 else 0.
    a = math.radians(-fr); X = fx + px*math.cos(a) - py*math.sin(a); Y = fy + px*math.sin(a) + py*math.cos(a)
    sz = one(p, 'size'); w, h = float(sz[1]), float(sz[2]); shp = p[3]
    if shp == 'circle': g = Point(0, 0).buffer(w/2)
    elif shp in ('oval',): g = LineString([(-(w-h)/2, 0), ((w-h)/2, 0)]).buffer(h/2) if w >= h else LineString([(0, -(h-w)/2), (0, (h-w)/2)]).buffer(w/2)
    elif shp == 'roundrect':
        rr = float(one(p, 'roundrect_rratio')[1]) * min(w, h); g = box(-w/2+rr, -h/2+rr, w/2-rr, h/2-rr).buffer(rr)
    else: g = box(-w/2, -h/2, w/2, h/2)
    g = affinity.rotate(g, pr, origin=(0, 0))       # absolute pad angle, CCW in board frame (y up)
    bx, by = T(X, Y); g = affinity.translate(g, bx, by)
    dr = one(p, 'drill'); d = float(dr[1]) if dr and len(dr) > 1 and dr[1] != 'oval' else (float(dr[2]) if dr and len(dr) > 2 else 0)
    return g, (bx, by, d), [l for l in one(p, 'layers')[1:]], p[2]

class Board:
    def __init__(s, path=PCB):
        B = parse(open(path).read()); s.B = B
        s.pads = {'F': [], 'B': []}; s.silk = {'F': [], 'B': []}; s.cu = {'F': [], 'B': []}; s.holes = []; s.court = {'F': [], 'B': []}
        s.texts = {'F': [], 'B': []}; s.fps = []; s.fp = {}
        st = one(one(B, 'setup'), 'stackup') if one(B, 'setup') else None     # copper weights, outer to outer
        s.copper_um = [float(one(l, 'thickness')[1])*1000 for l in (find(st, 'layer') if st else []) if one(l, 'type') and one(l, 'type')[1] == 'copper']
        s.thickness = float(one(one(B, 'general'), 'thickness')[1]) if one(B, 'general') and one(one(B, 'general'), 'thickness') else None
        for f in find(B, 'footprint'):
            at = one(f, 'at'); fx, fy = float(at[1]), float(at[2]); fr = float(at[3]) if len(at) > 3 else 0.
            a = math.radians(-fr)
            def xf(x, y, fx=fx, fy=fy, a=a): x, y = float(x), float(y); return T(fx + x*math.cos(a) - y*math.sin(a), fy + x*math.sin(a) + y*math.cos(a))
            ref = [p[2] for p in find(f, 'property') if p[1] == 'Reference'][0]
            s.fps.append((ref, T(fx, fy), fr, one(f, 'layer')[1]))
            rec = s.fp[ref] = {'at': T(fx, fy), 'rot': fr, 'side': one(f, 'layer')[1][0], 'fab': [], 'crt': [], 'pads': {}, 'name': f[1]}
            for g in f:
                if not (isinstance(g, list) and g and g[0] in ('fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly')): continue
                L = one(g, 'layer')[1]; sh = gshape(g, xf)
                if sh is None: continue
                if L in ('F.SilkS', 'B.SilkS'): s.silk[L[0]].append(sh)
                if L in ('F.CrtYd', 'B.CrtYd'): rec['crt'].append(sh)
                if L in ('F.Fab', 'B.Fab'): rec['fab'].append(sh)
            for t in find(f, 'fp_text') + [p for p in find(f, 'property')]:
                L = one(t, 'layer'); hd = one(t, 'hide'); ef = one(t, 'effects')
                if not L or L[1] not in ('F.SilkS', 'B.SilkS') or (hd and hd[1] == 'yes') or (ef and one(ef, 'hide')): continue
                ta = one(t, 'at'); txt = t[2] if t[0] == 'fp_text' else t[2]
                s.texts[L[1][0]].append((txt, xf(ta[1], ta[2]), float(one(one(ef, 'font'), 'size')[1]), float(ta[3]) if len(ta) > 3 else 0))
            for p in find(f, 'pad'):
                g, hole, lays, typ = pad_shape(p, fx, fy, fr)
                rec['pads'].setdefault(p[1], []).append(g)
                if hole[2] > 0: s.holes.append(hole)
                for side in 'FB':
                    if f'{side}.Cu' in lays or '*.Cu' in lays: s.cu[side].append(g)
                    if f'{side}.Mask' in lays or '*.Mask' in lays: s.pads[side].append(g)
        ends = set()
        for sg in find(B, 'segment') + find(B, 'arc'):
            ends.update((round(float(one(sg, k)[1]), 3), round(float(one(sg, k)[2]), 3)) for k in ('start', 'end'))
            L = one(sg, 'layer')[1]
            if L not in ('F.Cu', 'B.Cu'): continue
            a = T(*one(sg, 'start')[1:3]); b = T(*one(sg, 'end')[1:3]); w = float(one(sg, 'width')[1])
            pts = arc_pts(a, T(*one(sg, 'mid')[1:3]), b) if sg[0] == 'arc' else [a, b]
            s.cu[L[0]].append(LineString(pts).buffer(w/2))
        s.vias = []; s.routed_vias = []      # routed = a track ends on it (stitching vias can move, these cannot)
        for v in find(B, 'via'):
            at = one(v, 'at'); c = T(*at[1:3]); d = float(one(v, 'size')[1]); dr = float(one(v, 'drill')[1]); s.vias.append((c, d, dr))
            nn = one(v, 'net'); net = nn[1] if nn else ''
            if net != 'GND' or (round(float(at[1]), 3), round(float(at[2]), 3)) in ends: s.routed_vias.append((c, d))
            for side in 'FB': s.cu[side].append(Point(c).buffer(d/2))
        for z in find(B, 'zone'):
            for fp in find(z, 'filled_polygon'):
                L = one(fp, 'layer')[1]
                if L in ('F.Cu', 'B.Cu'): s.cu[L[0]].append(Polygon([T(*q[1:3]) for q in one(fp, 'pts') if q[0] == 'xy']).buffer(0))
        for g in find(B, 'gr_line') + find(B, 'gr_arc') + find(B, 'gr_poly') + find(B, 'gr_rect') + find(B, 'gr_circle'):
            L = one(g, 'layer')[1]
            if L in ('F.SilkS', 'B.SilkS'): s.silk[L[0]].append(gshape(g, T))
        for t in find(B, 'gr_text'):
            L = one(t, 'layer')[1]
            if L not in ('F.SilkS', 'B.SilkS'): continue
            ta = one(t, 'at'); ef = one(t, 'effects')
            s.texts[L[0]].append((t[1], T(ta[1], ta[2]), float(one(one(ef, 'font'), 'size')[1]), float(ta[3]) if len(ta) > 3 else 0))
        # outline: polygonize Edge.Cuts
        segs = []
        for g in find(B, 'gr_line') + find(B, 'gr_arc'):
            if one(g, 'layer')[1] != 'Edge.Cuts': continue
            a = T(*one(g, 'start')[1:3]); b = T(*one(g, 'end')[1:3])
            pts = arc_pts(a, T(*one(g, 'mid')[1:3]), b) if g[0] == 'gr_arc' else [a, b]
            pts = [a] + pts[1:-1] + [b]; segs.append(LineString([(round(x, 4), round(y, 4)) for x, y in pts]))
        from shapely.ops import polygonize
        s.outline = max(polygonize(unary_union(segs)), key=lambda p: p.area)
        for ref, rec in s.fp.items():   # filled courtyard / body outlines per footprint
            for key in ('crt', 'fab'):
                u = unary_union(rec[key]) if rec[key] else Polygon()
                rec[key] = unary_union([Polygon(p.exterior) for p in getattr(u, 'geoms', [u]) if p.geom_type == 'Polygon']) if not u.is_empty else u
            if rec['crt'] and not rec['crt'].is_empty: s.court[rec['side']].append(rec['crt'])
        for k in 'FB':
            s.court[k] = unary_union(s.court[k])
            s.cu[k] = unary_union(s.cu[k]); s.pads[k] = unary_union(s.pads[k]); s.silk[k] = unary_union([g for g in s.silk[k] if g is not None])
        s.drills = unary_union([Point(h[0], h[1]).buffer(h[2]/2) for h in s.holes] + [Point(c).buffer(dr/2) for c, d, dr in s.vias])

MASK = {'green': ((22, 92, 52), (40, 128, 68)), 'black': ((22, 24, 26), (44, 48, 50)), 'purple': ((54, 28, 92), (84, 52, 128))}

def render(bd, side, art=None, ppm=40, mask='green', title=None, margin=2.0, show_existing=True, drop=(), fontpath=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts', 'InterDisplay-ExtraBold.otf')):
    """side 'F' (viewed from top) or 'B' (viewed from below, mirrored). art: shapely geometry in board frame on that side's silk."""
    x0, y0, x1, y1 = bd.outline.bounds; x0 -= margin; y0 -= margin; x1 += margin; y1 += margin
    W, H = int((x1-x0)*ppm), int((y1-y0)*ppm); mir = side == 'B'
    def P(x, y): return (((x1 - x) if mir else (x - x0))*ppm, (y1 - y)*ppm)
    S = 2; img = Image.new('RGBA', (W*S, H*S), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    def fill(geom, col):
        if geom is None or geom.is_empty: return
        for pg in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
            if pg.geom_type != 'Polygon' or pg.is_empty: continue
            d.polygon([(a*S, b*S) for a, b in (P(*q) for q in pg.exterior.coords)], fill=col)
            for it in pg.interiors: d.polygon([(a*S, b*S) for a, b in (P(*q) for q in it.coords)], fill=(0, 0, 0, 0))
    def fill_holes(geom, col):   # interiors re-filled with col after cutting (draw order handles it)
        fill(geom, col)
    base, cuc = MASK[mask]
    # draw: substrate+mask, then copper-under-mask tint, then pads ENIG, then silk, then drills
    fill(bd.outline, base + (255,))
    cu = bd.cu[side].intersection(bd.outline)
    _draw_poly_with_holes(d, cu, P, S, cuc + (255,), base + (255,))
    pads = bd.pads[side].intersection(bd.outline)
    _draw_poly_with_holes(d, pads, P, S, (214, 178, 92, 255), base + (255,))
    silk = bd.silk[side] if show_existing else Polygon()
    if art is not None: silk = unary_union([silk, art])
    silk = silk.difference(bd.pads[side].buffer(0.05)).intersection(bd.outline.buffer(-0.15))
    _draw_poly_with_holes(d, silk, P, S, (244, 244, 238, 255), None, bd, side, cu, pads, base, cuc)
    if show_existing:
        for txt, (tx, ty), sz, rot in bd.texts[side]:
            if txt in drop: continue
            f = ImageFont.truetype(fontpath, max(6, int(sz*ppm*S*0.95)))
            tw = d.textlength(txt, font=f); tile = Image.new('RGBA', (int(tw)+8, int(sz*ppm*S*1.4)), (0, 0, 0, 0))
            ImageDraw.Draw(tile).text((4, 0), txt, font=f, fill=(244, 244, 238, 255))
            tile = tile.rotate(rot, expand=True); cx, cy = P(tx, ty)
            img.alpha_composite(tile, (int(cx*S - tile.size[0]/2), int(cy*S - tile.size[1]/2)))
    _draw_poly_with_holes(d, bd.drills, P, S, (30, 30, 30, 255), None)
    img = img.resize((W, H), Image.LANCZOS)
    return img

def _draw_poly_with_holes(d, geom, P, S, col, holecol, *a):
    if geom is None or geom.is_empty: return
    # rasterize via mask: draw exteriors then punch interiors by redrawing what's under them is hard; use a per-geometry mask
    from PIL import Image as _I
    im = d._image; m = _I.new('L', im.size, 0); dm = ImageDraw.Draw(m)
    from PIL import ImageChops
    for pg in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if pg.geom_type != 'Polygon' or pg.is_empty: continue
        if not pg.interiors:
            dm.polygon([(x*S, y*S) for x, y in (P(*q) for q in pg.exterior.coords)], fill=255); continue
        bx0, by0, bx1, by1 = pg.bounds; t = _I.new('L', im.size, 0); dt = ImageDraw.Draw(t)
        dt.polygon([(x*S, y*S) for x, y in (P(*q) for q in pg.exterior.coords)], fill=255)
        for it in pg.interiors: dt.polygon([(x*S, y*S) for x, y in (P(*q) for q in it.coords)], fill=0)
        m = ImageChops.lighter(m, t); dm = ImageDraw.Draw(m)
    im.paste(_I.new('RGBA', im.size, col), (0, 0), m)
