"""(7) free-free modes of the assembled bot: PA11 frame (bonded halves) + the ring as a rigid body through the 6 bolt bores
(126 g as 12 masses at r75.5 -> right Izz / Ixx), each motor+wheel a rigid body from its face mount to its outboard bearing
(52 g along the axis), battery / PCB stack / plates as mass smeared on their mounts. No spin stiffening."""
import numpy as np, math, re
from mesh34 import *
nt, X, T = mesh('modal', hmax=3.5)
N0 = len(X); r = np.hypot(X[:, 0], X[:, 1])
extra = []; mass = []        # (node index, kg)
def addnode(p, m):
    extra.append(p); i = N0+len(extra)-1; mass.append((i, m)); return i
rigid = {}
near_bolt = np.zeros(N0, bool)
for bx, by in bolt_xy(): near_bolt |= np.hypot(X[:, 0]-bx, X[:, 1]-by) < 1.85
rn = [addnode([75.5*math.cos(math.radians(a)), 75.5*math.sin(math.radians(a)), 14.5], 125.8e-3/12) for a in range(0, 360, 30)]
rigid['RING'] = list(np.flatnonzero(near_bolt))+rn
MOUNTS = {1: [(-6.72, -6.72), (6.72, 6.72), (-5.66, 5.66), (5.66, -5.66)], -1: [(-6.72, 6.72), (6.72, -6.72), (-5.66, -5.66), (5.66, 5.66)]}
XB1 = 51.4+0.05+9.15+3.5
for s in (1, -1):
    m = np.zeros(N0, bool)
    for (y0, dz) in MOUNTS[s]:
        rr = np.hypot(X[:, 1]-y0, X[:, 2]-(14.5+dz)); m |= (np.abs(X[:, 0]-s*23.5) < 0.1) & (rr > 1.7) & (rr < 3.15)
    ra = np.hypot(X[:, 1], X[:, 2]-14.5); b = (np.abs(X[:, 0]-s*(XB1+0.02)) < 0.1) & (ra > 5.25) & (ra < 6.05)
    mm = [addnode([s*x, 0, 14.5], w) for x, w in ((30, .014), (38, .014), (46, .012), (56, .012))]
    for dy, dz in ((10, 0), (-10, 0), (0, 10), (0, -10)): mm.append(addnode([s*56, dy, 14.5+dz], 0.0))
    rigid[f'MOT{"E" if s > 0 else "W"}'] = list(np.flatnonzero(m | b))+mm
smear = []
bat = (np.abs(np.abs(X[:, 0])-8.75) < 0.1) & (X[:, 2] > 17.0) & (X[:, 1] > -22.5) & (X[:, 1] < 31.5)
smear.append(('battery', 0.032, np.flatnonzero(bat)))
pcb = np.zeros(N0, bool)
for (hx, hy) in [(-16.6, 34.5), (16.6, 34.5), (-17.0, -34.5), (17.0, -34.5)]:
    pcb |= (np.hypot(X[:, 0]-hx, X[:, 1]-hy) < 4.0) & (X[:, 2] < 7.3)
smear.append(('pcb stack', 0.040, np.flatnonzero(pcb)))
smear.append(('plates', 0.0172, np.flatnonzero(((X[:, 2] > 28.3) | (X[:, 2] < 0.7)) & (r < 64.5) & (r > 20))))
for n, m, ids in smear:
    for i in ids: mass.append((i, m/len(ids)))
Xa = np.vstack([X, np.array(extra)])
name = 'modal'
with open(name+'.inp', 'w') as f:
    write_mesh(f, Xa, T)
    eid = len(T)
    for k, (i, m) in enumerate([q for q in mass if q[1] > 0]):
        f.write(f'*ELEMENT,TYPE=MASS,ELSET=EM{k}\n{eid+1},{i+1}\n*MASS,ELSET=EM{k}\n{m*1e-3:.6e}\n'); eid += 1
    for nm, ids in rigid.items():
        nset(f, nm, ids); f.write(f'*RIGID BODY,NSET={nm}\n')
    f.write('*STEP\n*FREQUENCY\n22\n*NODE FILE\nU\n*END STEP\n')
out = ccx(name)
dat = open(name+'.dat').read()
blk = dat.split('E I G E N V A L U E   O U T P U T')[1].split('P A R T I C I P A T I O N')[0]
fr = [float(l.split()[3]) for l in blk.splitlines() if re.match(r'\s+\d+\s+[-\d.E+]+\s+[-\d.E+]+\s+[-\d.E+]+', l)]
Us = frd_block(name, 'DISP', 3, len(Xa))
groups = {'ring': rn, 'motor E': rigid['MOTE'][-8:-4], 'motor W': rigid['MOTW'][-8:-4],
          'battery': list(smear[0][2]), 'frame rim': list(np.flatnonzero((r > 60) & ~near_bolt)), 'top/bot plate': list(smear[2][2])}
print(f"  total model mass {sum(m for _, m in mass)*1e3 + tet_vol(X, T).sum()*1.05e-6:.0f} g")
rows = []
for k, (f_, U) in enumerate(zip(fr, Us)):
    if f_ < 5: continue
    mag = {g: np.linalg.norm(U[ids], axis=1).mean() for g, ids in groups.items()}
    uz = {g: np.abs(U[ids, 2]).mean() for g, ids in groups.items()}
    top = sorted(mag, key=mag.get, reverse=True)[:2]
    zfrac = np.abs(U[:N0, 2]).sum()/np.linalg.norm(U[:N0], axis=1).sum()
    rows.append((k+1, f_, top, zfrac))
    print(f"  mode {k+1:2d}: {f_:7.0f} Hz  biggest motion: {top[0]} / {top[1]}  (out-of-plane share {zfrac:.0%})")
    np.save(f'modal_U{k+1}.npy', U[:N0])
np.save('modal_X.npy', X); np.save('modal_f.npy', np.array(fr))
