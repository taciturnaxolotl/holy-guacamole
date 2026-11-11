"""List the larger and taller solids of the Rev A board component model (v33m_pcbcomp.step) with their extents.
This is where the Rev A part heights in the README (XIAO shield, USB-C) come from. Reads /tmp/hg33b/ (not in this repo)."""
import cadquery as cq
M="/tmp/hg33b/holy_guacamole_v33b/step/"
s=cq.importers.importStep(M+"v33m_pcbcomp.step"); vs=s.solids().vals()
print("solids",len(vs))
rows=[]
for v in vs:
    b=v.BoundingBox(); rows.append((b.zmax,b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,v.Volume()))
for r in sorted(rows,reverse=True):
    if r[6]>0.3 or r[0]>3.5: print("ztop %5.2f zbot %5.2f x[%6.2f,%6.2f] y[%6.2f,%6.2f] vol %.1f"%(r[0],r[5],r[1],r[2],r[3],r[4],r[6]))
b=cq.Compound.makeCompound(vs).BoundingBox(); print("ALL",b.xmin,b.xmax,b.ymin,b.ymax,b.zmin,b.zmax)
