"""fit audit: every part vs both frame halves (and a few part-part pairs). For each pair, sample the part's surface
(~0.25 mm spacing), find the nearest frame surface, and bucket the gaps:
  contact <=0.02 (designed bearing face), TIGHT 0.02..0.30 (inside MJF +/-0.3), ok >0.30.
Tight patches are clustered and printed with location + area so each can be judged (intended press/snap vs accidental)."""
import numpy as np, trimesh, sys, json
from scipy.cluster.hierarchy import fcluster, linkage
P = 'v33m_'
FR = {n: trimesh.load(P+n+'.stl') for n in ('lower', 'upper')}
PARTS = [p for p in sys.argv[1:]] or ['battery', 'esc', 'escd', 'pcb', 'pcbcomp', 'switch', 'rx', 'ledT', 'ledB', 'usbf', 'motorR', 'motorL', 'wheelR', 'wheelL',
         'hubR', 'hubL', 'brgR', 'brgL', 'ring', 'liner', 'top', 'bot', 'xt30', 'inserts', 'bolts', 'pscrews', 'pcbscrews', 'mscrews', 'nuts']
PAIRS = []
SP = 0.25; LIM = 0.45; CON = 0.02
def sample(m, sp=SP):
    n = int(min(int(__import__('os').environ.get('NMAX', 120000)), max(4000, m.area/sp**2)))
    pts, fi = trimesh.sample.sample_surface_even(m, n) if n < 150000 else trimesh.sample.sample_surface(m, n)
    return np.asarray(pts), m.area/len(pts)
rows = []
def audit(pn, pm, fn, fm):
    lo, hi = fm.bounds; pl, ph = pm.bounds
    if np.any(ph < lo-1) or np.any(pl > hi+1): return
    pts, da = sample(pm)
    near = np.all((pts > lo-1) & (pts < hi+1), axis=1); pts = pts[near]
    if not len(pts): return
    # quick prefilter by bbox distance, then exact
    cp, d, _ = trimesh.proximity.closest_point(fm, pts)
    inside = fm.contains(pts[d < 0.05]) if (d < 0.05).any() else np.zeros(0, bool)
    con = d <= CON; tight = (d > CON) & (d < LIM)
    a_con, a_t = con.sum()*da, tight.sum()*da
    if a_t < 0.05 and a_con < 0.05: return
    cl = []
    if tight.sum() >= 3:
        T = pts[tight]; TD = d[tight]
        if len(T) > 6000: sel = np.random.default_rng(0).choice(len(T), 6000, replace=False); T = T[sel]; TD = TD[sel]
        lab = fcluster(linkage(T, 'single'), 1.5, 'distance')
        dd = d[tight][:len(T)] if len(T) == tight.sum() else None
        for k in np.unique(lab):
            Q = T[lab == k]
            if len(Q)*da*(tight.sum()/len(T)) < 0.3: continue
            sub = np.linalg.norm(pts[tight][:, None, :] - Q.mean(0), axis=2).min(1) < 3 if False else None
            cl.append({'c': np.round(Q.mean(0), 1).tolist(), 'ext': np.round(Q.max(0)-Q.min(0), 1).tolist(), 'area': round(len(Q)*da*(tight.sum()/len(T)), 1),
                       'gap_min': round(float(TD[lab == k].min()), 3), 'gap_med': round(float(np.median(TD[lab == k])), 3)})
    gmin = float(d[~con].min()) if (~con).any() else None
    rows.append({'part': pn, 'vs': fn, 'contact_mm2': round(a_con, 1), 'tight_mm2': round(a_t, 1), 'min_gap_noncontact': round(gmin, 3) if gmin is not None else None,
                 'penetrating_pts': int(inside.sum()), 'clusters': sorted(cl, key=lambda c: -c['area'])[:8]})
    print(f"{pn:10s} vs {fn:6s} contact {a_con:7.1f} mm2 | tight(<0.3) {a_t:6.1f} mm2 | inside {int(inside.sum())}", flush=True)
for pn in PARTS:
    try: pm = trimesh.load(P+pn+'.stl')
    except Exception: continue
    for fn, fm in FR.items(): audit(pn, pm, fn, fm)
for a, b in PAIRS: audit(a, trimesh.load(P+a+'.stl'), b, trimesh.load(P+b+'.stl'))
json.dump(rows, open('fit_audit_%s.json' % (sys.argv[1] if len(sys.argv) > 1 else 'all'), 'w'), indent=1)
