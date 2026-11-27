"""fine meshes of the printed parts for the viewer and renders (the generator's own STLs are coarser)"""
import cadquery as cq, sys
SRC = sys.argv[1] if len(sys.argv) > 1 else '../../scripts/v33m_'
for n in ('lower', 'upper', 'top', 'bot'):
    cq.exporters.export(cq.importers.importStep(f'{SRC}{n}.step'), f'{SRC}{n}fine.stl', tolerance=0.01, angularTolerance=0.05); print(n)
