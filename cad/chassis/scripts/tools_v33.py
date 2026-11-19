#!/usr/bin/env python3
"""tool-access sweeps for v3.2 service ops (battery out, top plate off unless stated)."""
import os, cadquery as cq
PFX = os.environ.get('PFX', 'v33m'); ZC = 14.5
imp = lambda n: cq.importers.importStep(f'{PFX}_{n}.step').val()
fixed = {n: imp(n) for n in ('lower', 'upper', 'ring', 'pcb', 'pcbcomp', 'esc', 'xt30', 'switch', 'rx', 'ledT', 'ledB', 'usbf', 'motorR', 'motorL')}
def cyl(p0, d, r, L): return cq.Solid.makeCylinder(r, L, cq.Vector(*p0), cq.Vector(*d))
def hit(tool, skip=()):
    out = []
    for n, s in fixed.items():
        if n in skip: continue
        try: v = s.intersect(tool).Volume()
        except Exception: v = -1
        if v > 0.5 or v < 0: out.append((n, round(v, 1)))
    return out
MOUNTS = {1: [(-6.72, -6.72), (6.72, 6.72), (-5.66, 5.66), (5.66, -5.66)], -1: [(-6.72, 6.72), (6.72, -6.72), (-5.66, -5.66), (5.66, 5.66)]}
print('motor M3 screws, 2.5 mm L-key (short leg 18, enters socket 2.5) from the bay, battery out + top plate off:')
for s in (1, -1):
    for y, dz in MOUNTS[s]:
        z = ZC+dz; xs = s*20.5                                     # socket face (head flush with the bay wall)
        short = cyl((xs, y, z), (-s, 0, 0), 1.25, 15.5)             # short leg back toward the centre
        xb = xs-s*15.5
        long_ = cyl((xb, y, z), (0, 0, 1), 1.25, 45.0)             # long leg straight up out of the open top
        h = hit(short.fuse(long_), skip=('motorR', 'motorL'))
        print(f"  {'R' if s == 1 else 'L'} hole y{y:+.2f} z{z:5.2f}: {'clear' if not h else h}")
print('switch: 2 mm hex key straight down through the Ø5.5 top-plate hole onto the screw (plate ON):')
top = imp('top'); key = cyl((-5.0, 50.5, 28.85), (0, 0, 1), 1.0, 20)
print('  ', 'clear' if not hit(key, skip=('switch',)) and top.intersect(key).Volume() < 0.5 else 'BLOCKED')
print('PCB screws (M2 wafer, 1.5 mm key from below, bottom plate ON — heads sit in plate holes):')
bot = imp('bot')
for x, y in [(-16.6, 34.5), (16.6, 34.5), (-17.0, -34.5), (17.0, -34.5)]:
    k = cyl((x, y, -30), (0, 0, 1), 0.75, 30.85)
    print(f'   ({x},{y}):', 'clear' if bot.intersect(k).Volume() < 0.5 and not hit(k, skip=('pcb',)) else 'BLOCKED')
print('ring bolts: 2 mm key from below (bottom plate off):')
import math
for a in (30, 90, 150, 210, 270, 330):
    x, y = 68.5*math.cos(math.radians(a)), 68.5*math.sin(math.radians(a))
    k = cyl((x, y, -30), (0, 0, 1), 1.0, 29.9)
    print(f'   {a:3d}°:', 'clear' if not hit(k, skip=()) else hit(k, skip=()))
