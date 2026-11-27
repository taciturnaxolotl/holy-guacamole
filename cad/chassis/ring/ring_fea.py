#!/usr/bin/env python3
"""full-ring 2D plane-stress FEA (calculix CPS6, t = plate thickness) of the AR550 weapon ring.
geometry: band Ri..Ro, 2 teeth (N/S, 2-fold symmetric, raked leading face, tip radius, root fillets, trailing taper),
6 inward ears with fillets into the band and bolt holes.
load: one tooth struck on its leading face, F tangential (+ a radial component from rake).
cases:  'fixed'   — all ear flanks + bolt holes fixed (all load through the frame; conservative)
        'inertia' — ring decelerates with the robot: tangential body force a_t = alpha*r on every element,
                    alpha chosen so the ring's own inertia carries SHARE of the tooth torque; the rest goes
                    through the ears (fixed flanks as springs ~ nylon).
usage: python3 ring_fea.py  (runs the sweep)
"""
import math, re, subprocess, json, sys, time
import numpy as np, gmsh
from shapely.geometry import Polygon, Point, box as sbox, LineString
from shapely.ops import unary_union
from shapely import affinity

RHO = 7.85e-9   # t/mm3
E_ST, NU = 200000.0, 0.29
SY = 1300.0     # MPa — AR550 conservative yield (UTS ~1700-1900)

def ring2d(Ri=78.0, Ro=84.0, T=12.0, rake=20.0, tipw=3.0, tipr=0.8, rf_lead=3.0, rf_trail=4.0, trail_deg=28.0,
           ear_rin=72.0, ear_w=12.0, ear_rc=2.0, ear_rf=3.0, bolt_r=76.0, bolt_d=3.4, ear_ang=(30, 90, 150, 210, 270, 330)):
    band = Point(0, 0).buffer(Ro, 720).difference(Point(0, 0).buffer(Ri, 720))
    # tooth at angle 90 (N), leading face on the +x side (bot spins clockwise seen from above => leading = +x at N)
    # build tooth in local polar-ish coords then place: base spans from trailing root (angle 90+trail) to leading root
    rk = math.radians(rake)
    lead_root = (tipw/2 + T*math.tan(rk), Ro-1.0)                 # leading face leans back (rake) from tip to root
    tip_l = (tipw/2, Ro+T); tip_t = (-tipw/2, Ro+T)
    # trailing side: from the tip back down to the band over trail_deg of arc
    n = 16
    trail = []
    for k in range(1, n+1):
        f = k/n; ang = math.radians(90 + trail_deg*f); rr = (Ro+T)*(1-f) + (Ro-2.0)*f
        trail.append((rr*math.cos(ang), rr*math.sin(ang)))
    base = [(lead_root[0], Ro-2.0)]
    tooth = Polygon(base + [lead_root, tip_l, tip_t] + trail).buffer(0)
    teeth = [tooth, affinity.rotate(tooth, 180, origin=(0, 0))]
    ears = []
    for a in ear_ang:
        e = sbox(ear_rin, -ear_w/2, Ri+1.5, ear_w/2).buffer(-ear_rc, join_style=1).buffer(ear_rc, join_style=1)
        ears.append(affinity.rotate(e, a, origin=(0, 0)))
    shape = unary_union([band] + teeth + ears)
    # concave fillets: closing with the root radius (tooth roots, ear-to-band junctions)
    rclose = max(rf_lead, ear_rf)
    shape = shape.buffer(rclose, join_style=1, resolution=24).buffer(-rclose, join_style=1, resolution=24)
    # restore the inner circle exactly (closing slightly grows nothing there, but keep it clean)
    # convex rounding: tip radius
    shape = shape.buffer(-tipr, join_style=1, resolution=16).buffer(tipr, join_style=1, resolution=16)
    for a in ear_ang:
        shape = shape.difference(Point(bolt_r*math.cos(math.radians(a)), bolt_r*math.sin(math.radians(a))).buffer(bolt_d/2, 48))
    return shape, dict(lead_tip=tip_l, lead_root=lead_root)

def mesh_poly(p, h=1.2, hfine=0.25, fine_pts=()):
    gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)
    def loop(coords):
        pts = [gmsh.model.occ.addPoint(x, y, 0) for x, y in coords[:-1]]
        lns = [gmsh.model.occ.addLine(pts[i], pts[(i+1) % len(pts)]) for i in range(len(pts))]
        return gmsh.model.occ.addCurveLoop(lns)
    outer = loop(list(p.exterior.coords)); holes = [loop(list(h.coords)) for h in p.interiors]
    gmsh.model.occ.addPlaneSurface([outer]+holes); gmsh.model.occ.synchronize()
    fields = []
    for (x, y, rad) in fine_pts:
        f = gmsh.model.mesh.field.add('Ball'); gmsh.model.mesh.field.setNumber(f, 'Radius', rad)
        gmsh.model.mesh.field.setNumber(f, 'XCenter', x); gmsh.model.mesh.field.setNumber(f, 'YCenter', y)
        gmsh.model.mesh.field.setNumber(f, 'VIn', hfine); gmsh.model.mesh.field.setNumber(f, 'VOut', h); fields.append(f)
    if fields:
        fm = gmsh.model.mesh.field.add('Min'); gmsh.model.mesh.field.setNumbers(fm, 'FieldsList', fields); gmsh.model.mesh.field.setAsBackgroundMesh(fm)
    gmsh.option.setNumber('Mesh.MeshSizeMax', h); gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary', 0)
    gmsh.option.setNumber('Mesh.ElementOrder', 2); gmsh.option.setNumber('Mesh.SecondOrderLinear', 1)
    gmsh.model.mesh.generate(2)
    nt, nc, _ = gmsh.model.mesh.getNodes(); X = nc.reshape(-1, 3)[:, :2]
    et, _, en = gmsh.model.mesh.getElements(2); tri = np.array(en[list(et).index(9)]).reshape(-1, 6)
    gmsh.finalize()
    # enforce counter-clockwise element orientation (ccx CPS6 needs positive jacobian)
    idx = {n: i for i, n in enumerate(nt)}
    P = np.array([[X[idx[n]] for n in e[:3]] for e in tri])
    sa = (P[:, 1, 0]-P[:, 0, 0])*(P[:, 2, 1]-P[:, 0, 1])-(P[:, 2, 0]-P[:, 0, 0])*(P[:, 1, 1]-P[:, 0, 1])
    cw = sa < 0
    tri[cw] = tri[cw][:, [0, 2, 1, 5, 4, 3]]
    return nt, X, tri

def solve(p, info, t=4.763, F=11000.0, case='fixed', share=0.30, label='ring', ear_ang=(30, 90, 150, 210, 270, 330), ear_w=12.0, ear_rin=72.0, Ri=78.0, Ro=84.0, T=12.0, bolt_r=76.0):
    lt, lr = info['lead_tip'], info['lead_root']
    fine = [(lr[0], lr[1], 6.0), (-lr[0], -lr[1], 6.0)]
    for a in ear_ang:
        for sgn in (1, -1):   # ear-band junctions
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a)); lx, ly = Ri, sgn*ear_w/2
            fine.append((lx*ca-ly*sa, lx*sa+ly*ca, 4.5))
    # trailing roots
    fine += [(-(T)*0.0 + (Ro)*math.cos(math.radians(90+28)), Ro*math.sin(math.radians(90+28)), 5.0), (-(Ro)*math.cos(math.radians(90+28)), -Ro*math.sin(math.radians(90+28)), 5.0)]
    nt, X, tri = mesh_poly(p, fine_pts=fine)
    nid = {n: i+1 for i, n in enumerate(nt)}; idx = {n: i for i, n in enumerate(nt)}
    # boundary sets
    r = np.hypot(X[:, 0], X[:, 1]); th = np.degrees(np.arctan2(X[:, 1], X[:, 0]))
    flank = np.zeros(len(nt), bool); bolt = np.zeros(len(nt), bool)
    for a in ear_ang:
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        xl = X[:, 0]*ca+X[:, 1]*sa; yl = -X[:, 0]*sa+X[:, 1]*ca
        flank |= (np.abs(np.abs(yl)-ear_w/2) < 0.06) & (xl > ear_rin+2.2) & (xl < Ri-0.5)     # straight part of the ear flanks
        bolt |= np.hypot(xl-bolt_r, yl) < 1.75
    # leading face of the N tooth: between tip and root (excluding the rounded ends)
    d = np.array(lr)-np.array(lt); L = np.linalg.norm(d); d /= L; nrm = np.array([d[1], -d[0]])   # outward normal (pointing +x-ish)
    v = X-np.array(lt); along = v@d; off = v@nrm
    face = np.flatnonzero((along > 1.0) & (along < L*0.7) & (np.abs(off) < 0.08))
    # force on the face: pushes the face back (-nrm direction), magnitude F (tangential at the tooth ~ along -x)
    fvec = -nrm*F
    lines = []
    for n_i in face: lines.append((nid[nt[n_i]], fvec/len(face)))
    body = []
    if case == 'inertia':
        # ring deceleration: tangential body force -alpha*r*rho per volume; torque balance: share_ring*F*R_hit = I_ring*alpha
        area = 0.0; I = 0.0; nodal_m = np.zeros(len(nt))
        for e in tri:
            a_, b_, c_ = X[idx[e[0]]], X[idx[e[1]]], X[idx[e[2]]]
            A = 0.5*abs((b_[0]-a_[0])*(c_[1]-a_[1])-(c_[0]-a_[0])*(b_[1]-a_[1])); area += A
            m = A*t*RHO
            for k in range(3, 6): nodal_m[idx[e[k]]] += m/3.0          # quadratic tri: lump mass to mid-side nodes
        I = float(np.sum(nodal_m*r**2))
        R_hit = float(np.linalg.norm(np.array(lt)*0.5+np.array(lr)*0.5))
        torque = abs(np.cross(np.append(np.array(lt)*0.5+np.array(lr)*0.5, 0), np.append(fvec, 0))[2])
        alpha = (1-share)*torque/I         # rad/s^2 (mm-t-s units -> N, MPa)
        sgn = np.sign(np.cross(np.append(np.array(lt), 0), np.append(fvec, 0))[2])
        # inertial force opposes the deceleration: f = -m * a, a = sgn*alpha x r (tangential)
        for i in range(len(nt)):
            if nodal_m[i] == 0: continue
            tdir = np.array([-X[i, 1], X[i, 0]])/max(r[i], 1e-9)
            f = -nodal_m[i]*(sgn*alpha*r[i])*tdir
            body.append((nid[nt[i]], f))
    with open(label+'.inp', 'w') as fh:
        fh.write('*NODE\n'+''.join(f"{nid[n]},{X[i,0]:.5f},{X[i,1]:.5f},0\n" for i, n in enumerate(nt)))
        fh.write('*ELEMENT,TYPE=CPS6,ELSET=EALL\n'+''.join(f"{i+1},"+",".join(str(nid[n]) for n in e)+"\n" for i, e in enumerate(tri)))
        # supports: the ear flanks bear on nylon notch walls (tangential springs), bolts bear on nylon bosses (radial+tangential)
        K_FLANK = 1700.0*19.0/2.5      # N/mm per flank side (E_nylon * bearing area / effective depth)
        K_BOLT = 1700.0*3.0*10.0/3.0   # N/mm per bolt per direction
        eid = len(tri)
        spr = []   # (elset, orientation, dof, node ids, k_per_node)
        for a in ear_ang:
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            xl = X[:, 0]*ca+X[:, 1]*sa; yl = -X[:, 0]*sa+X[:, 1]*ca
            for side in (1, -1):
                nn = np.flatnonzero(flank & (np.sign(yl) == side) & (np.abs(((th-a+180) % 360)-180) < 10))
                if len(nn): spr.append((f"F{a}{'p' if side > 0 else 'm'}", f"O{a}", 1, nn, K_FLANK/len(nn)))
            nb = np.flatnonzero(bolt & (np.abs(((th-a+180) % 360)-180) < 10))
            if len(nb):
                spr.append((f"BT{a}", f"O{a}", 1, nb, K_BOLT/len(nb))); spr.append((f"BR{a}", f"O{a}", 2, nb, K_BOLT/len(nb)))
        for a in ear_ang:
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            fh.write(f"*ORIENTATION,NAME=O{a},SYSTEM=RECTANGULAR\n{-sa:.6f},{ca:.6f},0,{ca:.6f},{sa:.6f},0\n")   # local x = tangential, local y = radial
        for (es, orn, dof, nn, k) in spr:
            fh.write(f"*ELEMENT,TYPE=SPRING1,ELSET={es}\n")
            for n_i in nn:
                eid += 1; fh.write(f"{eid},{nid[nt[n_i]]}\n")
        for (es, orn, dof, nn, k) in spr:
            fh.write(f"*SPRING,ELSET={es},ORIENTATION={orn}\n{dof}\n{k:.4f}\n")
        fh.write(f"*MATERIAL,NAME=AR\n*ELASTIC\n{E_ST},{NU}\n*DENSITY\n{RHO:.4e}\n*SOLID SECTION,ELSET=EALL,MATERIAL=AR\n{t}\n*STEP\n*STATIC\n*CLOAD\n")
        for n_, f in lines: fh.write(f"{n_},1,{f[0]:.5f}\n{n_},2,{f[1]:.5f}\n")
        for n_, f in body: fh.write(f"{n_},1,{f[0]:.6f}\n{n_},2,{f[1]:.6f}\n")
        fh.write("*EL FILE\nS\n*END STEP\n")
    subprocess.run(['ccx', '-i', label], capture_output=True, text=True)
    frd = open(label+'.frd').read()
    L_ = [l for l in re.search(r'\s-4\s+STRESS.*?\n(.*?)\n\s-3', frd, re.S).group(1).splitlines() if l.startswith(' -1')]
    ids = np.array([int(l[3:13]) for l in L_]); S = np.array([[float(l[13+12*k:13+12*(k+1)]) for k in range(6)] for l in L_])
    sx, sy, sz, sxy, syz, sxz = S.T; vm = np.sqrt(0.5*((sx-sy)**2+(sy-sz)**2+(sz-sx)**2+6*(sxy**2+syz**2+sxz**2)))
    P = X[ids-1]
    excl = np.zeros(len(ids), bool)
    loaded = set(nid[nt[i]] for i in face)
    excl |= np.isin(ids, list(loaded)); excl |= np.isin(ids, [nid[nt[i]] for i in np.flatnonzero(flank | bolt)])  # spring attachment nodes
    # also exclude a small zone around the load face ends (point-load singularity) -> look at roots/junctions
    ok = ~excl
    reg = {}
    pr = np.hypot(P[:, 0], P[:, 1]); pth = np.degrees(np.arctan2(P[:, 1], P[:, 0]))
    near_tooth = (np.abs(((pth-90+180) % 360)-180) < 35) & (pr > Ri+2)
    ear_junc = np.zeros(len(ids), bool)
    for a in ear_ang: ear_junc |= (np.abs(((pth-a+180) % 360)-180) < 12) & (pr < Ri+1.5) & (pr > 71.0)
    reg['tooth/root (struck)'] = vm[ok & near_tooth].max() if np.any(ok & near_tooth) else 0
    reg['ear junctions'] = vm[ok & ear_junc].max() if np.any(ok & ear_junc) else 0
    reg['band elsewhere'] = vm[ok & ~near_tooth & ~ear_junc].max()
    i = int(np.argmax(np.where(ok, vm, 0)))
    return dict(max=float(vm[ok].max()), at=(round(float(P[i, 0]), 1), round(float(P[i, 1]), 1)), regions={k: round(float(v), 0) for k, v in reg.items()}, nodes=len(nt))

if __name__ == '__main__':
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    res = []
    def run(name, gp, case='fixed', t=4.763):
        p, info = ring2d(**gp)
        r = solve(p, info, t=t, case=case, label='rf_'+name.replace(' ', '_').replace('.', ''), Ri=gp.get('Ri', 78.0), ear_rin=gp.get('ear_rin', 72.0), bolt_r=gp.get('bolt_r', 76.0), ear_ang=gp.get('ear_ang', (30, 90, 150, 210, 270, 330)))
        r.update(name=name, case=case, t=t, area=p.area, mass=p.area*t*7.85e-3)
        res.append(r)
        print(f"{name:34s} {case:7s} t={t:.2f} mass {r['mass']:5.1f} g | vM max {r['max']:6.0f} MPa at {r['at']} FoS {SY/r['max']:4.2f} | {r['regions']}")
        return p
    E30 = (0, 60, 120, 180, 240, 300)
    for case in ('fixed', 'inertia'):
        print(f'=== nylon-sprung ears, case {case}')
        run('v3.1 sharp, ears under teeth', dict(rf_lead=0.3, ear_rf=0.3, tipr=0.3), case)
        run('R3, ears under teeth', dict(rf_lead=3.0, ear_rf=3.0), case)
        run('R3, ears rotated 30deg', dict(rf_lead=3.0, ear_rf=3.0, ear_ang=E30), case)
        run('R4, ears rotated 30deg', dict(rf_lead=4.0, ear_rf=4.0, ear_ang=E30), case)
    print('=== R3 rotated, thickness (inertia)')
    for t in (3.175, 6.35): run('R3 rot', dict(rf_lead=3.0, ear_rf=3.0, ear_ang=E30), 'inertia', t)
    json.dump(res, open('ring_results.json', 'w'), indent=1, default=str)
