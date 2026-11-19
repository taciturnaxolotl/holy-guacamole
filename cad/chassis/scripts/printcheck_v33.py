#!/usr/bin/env python3
"""printability + assembly checks for v3.
FDM: slice each half in its print orientation; per-layer unsupported area (islands / overhangs beyond 45deg), bridge spans, thin walls.
MJF/SLS: min wall >= 1.0 mm, trapped cavities (closed internal shells).
assembly: vertical insertion sweeps for ring, motors (+wheel, bearing) into the lower half, and upper half onto the stack.
"""
import math, sys, os, numpy as np, trimesh, cadquery as cq
PFX = os.environ.get('PFX', 'v33m')
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
LAYER = 0.2; OVH = LAYER*math.tan(math.radians(45))   # allowed step-out per layer at 45deg

def load(name, flip=False):
    m = trimesh.load(f'{PFX}_{name}.stl')
    if flip:
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    m.apply_translation([0, 0, -m.bounds[0][2]])
    return m

def layers(m):
    zs = np.arange(LAYER/2, m.bounds[1][2], LAYER)
    secs = m.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs)
    out = []
    for z, s in zip(zs, secs):
        if s is None: out.append((z, Polygon())); continue
        polys = [p for p in s.polygons_full if p.area > 0.01]
        out.append((z, unary_union(polys) if polys else Polygon()))
    return out

def fdm(name, flip):
    m = load(name, flip); L = layers(m)
    print(f"\n[FDM] {name} ({'flipped: plate face on bed' if flip else 'as modeled: bottom on bed'}), height {m.bounds[1][2]:.1f} mm, {len(L)} layers, watertight={m.is_watertight}")
    tot_unsup = 0; islands = []; bridges = []; worst = (0, 0)
    for i in range(1, len(L)):
        z, cur = L[i]; prev = L[i-1][1]
        if cur.is_empty: continue
        unsup = cur.difference(prev.buffer(OVH)) if not prev.is_empty else cur
        if unsup.is_empty or unsup.area < 0.5: continue
        tot_unsup += unsup.area
        if unsup.area > worst[1]: worst = (z, unsup.area)
        for g in getattr(unsup, 'geoms', [unsup]):
            if g.area < 0.5: continue
            # island = region of cur that has no support underneath at all
            region = [r for r in getattr(cur, 'geoms', [cur]) if r.intersects(g)]
            touching = sum(r.intersection(prev).area for r in region) if not prev.is_empty else 0
            mrr = g.minimum_rotated_rectangle; xs, ys = mrr.exterior.coords.xy
            e = sorted([math.dist((xs[k], ys[k]), (xs[k+1], ys[k+1])) for k in range(2)])
            span = e[0]
            c = g.centroid
            rec = (round(z, 1), round(g.area, 1), round(span, 1), round(c.x, 0), round(c.y, 0))
            if touching < 0.5: islands.append(rec)
            else: bridges.append(rec)
    print(f"  unsupported area total {tot_unsup:.0f} mm² over all layers; worst layer z={worst[0]:.1f} ({worst[1]:.0f} mm²)")
    big = [b for b in bridges if b[2] > 10]
    print(f"  overhang/bridge regions: {len(bridges)}; with short-side span >10 mm (needs support or redesign): {len(big)}")
    for b in sorted(big, key=lambda r: -r[1])[:8]: print(f"     z={b[0]} area={b[1]} span={b[2]} at ({b[3]},{b[4]})")
    print(f"  ISLANDS (no material below at all): {len(islands)}")
    for b in sorted(islands, key=lambda r: -r[1])[:8]: print(f"     z={b[0]} area={b[1]} span={b[2]} at ({b[3]},{b[4]})")
    thin_check(L, 1.2, 'FDM (3 perimeters @0.4)')
    return m

def thin_check(L, tmin, label):
    thin_area = [];
    for z, cur in L[::5]:
        if cur.is_empty: continue
        opened = cur.buffer(-tmin/2, join_style=2).buffer(tmin/2, join_style=2)
        thin = cur.difference(opened.buffer(0.05))
        a = sum(g.area for g in getattr(thin, 'geoms', [thin]) if g.area > 0.3)
        if a > 0.5: thin_area.append((round(z, 1), round(a, 1)))
    if thin_area:
        w = max(thin_area, key=lambda r: r[1])
        print(f"  thin (<{tmin} mm) features [{label}]: present on {len(thin_area)} sampled layers, worst z={w[0]} {w[1]} mm²")
    else: print(f"  thin (<{tmin} mm) features [{label}]: none")

def mjf(name):
    s = cq.importers.importStep(f'{PFX}_{name}.step')
    shells = sum(len(so.Shells()) for so in s.solids().vals()); nsol = len(s.solids().vals())
    m = load(name); L = layers(m)
    print(f"\n[MJF] {name}: solids {nsol}, shells {shells} -> trapped cavities: {shells-nsol}")
    thin_check(L, 1.0, 'MJF min wall 1.0')

def assembly():
    print("\n[ASSEMBLY] build order, each part dropped vertically from +35 mm into what is already there (overlap cc; must be 0)")
    imp = lambda n: cq.importers.importStep(f'{PFX}_{n}.step')
    lower, upper, ring = imp('lower'), imp('upper'), imp('ring')
    def sweep(moving, fixed_list, name, dzs=(0.0, 0.5, 2, 5, 10, 20, 35)):
        worst = 0
        for dz in dzs:
            mv = moving.translate((0, 0, dz))
            for f in fixed_list:
                r = mv.intersect(f)
                v = r.val().Volume()/1000 if r.solids().vals() else 0
                worst = max(worst, v)
        print(f"  {name:44s} max overlap {worst:.3f} cc  -> {'OK' if worst < 0.01 else 'BLOCKED'}")
        return worst
    placed = [lower]
    for s_ in 'RL':
        mot = imp('motor'+s_).union(imp('wheel'+s_)).union(imp('hub'+s_)).union(imp('brg'+s_)); sweep(mot, placed, f'1. motor{s_} + hub + tread into lower'); placed.append(mot)
    lin = imp('liner'); sweep(lin, placed, '2a. TPU ear liners into the notches'); placed.append(lin)
    sweep(ring, placed, '2. ring (ears into lined notches) onto lower'); placed.append(ring)
    sweep(upper, placed, '3. upper half onto lower+ring+motors'); placed.append(upper)
    up = (0.0, -0.5, -2, -5, -10, -20, -35)
    pcb = imp('pcb').union(imp('pcbcomp')); sweep(pcb, placed, '4. PCB up from BELOW (ends into the ledge recesses)', dzs=up); placed.append(pcb)
    sweep(imp('ledB'), placed, '5. bottom TinySLED up into its pocket', dzs=up); placed.append(imp('ledB'))
    sweep(imp('bot'), placed, '7. bottom plate from below (4x M2.5)', dzs=up); placed.append(imp('bot'))
    for n, label in (('esc', '8. ESC on edge onto the S ledge'), ('xt30', '9. XT30 plugs down onto the board (SE + SW corridors)'),
                     ('switch', '10. switch down into its socket'), ('rx', '11. receiver, S pocket top'),
                     ('ledT', '12. top TinySLED into its pocket'), ('usbf', '13. USB-C port onto its shelves'),
                     ('battery', '14. battery (3S 380) down between the ribs')):
        p = imp(n); sweep(p, placed, label); placed.append(p)
    sweep(imp('top'), placed, '16. top plate (4x M2.5)')
    print("\n[SERVICE] each removal = reverse sweep with everything else in place")
    allp = {n: imp(n) for n in ('lower', 'upper', 'ring', 'motorR', 'motorL', 'wheelR', 'wheelL', 'hubR', 'hubL', 'pcb', 'pcbcomp', 'bot', 'esc', 'xt30', 'switch', 'rx', 'ledT', 'ledB', 'usbf', 'battery')}
    def svc(names, dzs, label):
        mv = None
        for n in names: mv = allp[n] if mv is None else mv.union(allp[n])
        sweep(mv, [v for k, v in allp.items() if k not in names], label, dzs=dzs)
    svc(['battery'], (0.0, 5, 10, 20, 35), 'battery out (top plate off)')
    svc(['switch'], (0.0, 5, 10, 20, 35), 'switch out (top plate off)')
    svc(['pcb', 'pcbcomp', 'bot'], up, 'PCB out the bottom (bottom plate off)')

if __name__ == '__main__':
    fdm('lower', False); fdm('upper', True)
    mjf('lower'); mjf('upper')
    assembly()
