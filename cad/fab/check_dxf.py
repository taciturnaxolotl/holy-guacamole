"""Sanity check for cut DXFs: every contour closed, overall size, cutouts, smallest cutout, thinnest web.

usage: uv run --with ezdxf --with shapely --with matplotlib python check_dxf.py dxf/*.dxf   (writes a .png preview
next to each DXF)
"""
import sys, math, ezdxf
from shapely.geometry import Polygon, LineString
from shapely.ops import linemerge
R = lambda p: (round(p[0], 4), round(p[1], 4))
for p in sys.argv[1:]:
    msp = ezdxf.readfile(p).modelspace(); loops, pieces = [], []
    for e in msp:
        t = e.dxftype()
        if t == 'LWPOLYLINE':
            q = [R(v[:2]) for v in e.get_points()]
            (loops if e.closed else pieces).append(q)
        elif t == 'LINE':
            pieces.append([R((e.dxf.start.x, e.dxf.start.y)), R((e.dxf.end.x, e.dxf.end.y))])
        elif t == 'CIRCLE':
            c, r = e.dxf.center, e.dxf.radius
            loops.append([(c.x + r * math.cos(2 * math.pi * i / 180), c.y + r * math.sin(2 * math.pi * i / 180)) for i in range(180)])
        elif t == 'ARC':
            c, r, a0, a1 = e.dxf.center, e.dxf.radius, e.dxf.start_angle, e.dxf.end_angle
            if a1 <= a0: a1 += 360
            n = max(4, int((a1 - a0) / 2))
            pts = [(c.x + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), c.y + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
            pts[0], pts[-1] = R(pts[0]), R(pts[-1]); pieces.append(pts)
    open_n = 0
    if pieces:
        m = linemerge([LineString(q) for q in pieces])
        for g in getattr(m, 'geoms', [m]):
            if g.is_ring: loops.append(list(g.coords))
            else: open_n += 1
    part = None
    for L in loops:
        g = Polygon(L).buffer(0); part = g if part is None else part.symmetric_difference(g)
    b = part.bounds; holes = [Polygon(h) for g in getattr(part, 'geoms', [part]) for h in g.interiors]
    small = min((2 * math.sqrt(h.area / math.pi) for h in holes), default=0)
    lo, hi = 0.0, 10.0
    for _ in range(30):
        m = (lo + hi) / 2; g = part.buffer(-m)
        if g.is_empty or g.geom_type == 'MultiPolygon' and len(g.geoms) > len(getattr(part, 'geoms', [part])): hi = m
        else: lo = m
    print('%s: %.1f x %.1f mm, %.0f mm2, %d contours (%d open), %d cutouts, smallest cutout ~%.2f mm, thinnest web ~%.2f mm'
          % (p.split('/')[-1], b[2] - b[0], b[3] - b[1], part.area, len(loops), open_n, len(holes), small, 2 * hi))
    if True:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 5))
        for g in getattr(part, 'geoms', [part]):
            x, y = g.exterior.xy; ax.fill(x, y, color='#777')
            for h in g.interiors: x, y = h.xy; ax.fill(x, y, color='white')
        ax.set_aspect('equal'); ax.axis('off'); fig.savefig(p.replace('.dxf', '.png'), dpi=110, bbox_inches='tight'); plt.close(fig)
