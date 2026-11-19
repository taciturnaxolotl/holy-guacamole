"""TPU ear liners to print at home: one U-shaped liner per ear (6 per bot), in a few fits.
Outer face = the printed notch minus 0.05 (slip in); inner face = steel ear + GAP. Smaller GAP = the ear bears on the
liner before the bolt does (the 0.3 default lets the Ti bolts take the hit first). Print all, keep the set that slides on snug."""
import os, sys, math, cadquery as cq
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely import affinity as _aff
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', 'ring'))
from ring_fea import ring2d
RI, RO, RING_T = 73.0, 78.0, float(os.environ.get('RING_T_MEAS', 4.763))
EAR_R, EAR_ANG, EAR_W, EAR_RIN, CLR, LINER_T = 68.5, [30, 90, 150, 210, 270, 330], 10.0, 64.5, 0.3, 0.8
R_SK = RI-0.4
RING2D, _ = ring2d(Ri=RI, Ro=RO, T=12.0, rake=20.0, tipw=3.0, tipr=0.8, rf_lead=4.0, trail_deg=28.0,
                   ear_rin=EAR_RIN, ear_w=EAR_W, ear_rc=2.0, ear_rf=4.0, bolt_r=EAR_R, bolt_d=3.4, ear_ang=EAR_ANG)
EARS = RING2D.simplify(0.02, preserve_topology=True).intersection(Point(0, 0).buffer(RI-0.05, 720))
SOLID = unary_union([Polygon(g.exterior) for g in getattr(EARS, 'geoms', [EARS])])
OUT = SOLID.buffer(CLR+LINER_T-0.05, join_style=1)
def prism(p, z0, z1):
    if p.geom_type == 'MultiPolygon':
        r = None
        for g in p.geoms: q = prism(g, z0, z1); r = q if r is None else r.union(q)
        return r
    wp = cq.Workplane('XY').workplane(offset=z0).polyline(list(p.exterior.coords)[:-1]).close().extrude(z1-z0)
    for h in p.interiors: wp = wp.cut(cq.Workplane('XY').workplane(offset=z0-1).polyline(list(h.coords)[:-1]).close().extrude(z1-z0+2))
    return wp
od = sys.argv[1] if len(sys.argv) > 1 else 'liners'; os.makedirs(od, exist_ok=True)
a0 = math.radians(90)
for gap in (0.30, 0.15, 0.05):
    L = OUT.difference(SOLID.buffer(gap, join_style=1)).intersection(Point(0, 0).buffer(R_SK, 720))
    # one liner (the 90° ear), laid flat at the origin for printing
    one = [g for g in getattr(L, 'geoms', [L]) if g.centroid.distance(Point(0, EAR_R)) < 12]
    one = unary_union(one); one = _aff.translate(_aff.rotate(one, -90, origin=(0, 0)), -EAR_R, 0)
    s = prism(one, 0, RING_T)
    t = CLR+LINER_T-0.05-gap
    n = f'{od}/ear_liner_t{t:.2f}_gap{gap:.2f}'
    cq.exporters.export(s, n+'.stl', tolerance=0.01, angularTolerance=0.1); cq.exporters.export(s, n+'.step')
    print(n, f'wall {t:.2f} mm, ear clearance {gap:.2f}, h {RING_T:.3f}')
