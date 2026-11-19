"""(5) local poke on the 1.0 mm outer skin. 300 N over a 6 mm patch, normal to the surface, frame held at the 6 ring bolts.
Linear: reports peak stress, deflection under the patch, and the force at which the skin first reaches 52 MPa (first-yield)."""
import numpy as np, math, sys, os
TAG = os.environ.get('TAG', 'skin')
from mesh34 import *
F = 300.0; PATCH = 3.0; SY = 52.0
# (label, theta deg, r, z, normal angle from horizontal deg)
SITES = [('roll45_NE', 60, 70.36, 26.66, 45), ('roll45_SE', 300, 70.36, 26.66, 45),
         ('side_NE', 60, 72.65, 22.0, 5), ('topedge_NE', 60, 68.5, 28.0, 70)]
if os.environ.get('SITES') == 'fins':   # between fins (65) and on a fin (60)
    SITES = [('roll45_bay', 65, 70.36, 26.66, 45), ('topedge_bay', 65, 68.5, 28.0, 70), ('roll45_onfin', 60, 70.36, 26.66, 45)]
ref = [(r*math.cos(math.radians(t)), r*math.sin(math.radians(t)), z, 7.0, 0.45) for _, t, r, z, _ in SITES]
nt, X, T = mesh(TAG, ref)
# surface nodes = nodes on tet faces used once
fc = np.sort(np.concatenate([T[:, [0, 1, 2]], T[:, [0, 1, 3]], T[:, [0, 2, 3]], T[:, [1, 2, 3]]]), axis=1)
u, cnt = np.unique(fc, axis=0, return_counts=True); surf = np.zeros(len(X), bool); surf[np.unique(u[cnt == 1])] = True
# include mid-side nodes of surface faces
fc6 = np.concatenate([T[:, [0, 1, 2, 4, 5, 6]], T[:, [0, 1, 3, 4, 8, 7]], T[:, [0, 2, 3, 6, 9, 7]], T[:, [1, 2, 3, 5, 9, 8]]])
key = np.sort(fc6[:, :3], axis=1); _, inv, c2 = np.unique(key, axis=0, return_inverse=True, return_counts=True)
surf[np.unique(fc6[c2[inv.ravel()] == 1])] = True
fix = np.zeros(len(X), bool)
for bx, by in bolt_xy(): fix |= np.hypot(X[:, 0]-bx, X[:, 1]-by) < 1.85
res = []
for lab, th, r, z, na in SITES:
    t = math.radians(th); p = np.array([r*math.cos(t), r*math.sin(t), z])
    n = np.array([math.cos(math.radians(na))*math.cos(t), math.cos(math.radians(na))*math.sin(t), math.sin(math.radians(na))])
    d = np.linalg.norm(X-p, axis=1)
    pat = np.flatnonzero(surf & (d < PATCH) & ((X-p)@n > -1.0))
    name = f'{TAG}_{lab}'
    with open(name+'.inp', 'w') as f:
        write_mesh(f, X, T); nset(f, 'FIX', np.flatnonzero(fix))
        f.write('*BOUNDARY\nFIX,1,3\n*STEP\n*STATIC,SOLVER=ITERATIVE CHOLESKY\n*CLOAD\n')
        fv = -F*n/len(pat)
        for i in pat: f.write(''.join(f"{i+1},{k+1},{fv[k]:.6f}\n" for k in range(3)))
        f.write('*EL FILE\nS\n*NODE FILE\nU\n*END STEP\n')
    ccx(name)
    S = frd_block(name, 'STRESS', 6, len(X))[0]; U = frd_block(name, 'DISP', 3, len(X))[0]
    vm = vonmises(S); near = d < 15; out = near & (d > PATCH+1.0)
    dn = -(U[pat]@n).mean()
    i = int(np.argmax(np.where(out, vm, 0)))
    res.append((lab, len(pat), vm[near].max(), np.percentile(vm[near & (d < PATCH+1.0)], 90), vm[out].max(), dn, X[i]))
    np.save(name+'_vm.npy', vm); np.save(name+'_U.npy', U)
    print(f"{lab:15s} patch {len(pat):3d} nodes | vM under patch p90 {res[-1][3]:5.1f}  around it {vm[out].max():5.1f} MPa at r{np.hypot(*X[i,:2]):.1f} z{X[i,2]:.1f} | "
          f"dent {dn:.3f} mm | first-yield force ~{F*SY/vm[out].max():.0f} N | stiffness {F/dn/1000:.1f} N/um", flush=True)
np.save(f'{TAG}_X.npy', X)
