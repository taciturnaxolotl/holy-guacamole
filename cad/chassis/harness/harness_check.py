import json, sys, numpy as np, trimesh
from scipy.spatial import cKDTree
S = '../sim/v33/v33m_'
D = json.load(open('harness_samples.json')); W = D['wires']
END = 1.6          # mm at each end allowed to touch what it plugs into
# ---- wire vs wire ----
bad = []
tree = [cKDTree(np.array(w['pts'])) for w in W]
for a in range(len(W)):
    for b in range(a+1, len(W)):
        wa, wb = W[a], W[b]
        d, j = tree[b].query(np.array(wa['pts']))
        need = wa['r'] + wb['r'] + 0.05
        if wa['w'] or wb['w']: need = (wa['w'] or wb['w'])/2 + 0.5
        k = np.argmin(d - need)
        if d[k] < need:
            bad.append((round(need-d[k], 2), f"{wa['id']}{wa['i']} x {wb['id']}{wb['i']}", np.round(wa['pts'][k], 1).tolist()))
bad.sort(reverse=True)
print('WIRE-WIRE clashes:', len(bad))
for x in bad[:40]: print('  ', x)
# ---- wire vs solids ----
parts = ['lower', 'upper', 'battery', 'escd', 'pcb', 'pcbcomp', 'switch', 'rx', 'ledT', 'ledB', 'usbf', 'motorR', 'motorL', 'ring', 'top', 'bot']
solids = {n: trimesh.load(S+n+'.stl') for n in parts}
_pc = [g for g in solids['pcbcomp'].split(only_watertight=False) if not (g.bounds[0][0] < -19 and g.bounds[1][0] > -7.5 and g.bounds[0][1] < -29)]   # drop the LED-corner plug-zone courtyard (real plug bodies checked instead)
solids['pcbcomp'] = trimesh.util.concatenate(_pc)
def boxmesh(b): return trimesh.creation.box(bounds=[[b[0], b[2], b[4]], [b[1], b[3], b[5]]])
for p in D['plugs']:
    if p['k'] == 'box': solids[p['id']] = boxmesh(p['b'])
    elif p['k'] in ('bullet', 'sleeve'):
        if p.get('ay'): cyl = trimesh.creation.cylinder(radius=p['r'], segment=[[p['x'], p['y0'], p['z']], [p['x'], p['y1'], p['z']]])
        else: cyl = trimesh.creation.cylinder(radius=p['r'], segment=[[p['x0'], p['y'], p['z']], [p['x1'], p['y'], p['z']]])
        solids[p['id']] = cyl
    else:
        (x0, y0), (x1, y1) = p['pins']; cx, cy = (x0+x1)/2, (y0+y1)/2
        ax = abs(x1-x0) > abs(y1-y0)
        hw = (5.3, 2.8) if ax else (2.8, 5.3)
        solids[p['id']+'f'] = boxmesh([cx-hw[0], cx+hw[0], cy-hw[1], cy+hw[1], 2.5, 11.0])
        solids[p['id']+'m'] = boxmesh([cx-hw[0], cx+hw[0], cy-hw[1], cy+hw[1], 11.0, 19.8])
        for (x, y) in p['pins']:
            c = trimesh.creation.cylinder(radius=1.7, height=3.5); c.apply_translation([x, y, 19.8+1.75]); solids[p['id']+'cup'] = c if p['id']+'cup' not in solids else trimesh.util.concatenate([solids[p['id']+'cup'], c])
hits = []
for w in W:
    P = np.array(w['pts']); s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    keep = (s > END) & (s < s[-1]-END); Q = P[keep]
    rr = (w['w']/2 if w['w'] else w['r'])
    for n, m in solids.items():
        lo, hi = m.bounds[0]-rr-0.5, m.bounds[1]+rr+0.5
        sel = np.all((Q > lo) & (Q < hi), axis=1)
        if not sel.any(): continue
        Qs = Q[sel]
        sd = trimesh.proximity.signed_distance(m, Qs)            # + inside
        pen = sd + w['r']
        if n == 'pcbcomp': pen = np.where(np.linalg.norm(Qs-P[-1],axis=1) < 4.5, -1, pen)
        k = np.argmax(pen)
        if pen[k] > 0.05: hits.append((round(float(pen[k]), 2), f"{w['id']}{w['i']} in {n}", np.round(Qs[k], 1).tolist()))
hits.sort(reverse=True)
# ---- plug bodies vs frame / parts ----
pb = {k: v for k, v in solids.items() if k not in parts and not k.endswith('h')}
for k, v in pb.items():
    for n in ['lower', 'upper', 'battery', 'escd', 'motorR', 'motorL', 'switch', 'top', 'bot'] + [q for q in pb if q != k]:
        try:
            iv = v.intersection(solids[n]).volume
        except Exception: continue
        if iv > 0.02: hits.append((round(iv, 2), f'BODY {k} x {n} (mm3)', np.round(v.centroid, 1).tolist()))
hits.sort(reverse=True)
print('WIRE-SOLID clashes:', len(hits))
for x in hits[:60]: print('  ', x)

# ---- U5 clearance (board review: >= 2 mm from any harness item to the H3LIS331DL courtyard) ----
u5 = trimesh.creation.box(bounds=[[-6.35, -19.47, 2.5], [-2.35, -15.47, 3.5]])
worst = min(((float(np.min(np.linalg.norm(np.array(w['pts']) - u5.nearest.on_surface(np.array(w['pts']))[0], axis=1)) - (w['w']/2 if w['w'] else w['r'])), w['id']+str(w['i'])) for w in W))
print('U5 clearance: %.2f mm (%s)' % worst)
