"""Planar sections of v33 rev B lower/upper/bot/top (from the mjf STLs that concept_v33 exports with the STEPs).
Writes sections/v33b_z*.dxf (layer per part), .png, and solid_<part>_z*.wkt (shapely) used by build_rev2.py."""
import trimesh, ezdxf, sys, os, numpy as np
from shapely.geometry import box
from shapely.ops import unary_union
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
SRC = "/tmp/hg33b/holy_guacamole_v33b/step/"   # v33 rev B (read-only)
M = "/tmp/hg33b_work/"                          # tessellated copies (made here if missing)
import cadquery as cq
os.makedirs(M, exist_ok=True)
for n in ("lower", "upper", "bot", "top"):
    if not os.path.exists(M + f"v33b_{n}.stl"):
        cq.exporters.export(cq.importers.importStep(SRC + f"v33m_{n}.step"), M + f"v33b_{n}.stl", tolerance=0.02, angularTolerance=0.1)
os.makedirs("sections", exist_ok=True)
NAMES = ("lower", "upper", "bot", "top")
mesh = {n: trimesh.load(M + f"v33b_{n}.stl") for n in NAMES}
WIN = box(-45, -75, 45, 75)
COL = {"lower": "#d97a2b", "upper": "#e8a15c", "bot": "#2e343d", "top": "#2e343d"}
def section(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None: return None
    p2 = s.to_2D(to_2D=np.eye(4))[0] if hasattr(s, "to_2D") else s.to_planar(to_2D=np.eye(4))[0]
    return unary_union([p.buffer(0) for p in p2.polygons_full])
ZS = [float(a) for a in sys.argv[1:]] or [0.1, 0.45, 0.75, 1.35, 2.2, 3.0, 4.5, 6.0, 7.0, 7.25, 7.5, 10.0, 14.0, 17.5, 20.0, 25.0, 26.0, 27.5, 28.8]
for z in ZS:
    geo = {}
    for n, m in mesh.items():
        if m.bounds[0][2] < z < m.bounds[1][2]:
            g = section(m, z)
            if g is not None: geo[n] = g
    doc = ezdxf.new("R2000"); doc.units = 4; msp = doc.modelspace()
    fig, ax = plt.subplots(figsize=(6, 10))
    for n, g in geo.items():
        doc.layers.add(n)
        open(f"sections/solid_{n}_z{z:+06.2f}.wkt", "w").write(g.wkt)
        g = g.intersection(WIN)
        for p in getattr(g, "geoms", [g]):
            if p.is_empty or p.geom_type != "Polygon": continue
            for r in [p.exterior] + list(p.interiors):
                msp.add_lwpolyline(list(r.coords), close=True, dxfattribs={"layer": n})
            ax.fill(*p.exterior.xy, color=COL[n], alpha=0.75, lw=0)
            for h in p.interiors: ax.fill(*h.xy, color="white", lw=0)
    doc.saveas(f"sections/v33b_z{z:+06.2f}.dxf")
    ax.plot(*box(-20.5, -39.5, 20.5, 39.5).exterior.xy, "k--", lw=0.6)
    ax.plot(*box(-20, -38, 20, 38).exterior.xy, "g-", lw=0.8)
    ax.set_xlim(-45, 45); ax.set_ylim(-75, 75); ax.set_aspect("equal"); ax.grid(lw=0.3)
    ax.set_xticks(range(-45, 46, 5)); ax.set_yticks(range(-75, 76, 5)); ax.tick_params(labelsize=6)
    ax.set_title(f"v33 z={z} ({', '.join(geo)}); dashed=BAY, green=40x76", fontsize=8)
    fig.savefig(f"sections/v33b_z{z:+06.2f}.png", dpi=70, bbox_inches="tight"); plt.close(fig)
    print("z", z, {n: round(g.intersection(WIN).area, 1) for n, g in geo.items()}, flush=True)
