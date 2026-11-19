"""(6) ring-ear loads under an 11 kN tangential tooth hit (tooth tip r88 at +y, spinning CCW).
Free body (manual inertia relief): the ears push the frame; the frame + everything on it decelerates (linear a, angular alpha);
each component's inertia load goes in at its mounts, the frame's own as body force; a 3-2-1 support carries ~0.
case 'bolts': all ear load as bearing on the bolt bores (liner gone / worst);  case 'liner': tangential part on the TPU flank, radial on the bores."""
import numpy as np, math, os
from mesh34 import *
F = 11000.0; R_HIT = 88.0; HIT_ANG = 90.0
RHO = 1.05e-9
M_RING, I_RING = 125.8e-3, 721208e-9                     # kg, kg m2
ref = [(x, y, 14.5, 6.0, 0.7) for x, y in bolt_xy()]
nt, X, T = mesh('ears2', ref, hmax=3.5)
V = tet_vol(X, T); mn = np.zeros(len(X)); np.add.at(mn, T.ravel(), np.repeat(V*RHO*1e3/10, 10))   # node masses, kg (frame only)
r = np.hypot(X[:, 0], X[:, 1])
# ---- component masses (kg) and where their inertia goes in ----
MOUNTS = {1: [(-6.72, -6.72), (6.72, 6.72), (-5.66, 5.66), (5.66, -5.66)], -1: [(-6.72, 6.72), (6.72, -6.72), (-5.66, -5.66), (5.66, 5.66)]}
XB1 = 51.4+0.05+9.15+3.5
items = []
for s in (1, -1):
    m = np.zeros(len(X), bool)
    for (y0, dz) in MOUNTS[s]:
        rr = np.hypot(X[:, 1]-y0, X[:, 2]-(14.5+dz)); m |= (np.abs(X[:, 0]-s*23.5) < 0.1) & (rr > 1.7) & (rr < 3.15)
    ra = np.hypot(X[:, 1], X[:, 2]-14.5); b = (np.abs(X[:, 0]-s*(XB1+0.02)) < 0.1) & (ra > 5.25) & (ra < 6.05)
    items += [(f'motor{s:+d}', 0.040, np.array([s*36., 0, 14.5]), np.flatnonzero(m)), (f'wheel{s:+d}', 0.012, np.array([s*56., 0, 14.5]), np.flatnonzero(b))]
bat = (np.abs(np.abs(X[:, 0])-8.75) < 0.1) & (X[:, 2] > 17.0) & (X[:, 1] > -22.5) & (X[:, 1] < 31.5)
items.append(('battery', 0.032, np.array([0, 4.2, 17.2]), np.flatnonzero(bat)))
pcb = np.zeros(len(X), bool)
for (hx, hy) in [(-16.6, 34.5), (16.6, 34.5), (-17.0, -34.5), (17.0, -34.5)]:
    pcb |= (np.abs(np.hypot(X[:, 0]-hx, X[:, 1]-hy)-1.6) < 0.1) & (X[:, 2] > 2.65) & (X[:, 2] < 6.2)
items.append(('pcb+esc+xt30+misc', 0.040, np.array([0, -5., 6.]), np.flatnonzero(pcb)))
plates = ((X[:, 2] > 28.3) | (X[:, 2] < 0.7)) & (r < 64.5) & (r > 50)
items.append(('plates', 0.0172, np.array([0, 0, 14.5]), np.flatnonzero(plates)))
for n, m, c, ids in items: print(f'  {n:18s} {m*1e3:5.1f} g on {len(ids)} nodes')
Mf = mn.sum() + sum(i[1] for i in items)
If = (mn*(r*1e-3)**2).sum() + sum(m*(c[0]**2+c[1]**2)*1e-6 for _, m, c, _ in items) + 0.6*sum(i[1] for i in items[:4])*0.014**2
Mt = Mf + M_RING; It = If + I_RING
print(f'  model: non-ring {Mf*1e3:.0f} g, Izz {If*1e9:.0f} g.mm2 | ring share of Izz {I_RING/It:.2f}')
# ---- rigid-body deceleration of the whole bot ----
th = math.radians(HIT_ANG); ph = np.array([R_HIT*math.cos(th), R_HIT*math.sin(th)])
fdir = np.array([math.sin(th), -math.cos(th)])                     # CCW velocity is (-sin, cos); force opposes it
Fv = F*fdir; Tz = (ph[0]*Fv[1]-ph[1]*Fv[0])*1e-3                 # N m
a = Fv/Mt; al = Tz/It                                              # m/s2, rad/s2
print(f'  hit: {F/1e3:.0f} kN at r{R_HIT:.0f}; bot decel {np.linalg.norm(a)/9.81:.0f} g, alpha {al:.3g} rad/s2 ({al*It/Tz*0:.0f})')
def inertial(m, c):        # inertia force (N) on a mass m at c (mm): -m (a + alpha x r)
    return -m*(a + al*np.array([-c[1], c[0]])*1e-3)
# ear forces = what the ring must push into the frame = -(sum of frame-side inertia)
Fear_tot = -(inertial(Mf, np.zeros(2)))
Tear = If*al
B = np.array(bolt_xy()); ear_f = []
for (bx, by) in B:
    ft = Fear_tot/6 + Tear/(6*(68.5e-3)**2)*np.array([-by, bx])*1e-3
    ear_f.append(ft)
ear_f = np.array(ear_f)
print('  per-ear force on the frame (N):', ', '.join(f'{a_}:{np.linalg.norm(f):.0f}' for a_, f in zip(EAR_ANG, ear_f)))
# bore nodes per bolt (lower bore + upper insert bore, outside the ring gap)
bores = []
for (bx, by) in B:
    d = np.hypot(X[:, 0]-bx, X[:, 1]-by)
    bores.append(np.flatnonzero((d < 2.45) & (d > 1.4) & ((X[:, 2] < Z_RB-0.05) | (X[:, 2] > Z_RT+0.05)) & (X[:, 2] > 3.4) & (X[:, 2] < 25.0)))
flanks = {}
for a_ in EAR_ANG:
    ca, sa = math.cos(math.radians(a_)), math.sin(math.radians(a_))
    xl = X[:, 0]*ca+X[:, 1]*sa; yl = -X[:, 0]*sa+X[:, 1]*ca
    for sg in (1, -1):
        flanks[(a_, sg)] = np.flatnonzero((np.abs(yl-sg*(EAR_W/2+1.1)) < 0.08) & (xl > EAR_RIN-0.5) & (xl < R_SK-0.2) & (X[:, 2] >= Z_RB-0.01) & (X[:, 2] <= Z_RT+0.4))
def bearing(ids, c, f):        # cosine-weighted bearing on a bore, pushed in direction f
    v = X[ids, :2]-c; w = np.maximum(0, (v@f)/np.linalg.norm(v, axis=1)/np.linalg.norm(f)) if np.linalg.norm(f) > 0 else np.zeros(len(ids))
    return ids[w > 0], np.outer(w[w > 0]/w.sum(), f) if w.sum() > 0 else np.zeros((0, 2))
rimn = np.flatnonzero((r > R_SK-0.08) & (X[:, 2] >= Z_RB-0.01) & (X[:, 2] <= Z_RT+0.01))
def run(case):
    P = np.zeros((len(X), 2))
    if case == 'rim':          # as designed: ring shifts 0.3 mm and bears on the rim arc for the linear part; the torque part on the TPU flanks
        u = Fear_tot/np.linalg.norm(Fear_tot); nr = X[rimn, :2]/r[rimn, None]
        w = np.maximum(0, -(nr@u))**2; P[rimn] += np.outer(w/w.sum(), Fear_tot)
        for k, a_ in enumerate(EAR_ANG):
            tv = np.array([-math.sin(math.radians(a_)), math.cos(math.radians(a_))]); ft = Tear/(6*68.5e-3)*tv
            ids = flanks[(a_, -1 if ft@tv > 0 else 1)]; P[ids] += ft/len(ids)
    for k, (c, f) in enumerate(zip(B, ear_f)):
        if case == 'rim': break
        a_ = EAR_ANG[k]; tv = np.array([-math.sin(math.radians(a_)), math.cos(math.radians(a_))])
        if case == 'liner':
            ftan = (f@tv)*tv; frad = f-ftan
            ids = flanks[(a_, -1 if f@tv > 0 else 1)]        # the ear pushes on the flank ahead of it
            P[ids] += ftan/len(ids); i2, ff = bearing(bores[k], c, frad); P[i2] += ff
        else:
            i2, ff = bearing(bores[k], c, f); P[i2] += ff
    for n, m, c, ids in items: P[ids] += inertial(m, c)/len(ids)
    ext = np.abs(P).sum(1) > 0
    P += -mn[:, None]*(a + al*np.c_[-X[:, 1], X[:, 0]]*1e-3)       # frame body force
    fm = mn > 0; Mn = mn[fm].sum(); In = (mn[fm]*(r[fm]**2)).sum()
    for _ in range(3):                                              # trim the frame body force so the free body balances exactly (Fx, Fy, Mz)
        res = P.sum(0); P[fm] -= np.outer(mn[fm]/Mn, res)
        mres = (X[:, 0]*P[:, 1]-X[:, 1]*P[:, 0]).sum(); P[fm] -= (mres/In)*mn[fm, None]*np.c_[-X[fm, 1], X[fm, 0]]
    res = P.sum(0); mres = (X[:, 0]*P[:, 1]-X[:, 1]*P[:, 0]).sum()
    mx = (X[:, 2]*P[:, 1]).sum(); my = -(X[:, 2]*P[:, 0]).sum()
    print(f'  [{case}] out-of-plane residual moments Mx {mx/1e3:.2f} My {my/1e3:.2f} N m')
    print(f'  [{case}] residual force {np.linalg.norm(res):.2f} N, moment {mres/1e3:.3f} N m (of {Tz:.0f})')
    # 3-2-1 support far apart on the bottom face
    A = np.argmin(np.linalg.norm(X-[0, 40, 0], axis=1)); Bn = np.argmin(np.linalg.norm(X-[0, -40, 0], axis=1)); C = np.argmin(np.linalg.norm(X-[40, 0, 0], axis=1))
    name = f'ears_{case}'
    with open(name+'.inp', 'w') as f:
        write_mesh(f, X, T)
        f.write(f'*BOUNDARY\n{A+1},1,3\n{Bn+1},1,1\n{Bn+1},3,3\n{C+1},3,3\n*STEP\n*STATIC\n*CLOAD\n')
        for i in np.flatnonzero(np.abs(P).sum(1) > 0): f.write(f"{i+1},1,{P[i,0]:.6f}\n{i+1},2,{P[i,1]:.6f}\n")
        f.write('*NODE PRINT,NSET=NALL\nRF\n*EL FILE\nS\n*NODE FILE\nU\n*END STEP\n')
    if not (os.path.exists(name+'.frd') and os.path.getsize(name+'.frd') > 1000): ccx(name)
    S = frd_block(name, 'STRESS', 6, len(X))[0]; U = frd_block(name, 'DISP', 3, len(X))[0]; vm = vonmises(S)
    np.save(name+'_vm.npy', vm); np.save(name+'_U.npy', U)
    nb = np.zeros(len(X), bool)
    for c in B: nb |= np.hypot(X[:, 0]-c[0], X[:, 1]-c[1]) < 6
    loaded = ext
    far = ~nb & ~loaded
    for k, c in enumerate(B):
        d = np.hypot(X[:, 0]-c[0], X[:, 1]-c[1]); ring_ = (d > 2.6) & (d < 6)
        print(f'    ear {EAR_ANG[k]:3d}: |F| {np.linalg.norm(ear_f[k]):5.0f} N | vM around bore (2.6-6 mm) max {vm[ring_].max():5.1f}, p95 {np.percentile(vm[ring_], 95):5.1f} MPa')
    i = int(np.argmax(np.where(far, vm, 0)))
    print(f'    away from the ears: vM max {vm[far].max():.1f} MPa at ({X[i,0]:.0f},{X[i,1]:.0f},{X[i,2]:.0f}); p99 {np.percentile(vm[far], 99):.1f} | disp max {np.linalg.norm(U, axis=1).max():.3f} mm')
for c in ('bolts', 'liner', 'rim'): run(c)
np.save('ears_X.npy', X); np.save('ears_earf.npy', ear_f)
