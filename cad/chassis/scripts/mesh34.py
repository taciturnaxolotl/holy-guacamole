"""shared mesher for the v3.4e structural sims: fused lower+upper (bonded at the split), C3D10, cached.
mesh(tag, refine=[(x,y,z,r,h), ...]) -> nt, X, tets (ccx node order), plus helpers to write/read ccx."""
import gmsh, numpy as np, os, re, subprocess, math, time
PFX = os.environ.get('PFX', 'v33m'); HMAX = 2.5
H = 29.0; ZC = 14.5; RING_T = 4.763; Z_RB, Z_RT = ZC-RING_T/2, ZC+RING_T/2; R_SK = 72.6
EAR_R = 68.5; EAR_ANG = [30, 90, 150, 210, 270, 330]; EAR_W = 10.0; EAR_RIN = 64.5

def mesh(tag, refine=(), hmax=None):
    global HMAX
    if hmax: HMAX = hmax
    cache = f'mesh34_{tag}.npz'
    if os.path.exists(cache):
        d = np.load(cache); return d['nt'], d['X'], d['T']
    t0 = time.time(); gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)
    vL = gmsh.model.occ.importShapes(f'{PFX}_lower.step'); vU = gmsh.model.occ.importShapes(f'{PFX}_upper.step')
    gmsh.model.occ.fragment(vL, vU); gmsh.model.occ.synchronize()
    if refine:
        fs = []
        for (x, y, z, r, h) in refine:
            f = gmsh.model.mesh.field.add('Ball'); fs.append(f)
            for k, v in (('XCenter', x), ('YCenter', y), ('ZCenter', z), ('Radius', r), ('Thickness', r), ('VIn', h), ('VOut', HMAX)):
                gmsh.model.mesh.field.setNumber(f, k, v)
        fm = gmsh.model.mesh.field.add('Min'); gmsh.model.mesh.field.setNumbers(fm, 'FieldsList', fs)
        gmsh.model.mesh.field.setAsBackgroundMesh(fm)
    gmsh.option.setNumber('Mesh.MeshSizeMax', HMAX)
    gmsh.option.setNumber('Mesh.ElementOrder', 2); gmsh.option.setNumber('Mesh.SecondOrderLinear', 1)
    gmsh.option.setNumber('Mesh.Optimize', 1); gmsh.option.setNumber('Mesh.OptimizeNetgen', 1)
    for a2, a3 in ((1, 1), (6, 1), (5, 1), (6, 10), (1, 4)):
        try:
            gmsh.model.mesh.clear(); gmsh.option.setNumber('Mesh.Algorithm', a2); gmsh.option.setNumber('Mesh.Algorithm3D', a3)
            gmsh.option.setNumber('Mesh.MeshSizeMin', 0.4 if refine else 0.7)
            gmsh.model.mesh.generate(3); gmsh.model.mesh.removeDuplicateNodes()
            if 11 in gmsh.model.mesh.getElements(3)[0]: print(f'  meshed 2D {a2} 3D {a3}'); break
        except Exception as e: print(f'  mesh {a2}/{a3} failed: {str(e)[:60]}')
    nt, nc, _ = gmsh.model.mesh.getNodes(); X = nc.reshape(-1, 3)
    et, _, en = gmsh.model.mesh.getElements(3); T = np.array(en[list(et).index(11)]).reshape(-1, 10)[:, [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]]
    gmsh.finalize()
    ix = np.searchsorted(nt, T, sorter=np.argsort(nt)); ix = np.argsort(nt)[ix]; T = ix          # -> 0-based node indices
    C = X[T[:, :4]]
    v = np.einsum('ij,ij->i', np.cross(C[:, 1]-C[:, 0], C[:, 2]-C[:, 0]), C[:, 3]-C[:, 0])/6
    T[v < 0] = T[v < 0][:, [0, 2, 1, 3, 6, 5, 4, 7, 9, 8]]
    E = np.stack([np.linalg.norm(C[:, i]-C[:, j], axis=1) for i, j in ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))], 1).max(1)
    q = 6*np.sqrt(2)*np.abs(v)/E**3; T = T[q >= 1e-3]
    used = np.unique(T); remap = -np.ones(len(X), int); remap[used] = np.arange(len(used))
    X = X[used]; T = remap[T]; nt = np.arange(len(X))
    np.savez(cache, nt=nt, X=X, T=T)
    print(f'  mesh {tag}: {len(X)} nodes, {len(T)} C3D10, dropped {np.sum(q < 1e-3)} slivers ({time.time()-t0:.0f}s)')
    return nt, X, T

def tet_vol(X, T):
    C = X[T[:, :4]]; return np.abs(np.einsum('ij,ij->i', np.cross(C[:, 1]-C[:, 0], C[:, 2]-C[:, 0]), C[:, 3]-C[:, 0]))/6

def bolt_xy():
    return [(EAR_R*math.cos(math.radians(a)), EAR_R*math.sin(math.radians(a))) for a in EAR_ANG]

def write_mesh(f, X, T, E=1700., nu=0.38, rho=1.05e-9):
    f.write('*NODE\n'+''.join(f"{i+1},{x:.4f},{y:.4f},{z:.4f}\n" for i, (x, y, z) in enumerate(X)))
    f.write('*ELEMENT,TYPE=C3D10,ELSET=EALL\n'+''.join(f"{i+1},"+",".join(str(n+1) for n in t)+"\n" for i, t in enumerate(T)))
    f.write(f"*MATERIAL,NAME=M\n*ELASTIC\n{E},{nu}\n*DENSITY\n{rho:.4e}\n*SOLID SECTION,ELSET=EALL,MATERIAL=M\n")

def nset(f, name, idx): f.write(f'*NSET,NSET={name}\n'+"\n".join(str(i+1) for i in idx)+"\n")

def ccx(name):
    r = subprocess.run(['ccx', '-i', name], capture_output=True, text=True)
    if 'ERROR' in r.stdout: print(r.stdout[-1500:])
    return r.stdout

def frd_block(name, key, nc, nn):
    frd = open(name+'.frd').read(); outs = []
    for m in re.finditer(r'\s-4\s+'+key+r'.*?\n(.*?)\n\s-3', frd, re.S):
        out = np.zeros((nn, nc))
        for l in m.group(1).splitlines():
            if l.startswith(' -1'): out[int(l[3:13])-1] = [float(l[13+12*i:13+12*(i+1)]) for i in range(nc)]
        outs.append(out)
    return outs

def vonmises(S):
    sx, sy, sz, sxy, syz, sxz = S.T
    return np.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2+6*(sxy**2+syz**2+sxz**2)))
