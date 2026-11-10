"""DC resistance of a net between two pads: rasterize copper per layer, couple layers at vias / PTH barrels, solve Laplace.
usage: python3 hardware/scripts/review/rsolve.py NET PAD_A PAD_B [I_amps]   (PCB=path overrides the board file)"""
import sys, numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity, vectorized
from kpcb import load
NET, PA, PB = sys.argv[1], sys.argv[2], sys.argv[3]; I = float(sys.argv[4]) if len(sys.argv) > 4 else 10.0
import os; D = load(os.environ.get('PCB', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'guac.kicad_pcb')))
LAY = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']; T = {'F.Cu': 70e-6, 'In1.Cu': 35e-6, 'In2.Cu': 35e-6, 'B.Cu': 70e-6}; RHO = 1.72e-8
ZL = {'F.Cu': 0.0, 'In1.Cu': 0.36e-3, 'In2.Cu': 1.24e-3, 'B.Cu': 1.6e-3}
H = 0.1  # mm
def padgeom(p):
    w, h = p['w'], p['h']
    g = box(-w/2, -h/2, w/2, h/2) if p['shape'] in ('rect', 'roundrect', 'custom', 'trapezoid') else (Point(0, 0).buffer(w/2) if p['shape'] == 'circle' else LineString([(-(w-h)/2 if w > h else 0, -(h-w)/2 if h > w else 0), ((w-h)/2 if w > h else 0, (h-w)/2 if h > w else 0)]).buffer(min(w, h)/2))
    return affinity.translate(affinity.rotate(g, -p['rot'], origin=(0, 0)), p['x'], p['y'])
geo = {L: [] for L in LAY}; vias = []; term = {}
for f in D['fp']:
    for p in f['pads']:
        if p['net'] != NET: continue
        th = any(l == '*.Cu' for l in p['layers'])
        for L in (LAY if th else [l for l in p['layers'] if l in LAY]): geo[L].append(padgeom(p))
        if th: vias.append((p['x'], p['y'], 1.5, 20e-6, 6))   # PTH barrel (approx drill)
        term[f"{f['ref']}.{p['num']}"] = (padgeom(p), th, [l for l in p['layers'] if l in LAY] if not th else LAY)
for s in D['seg']:
    if s['net'] == NET: geo[s['layer']].append(LineString([s['a'], s['b']]).buffer(s['w']/2))
for v in D['via']:
    if v['net'] == NET:
        for L in LAY: geo[L].append(Point(v['p']).buffer(v['d']/2))
        vias.append((v['p'][0], v['p'][1], v.get('drill', 0.3), 20e-6, 1))
for z in D['zone']:
    if z['net'] != NET: continue
    for L, pts in z['fills']:
        if L in geo and len(pts) > 2: geo[L].append(Polygon(pts).buffer(0))
U = {L: unary_union(g) for L, g in geo.items() if g}
allb = unary_union(list(U.values())).bounds
xs = np.arange(allb[0], allb[2]+H, H); ys = np.arange(allb[1], allb[3]+H, H); X, Y = np.meshgrid(xs, ys)
idx = {}; n = 0; masks = {}
for L, u in U.items():
    m = vectorized.contains(u, X, Y); masks[L] = m; ii = -np.ones(m.shape, int); ii[m] = np.arange(n, n+m.sum()); n += m.sum(); idx[L] = ii
rows, cols, vals = [], [], []
def add(a, b, g): rows.extend([a, b, a, b]); cols.extend([a, b, b, a]); vals.extend([g, g, -g, -g])
for L, ii in idx.items():
    g = T[L]/RHO   # sheet conductance between neighbouring square cells
    for di, dj in ((0, 1), (1, 0)):
        a = ii[:ii.shape[0]-di, :ii.shape[1]-dj]; b = ii[di:, dj:]; k = (a >= 0) & (b >= 0)
        for x, y in zip(a[k], b[k]): add(x, y, g)
LS = [L for L in LAY if L in idx]
for (vx, vy, d, tp, mult) in vias:
    j = int(round((vx-xs[0])/H)); i = int(round((vy-ys[0])/H))
    for L1, L2 in zip(LS, LS[1:]):
        a, b = idx[L1][i, j], idx[L2][i, j]
        if a >= 0 and b >= 0:
            Rv = RHO*abs(ZL[L2]-ZL[L1])/(np.pi*d*1e-3*tp)/mult
            add(a, b, 1/Rv)
G = sp.csr_matrix((vals, (rows, cols)), shape=(n, n))
def nodes(t):
    g, th, ls = term[t]; out = []
    for L in ls:
        if L in idx: m = vectorized.contains(g, X, Y) & (idx[L] >= 0); out += list(idx[L][m])
    return np.array(out)
A, B = nodes(PA), nodes(PB)
# A held at 1 V, B at 0 V (pads are solder-filled: equipotential)
fixed = np.zeros(n, bool); fixed[A] = fixed[B] = True; V = np.zeros(n); V[A] = 1.0
free = ~fixed; Gff = G[free][:, free]; rhs = -G[free][:, fixed] @ V[fixed]
V[free] = spl.spsolve(Gff.tocsc(), rhs)
Iin = (G @ V)[A].sum(); R = 1/Iin
print(f'{NET} {PA}->{PB}: R = {R*1e3:.2f} mOhm  ({n} cells) | at {I:.0f} A: drop {I*R*1e3:.0f} mV, loss {I*I*R:.2f} W')
# hotspot: local current density at I amps (A/mm width) per layer
Vs = V*I*R
for L, ii in idx.items():
    vv = np.full(ii.shape, np.nan); vv[ii >= 0] = Vs[ii[ii >= 0]]
    gy, gx = np.gradient(vv, H*1e-3); J = np.hypot(gx, gy)/RHO*T[L]   # A per m of width
    jm = np.nanmax(J); k = np.unravel_index(np.nanargmax(J), J.shape)
    print(f'  {L}: peak {jm/1000:.1f} A/mm at ({xs[k[1]]-80:.1f}, {65.5-ys[k[0]]:.1f})')
