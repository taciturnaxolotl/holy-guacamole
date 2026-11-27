"""Cut files for the flat chassis parts: the top face of each STEP in ../chassis/step, written as a 1:1 DXF in mm.

usage (from cad/fab/):  uv run --with cadquery-ocp --with ezdxf python export_dxf.py
then:                   uv run --with ezdxf --with shapely --with matplotlib python check_dxf.py dxf/*.dxf

Lines, arcs and circles are written as such. A contour made only of straight segments (the ring, which the chassis
generator builds as a polygon) is rebuilt: runs of vertices that lie on one circle (to 2 um) become true ARCs, a loop
that is all one circle becomes a CIRCLE, and what is left stays as lines. The ring's OD otherwise goes out as ~10 mm
chords (0.16 mm flats) and its bolt holes as 32-gons.
Coordinates are the chassis frame (origin on the spin axis, +Y = N), so the files line up with each other.
"""
import sys, math
import ezdxf
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_WIRE, TopAbs_EDGE
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.GeomAbs import GeomAbs_Plane, GeomAbs_Line, GeomAbs_Circle
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.TopoDS import TopoDS
import os
HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = {   # STEP in ../chassis/step -> DXF in dxf/
    "v33m_ring.step": "ring_AR550_4.76mm.dxf",
    "v33m_top.step": "plate_top_0.8mm.dxf",
    "v33m_bot.step": "plate_bottom_0.8mm.dxf",
}


def _circle3(a, b, c):
    (x1, y1), (x2, y2), (x3, y3) = a, b, c
    d = 2*(x1*(y2-y3) + x2*(y3-y1) + x3*(y1-y2))
    if abs(d) < 1e-12: return None
    ux = ((x1*x1+y1*y1)*(y2-y3) + (x2*x2+y2*y2)*(y3-y1) + (x3*x3+y3*y3)*(y1-y2))/d
    uy = ((x1*x1+y1*y1)*(x3-x2) + (x2*x2+y2*y2)*(x1-x3) + (x3*x3+y3*y3)*(x2-x1))/d
    return (ux, uy, math.hypot(x1-ux, y1-uy))


def emit_polygon(msp, pts, n, tol=0.002, rmax=500.0):
    """closed polygon -> ARC / CIRCLE / LINE entities. Runs of >= 4 vertices on one circle become an arc."""
    m = len(pts)
    c = _circle3(pts[0], pts[m//3], pts[2*m//3])
    if c and c[2] < rmax and all(abs(math.hypot(x-c[0], y-c[1]) - c[2]) < tol for x, y in pts):
        msp.add_circle((c[0], c[1]), c[2]); n['circle'] += 1; return
    on = lambda c, q: abs(math.hypot(q[0]-c[0], q[1]-c[1]) - c[2]) < tol
    # start at a vertex where the curvature changes, so no run wraps past index 0
    def fits(i):
        c = _circle3(pts[i-1], pts[i], pts[(i+1) % m]); return c if (c and c[2] < rmax) else None
    start = 0
    for i in range(m):
        a, b = fits(i), fits((i+1) % m)
        if not (a and b and on(a, pts[(i+2) % m])): start = (i+1) % m; break
    P = pts[start:] + pts[:start]; k = 0
    while k < m:
        j = k + 2
        c = _circle3(P[k], P[(k+1) % m], P[j % m]) if j < m + 1 else None
        if c and c[2] < rmax:
            while j + 1 <= m and on(c, P[(j+1) % m]): j += 1
        if c and c[2] < rmax and j - k >= 3:
            p0, pm, p1 = P[k], P[(k+j)//2 % m], P[j % m]
            c = _circle3(p0, pm, p1) or c                         # exact through both ends, so the lines meet the arc
            a0 = math.degrees(math.atan2(p0[1]-c[1], p0[0]-c[0])); a1 = math.degrees(math.atan2(p1[1]-c[1], p1[0]-c[0]))
            am = math.degrees(math.atan2(pm[1]-c[1], pm[0]-c[0]))
            ccw = (am - a0) % 360 < (a1 - a0) % 360            # the CCW sweep a0 -> a1 passes through the middle vertex
            msp.add_arc((c[0], c[1]), c[2], a0 if ccw else a1, a1 if ccw else a0); n['arc'] += 1; k = j
        else:
            msp.add_line(P[k], P[(k+1) % m]); n['line'] += 1; k += 1


def export(src, dst):
    r = STEPControl_Reader(); r.ReadFile(src); r.TransferRoots(); shape = r.OneShape()
    best = None; e = TopExp_Explorer(shape, TopAbs_FACE)
    while e.More():
        f = TopoDS.Face(e.Current()); a = BRepAdaptor_Surface(f)
        if a.GetType() == GeomAbs_Plane and abs(a.Plane().Axis().Direction().Z()) > 1 - 1e-6:
            g = GProp_GProps(); BRepGProp.SurfaceProperties_s(f, g)
            z = a.Plane().Location().Z()
            if best is None or g.Mass() > best[0] + 1e-6 or (abs(g.Mass() - best[0]) < 1e-6 and z > best[1]): best = (g.Mass(), z, f)
        e.Next()
    area, z, face = best
    doc = ezdxf.new('R2010', setup=False); doc.units = ezdxf.units.MM; doc.header['$INSUNITS'] = 4
    msp = doc.modelspace()
    n = {'line': 0, 'arc': 0, 'circle': 0, 'spline': 0}; loops = 0
    w = TopExp_Explorer(face, TopAbs_WIRE)
    while w.More():
        loops += 1
        ex = BRepTools_WireExplorer(TopoDS.Wire(w.Current()))
        # a loop of straight segments (the ring is a fine polygon in its source) goes out as one closed polyline
        pts, all_lines = [], True
        probe = BRepTools_WireExplorer(TopoDS.Wire(w.Current()))
        while probe.More():
            c = BRepAdaptor_Curve(probe.Current())
            if c.GetType() != GeomAbs_Line: all_lines = False
            pts.append(c.Value(c.FirstParameter()) if probe.Orientation() == 0 else c.Value(c.LastParameter()))
            probe.Next()
        if all_lines and len(pts) > 8:
            emit_polygon(msp, [(p.X(), p.Y()) for p in pts], n)
            w.Next(); continue
        while ex.More():
            edge = ex.Current(); c = BRepAdaptor_Curve(edge); t0, t1 = c.FirstParameter(), c.LastParameter()
            p0, p1 = c.Value(t0), c.Value(t1)
            if c.GetType() == GeomAbs_Line:
                msp.add_line((p0.X(), p0.Y()), (p1.X(), p1.Y())); n['line'] += 1
            elif c.GetType() == GeomAbs_Circle:
                ci = c.Circle(); ctr = ci.Location(); R = ci.Radius()
                if abs((t1 - t0) - 2 * math.pi) < 1e-7:
                    msp.add_circle((ctr.X(), ctr.Y()), R); n['circle'] += 1
                else:
                    a0 = math.degrees(math.atan2(p0.Y() - ctr.Y(), p0.X() - ctr.X())); a1 = math.degrees(math.atan2(p1.Y() - ctr.Y(), p1.X() - ctr.X()))
                    if ci.Axis().Direction().Z() < 0: a0, a1 = a1, a0
                    msp.add_arc((ctr.X(), ctr.Y()), R, a0, a1); n['arc'] += 1
            else:
                d = GCPnts_QuasiUniformDeflection(c, 0.005, t0, t1)
                msp.add_lwpolyline([(d.Value(i).X(), d.Value(i).Y()) for i in range(1, d.NbPoints() + 1)]); n['spline'] += 1
            ex.Next()
        w.Next()
    doc.saveas(dst)
    print('%s: top face z %.2f, %.1f mm2, %d contours, %s' % (os.path.basename(dst), z, area, loops, {k: v for k, v in n.items() if v}))


if __name__ == "__main__":
    os.makedirs(os.path.join(HERE, "dxf"), exist_ok=True)
    for src, dst in PARTS.items():
        export(os.path.join(HERE, "..", "chassis", "step", src), os.path.join(HERE, "dxf", dst))
