#!/usr/bin/env python3
"""3D calculix check of the v3 skeleton (lower+upper fused; halves are clamped by 6 through-bolts).
BC 'ring': rim nodes at the ring plane supported radially (cylindrical *TRANSFORM, dof1) + ear-notch walls fixed + bolt holes fixed
BC 'bolts': bolt holes only (conservative).
loads: centrifugal self-weight + components at 4000 rpm; impact = 800 g tangential on components (both senses).
usage: python3 fea_v3.py <E MPa> <allow MPa> <rho t/mm3> <label> [mesh_max]
"""
import sys, os, math, re, time, subprocess, numpy as np, gmsh, cadquery as cq
PFX = os.environ.get('PFX', 'v33m')
E = float(sys.argv[1]); ALLOW = float(sys.argv[2]); RHO = float(sys.argv[3]); LABEL = sys.argv[4]
HMAX = float(sys.argv[5]) if len(sys.argv) > 5 else 2.5
H = 29.0; ZC = 14.5; RING_T = 4.763; Z_RB, Z_RT = ZC-RING_T/2, ZC+RING_T/2; R_SK = 72.6   # v3.4f: ring bore clearance 0.4 radial
EAR_R = 68.5; EAR_ANG = [30, 90, 150, 210, 270, 330]; EAR_W = 10.0; EAR_RIN = 64.5; BRG_X = 60.0
w = 4000*2*math.pi/60; DECEL = 800*9.81

# mesh each half separately (they are separate printed parts clamped by bolts) and *TIE them at the split face
def mesh_half(name):
    gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)
    gmsh.model.occ.importShapes(f'v3_{name}.step'); gmsh.model.occ.synchronize()
    gmsh.option.setNumber('Mesh.MeshSizeMin', 0.7); gmsh.option.setNumber('Mesh.MeshSizeMax', HMAX)
    gmsh.option.setNumber('Mesh.ElementOrder', 2); gmsh.option.setNumber('Mesh.SecondOrderLinear', 1); gmsh.option.setNumber('Mesh.HighOrderOptimize', 0)
    for a2, a3 in ((1, 1), (6, 1), (5, 1), (6, 10), (1, 4)):
        try:
            gmsh.model.mesh.clear(); gmsh.option.setNumber('Mesh.Algorithm', a2); gmsh.option.setNumber('Mesh.Algorithm3D', a3)
            gmsh.model.mesh.generate(3); et, _, en = gmsh.model.mesh.getElements(3)
            if 11 in et: break
        except Exception as e: print('   ', name, a2, a3, 'fail', str(e)[:60])
    nt, nc, _ = gmsh.model.mesh.getNodes(); X = nc.reshape(-1, 3)
    et, _, en = gmsh.model.mesh.getElements(3); T = np.array(en[list(et).index(11)]).reshape(-1, 10)[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
    gmsh.finalize(); return nt, X, T
t0 = time.time()
gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)
vL = gmsh.model.occ.importShapes(f'{PFX}_lower.step'); vU = gmsh.model.occ.importShapes(f'{PFX}_upper.step')
gmsh.model.occ.fragment(vL, vU); gmsh.model.occ.synchronize()
print('  volumes after fragment:', len(gmsh.model.getEntities(3)))
gmsh.option.setNumber('Mesh.MeshSizeMin', 0.7); gmsh.option.setNumber('Mesh.MeshSizeMax', HMAX)
gmsh.option.setNumber('Mesh.ElementOrder', 2); gmsh.option.setNumber('Mesh.SecondOrderLinear', 1)
gmsh.option.setNumber('Mesh.Optimize', 1); gmsh.option.setNumber('Mesh.OptimizeNetgen', 1)
for a2, a3, hmin in ((1, 1, 0.7), (6, 1, 0.7), (5, 1, 0.7), (6, 10, 0.7), (1, 4, 0.7)):
    try:
        gmsh.model.mesh.clear(); gmsh.option.setNumber('Mesh.Algorithm', a2); gmsh.option.setNumber('Mesh.Algorithm3D', a3); gmsh.option.setNumber('Mesh.MeshSizeMin', hmin)
        gmsh.model.mesh.generate(3); gmsh.model.mesh.removeDuplicateNodes()
        et_, _, _ = gmsh.model.mesh.getElements(3)
        if 11 in et_: print(f'  meshed: 2D {a2} 3D {a3} hmin {hmin}'); break
    except Exception as e: print(f'  mesh {a2}/{a3}/{hmin} failed: {str(e)[:60]}')
nt, nc, _ = gmsh.model.mesh.getNodes(); X = nc.reshape(-1, 3)
et, _, en = gmsh.model.mesh.getElements(3); tets = np.array(en[list(et).index(11)]).reshape(-1, 10)[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
Pq = X[np.searchsorted(nt, tets[:, :4], sorter=np.argsort(nt))] if False else None
gmsh.finalize()
_ix = {n: i for i, n in enumerate(nt)}
_C = np.array([[X[_ix[n]] for n in t[:4]] for t in tets])
_v = np.einsum('ij,ij->i', np.cross(_C[:, 1]-_C[:, 0], _C[:, 2]-_C[:, 0]), _C[:, 3]-_C[:, 0])/6
_neg = _v < 0
tets[_neg] = tets[_neg][:, [0, 2, 1, 3, 6, 5, 4, 7, 9, 8]]          # flip inverted tets (ccx C3D10 order)
_E = np.stack([np.linalg.norm(_C[:, i]-_C[:, j], axis=1) for i, j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))], 1).max(1)
_q = 6*np.sqrt(2)*np.abs(_v)/_E**3                                   # 1 = regular tet
_bad = _q < 1e-3
print(f"  tets: {_neg.sum()} flipped, {_bad.sum()} slivers q<0.02 dropped ({_bad.mean()*100:.2f}%), min q {_q.min():.1e}")
tets = tets[~_bad]
TL = tets; TU = tets[:0]; ntL = nt; nL_el = len(tets)
# sanity: all tets positive volume
P = X[np.searchsorted(np.sort(nt), tets[:, :4])] if False else None
nid = {n: i+1 for i, n in enumerate(nt)}; IDX = {n: i for i, n in enumerate(nt)}
used = set(np.unique(tets)); keepn = np.array([n in used for n in nt]);
r = np.hypot(X[:, 0], X[:, 1]); ang = np.degrees(np.arctan2(X[:, 1], X[:, 0]))
print(f"  mesh {len(nt)} nodes, {len(tets)} C3D10 (lower {len(TL)}, upper {len(TU)}) ({time.time()-t0:.0f}s)")
bolts = [(EAR_R*math.cos(math.radians(a)), EAR_R*math.sin(math.radians(a))) for a in EAR_ANG]
near_bolt = np.zeros(len(nt), bool)
for bx, by in bolts: near_bolt |= np.hypot(X[:, 0]-bx, X[:, 1]-by) < 1.85
rim = (r > R_SK-0.08) & (X[:, 2] >= Z_RB-0.01) & (X[:, 2] <= Z_RT+0.01) & keepn
ear_wall = np.zeros(len(nt), bool); ear_sets = {}
for a in EAR_ANG:
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    xl = X[:, 0]*ca+X[:, 1]*sa; yl = -X[:, 0]*sa+X[:, 1]*ca
    m = (np.abs(np.abs(yl)-(EAR_W/2+1.1)) < 0.08) & (xl > EAR_RIN-0.5) & (xl < R_SK-0.2) & (X[:, 2] >= Z_RB-0.01) & (X[:, 2] <= Z_RT+0.4) & keepn & ~near_bolt
    ear_sets[a] = m; ear_wall |= m
# TPU 95A liner (E ~26 MPa, 0.8 mm) as an elastic foundation on the notch flanks: k = E/t per mm2, spread over the flank nodes
K_LINER = 26.0/0.8*(R_SK-0.2-EAR_RIN)*4.763*EAR_W/max(1, ear_wall.sum())
print(f"  bolt nodes {near_bolt.sum()}, rim nodes {rim.sum()}, ear-wall nodes {ear_wall.sum()}")

def sel(f): return np.flatnonzero(keepn & f)
axr = np.hypot(X[:, 1], X[:, 2]-ZC)
loads = []
MOUNTS = {1: [(-6.72, -6.72), (6.72, 6.72), (-5.66, 5.66), (5.66, -5.66)], -1: [(-6.72, 6.72), (6.72, -6.72), (-5.66, -5.66), (5.66, 5.66)]}
for s in (1, -1):
    # cantilevered motor: 4 M3 heads bear on the counterbore floors (x = +-(20.5+3)); real hole pattern; motor+wheel 47 g
    Fc = 47e-3*w*w*0.040; Fi = 47e-3*DECEL
    sel_m = np.zeros(len(nt), bool)
    for (y0, dz) in MOUNTS[s]:
        rr = np.hypot(X[:, 1]-y0, X[:, 2]-(ZC+dz))
        sel_m |= (np.abs(X[:, 0]-s*23.5) < 0.1) & (rr > 1.7) & (rr < 3.15)
    loads.append((sel(sel_m), Fc*np.array([s, 0.]), np.array([0., s]), Fi))
SHOCK = 500*9.81
# outboard bearing: rotor (~22 g) + wheel/hub/bearing (~8 g) pull outward along the motor axis, into the lip of each end-wall housing
XB1 = 51.4+0.05+9.15+3.5
for s in (1, -1):
    ra = np.hypot(X[:, 1], X[:, 2]-ZC)
    m = (np.abs(X[:, 0]-s*(XB1+0.02)) < 0.1) & (ra > 5.25) & (ra < 6.05)
    loads.append((sel(m), 30e-3*w*w*0.048*np.array([s, 0.]), np.array([0., s]), 8e-3*DECEL))
# battery 37.8 g: vertical/lateral shock -> in-plane share through the +x rib face (upper half, x=8.25, |y| 11..31.5)
loads.append((sel((np.abs(X[:, 0]-8.75) < 0.1) & (X[:, 2] > 17.0) & (((X[:, 1] > 11.0) & (X[:, 1] < 31.5)) | ((X[:, 1] > -22.5) & (X[:, 1] < -11.0)))), np.array([0., 0.]), np.array([1., 0.]), 32.0e-3*SHOCK))   # 55 mm pack on the +x rib
loads.append((sel((np.abs(X[:, 1]-32.0) < 0.1) & (np.abs(X[:, 0]) < 8.5) & (X[:, 2] > 17.2) & (X[:, 2] < 27.0)), 32.0e-3*w*w*0.0042*np.array([0, 1.]), np.array([0, 1.]), 32.0e-3*SHOCK))   # spin pull of the off-centre pack + shock into the N stop lip
# XT30 3 g on the N ledge top (z 7.2) + bay wall, ESC 6 g on the S ledge top
loads.append((sel((np.abs(X[:, 0]-20.5) < 0.1) & (X[:, 1] > 13.0) & (X[:, 1] < 34.0) & (X[:, 2] > 7.2) & (X[:, 2] < 15.5)), 3.0e-3*w*w*0.025*np.array([1., 0]), np.array([-1., 0]), 3.0e-3*SHOCK))
loads.append((sel((np.abs(X[:, 2]-7.2) < 0.1) & (X[:, 1] < -37.2) & (X[:, 1] > -39.4) & (np.abs(X[:, 0]) < 13.0)), 6.0e-3*w*w*0.0383*np.array([0, -1.]), np.array([1., 0]), 6.0e-3*SHOCK))
# switch 2.15 g -> socket outer wall (y=57.05); rx+LED 1.5 g -> S pocket outer wall (y=-58)
loads.append((sel((np.abs(X[:, 1]-57.05) < 0.1) & (X[:, 0] > -8.4) & (X[:, 0] < -1.6) & (X[:, 2] > 16)), 2.15e-3*w*w*0.051*np.array([0, 1.]), np.array([-1., 0]), 2.15e-3*SHOCK))
loads.append((sel((np.abs(X[:, 1]+58.0) < 0.1) & (np.abs(X[:, 0]) < 13.0)), 1.5e-3*w*w*0.051*np.array([0, -1.]), np.array([1., 0]), 1.5e-3*SHOCK))
# PCB 9 g hangs on the 2 tab inserts (Ø4 bores above the tab pockets)
pcb_sel = np.zeros(len(nt), bool)
for (hx, hy) in [(-16.6, 34.5), (16.6, 34.5), (-17.0, -34.5), (17.0, -34.5)]:   # rev-2: 4x M2 bores in the ledges
    pcb_sel |= (np.abs(np.hypot(X[:, 0]-hx, X[:, 1]-hy)-1.6) < 0.1) & (X[:, 2] > 2.65) & (X[:, 2] < 6.2)
loads.append((sel(pcb_sel), np.array([0., 0.]), np.array([1., 0]), 12e-3*SHOCK))
print('  load node counts', [len(l[0]) for l in loads])
for i, l in enumerate(loads):
    if len(l[0]) == 0: print('  !! empty load set', i)

def run(bc, case):
    global tets
    name = f"{LABEL}_{bc}_{case}"
    with open(name+'.inp', 'w') as f:
        f.write('*NODE\n'+''.join(f"{nid[n]},{X[i,0]:.4f},{X[i,1]:.4f},{X[i,2]:.4f}\n" for i, n in enumerate(nt)))
        f.write('*ELEMENT,TYPE=C3D10,ELSET=EALL\n'+''.join(f"{i+1},"+",".join(str(nid[n]) for n in t)+"\n" for i, t in enumerate(tets)))
        fx = np.flatnonzero(near_bolt & keepn)
        f.write('*NSET,NSET=FIX\n'+"\n".join(str(nid[nt[i]]) for i in fx)+"\n")
        if bc == 'ring':                                           # ears bear on the notch flanks through the TPU liner
            eid = len(tets)
            for a, m in ear_sets.items():
                idx = np.flatnonzero(m)
                if len(idx) == 0: continue
                ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
                f.write(f'*NSET,NSET=EAR{a}\n'+"\n".join(str(nid[nt[i]]) for i in idx)+"\n")
                f.write(f'*TRANSFORM,NSET=EAR{a},TYPE=R\n{-sa:.6f},{ca:.6f},0.,{ca:.6f},{sa:.6f},0.\n')
                f.write('*ELEMENT,TYPE=SPRING1,ELSET=ESPR\n'+"".join(f"{eid+j+1},{nid[nt[i]]}\n" for j, i in enumerate(idx))); eid += len(idx)
            f.write(f'*SPRING,ELSET=ESPR\n1\n{K_LINER:.4f}\n')
        if bc == 'ring':
            rn = np.flatnonzero(rim & ~near_bolt & ~ear_wall)
            f.write('*NSET,NSET=RIM\n'+"\n".join(str(nid[nt[i]]) for i in rn)+"\n")
            f.write('*TRANSFORM,NSET=RIM,TYPE=C\n0.,0.,0.,0.,0.,1.\n')
        f.write(f"*MATERIAL,NAME=M\n*ELASTIC\n{E},0.38\n*DENSITY\n{RHO:.4e}\n*SOLID SECTION,ELSET=EALL,MATERIAL=M\n*BOUNDARY\nFIX,1,3\n")
        if bc == 'ring': f.write("RIM,1,1\n")
        f.write(f"*STEP\n*STATIC\n*DLOAD\nEALL,CENTRIF,{w*w:.3f},0,0,0,0,0,1\n*CLOAD\n")
        for ids, fc, ut, fi in loads:
            if len(ids) == 0: continue
            ff = fc + (fi*ut if case == 'imp+' else -fi*ut if case == 'imp-' else 0)
            for i in ids: f.write(f"{nid[nt[i]]},1,{ff[0]/len(ids):.6f}\n{nid[nt[i]]},2,{ff[1]/len(ids):.6f}\n")
        f.write("*EL FILE\nS\n*NODE FILE\nU\n*END STEP\n")
    rr = subprocess.run(['ccx', '-i', name], capture_output=True, text=True)
    badel = sorted({int(m) for m in re.findall(r'determinant in element\s+(\d+)', rr.stdout)})
    if badel:
        print(f"  !! {len(badel)} elements with nonpositive jacobian -> dropping and re-running")
        keep = np.ones(len(tets), bool); keep[np.array(badel)-1] = False; tets = tets[keep]
        return run(bc, case)
    frd = open(name+'.frd').read()
    blk = lambda k: re.search(r'\s-4\s+'+k+r'.*?\n(.*?)\n\s-3', frd, re.S).group(1).splitlines()
    def full(k, nc):
        out = np.zeros((len(nt), nc))
        for l in blk(k):
            if l.startswith(' -1'): out[int(l[3:13])-1] = [float(l[13+12*i:13+12*(i+1)]) for i in range(nc)]
        return out
    S = full('STRESS', 6)
    U = full('DISP', 3)
    sx, sy, sz, sxy, syz, sxz = S.T; vm = np.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2+6*(sxy**2+syz**2+sxz**2)))
    excl = np.zeros(len(nt), bool)
    for bx, by in bolts: excl |= np.hypot(X[:, 0]-bx, X[:, 1]-by) < 3.5
    for ids, *_ in loads: excl[ids] = True
    excl |= ear_wall
    ok = keepn & ~excl
    i = int(np.argmax(np.where(ok, vm, 0))); um = np.linalg.norm(U, axis=1)
    p99 = np.percentile(vm[ok], 99)
    print(f"  {bc:5s} {case:5s}: vM max {vm[ok].max():5.1f} MPa (p99 {p99:4.1f}) at ({X[i,0]:.0f},{X[i,1]:.0f},{X[i,2]:.0f}) FoS {ALLOW/vm[ok].max():4.2f} | disp max {um.max():.2f} mm")
    np.save(name+'_vm.npy', np.where(keepn, vm, 0))
    return vm[ok].max()

worst = {}
for bc in ('ring', 'bolts'):
    worst[bc] = max(run(bc, c) for c in ('cent', 'imp+', 'imp-'))
print(f"  => worst: ring-supported FoS {ALLOW/worst['ring']:.2f}, bolts-only FoS {ALLOW/worst['bolts']:.2f} (allow {ALLOW} MPa)")
np.save(f'{LABEL}_X.npy', X)
