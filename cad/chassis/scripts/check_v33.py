#!/usr/bin/env python3
"""mass / balance / static-overlap check of the exported v3.2 STEPs (bbox prefilter, robust booleans)."""
import os, sys, math, itertools, numpy as np, cadquery as cq
from OCP.ShapeFix import ShapeFix_Shape
PFX = os.environ.get('PFX', 'v33m'); RHO = 1.05 if PFX.endswith('m') else 1.10
names = ['lower', 'upper', 'ring', 'top', 'bot', 'liner', 'usbf', 'hubR', 'hubL', 'brgR', 'brgL', 'battery', 'switch', 'xt30', 'esc', 'rx', 'pcb', 'pcbcomp', 'ledT', 'ledB', 'motorR', 'wheelR', 'motorL', 'wheelL']
MASS = {'usbf': 1.5, 'hubR': 3.1, 'hubL': 3.1, 'brgR': 1.3, 'brgL': 1.3, 'battery': 32.0, 'switch': 2.15, 'xt30': 3.0, 'esc': 6.0, 'rx': 0.5, 'pcb': 12.0, 'pcbcomp': 0.0, 'ledT': 0.4, 'ledB': 0.4, 'motorR': 44.0, 'motorL': 44.0, 'wheelR': 3.6, 'wheelL': 3.6}
DENS = {'lower': RHO, 'upper': RHO, 'ring': 7.85, 'top': RHO, 'bot': RHO, 'rindT': 1.21, 'rindB': 1.21, 'liner': 1.21}
def fix(s):
    sf = ShapeFix_Shape(s.wrapped); sf.Perform(); return cq.Shape.cast(sf.Shape())
S = {}
mx = np.zeros(3); mt = 0
for n in names:
    s = cq.importers.importStep(f'{PFX}_{n}.step').val()
    if not s.isValid(): s = fix(s)
    S[n] = s
    m = s.Volume()/1000*DENS[n] if n in DENS else MASS[n]
    c = cq.Shape.centerOfMass(s) if n in DENS else s.Center()
    mx += m*np.array([c.x, c.y, c.z]); mt += m
    print(f'{n:8s} valid={s.isValid()} {m:6.1f} g')
mt += 20.9; com = mx/mt
print(f'TOTAL {mt:.0f} g (incl 6.5 wire + 15.3 fasteners/inserts/foam)  limit 454 -> over {mt-454:+.0f} g')
print(f'CoM x {com[0]:+.2f} y {com[1]:+.2f} -> {math.hypot(com[0], com[1])*mt/44:.1f} g trim at r44')
if '--no-overlap' in sys.argv: sys.exit()
def bbo(a, b):
    A, B = a.BoundingBox(), b.BoundingBox()
    return A.xmin < B.xmax and B.xmin < A.xmax and A.ymin < B.ymax and B.ymin < A.ymax and A.zmin < B.zmax and B.zmin < A.zmax
bad = []
for a, b in itertools.combinations(names, 2):
    if {a, b} in ({'pcb', 'pcbcomp'}, {'liner', 'ring'}, {'wheelR', 'hubR'}, {'wheelL', 'hubL'}, {'brgR', 'hubR'}, {'brgL', 'hubL'}) or not bbo(S[a], S[b]): continue
    try:
        r = S[a].intersect(S[b]); v = r.Volume()/1000 if r is not None else 0
    except Exception as e:
        v = -1
    if v > 0.005 or v < 0: bad.append((a, b, round(v, 3)))
print('overlaps:', bad if bad else 'none', '(-1 = boolean failed)')
