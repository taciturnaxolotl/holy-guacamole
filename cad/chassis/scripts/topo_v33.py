#!/usr/bin/env python3
"""v3 2D topology optimization of the melty skeleton plan view.
- SIMP + density filter + Heaviside projection (beta continuation) -> crisp 0/1 with min member size ~2*rmin
- real load path: nylon rim bears radially on the steel ring ID all the way round (radial springs on rim nodes),
  ring ears key the skeleton tangentially at 6 places (fully fixed pads)
- multi-load: centrifugal, centrifugal + impact (cw), centrifugal + impact (ccw); minimize summed compliance
usage: python3 topo_v3.py [volfrac] [res_mm]
"""
import sys, math, time, json
import numpy as np
from scipy.sparse import coo_matrix, csr_matrix, diags
from scipy.sparse.linalg import splu
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

VOLFRAC = float(sys.argv[1]) if len(sys.argv) > 1 else 0.22
RES = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
R_SK = 72.7; RIM = 2.0                     # skeleton OD (bears on ring ID 78), passive rim band
EAR_R = 68.5; EAR_ANG = [30, 90, 150, 210, 270, 330]   # ring ears / bolt positions (bolt at r=76)
RMIN = 1.6                                  # filter radius mm -> min member ~3 mm
RPM = 4000; w = RPM*2*math.pi/60; DECEL = 800*9.81

N = int(math.ceil(2*R_SK/RES)); nelx = nely = N
xs = (np.arange(N)+0.5)*RES - R_SK
EX, EY = np.meshgrid(xs, xs, indexing='ij'); ER = np.hypot(EX, EY)
inb = ER <= R_SK

# ---------- regions (plan view, v2 dimensions) ----------
def rect(x0, x1, y0, y1): return (EX >= x0) & (EX <= x1) & (EY >= y0) & (EY <= y1)
void = np.zeros_like(inb)
void |= rect(-20.5, 20.5, -39.5, 39.5)                      # central bay (symmetric): PCB, battery on ledges, ESC across the S end, XT30 across the N end
void |= rect(-8.4, -1.6, 43.95, 57.05)                       # N: vertical switch socket (hex key from the top)
void |= rect(0.7, 12.7, 48.0, 58.0)                          # N: USB-C cable chimney (plug runs under the XT30 at z<7)
void |= rect(-13, 13, -58, -43.5)                           # S: receiver + heading LED + trim
for s in (1, -1):
    lo, hi = sorted((s*26, s*50.5)); void |= rect(lo, hi, -15.5, 15.5)    # can bore (real PBB2822: can to 51.4)
    lo, hi = sorted((s*50.4, s*62.9)); void |= rect(lo, hi, -23.5, 23.5)    # wheel well (Ø39x9 wheel 51.4..60.4)
void &= inb
from scipy.ndimage import binary_dilation, distance_transform_edt
solid = binary_dilation(void, iterations=int(round(2.0/RES))) & ~void & inb      # 2 mm pocket skins
solid |= (ER >= R_SK-RIM) & inb                                                     # rim band
for s in (1, -1):
    lo, hi = sorted((s*21, s*26)); solid |= rect(lo, hi, -18.5, 18.5) & ~void        # stator mount wall (motor hangs off this)
for a in EAR_ANG:
    bx, by = EAR_R*math.cos(math.radians(a)), EAR_R*math.sin(math.radians(a))
    solid |= (np.hypot(EX-bx, EY-by) <= 5.0) & inb                                   # ear pad / boss
for bx, by in [(-24.75, 24.0), (24.5, -24.0)]: solid |= (np.hypot(EX-bx, EY-by) <= 4.5) & inb   # PCB tab screw bosses (M3 insert)
solid &= ~void
design = inb & ~void & ~solid
print(f"grid {N}x{N} @ {RES} mm: design {design.sum()} el ({design.sum()*RES**2:.0f} mm²), passive {solid.sum()*RES**2:.0f} mm², volfrac {VOLFRAC}")

# ---------- FE (Q4 plane stress, unit thickness, E=1) ----------
nu = 0.38; penal = 3.0; Emin = 1e-6
k = np.array([1/2-nu/6, 1/8+nu/8, -1/4-nu/12, -1/8+3*nu/8, -1/4+nu/12, -1/8-nu/8, nu/6, 1/8-3*nu/8])
KE = 1/(1-nu**2)*np.array([
 [k[0],k[1],k[2],k[3],k[4],k[5],k[6],k[7]],[k[1],k[0],k[7],k[6],k[5],k[4],k[3],k[2]],
 [k[2],k[7],k[0],k[5],k[6],k[3],k[4],k[1]],[k[3],k[6],k[5],k[0],k[1],k[2],k[7],k[4]],
 [k[4],k[5],k[6],k[1],k[0],k[7],k[2],k[3]],[k[5],k[4],k[3],k[2],k[7],k[0],k[1],k[6]],
 [k[6],k[3],k[4],k[7],k[2],k[1],k[0],k[5]],[k[7],k[2],k[1],k[4],k[3],k[6],k[5],k[0]]])
nidx = lambda i, j: i*(N+1)+j
I, J = np.meshgrid(np.arange(N), np.arange(N), indexing='ij'); I = I.ravel(); J = J.ravel()
n1, n2, n3, n4 = nidx(I, J), nidx(I+1, J), nidx(I+1, J+1), nidx(I, J+1)
edof = np.stack([2*n1, 2*n1+1, 2*n2, 2*n2+1, 2*n3, 2*n3+1, 2*n4, 2*n4+1], 1)
ndof = 2*(N+1)**2
iK = np.repeat(edof, 8, 1).ravel(); jK = np.tile(edof, 8).ravel()
NXg, NYg = np.meshgrid(np.arange(N+1)*RES-R_SK, np.arange(N+1)*RES-R_SK, indexing='ij')
NX, NY = NXg.ravel(), NYg.ravel(); NR = np.hypot(NX, NY)
# nodes that belong to at least one in-body element
used = np.zeros(ndof//2, bool); used[edof[inb.ravel()][:, ::2]//2] = True
# ear pads: fully fixed (ring ears key the skeleton)
fixed_nodes = np.zeros(ndof//2, bool)
for a in EAR_ANG:
    bx, by = EAR_R*math.cos(math.radians(a)), EAR_R*math.sin(math.radians(a))
    fixed_nodes |= (np.hypot(NX-bx, NY-by) <= 2.0)
fixed_nodes &= used
fixdof = np.concatenate([2*np.flatnonzero(fixed_nodes), 2*np.flatnonzero(fixed_nodes)+1])
# radial springs on rim nodes (rim bears on ring ID). stiffness ~ local nylon->steel contact, large vs E=1
rim_nodes = np.flatnonzero(used & (NR >= R_SK-RES*1.2) & ~fixed_nodes)
ksp = 5.0
nr = np.stack([NX[rim_nodes], NY[rim_nodes]], 1)/NR[rim_nodes, None]
si, sj, sv = [], [], []
for a_, b_ in ((0, 0), (0, 1), (1, 0), (1, 1)):
    si.append(2*rim_nodes+a_); sj.append(2*rim_nodes+b_); sv.append(ksp*nr[:, a_]*nr[:, b_])
Ksp = coo_matrix((np.concatenate(sv), (np.concatenate(si), np.concatenate(sj))), shape=(ndof, ndof)).tocsc()
# drop dofs of nodes not in the body
keep = np.ones(ndof, bool); keep[fixdof] = False
unused = np.flatnonzero(~used); keep[2*unused] = False; keep[2*unused+1] = False
free = np.flatnonzero(keep)
print(f"fixed nodes {fixed_nodes.sum()}, rim spring nodes {len(rim_nodes)}, free dofs {len(free)}")

# ---------- loads (N, unit thickness -> scaled consistently; only relative magnitudes matter) ----------
solid_node = np.zeros(ndof//2, bool); solid_node[edof[solid.ravel()][:, ::2]//2] = True   # nodes touching passive material
def nodes_in(x0, x1, y0, y1): return np.flatnonzero(solid_node & (NX >= x0-1e-9) & (NX <= x1+1e-9) & (NY >= y0-1e-9) & (NY <= y1+1e-9))
comps = []   # (node ids, centrifugal vec, impact unit tangent, impact mag)
for s in (1, -1):
    # cantilevered hub motor: 4 M3 heads pull on the inner face of the stator wall (x=+-21); motor+wheel 47 g, CoM ~x=40
    Fc = 47e-3*w*w*0.040; Fi = 47e-3*DECEL
    comps.append((nodes_in(min(s*21-RES*1.1, s*21+RES*1.1), max(s*21-RES*1.1, s*21+RES*1.1), -10, 10), Fc*np.array([s, 0.]), np.array([0, s]), Fi))
comps.append((nodes_in(-20.5, 20.5, 39.5-RES*1.1, 39.5+RES*1.1), 4e-3*w*w*0.036*np.array([0, 1.]), np.array([-1, 0.]), 30e-3*DECEL))   # XT30 at the N end (+ bay inertia share)
comps.append((nodes_in(-20.5, 20.5, -39.5-RES*1.1, -39.5+RES*1.1), 6e-3*w*w*0.036*np.array([0, -1.]), np.array([1, 0.]), 30e-3*DECEL))  # ESC at the S end
comps.append((nodes_in(-8.4, -1.6, 57.05-RES*1.1, 57.05+RES*1.1), 3e-3*w*w*0.050*np.array([0, 1.]), np.array([-1, 0.]), 3e-3*DECEL))            # switch
comps.append((nodes_in(-13, 13, -58-RES*1.1, -58+RES*1.1), 3e-3*w*w*0.050*np.array([0, -1.]), np.array([1, 0.]), 3e-3*DECEL))          # rx + LED + trim
for c in comps: assert len(c[0]) > 0, 'empty load set'
print('load node counts', [len(c[0]) for c in comps])
def build(case):
    F = np.zeros(ndof)
    for ids, fc, ut, fi in comps:
        f = fc.copy()
        if case == 1: f = f + fi*ut
        if case == 2: f = f - fi*ut
        F[2*ids] += f[0]/len(ids); F[2*ids+1] += f[1]/len(ids)
    return F
Fs = [build(0), build(1), build(2)]
case_w = [1.0, 1.0, 1.0]

# ---------- density filter matrix ----------
r = int(math.ceil(RMIN/RES)); rows = []; cols = []; vals = []
ii, jj = np.meshgrid(np.arange(N), np.arange(N), indexing='ij'); ii = ii.ravel(); jj = jj.ravel()
for di in range(-r, r+1):
    for dj in range(-r, r+1):
        d = math.hypot(di, dj)*RES
        if d >= RMIN: continue
        i2 = ii+di; j2 = jj+dj; ok = (i2 >= 0) & (i2 < N) & (j2 >= 0) & (j2 < N)
        rows.append((ii*N+jj)[ok]); cols.append((i2*N+j2)[ok]); vals.append(np.full(ok.sum(), RMIN-d))
Hm = csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N*N, N*N))
inb_f = inb.ravel().astype(float)
Hm = Hm.multiply(inb_f[None, :]).tocsr()         # only filter over body
Hs = np.asarray(Hm.sum(1)).ravel(); Hs[Hs == 0] = 1

d_f = design.ravel(); s_f = solid.ravel(); v_f = void.ravel(); o_f = ~inb.ravel()
x = np.where(d_f, VOLFRAC, 0.0); x[s_f] = 1.0
beta = 1.0; eta = 0.5
def proj(xt, beta): return (np.tanh(beta*eta)+np.tanh(beta*(xt-eta)))/(np.tanh(beta*eta)+np.tanh(beta*(1-eta)))
def dproj(xt, beta): return beta*(1-np.tanh(beta*(xt-eta))**2)/(np.tanh(beta*eta)+np.tanh(beta*(1-eta)))

# MMA would be nicer; OC with projection works fine with moderate moves
loop = 0; hist = []; t0 = time.time()
while loop < 200:
    loop += 1
    xt = (Hm @ x)/Hs
    xp = proj(xt, beta); xp[s_f] = 1.0; xp[v_f | o_f] = 0.0
    Ee = Emin + xp**penal*(1-Emin); Ee[o_f] = 0.0; Ee[v_f] = Emin*1e-3
    K = coo_matrix(((KE.ravel()[None, :]*Ee[:, None]).ravel(), (iK, jK)), shape=(ndof, ndof)).tocsc() + Ksp
    lu = splu(K[free][:, free].tocsc())
    c = 0.0; dc = np.zeros(N*N)
    for F, cw in zip(Fs, case_w):
        U = np.zeros(ndof); U[free] = lu.solve(F[free])
        ce = np.einsum('ij,jk,ik->i', U[edof], KE, U[edof])
        c += cw*(Ee*ce).sum()
        dc += -cw*penal*xp**(penal-1)*(1-Emin)*ce
    dc = dc*dproj(xt, beta); dc = (Hm.T @ (dc/Hs))
    dv = (Hm.T @ (dproj(xt, beta)/Hs))
    dc[~d_f] = 0; dv[~d_f] = 0
    # OC on design elements; volume measured on projected densities
    l1, l2, move = 1e-12, 1e12, 0.1; xold = x.copy()
    while (l2-l1)/(l1+l2) > 1e-4:
        lm = math.sqrt(l1*l2)
        xn = x.copy()
        B = np.sqrt(np.maximum(1e-30, -dc/np.maximum(1e-30, dv)/lm))
        xn[d_f] = np.clip(x[d_f]*B[d_f], np.maximum(0, x[d_f]-move), np.minimum(1, x[d_f]+move))
        vol = proj((Hm @ xn)/Hs, beta)[d_f].mean()
        if vol > VOLFRAC: l1 = lm
        else: l2 = lm
    x = xn; ch = np.abs(x-xold)[d_f].max()
    grey = np.mean(4*xp[d_f]*(1-xp[d_f]))
    hist.append(c)
    if loop % 10 == 0 or loop == 1:
        print(f"it {loop:3d} beta {beta:4.0f} c {c:.4e} vol {xp[d_f].mean():.3f} grey {grey:.3f} ch {ch:.3f}  ({time.time()-t0:.0f}s)")
    if (loop % 25 == 0 or ch < 0.01) and beta < 32: beta *= 2
    elif beta >= 32 and ch < 0.01: break
xt = (Hm @ x)/Hs; xp = proj(xt, beta); xp[s_f] = 1; xp[v_f | o_f] = 0
X2 = xp.reshape(N, N)
np.savez(f'topo_v33_{VOLFRAC}.npz', x=X2, res=RES, R=R_SK, solid=solid, void=void, inb=inb)
print(f"done {loop} its, compliance {c:.4e}, grey {np.mean(4*xp[d_f]*(1-xp[d_f])):.3f}")

fig, ax = plt.subplots(figsize=(8, 8))
img = np.ones((N, N, 3)); g = 1-X2; img[..., 0] = g; img[..., 1] = g; img[..., 2] = g
img[void] = [0.85, 0.92, 1.0]; img[solid] = [0.85, 0.48, 0.17]; img[~inb] = 1
ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=[-R_SK, R_SK, -R_SK, R_SK])
ax.add_patch(plt.Circle((0, 0), 84, fill=False, color='gray', lw=6, alpha=.5))
for a in EAR_ANG: ax.plot(EAR_R*math.cos(math.radians(a)), EAR_R*math.sin(math.radians(a)), 'r.', ms=9)
ax.set_title(f'v3.3 topopt: rim bears on ring, ears key tangentially; 3 load cases; volfrac {VOLFRAC}\nblack=optimized members, orange=fixed skins/walls/rim, blue=pockets', fontsize=10)
ax.set_aspect('equal'); plt.savefig(f'topo_v33_{VOLFRAC}.png', dpi=120, bbox_inches='tight')
