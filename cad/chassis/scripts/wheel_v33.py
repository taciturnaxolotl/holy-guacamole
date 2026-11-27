#!/usr/bin/env python3
"""Ø42 x 12 hub-motor wheel (v3.4h: was 9): MJF PA11 spoked hub + cast urethane tread (VytaFlex 40), plus a 3-part printable mould.
local coords: wheel axis = +z, z=0 is the face that bolts to the motor can (3x M2 on Ø12).
exports wheel_hub.step/.stl, wheel_tread.step/.stl, mould_base.stl, mould_ring.stl, mould_lid.stl
"""
import math, cadquery as cq
W = 12.0; R_T = 21.0; R_H = 18.0; R_RIM_IN = 16.2          # tread OD, hub OD (= tread ID), hub rim ID
R_BOSS = 8.0; BOSS_T = 4.0; WEB_T = 3.0; N_SPOKE = 5; SPOKE_W = 3.0
BORE = 2.1; BC = 6.0; M2 = 1.1; M2_CB_R, M2_CB_D = 2.0, 1.4
N_RIB = 12; RIB_W, RIB_H = 1.0, 0.7                         # axial ribs on the hub OD: torque key
GROOVE_W0, GROOVE_W1, GROOVE_D = 2.0, 3.4, 1.2              # circumferential dovetail on the hub OD (0.7 mm undercut per side): holds the tread against spin
BRG_ID, BRG_OD, BRG_W = 8.0, 12.0, 3.5                      # MR128 outboard support bearing on a hub stub
STUB_Z0 = W+0.15; STUB_Z1 = STUB_Z0+BRG_W+0.2; COL_R = 4.6     # column shoulder (Ø9.2) pushes the inner race outward

def cyl(r, z0, z1): return cq.Workplane('XY').circle(r).extrude(z1-z0).translate((0, 0, z0))
# --- hub ---
hub = cyl(R_H, 0, W).cut(cyl(R_RIM_IN, -1, W+1))                                   # rim
hub = hub.union(cyl(R_BOSS, 0, BOSS_T))                                            # boss on the can face
zc = (W-WEB_T)/2*0 + 0.0
for k in range(N_SPOKE):                                                           # spokes (in the boss plane, flush with the can face)
    sp = cq.Workplane('XY').box(R_RIM_IN-R_BOSS+1.0, SPOKE_W, WEB_T).translate(((R_RIM_IN+R_BOSS)/2, 0, WEB_T/2))
    hub = hub.union(sp.rotate((0, 0, 0), (0, 0, 1), 360/N_SPOKE*k))
# dovetail grooves (revolved trapezoids, wider at the bottom = undercut): two on the 12 mm hub, at 1/3 and 2/3 width
for zm in (W/3, 2*W/3):
    groove = cq.Workplane('XZ').polyline([(R_H-GROOVE_D, zm-GROOVE_W1/2), (R_H, zm-GROOVE_W0/2), (R_H+0.6, zm-GROOVE_W0/2), (R_H+0.6, zm+GROOVE_W0/2), (R_H, zm+GROOVE_W0/2), (R_H-GROOVE_D, zm+GROOVE_W1/2)]).close().revolve(360, (0, 0, 0), (0, 1, 0))
    hub = hub.cut(groove)
for k in range(N_RIB):                                                             # axial ribs (urethane flows round them)
    rb = cq.Workplane('XY').box(RIB_H+0.3, RIB_W, W).translate((R_H+RIB_H/2-0.15, 0, W/2))
    hub = hub.union(rb.rotate((0, 0, 0), (0, 0, 1), 360/N_RIB*k+15))
hub = hub.union(cyl(COL_R, 0, STUB_Z0)).union(cyl(BRG_ID/2, STUB_Z0-0.01, STUB_Z1))   # centre column + bearing stub
hub = hub.cut(cyl(BORE, -1, STUB_Z1+1))
for k in range(3):
    a = math.radians(120*k+90); x, y = BC*math.cos(a), BC*math.sin(a)
    hub = hub.cut(cq.Workplane('XY').center(x, y).circle(M2).extrude(W+2).translate((0, 0, -1)))
    hub = hub.cut(cq.Workplane('XY').center(x, y).circle(M2_CB_R).extrude(M2_CB_D+1).translate((0, 0, BOSS_T-M2_CB_D)))   # heads recessed in the boss
# --- tread = annulus minus hub (fills the groove and wraps the ribs) ---
tread = cyl(R_T, 0, W).cut(cyl(R_H-GROOVE_D-0.01, -1, W+1)).cut(hub)
bearing = cyl(BRG_OD/2, STUB_Z0, STUB_Z0+BRG_W).cut(cyl(BRG_ID/2, STUB_Z0-1, STUB_Z0+BRG_W+1))
# --- mould: base (locates the hub on its bore + seals the rim face), ring (tread OD), lid (seals the other face, pour + vent) ---
MO_R = R_T+5.0
base = cyl(MO_R, -3.0, 0).union(cyl(R_RIM_IN-0.3, 0, 0.01)).union(cyl(BORE-0.08, 0, 6.0))
base = base.cut(cq.Workplane('XY').circle(MO_R+1).circle(MO_R-1.5).extrude(1.5).translate((0, 0, -1.5)))   # register step for the ring
ring = cyl(MO_R-1.6, -1.5, W).cut(cyl(R_T, -2, W+1)).union(cyl(MO_R, 0, W).cut(cyl(MO_R-1.6, -1, W+1)))
lid = cyl(MO_R, W, W+3.0).cut(cyl(COL_R+0.3, W-1, W+4))                         # clears the column/stub
lid = lid.cut(cq.Workplane('XY').center(0, (R_H+R_T)/2).circle(2.0).extrude(5).translate((0, 0, W-1)))      # pour
lid = lid.cut(cq.Workplane('XY').center(0, -(R_H+R_T)/2).circle(1.0).extrude(5).translate((0, 0, W-1)))     # vent
if __name__ == '__main__':
    vh, vt = hub.val().Volume()/1000, tread.val().Volume()/1000
    print(f"hub {vh:.2f} cc -> {vh*1.05:.2f} g PA11 | tread {vt:.2f} cc -> {vt*1.0:.2f} g VytaFlex 40 | wheel {vh*1.05+vt:.2f} g + 3x M2 screws")
    print('valid', hub.val().isValid(), tread.val().isValid())
    for n, v in (('wheel_hub', hub), ('wheel_tread', tread), ('wheel_bearing', bearing)):
        cq.exporters.export(v, n+'.step'); cq.exporters.export(v, n+'.stl', tolerance=0.02, angularTolerance=0.1)
    for n, v in (('mould_base', base), ('mould_ring', ring), ('mould_lid', lid)):
        cq.exporters.export(v, n+'.stl', tolerance=0.02, angularTolerance=0.1)
