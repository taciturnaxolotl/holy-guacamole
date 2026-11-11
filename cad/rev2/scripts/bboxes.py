"""Print the bounding box of each named v33 rev B part: python scripts/bboxes.py lower upper bot ...
Reads v33m_<part>.step from /tmp/hg33b/ (not in this repo)."""
import cadquery as cq, sys
M="/tmp/hg33b/holy_guacamole_v33b/step/"   # v33 rev B
for n in sys.argv[1:]:
    s=cq.importers.importStep(M+f"v33m_{n}.step"); vs=s.solids().vals()
    b=s.val().BoundingBox() if len(vs)==1 else cq.Compound.makeCompound(vs).BoundingBox()
    print(f"{n:9s} solids={len(vs):3d} x[{b.xmin:8.2f},{b.xmax:8.2f}] y[{b.ymin:8.2f},{b.ymax:8.2f}] z[{b.zmin:6.2f},{b.zmax:6.2f}]")
