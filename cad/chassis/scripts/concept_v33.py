#!/usr/bin/env python3
"""concept v3.2 — v3.1 architecture rebuilt around Kieran's REAL parts (motor.step, switch.igs, pcb.step):
  * PBB D2822 from the vendor STEP. leads exit radially from the stator base 2-4 mm behind the mount face; pointing them
    up or down puts the wire bend above the top plate / below the bottom plate (axis z 14.5 + r 16 = 30.5 > 29.3), so the
    leads point -y (horizontal, toward the ESC at the S end) on BOTH motors (left = right rotated 180° about y).
    lead channel through the outer corner of each stator wall (z 9.8..19.2) into the bay side corridors.
    real hole pattern (16 + 19 mm, 45° cross) re-derived for that orientation.
  * FingerTech mini switch stands vertical in a socket in the N lobe, hex screw up, under a Ø5.5 top-plate hole:
    switch works with the bot fully assembled. terminals poke through a slot in the N bay wall straight into the bay.
  * carrier PCB (59.5 x 58.5 with 2 diagonal tabs) right-side up, low (board z 0.9..1.81), IMU centre on the spin axis.
    tabs sit in shallow pockets in the lower half; 2x M3 button heads from below (heads sit in bottom-plate holes) into
    heat-set inserts in the pocket ceilings. bottom LED shows through a bottom-plate window.
  * battery 63x15.5x21 on end ledges (z 7.2, clear of the 4.3 mm USB-C/XIAO), laterally held by 2 mm rib segments
    hanging from the upper half (|y| 11..33.5: the gap at |y|<11 is the L-key path to the motor screws).
  * XIAO USB-C reachable with the top plate off and the battery IN: plug channel under the XT30 (z<7.2) through the
    N bay wall into a cable chimney.
  * bottom plate has its own 4x M2.5 screws (ring bolts head into counterbores in the lower half): plate off -> PCB out.
  * ring: filleted AR550 from ring_fea.ring2d (R4 roots + ear junctions, 28° trailing taper; FoS 1.8 / 2.2).
usage: python3 concept_v32.py topo_v32_0.22.npz [mjf|fdm]
"""
import sys, math, itertools, os
import numpy as np, cadquery as cq
from skimage import measure
from shapely.geometry import Polygon, Point, box as sbox
from shapely.ops import unary_union
from shapely import affinity as _aff
HERE = os.path.dirname(os.path.abspath(__file__)); REAL = os.environ.get('REAL', os.path.join(HERE, '..', 'real'))   # vendor STEPs (motor.step, switch.step), not in the repo
sys.path.insert(0, os.path.join(HERE, '..', 'ring')); from ring_fea import ring2d

NPZ = sys.argv[1] if len(sys.argv) > 1 else 'topo_v33_0.16.npz'
VARIANT = sys.argv[2] if len(sys.argv) > 2 else 'mjf'
P = os.environ.get('POUT', f'v33{VARIANT[0]}')
# ---------------- dims ----------------
H = 29.0; ZC = 14.5; CLR = 0.3
RI, RO, RING_T = 73.0, 78.0, 4.763
Z_RB, Z_RT = ZC-RING_T/2, ZC+RING_T/2
Z_SPLIT = Z_RT
RING_SLOT = float(os.environ.get('RING_T_MEAS', RING_T))+CLR                  # v3.4f: slot = measured ring thickness + 0.3 (3/16 AR plate runs over nominal: set RING_T_MEAS)
CLR_R = 0.4                                                          # v3.4f: ring bore vs rim 0.4 radial (MJF +-0.3% on 145 mm = +-0.22, plus warp); sand the band if tight
R_SK = RI-CLR_R; R_LIP = RI+2.2
EAR_R = 68.5; EAR_ANG = [30, 90, 150, 210, 270, 330]; EAR_W = 10.0; EAR_RIN = 64.5   # bolt circle pulled in 2.5 mm so the frame fully wraps the bolt (2.5 mm wall to the OD)
# motor (vendor STEP, transformed): base 26..31.33 r13.85, can 31.64..51.4 r13.9, shaft back to 24.4
WALL0, WALL1 = 20.5, 26.0
CAN_R = 14.0; CAN0 = 26.0; CAN1 = 51.4
WHEEL_R = 21.0; WHEEL_W = 12.0; HUB_R = 18.0; W0, W1 = CAN1, CAN1+WHEEL_W   # Ø42 x 12 (v3.4h, was 9; wheel_v33.py): MJF PA11 spoked hub, 3x M2 to the can face, 3 mm cast VytaFlex 40 tread on a dovetail + ribs tread
WELL0, WELL1, WELL_Y = CAN1-1.0, W1+0.6, WHEEL_R+4.0
XB0 = W0+0.05+WHEEL_W+0.15; XB1 = XB0+3.5   # bearing follows the wheel out (end wall 7 -> 4 mm)
BRG_SEAT_R = 5.9                                                     # v3.4f: Ø11.8 as printed, ream to 12.0 for the MR128 (MJF can't hold the old Ø12.1 slip)                                  # MR128 outboard support bearing (8x12x3.5) on the hub stub
M_R = cq.Matrix([[0, 1, 0, CAN0], [1, 0, 0, 0], [0, 0, -1, ZC]])     # model y = axis, model -x (leads) -> bot -y
M_L = cq.Matrix([[0, -1, 0, -CAN0], [1, 0, 0, 0], [0, 0, 1, ZC]])    # right rotated 180° about bot y: leads still -y
MOUNT = {1: [(-6.72, -6.72), (6.72, 6.72), (-5.66, 5.66), (5.66, -5.66)],   # (y, dz) of the 4 M3 tapped holes
         -1: [(-6.72, 6.72), (6.72, -6.72), (-5.66, -5.66), (5.66, 5.66)]}
LEADCH = (19.5, 31.5, -25.0, -15.0, 9.8, 19.2)                      # |x| range, y, z of the lead channel (both sides)
# pockets
BAY = (-20.5, 20.5, -39.5, 39.5)
SPK = (-13.0, 13.0, -58.0, -43.5, 1.5)          # receiver + heading LED (plate windows)
SW = (-5.0, 50.5); SW_TOP = 28.2; SW_DZ = SW_TOP-8.24                # switch screw axis xy; model z -> bot z offset
SWCAV = (SW[0]-3.6, SW[0]+3.6, SW[1]-6.75, SW[1]+6.75)          # v3.4f: 0.4 round the 6.4 x 12.7 switch body (was 0.2); foam tape against rattle
USB_X = (0.7, 12.7); CHIM_Y = (48.0, 58.0); USB_Z1 = 7.2
PCB_Z = 0.9; PCB_T = 1.6                                  # rev-2 carrier, 1.6 mm
PCB_TABHOLES = [(-16.6, 34.5), (16.6, 34.5), (-17.0, -34.5), (17.0, -34.5)]   # rev-2: 4x M2 into 3 mm heat-sets in the end-ledge undersides (S pair at +-17.0 for a 1.9 mm wall to the groove)
BAT_Z0 = 7.2; BAT_H = 20.0; BAT_W = 17.0; BAT_L = 55.0; BAT_YC = 4.2    # GNB 3S 380 HV 90C (55 x 17 x 20, 32 g, Kieran's listing), 20 tall; shifted 4.6 mm N = balance; leads + XH out of the S end
LEDGE_Y0 = 29.9
RIB_X0, RIB_T = 8.9, 1.85                                                               # v3.4f: 0.4 per side to the 17 mm pack (was 0.25), outer face kept at 10.75 for the XT30 windows                                                               # battery side ribs (upper half)
TOPSCREW = [(59.5*math.cos(math.radians(a)), 59.5*math.sin(math.radians(a))) for a in (30, 150, 210, 330)]   # top AND bottom plate screws, radially in line with the ring bolts
LED_ANG, LED_R0, LED_L = 225.0, 38.0, 21.75                        # TinySLEDs radial on the SW diagonal, r 38..59.75: fully under the plate (3.5 mm inside its edge), clear of ESC/rx/motors
def rbox(r0, r1, hw, z0, z1, ang=LED_ANG): return boxr(r0, r1, -hw, hw, z0, z1).rotate((0, 0, 0), (0, 0, 1), ang)
def led_pockets():   # 1.9 deep below the plate pocket floor: LED (1.6) + 0.3 foam; the plate clamps it. lead channel to the bay at the inner end
    v = rbox(LED_R0-0.5, LED_R0+LED_L+0.5, 3.6, H-PLK-1.9, H+5).union(rbox(LED_R0-0.5, LED_R0+LED_L+0.5, 3.6, -5, PLK+1.9))   # v3.4f: 0.4 round the LED
    v = v.union(boxr(-28.5, -19.0, -28.5, -25.5, H-PLK-3.4, H+5)).union(boxr(-28.5, -19.0, -28.5, -25.5, -5, PLK+3.4))
    return v
PLATE_T = 0.8                                                        # v3.4f: MJF PA11 0.8 (was Tegris 0.91); printed with the halves
R_PL = 63.3; PLK = 0.6                                               # plates in a 0.6 deep pocket (R63.5) with a 1.2 mm land before the R8 round; 0.6 not flush: the on-end XT30 (top z 28.25) caps how far the top plate can drop
RIND_T = 0.8
RHO = {'mjf': 1.05, 'fdm': 1.10}[VARIANT]                     # MJF PA11 (tougher than PA12: 50% vs 20% elongation, 6 vs 3.6 kJ/m2 notched Izod)

def box(x, y, z, dx, dy, dz): return cq.Workplane('XY').box(dx, dy, dz).translate((x, y, z))
def boxr(x0, x1, y0, y1, z0, z1): return box((x0+x1)/2, (y0+y1)/2, (z0+z1)/2, abs(x1-x0), abs(y1-y0), abs(z1-z0))
def disc(r, h, z0=0.0): return cq.Workplane('XY').circle(r).extrude(h).translate((0, 0, z0))
def cyl_x(x0, x1, r, y=0.0, z=ZC): return cq.Workplane('YZ').workplane(offset=min(x0, x1)).center(y, z).circle(r).extrude(abs(x1-x0))
def cyl_z(x, y, r, z0, z1): return cq.Workplane('XY').center(x, y).circle(r).extrude(z1-z0).translate((0, 0, z0))
def prism(p, z0, z1):
    if p.geom_type == 'MultiPolygon': return U(*[prism(g, z0, z1) for g in p.geoms])
    wp = cq.Workplane('XY').workplane(offset=z0).polyline(list(p.exterior.coords)[:-1]).close().extrude(z1-z0)
    for h in p.interiors:
        wp = wp.cut(cq.Workplane('XY').workplane(offset=z0-1).polyline(list(h.coords)[:-1]).close().extrude(z1-z0+2))
    return wp
def srect(x0, x1, y0, y1): return sbox(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
def U(*ws):
    out = None
    for w in ws: out = w if out is None else out.union(w)
    return out

# ---------------- real parts ----------------
_motor = cq.importers.importStep(os.path.join(REAL, 'motor.step')).val()
# rev-2 carrier from Kieran's cad/rev2/board_outline.dxf (40 x 76, USB notch) + the keepout.dxf placement courtyards
import ezdxf
REV2 = os.environ.get('REV2', os.path.join(HERE, '..', '..', 'rev2'))   # repo: cad/rev2
def _dxf_loop(path, layer):
    segs = []
    for e in ezdxf.readfile(path).modelspace():
        if e.dxf.layer != layer: continue
        if e.dxftype() == 'LINE': segs.append([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)])
        elif e.dxftype() == 'ARC':
            a0, a1 = e.dxf.start_angle, e.dxf.end_angle
            if a1 < a0: a1 += 360
            n = max(4, int((a1-a0)/5)); c, r = e.dxf.center, e.dxf.radius
            segs.append([(c.x+r*math.cos(math.radians(a0+(a1-a0)*k/n)), c.y+r*math.sin(math.radians(a0+(a1-a0)*k/n))) for k in range(n+1)])
    from shapely.ops import polygonize, linemerge
    from shapely.geometry import LineString as _LS
    segs = [[(round(x, 4), round(y, 4)) for x, y in sg] for sg in segs]          # snap arc ends onto the line ends
    return max(polygonize(unary_union([_LS(sg) for sg in segs])), key=lambda g: g.area)
BOARD2D_OUT = _dxf_loop(os.path.join(REV2, 'board_outline.dxf'), 'Edge.Cuts')
BOARD2D = BOARD2D_OUT.difference(unary_union([Point(x, y).buffer(1.1, 32) for x, y in PCB_TABHOLES]))
def _dxf_rects(path, prefix):
    out = {}
    for e in ezdxf.readfile(path).modelspace():
        if e.dxf.layer.startswith(prefix) and e.dxftype() == 'LWPOLYLINE':
            out[e.dxf.layer[len(prefix):]] = Polygon([(p[0], p[1]) for p in e.get_points()])
    return out
def _dxf_circles(path, layer): return [(e.dxf.center.x, e.dxf.center.y, e.dxf.radius) for e in ezdxf.readfile(path).modelspace() if e.dxf.layer == layer and e.dxftype() == 'CIRCLE']
PLACE = _dxf_rects(os.path.join(REV2, 'keepout.dxf'), 'PLACEMENT_')
THT_RELIEF = _dxf_circles(os.path.join(REV2, 'keepout.dxf'), 'BOTTOM_PLATE_THT_RELIEF')
PART_H = {'U1_XIAO': 3.2, 'U1_USBC': 4.3, 'L1': 5.8, 'C21': 4.3, 'U2_BUCK': 1.2, 'D2': 2.2, 'J1_ESC_PWR': 0.5, 'J4_ESC_SIG': 4.25, 'J5_RX': 4.25,
          'J2_LED': 4.25, 'J2_PLUG': 4.25, 'J4_REARPADS': 0.2, 'J5_REARPADS': 0.2, 'U4': 1.0, 'U5': 1.0, 'U6': 1.0, 'J6_XT30_BAT': 21.0, 'J7_XT30_SW': 21.0}   # mm above the board (XT30 = mated, assumed)
TABS2D = BOARD2D_OUT.difference(srect(*BAY))                         # the parts of the board under the frame

# ---------------- topopt -> plan ----------------
d = np.load(NPZ); X = d['x']; RES = float(d['res']); R = float(d['R'])
plan = Polygon()
for c in sorted([Polygon((c-1+0.5)*RES-R).buffer(0) for c in measure.find_contours(np.pad(X, 1), 0.5) if len(c) > 3], key=lambda p: -p.area):
    plan = plan.symmetric_difference(c)
plan = plan.buffer(-0.6, join_style=1).buffer(1.4, join_style=1).buffer(-0.8, join_style=1).simplify(0.15)
disk = Point(0, 0).buffer(R_SK, 256); plan = plan.intersection(disk)

# ---------------- passive 2D (same as topopt) ----------------
pv_void = unary_union([srect(*BAY), srect(*SWCAV), srect(USB_X[0], USB_X[1], *CHIM_Y), srect(*SPK[:4])] +
                      [srect(s*CAN0, s*50.5, -15.5, 15.5) for s in (1, -1)] + [srect(s*50.4, s*(W1+2.5), -WELL_Y, WELL_Y) for s in (1, -1)])
pv = [pv_void.buffer(2.0, join_style=2).difference(pv_void), disk.difference(Point(0, 0).buffer(R_SK-2.0, 256))]
pv += [srect(s*WALL0, s*WALL1, -18.5, 18.5) for s in (1, -1)]
pv += [Point(EAR_R*math.cos(math.radians(a)), EAR_R*math.sin(math.radians(a))).buffer(5.6, 64) for a in EAR_ANG]   # ear pads r5.6: 0.5 mm clear of the lined notch flank (6.1) — r7.5 made sliver tets at the flank
pv += [Point(x, y).buffer(3.5, 48) for x, y in TOPSCREW]
pv += [Point(x, y).buffer(4.5, 48) for x, y in PCB_TABHOLES]
passive2d = unary_union(pv).intersection(disk).difference(pv_void)
mem2d = plan.difference(passive2d.buffer(-0.5)).buffer(-0.6, join_style=1).buffer(1.2, join_style=1).buffer(-0.6, join_style=1)
mem_polys = [g for g in getattr(mem2d, 'geoms', [mem2d]) if g.area > 4.0]
outline = unary_union([passive2d.buffer(0.01)] + mem_polys)
outline = outline.buffer(0.7, join_style=1).buffer(-1.4, join_style=1).buffer(0.7, join_style=1).union(passive2d)
outline = outline.buffer(0.25, join_style=1).buffer(-0.25, join_style=1).simplify(0.2, preserve_topology=True)
outline = unary_union([g for g in getattr(outline, 'geoms', [outline]) if g.area > 4.0])
outline = outline.union(Point(0, 0).buffer(R_SK+0.6, 720).difference(Point(0, 0).buffer(R_SK-1.0, 720)))   # overshoot the OD so disc(R_SK) trims it to a true cylinder (simplify() chords near-tangent to the slope made mesher slivers)
print(f"[{VARIANT}] outline {outline.geom_type} {outline.area:.0f} mm² (members {sum(g.area for g in mem_polys):.0f}, passive {passive2d.area:.0f})")

# ---------------- ring (filleted) ----------------
RING2D, _ = ring2d(Ri=RI, Ro=RO, T=12.0, rake=20.0, tipw=3.0, tipr=0.8, rf_lead=4.0, trail_deg=28.0,
                   ear_rin=EAR_RIN, ear_w=EAR_W, ear_rc=2.0, ear_rf=4.0, bolt_r=EAR_R, bolt_d=3.4, ear_ang=EAR_ANG)
RING2D = RING2D.simplify(0.02, preserve_topology=True)
EARS2D = RING2D.intersection(Point(0, 0).buffer(RI-0.05, 720))       # ears incl. their R4 junction flares
LINER_T = 0.8                                                        # TPU shock liner between each steel ear and the nylon notch
NOTCH2D = unary_union([EARS2D.buffer(CLR+LINER_T, join_style=1)] +
                      [_aff.rotate(srect(EAR_RIN+2.0, R_SK+0.5, -EAR_W/2-CLR-LINER_T, EAR_W/2+CLR+LINER_T), a, origin=(0, 0)) for a in EAR_ANG])
_EARS_SOLID = unary_union([Polygon(g.exterior) for g in getattr(EARS2D, 'geoms', [EARS2D])])   # ignore the bolt holes, or the buffer puts liner rings inside them
LINER2D = _EARS_SOLID.buffer(CLR+LINER_T, join_style=1).difference(_EARS_SOLID.buffer(CLR, join_style=1)).intersection(Point(0, 0).buffer(R_SK, 720))
NOTCH2D = unary_union([Polygon(g.exterior) for g in getattr(NOTCH2D, 'geoms', [NOTCH2D])])

# ---------------- voids ----------------
voids = boxr(*BAY, -5, H+5)
voids = voids.union(boxr(*SPK[:4], SPK[4], H+5))
voids = voids.union(boxr(*SWCAV, 15.5, H+5))                                        # switch socket (drops in from the top)
voids = voids.union(boxr(SW[0]-2.2, SW[0]+2.2, BAY[3]-1, SWCAV[2]+0.5, 17.7, H+5))   # terminal slot through the N bay wall
voids = voids.union(boxr(USB_X[0], USB_X[1], CHIM_Y[0], CHIM_Y[1], -5, H+5))        # USB cable chimney
voids = voids.union(boxr(USB_X[0], USB_X[1], LEDGE_Y0-0.2, CHIM_Y[1], -5, USB_Z1))  # USB-C plug channel (under the XT30)
for s in (1, -1):
    voids = voids.union(cyl_x(s*CAN0, s*(WELL0+0.1), CAN_R+1.5))                      # can bore
    voids = voids.union(boxr(s*WELL0, s*WELL1, -WELL_Y, WELL_Y, -5, H+5))            # wheel well
    voids = voids.union(cyl_x(s*(WALL0-1), s*(WALL1+0.1), 2.5))                       # rear shaft
    voids = voids.union(boxr(s*(WALL0-1), s*(WALL1+0.1), -2.5, 2.5, ZC, Z_SPLIT+0.5))   # ...slotted up to the split so the motor drops in
    for (y, dz) in MOUNT[s]:                                                          # M3 clearance + Ø6.2 cbore 3 deep from the bay
        voids = voids.union(cyl_x(s*(WALL0-1), s*(WALL1+0.1), 1.65, y=y, z=ZC+dz))
        voids = voids.union(cyl_x(s*(WALL0-1), s*(WALL0+3.0), 3.1, y=y, z=ZC+dz))
    x0, x1, y0, y1, z0, z1 = LEADCH
    voids = voids.union(boxr(s*x0, s*x1, y0, y1, z0, z1))                             # motor lead channel -> bay side corridor
# receiver lead groove: 4x 30 AWG lie flat out of the S pocket, over the walls and the ESC top edge (z 27.25), then drop down the 3 mm gap beside the ESC
voids = voids.union(boxr(-3.0, 3.0, -45.5, -39.0, 27.35, H+5))
bolt_xy = [(EAR_R*math.cos(math.radians(a)), EAR_R*math.sin(math.radians(a))) for a in EAR_ANG]
def hexprism(x, y, af, z0, z1):
    r = af/math.sqrt(3); pts = [(x+r*math.cos(math.radians(60*k+30)), y+r*math.sin(math.radians(60*k+30))) for k in range(6)]
    return cq.Workplane('XY').workplane(offset=z0).polyline(pts).close().extrude(z1-z0)
nuts = U(*[hexprism(bx, by, 5.6, H-3.0, H+1) for bx, by in bolt_xy])
heads = U(*[cyl_z(bx, by, 3.2, -1, 2.0) for bx, by in bolt_xy])                   # ring-bolt button heads, counterbored into the lower half
tabpk = boxr(BAY[0], BAY[1], -38.5, 38.5, -1.0, PCB_Z+PCB_T+0.1)                    # rev-2: the board ends sit in recesses under both end ledges (replaces the tab pockets)
tab_ins = U(*[cyl_z(x, y, 1.6, PCB_Z+PCB_T+0.09, PCB_Z+PCB_T+0.1+3.6) for x, y in PCB_TABHOLES])  # M2 x 3 heat-set bores Ø3.2 x 3.6, pressed from below

# ---------------- skeleton ----------------
sk = prism(outline, 0, H)
for s in (1, -1): sk = sk.union(cyl_x(s*(WALL0), s*(WELL0), CAN_R+1.5+2.5))          # can sleeve
sk = sk.intersect(disc(R_SK, H))
LIPH = R_LIP-R_SK
# ring lip as an ogee (Kieran: no sharp edge): concave R3 from the flank into a 0.5 land at the lip tip, same 2.2 mm overlap on the ring face.
# Arc centre sits 0.1 inside the flank radius so it meets the flank at ~15° (not tangent: tangent faces break the mesher).
_LR, _LAND = 3.0, 0.5
_cx = R_SK + _LR - 0.1; _z1 = Z_RT + _LAND; _cz = _z1 + math.sqrt(_LR**2 - (R_LIP-_cx)**2)
_ae = math.pi + math.acos((_cx-R_SK)/_LR); _zf = _cz + _LR*math.sin(_ae)          # flank intersection (r R_SK, z _zf)
_as = math.atan2(_z1-_cz, R_LIP-_cx) % (2*math.pi); _am = (_as+_ae)/2
lip_hi = (cq.Workplane('XZ').moveTo(R_SK-2.0, Z_RT).lineTo(R_LIP, Z_RT).lineTo(R_LIP, _z1)
          .threePointArc((_cx+_LR*math.cos(_am), _cz+_LR*math.sin(_am)), (R_SK, _zf)).lineTo(R_SK-2.0, _zf).close()
          .revolve(360, (0, 0, 0), (0, 1, 0)).rotate((0, 0, 0), (0, 0, 1), 60))
lip_lo = lip_hi.mirror('XY', basePointVector=(0, 0, ZC))
sk = sk.union(lip_lo).union(lip_hi)
sk = sk.cut(prism(NOTCH2D, Z_RB, Z_RB+RING_SLOT))
# 1.2 mm 45° chamfers where each notch flank exits the rim: the ear bears on the flank, not on a sharp mouth edge (FEA hot spot)
_hw = EAR_W/2+CLR+LINER_T; _mc = 1.2
MOUTH2D = unary_union([_aff.rotate(Polygon([(R_SK-_mc, sy*_hw), (R_SK+0.6, sy*_hw), (R_SK+0.6, sy*(_hw+_mc+0.6))]), a, origin=(0, 0)) for a in EAR_ANG for sy in (1, -1)])
sk = sk.cut(prism(MOUTH2D, Z_RB, Z_RB+RING_SLOT))
sk = sk.cut(voids)
# solids re-added inside voids
for sy in (1, -1):                                                                     # battery / XT30 / ESC end ledges (full depth)
    sk = sk.union(boxr(BAY[0]-0.01, BAY[1]+0.01, sy*LEDGE_Y0, sy*(BAY[3]+0.01), 0.0, BAT_Z0))
sk = sk.cut(boxr(USB_X[0], USB_X[1], LEDGE_Y0-0.2, CHIM_Y[1], -5, USB_Z1))
sk = sk.cut(boxr(-4.5, 13.5, -39.45, -LEDGE_Y0+0.3, PCB_Z+PCB_T+0.2, BAT_Z0+0.1))   # S-ledge wire groove: ESC battery + signal leads drop off its pad edge (down) and run north to the PCB S edge
sk = sk.union(boxr(SWCAV[0]-0.01, SWCAV[1]+0.01, SWCAV[2]-0.01, SWCAV[3]+0.01, 11.5, 15.5))   # switch socket floor
# 55 mm pack: N end sits on the N ledge (2.2 mm), S end on a cross-beam; lips stop it in y (the 4.6 mm offset pulls it N at ~24 N at 4000 rpm)
BAT_S, BAT_N = BAT_YC-BAT_L/2, BAT_YC+BAT_L/2
sk = sk.union(boxr(BAY[0]-0.01, BAY[1]+0.01, BAT_S-1.5, BAT_S+3.5, 4.0, BAT_Z0))                 # S cross-beam, z 4.0-7.2 (board parts under it <= 1.2)
sk = sk.union(boxr(-BAT_W/2, BAT_W/2, BAT_S-1.7, BAT_S-0.5, BAT_Z0-0.01, BAT_Z0+2.8))            # S stop lip (v3.4f: 0.5 to the pack, LiPos swell)
sk = sk.union(boxr(-BAT_W/2, USB_X[1]+2.0, BAT_N+0.5, BAT_N+5.3, BAT_Z0-0.01, BAT_Z0+6.8))     # N stop: a 5 x 6.8 beam (4 x 4.8 still hit 72 MPa)
sk = sk.union(boxr(-RIB_X0-RIB_T, RIB_X0+RIB_T, BAT_N+0.5, BAY[3]+0.01, Z_SPLIT, H)).cut(boxr(-12.0, -1.3, BAT_N+3.3, BAY[3]+1.0, 17.5, H+1.0))   # tied to the N wall + both ribs; notch W of the switch tabs for the pigtail (Kieran)                 # main N stop in the upper half (z 16.9-29, between the ribs): takes the pack's y load high and stiff; the lower beam only carries it vertically bridging the USB plug channel (the ledge is cut away under x 0.7..12.7 — a plain lip there floated: 475 MPa)
# rev-2: the shelves stop over the board XT30s so the plugs go straight down (J6 SE: x 8.5..19.7, y -14.6..-8.4; J7 NW: x -19.7..-8.5, y 22.3..28.5)
SHELF_SEGS = {(1, 11.0): [(11.0, 31.5)], (1, -22.5): [(-22.5, -19.2)], (-1, 11.0): [(11.0, 31.5)], (-1, -22.5): [(-22.5, -19.2)]}   # v3.4g: J7 moved to the SW (mirror of J6): SW window opens, NW window closes   # rev-2 1c456dd: windows over the turned J6 (y -18.6..-8.0) and J7 (19.0..29.6) so the mated plugs go straight down
for sx in (1, -1):                                                                     # battery side ribs (upper half only)
    xr = (sx*RIB_X0, sx*(RIB_X0+RIB_T))
    for ya, yb in ((11.0, BAT_YC+BAT_L/2+1.0), (-22.5, -11.0)):   # N rib runs into the N stop block                                     # along the 55 mm pack (y -22.9..32.1)
        if ya < 0: yb = -19.2                                         # SE rib stops with its shelf: the bit beside the turned J6 had no shelf and cantilevered 5.5 mm under impact (119 MPa)
        sk = sk.union(boxr(*xr, ya, yb, Z_SPLIT, H))
        for sa, sb in SHELF_SEGS[(sx, ya)]:
            sk = sk.union(boxr(sx*(RIB_X0+RIB_T-0.01), sx*(BAY[1]+0.01), sa, sb, 25.5, H))  # L-section (2.9 mm after the plate pocket; 1.9 doubled the rib deflection): shelf to the bay wall, above the wire corridor
sk = sk.cut(tabpk).cut(tab_ins)
# TinySLED cradles: the topopt lattice leaves no material under the LED footprint (Kieran: 'hanging in thin air'). A 9 mm wide pad per half,
# r 36.6..61.5 (overlaps the rim keep), leaves a 2.1 mm floor/ceiling under each 0.3 foam + LED and 1 mm walls each side of the pocket.
sk = sk.union(rbox(LED_R0-1.4, 71.5, 4.5, H-PLK-4.8, H)).union(rbox(LED_R0-1.4, 71.5, 4.5, 0.0, PLK+4.4))   # runs out into the R8 skin (inner r ~71 at z 23.6); the edge-round cut trims what pokes outside
# J1 strain relief (rev-2 J1 = SMD lap pads, no room for tie slots on the board): snap channels on the S-ledge top for the two 20 AWG ESC leads
# just before they drop down the ledge face; slots 1.5 wide for 1.6-1.8 mm silicone 20 AWG (interference fit), walls to z 9.2 (bullets above start z 10.7)
for x0, x1 in ((13.6, 14.6), (16.5, 17.5), (19.4, BAY[1]+0.1)):   # v3.4f: 1.9 wide, 1.0 walls (MJF min) (was 1.5 interference): lay the leads in, zip-tie / epoxy
    sk = sk.union(boxr(x0, x1, -31.8, -30.2, BAT_Z0-0.1, 9.2))
# receiver tray (Kieran: 'what does the receiver rest on?' -> nothing: the S pocket runs open from z 1.5 to the top). A 1.4 mm floor across the pocket
# under the ELRS Lite (11 x 10 x 3, chip antenna end S) + a 1 mm fence on W/E/S (N open for the leads); receiver on 0.4 VHB, top plate 0.4 above it.
sk = sk.union(boxr(SPK[0]-0.6, SPK[1]+0.6, SPK[2]-0.6, SPK[3]+0.6, 23.2, 24.6))
for fb in ((-6.9, -5.9, -55.4, -44.4), (5.9, 6.9, -55.4, -44.4), (-6.9, 6.9, -56.4, -55.4)):
    sk = sk.union(boxr(*fb, 24.5, 26.6))
# ESC (Repeat AM32 dual, 28 x 20, ~2 mm with parts): FET side faces the S wall 0.8 off it on 4 corner posts so air reaches both faces (no foam on the FETs);
# corner shoes on the ledge (bottom) and keepers off the S wall (top) cup the board ends and its N face; vertical slide-in from the top, plate off.
ESC_Y0 = BAY[2]+0.8; ESC_Y1 = ESC_Y0+2.0                                        # parts face y -38.7..-37.7, board -37.7..-36.7
for sx in (1, -1):
    for z0, z1 in ((BAT_Z0-0.05, 9.6), (24.8, 27.6)):
        sk = sk.union(boxr(sx*14.4, sx*15.4, BAY[2]-0.3, ESC_Y1+1.0, z0, z1))      # end wall (board ends at x +-14.0; v3.4f 0.4 clear)
        sk = sk.union(boxr(sx*13.2, sx*15.4, ESC_Y1+0.4, ESC_Y1+1.0, z0, z1))      # lip on the N face, 1.1 mm over the board end, 0.4 clear (v3.4f)
    for z0, z1 in ((7.6, 9.0), (25.4, 26.8)):
        sk = sk.union(boxr(sx*12.6, sx*13.8, BAY[2]-0.1, ESC_Y0, z0, z1))          # 0.8 standoff posts on the S wall at the board corners
# ESC cooling (Kieran: the dual runs hot): spinning pumps air in through top-plate slots over the ESC N gap (r ~35), across both faces,
# through the S wall into the receiver pocket, up past the tray's S end and out through top-plate slots at r ~57 (~200 Pa at 4000 rpm)
for sx in (1, -1):
    for z0, z1 in ((11.5, 15.0), (18.5, 22.0)):
        sk = sk.cut(boxr(sx*4.5, sx*10.5, SPK[3]-0.5, BAY[2]+0.5, z0, z1))          # S-wall vents, ESC slot -> S pocket
    sk = sk.cut(boxr(sx*1.5, sx*11.0, SPK[2]+0.3, -56.8, 23.0, 24.8))              # tray vent S of the receiver fence
sk = sk.cut(led_pockets())
for sy in (1, -1): sk = sk.union(boxr(USB_X[0]-0.01, USB_X[1]+0.01, *sorted((CHIM_Y[0] if sy == 1 else CHIM_Y[1], CHIM_Y[0]+2.6 if sy == 1 else CHIM_Y[1]-2.6)), 19.4, 21.4))   # v3.4f: 2.6 deep so the 6.8 board (y 49.6..56.4) actually overlaps them by 1.0   # shelves for the USB-C female board
if VARIANT == 'mjf':
    ZB = 8.0
    cut2d = outline.difference(passive2d).buffer(0.5, join_style=1).difference(passive2d.buffer(1.5, join_style=2)).buffer(-0.6, join_style=1).buffer(0.6, join_style=1)
    cut2d = cut2d.intersection(Point(0, 0).buffer(R_SK-2.5, 256))
    def decimate(p, dmin=0.6):
        def ring(cs):
            cs = list(cs)[:-1]; out = [cs[0]]
            for c in cs[1:]:
                if math.dist(c, out[-1]) >= dmin: out.append(c)
            if len(out) > 3 and math.dist(out[-1], out[0]) < dmin: out.pop()
            return out
        q = Polygon(ring(p.exterior.coords), [ring(h.coords) for h in p.interiors if Polygon(h).area > 3]).buffer(0)
        return max(getattr(q, 'geoms', [q]), key=lambda g: g.area)
    for g in [g for g in getattr(cut2d, 'geoms', [cut2d]) if g.area > 3.0]:
        g = decimate(g.simplify(0.15, preserve_topology=True))
        sk = sk.cut(prism(g, -1.0, ZC-ZB)).cut(prism(g, ZC+ZB, H+1.0))
    rimcut = disc(R_SK-1.2, H+2, -1).cut(disc(R_SK-2.5, H+4, -2)).cut(disc(R_SK+4, 2*7.0, ZC-7.0))   # keep a 1.2 mm full-height outer skin (closes the sides)
    for bx, by in bolt_xy: rimcut = rimcut.cut(cyl_z(bx, by, 5.6, -3, H+3))
    for x, y in TOPSCREW: rimcut = rimcut.cut(cyl_z(x, y, 4.1, -3, H+3))
    pass   # rim pockets dropped: the 45° band capped them into sealed wedge voids (trapped powder + broke the mesher)
# for the revolved slope and everything after it, OCC's ShapeUpgrade (clean) fails on the seam edges ("Courbes non jointives"): skip clean() from here on
_cq_cut, _cq_union, _cq_isect = cq.Workplane.cut, cq.Workplane.union, cq.Workplane.intersect
cq.Workplane.cut = lambda self, o, clean=False, **k: _cq_cut(self, o, clean=clean, **k)
cq.Workplane.union = lambda self, o=None, clean=False, **k: _cq_union(self, o, clean=clean, **k)
cq.Workplane.intersect = lambda self, o, clean=False, **k: _cq_isect(self, o, clean=clean, **k)
# ---- v34 lightening (frame audit: the rim band was 44 g, 35% of the frame) ----
# 1) rim pockets above and below the ring-support band (z ZC+-7 stays solid), vented inward under the plates so MJF powder drains
RIM_RIN, VENT_R1 = 61.0, 62.5
_rp = Point(0, 0).buffer(R_SK+2.0, 720).difference(Point(0, 0).buffer(RIM_RIN, 720))
_keep = [ _aff.rotate(srect(56.0, R_SK+3.0, -(EAR_W/2+CLR+LINER_T+4.0), EAR_W/2+CLR+LINER_T+4.0), a, origin=(0, 0)) for a in EAR_ANG ]     # ear notches, bolt bosses, inserts
_keep += [Point(x, y).buffer(4.7, 48) for x, y in TOPSCREW]                                                              # plate-screw bosses
_keep += [srect(45.0, R_SK+3.0, -10.0, 10.0), srect(-R_SK-3.0, -45.0, -10.0, 10.0), srect(45.0, 62.5, -27.0, 27.0), srect(-62.5, -45.0, -27.0, 27.0)]   # struts/housings |y|<10, well walls to x 62.5
_keep += [_aff.rotate(srect(36.0, R_SK+3.0, -5.5, 5.5), LED_ANG, origin=(0, 0))]   # TinySLED pockets + cradles: no rim pockets in this sector, so the cradle ties into solid rim
_keep += [pv_void.buffer(3.5, join_style=2)]                                                     # >= 3.5 mm of wall round the S pocket, switch socket, chimney (thin walls there = 300-970 MPa spikes)                                       # wheel wells, bearing housings + struts
RP2D = _rp.difference(unary_union(_keep)).buffer(-0.8, join_style=1).buffer(0.8, join_style=1)
_vent = RP2D.intersection(Point(0, 0).buffer(VENT_R1, 720))
ZR_TOP, ZR_BOT = H-PLK-1.0, PLK+1.0                                                                    # 1.0 mm floor under each plate pocket
for g in getattr(RP2D, 'geoms', [RP2D]):
    if g.area > 4: sk = sk.cut(prism(g, ZC+6.6, ZR_TOP)).cut(prism(g, ZR_BOT, ZC-6.6))   # solid ring-support band z 7.9..21.1: must reach the R8 round (z 21 / 8) or the pocket cuts through the OD (pass-2 bug: 400 MPa at the lip)
for g in getattr(_vent, 'geoms', [_vent]):
    if g.area > 1: sk = sk.cut(prism(g, ZR_TOP-0.01, H+1.0)).cut(prism(g, -1.0, ZR_BOT+0.01))
# 2) N and S lobe pockets (S deeper: it also cancels the south-heavy balance)
_lobe_void = pv_void.buffer(1.6, join_style=2)
for (y0, y1, zb) in ():   # lobe pockets dropped: every version put a thin, load-bearing wall next to a pocket (S: receiver, N: switch) and N-only made the balance worse: S-lobe pockets left the receiver-pocket wall as an unbacked flap (100-330 MPa)
    L = srect(-23.0, 23.0, y0, y1).intersection(Point(0, 0).buffer(RIM_RIN-2.0, 360))   # 2 mm wall to the rim pockets (0.5 left a sliver web = the 250-500 MPa hot spots).difference(_lobe_void).difference(unary_union(_keep))
    L = L.buffer(-0.8, join_style=1).buffer(0.8, join_style=1)
    for g in getattr(L, 'geoms', [L]):
        if g.area > 6: sk = sk.cut(prism(g, -1.0, ZC-zb)).cut(prism(g, ZC+zb, H+1.0))
# 3) motor-wall pockets (open to the plates, outside the screw pattern) and can-sleeve side windows
for s_ in (1, -1):
    for sy in (1, -1):
        sk = sk.cut(boxr(s_*(WALL0+1.2), s_*(WALL1-1.2), sy*11.0, sy*17.3, H-7.0, H+1.0)).cut(boxr(s_*(WALL0+1.2), s_*(WALL1-1.2), sy*11.0, sy*17.3, -1.0, 7.0))
        sk = sk.cut(boxr(s_*31.0, s_*46.0, sy*13.0, sy*20.0, ZC-4.0, ZC+4.0))
# 45° sloped outer edge (top + bottom), 3.5 mm: chamfer the frame and add a 1.2 mm nylon shell under the slope so it stays closed
RF = 8.0; C0 = R_SK-RF; BT = 1.0;   # skin 1.2 -> 1.0 (Kieran: save ~2 g; MJF min ~0.8)
_BT_OLD = 1.2; _s = math.sqrt(0.5)                # R8 rounded outer edge (profile B), 1.2 mm nylon skin under the round
cham = (cq.Workplane('XZ').moveTo(C0, H+1).lineTo(R_SK+1, H+1).lineTo(R_SK+1, H-RF).lineTo(R_SK, H-RF)
        .threePointArc((C0+RF*_s, H-RF+RF*_s), (C0, H)).close().revolve(360, (0, 0, 0), (0, 1, 0)))
band = (cq.Workplane('XZ').moveTo(C0, H).threePointArc((C0+RF*_s, H-RF+RF*_s), (R_SK, H-RF)).lineTo(R_SK-BT, H-RF)
        .threePointArc((C0+(RF-BT)*_s, H-RF+(RF-BT)*_s), (C0, H-BT)).close().revolve(360, (0, 0, 0), (0, 1, 0)))
cham = cham.rotate((0, 0, 0), (0, 0, 1), 60); band = band.rotate((0, 0, 0), (0, 0, 1), 60)   # move the revolve seam off the 0°/180° bearing struts (seam + strut made a mesher-breaking sliver)
for top_ in (True, False):
    c_, b_ = (cham, band) if top_ else (cham.mirror('XY', basePointVector=(0, 0, ZC)), band.mirror('XY', basePointVector=(0, 0, ZC)))
    sk = sk.cut(c_).union(b_)
# skin gussets: the 1.0 mm R8 curl was a free cantilever over the rim pockets (poke FEA: first yield at 50-90 N, 3-6 mm dent at 300 N).
# radial fins tie it to the solid ring-support band every FIN_P degrees; skipped at the wheel wells, the LED sector and the ear/spot-face zones
FIN_P = float(os.environ.get('FIN_P', '0')); FIN_T = float(os.environ.get('FIN_T', '1.2'))
def _adiff(a, b): return abs((a-b+180) % 360-180)
if FIN_P > 0:
    fins = []
    for k in range(int(round(360/FIN_P))):
        a = k*FIN_P
        if min(_adiff(a, 0), _adiff(a, 180)) < 24 or _adiff(a, LED_ANG) < 7 or min(_adiff(a, e) for e in EAR_ANG) < 7.5: continue
        f = boxr(R_PL+0.5, R_SK-0.2, -FIN_T/2, FIN_T/2, ZC+6.0, H).rotate((0, 0, 0), (0, 0, 1), a)
        fins.append(f.cut(cham))
        fins.append(f.cut(cham).mirror('XY', basePointVector=(0, 0, ZC)))
    for f in fins: sk = sk.union(f)
    print(f'skin fins: {len(fins)//2} per half at {FIN_P:g} deg pitch, {FIN_T} thick')
sk = sk.cut(led_pockets())
sk = sk.cut(disc(R_PL+0.5, PLK+1, H-PLK)).cut(disc(R_PL+0.5, PLK+1, -1))   # v3.4f: 0.5 radial round the plates (was 0.2)   # plate pockets (plates sit 0.31 proud)
# ring-bolt bosses poke up/down through the rind scallops to the pad faces: the nut/head clamps nylon, not TPU (compression limiter)
# ring bolts fully recessed: button head in a counterbore in the lower half, nyloc in a side-loaded trap in the upper half (tip below the top face)
INS_Z0, INS_Z1 = 19.3, 25.0                                        # M3 x 5.7 heat-set insert, top flush with the spot face; Ti M3x20 button head from below (tip z 23.3)
SPOT_T, SPOT_B, SPOT_R, SPOT_W = 25.0, 3.3, 3.5, 3.6; SPOT_RB = 3.75                # flat spot faces at each ring bolt: the R8 round had curved in past the insert / head OD (Kieran, option A)
def _spot(a, bx, by, z0, z1):
    sl = cq.Workplane('XY').box(84.0-EAR_R, 2*SPOT_W, z1-z0).translate(((84.0+EAR_R)/2, 0, (z0+z1)/2)).rotate((0, 0, 0), (0, 0, 1), a)
    return cyl_z(bx, by, SPOT_R, z0, z1)                            # plain Ø7.6 spot face: max r 72.3 < flank 72.7 (no tangency), breaks out through the round above z 25 / below z 3.3 (slot version failed to mesh)
for a, (bx, by) in zip(EAR_ANG, bolt_xy):
    sk = sk.cut(_spot(a, bx, by, SPOT_T, H+1), clean=False)         # top spot face
    sk = sk.cut(cyl_z(bx, by, SPOT_RB, -1, SPOT_B), clean=False)    # bottom spot face = head + Ø7 washer seat (v3.4f Ø7.5: r 64.75..72.25, clear of the r64.6 flat/round edge and the 72.6 flank)
    sk = sk.cut(cyl_z(bx, by, 2.0, INS_Z0, H+1), clean=False)       # Ø4.0 insert bore, pressed from the spot face
# outboard bearing housings in the wheel-well end walls: the frame takes the rotor+wheel axial pull (~250 N at 4000 rpm), not the motor e-clip
for s in (1, -1):
    sk = sk.union(boxr(s*WELL1, s*(XB1+2.5), -9.0, 9.0, ZC-8.0, ZC+8.0)).union(boxr(s*(XB1+2.4), s*(R_SK+1), -7.0, 7.0, ZC-7.0, ZC+7.0).intersect(disc(R_SK-0.3, H)))   # strut: bearing pull goes straight into the rim -> steel ring
    sk = sk.cut(cyl_x(s*(XB0-0.4), s*(XB1+0.02), BRG_SEAT_R)).cut(cyl_x(s*XB1, s*(XB1+1.5), 5.25))          # race seat + lip (lip bears on the outer race only)
    sk = sk.cut(boxr(s*(XB0-0.4), s*(XB1+0.02), -BRG_SEAT_R, BRG_SEAT_R, ZC, Z_SPLIT)).cut(boxr(s*XB1, s*(XB1+1.5), -4.1, 4.1, ZC, Z_SPLIT))   # open to the split in the LOWER half only (the old +0.5 notched the upper-half lip = 51 MPa hot spot); lip slot 8.2 wide just clears the Ø8 stub
for bx, by in bolt_xy: sk = sk.cut(cyl_z(bx, by, 1.7, -5, H+5))   # Ø3.4 through, fully enclosed
for x, y in TOPSCREW:
    sk = sk.cut(cyl_z(x, y, 1.75, H-6.0-PLK, H+1)).cut(cyl_z(x, y, 1.75, -1, 6.0+PLK))          # M2.5 heat-set Ø3.5 x 6, top AND bottom
def keep_big(wp, mincc=0.05):
    ss = [s for s in wp.solids().vals() if s.Volume()/1000 > mincc]
    return cq.Workplane('XY').newObject([cq.Compound.makeCompound(ss)]), len(wp.solids().vals())-len(ss)
sk, dropped = keep_big(sk)
lower, d1 = keep_big(sk.intersect(boxr(-200, 200, -200, 200, -1, Z_SPLIT)))
upper, d2 = keep_big(sk.intersect(boxr(-200, 200, -200, 200, Z_SPLIT, H+1)))

ring = prism(RING2D, Z_RB, Z_RT)
# ---------------- plates (solid, MJF PA11 0.8) + lime TPU rinds ----------------
PAD2D = unary_union([Point(bx, by).buffer(5.0, 64) for bx, by in bolt_xy]).intersection(Point(0, 0).buffer(R_LIP, 720))
def plate(top):
    p = disc(R_PL, PLATE_T)
    for s in (1, -1): p = p.cut(boxr(s*(WELL0-0.5), s*(WELL1+5), -WELL_Y-0.5, WELL_Y+0.5, -1, 2))   # wheel notch = well + 0.5 (v3.4f)
    for x, y in TOPSCREW: p = p.cut(cyl_z(x, y, 1.4, -1, 2))
    p = p.cut(rbox(LED_R0+1.0, LED_R0+LED_L-1.0, 2.0, -1, 2))                     # heading LED window (LEDs show through; plate holds the SLED down)
    if top:
        p = p.cut(cyl_z(SW[0], SW[1], 2.75, -1, 2))                                    # Ø5.5 hex-key hole over the switch screw
        p = p.cut(boxr(2.2, 11.2, 51.5, 54.5, -1, 2))                                  # USB-C port slot (ribbon extension below)
        for sx in (1, -1):
            p = p.cut(boxr(sx*4.5, sx*12.5, -35.9, -34.7, -1, 2))                     # ESC cooling inlet (over the N gap, clear of the rx groove at x +-3)
            p = p.cut(boxr(sx*1.5, sx*11.0, -57.8, -56.6, -1, 2))                     # outlet over the S end of the receiver pocket
    else:
        for x, y in PCB_TABHOLES: p = p.cut(cyl_z(x, y, 2.0, -1, 2))                   # Ø4.0 holes: the M2 wafer heads sit in the plate
        for x, y, r in THT_RELIEF: p = p.cut(cyl_z(x, y, r, -1, 2))                    # relief for the through-hole pin tails of J1/J6/J7 (0.32 gap under the board)
    return p
top = plate(True).translate((0, 0, H-PLK+0.02)); bot = plate(False).translate((0, 0, PLK-0.02-PLATE_T))
def rind(top, C=3.5, PROUD=0.3):
    ri, ro = R_PL+0.5, R_LIP; zf0 = H+CLR; zt = H+CLR+PLATE_T+PROUD; zs0 = Z_RT+1.8; t = RIND_T
    k_out = ro+(zt-C)                                   # outer 45° chamfer: r + z = k_out
    k_in = k_out-t*math.sqrt(2)
    prof = [(ri, zf0), (k_in-zf0, zf0), (ro-t, k_in-(ro-t)), (ro-t, zs0), (ro, zs0), (ro, zt-C), (ro-C, zt), (ri, zt)]
    w = cq.Workplane('XZ').polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0))
    w = w.union(prism(PAD2D, H+0.02, zt))                                          # flat lime scallop pads at the 6 ring bolts (the v1 bumps)
    for bx, by in bolt_xy: w = w.cut(cyl_z(bx, by, 3.2, H-5, H+5))                    # clearance round the nylon boss; M3 Ø9 (DIN 9021) washer overlaps the TPU
    w = w.cut(disc(R_SK+0.2, H+0.01-(H-12), H-12))                                    # keep the rind out of the frame's envelope below the plate
    if not top: w = w.mirror('XY', basePointVector=(0, 0, ZC))
    for s in (1, -1): w = w.cut(boxr(s*(WELL0-0.5), s*(WELL1+0.5), -WELL_Y-0.5, WELL_Y+0.5, -5, H+5))
    pass
    return w
liner = prism(LINER2D, Z_RB, Z_RT)
# ---------------- components ----------------
def motor(s): return cq.Workplane('XY').newObject([_motor.transformGeometry(M_R if s == 1 else M_L)])
_WH = {n: cq.importers.importStep(os.path.join(HERE, f'wheel_{n}.step')).val() for n in ('hub', 'tread', 'bearing')}
def _place(shape, s):
    m = cq.Matrix([[0, 0, s, s*(W0+0.05)], [0, 1, 0, 0], [-s, 0, 0, ZC]])          # wheel local z (can face) -> bot +-x
    return cq.Workplane('XY').newObject([shape.transformGeometry(m)])
def wheel(s): return _place(_WH['tread'], s)
def hub(s): return _place(_WH['hub'], s)
def brg(s): return _place(_WH['bearing'], s)
usbf = boxr(1.5, 11.9, 49.6, 56.4, 21.4, 28.0)                                       # USB-C female breakout on the shelves
battery = boxr(-BAT_W/2, BAT_W/2, BAT_YC-BAT_L/2+0.05, BAT_YC+BAT_L/2-0.05, BAT_Z0+0.05, BAT_Z0+0.05+BAT_H)
# switch: body + 2 terminal tabs (from the IGES), rotated so terminals point -y into the bay
sw_body = boxr(SW[0]-3.175, SW[0]+3.175, SW[1]-6.35, SW[1]+6.35, SW_TOP-12.7, SW_TOP)
sw_terms = U(*[boxr(SW[0]-1.675, SW[0]+1.675, SW[1]-12.7, SW[1]-6.35, SW_DZ+z0, SW_DZ+z1) for z0, z1 in ((-1.6, -0.6), (4.39, 5.39))])
switch = sw_body.union(sw_terms)
xt30 = U(*[prism(PLACE[k], PCB_Z+PCB_T+0.02, PCB_Z+PCB_T+PART_H[k]) for k in ('J6_XT30_BAT', 'J7_XT30_SW')])   # rev-2: two board-mount XT30s (mated) in the SE and SW corridors (v3.4g)
esc = boxr(-14.0, 14.0, ESC_Y0, ESC_Y1, BAT_Z0+0.05, BAT_Z0+20.05)                     # Repeat AM32 dual 28 x 20, 2 mm with parts, 0.8 off the S wall
rx = boxr(-5.5, 5.5, -55.0, -45.0, H-4.0, H-1.0)
pcb = prism(BOARD2D, PCB_Z, PCB_Z+PCB_T)
pcbcomp = U(*[prism(g, PCB_Z+PCB_T+0.02, PCB_Z+PCB_T+PART_H[k]) for k, g in PLACE.items() if k in PART_H and not k.startswith(('J6', 'J7'))])
# 2x orange TinySLED 2-3S (21.75 x 6.3, 2x 5730), paralleled on J2/J3: one faces up, one faces down (invertible), radial along the S axis
ledT = rbox(LED_R0, LED_R0+LED_L, 3.15, H-PLK-1.6, H-PLK-0.02)
ledB = rbox(LED_R0, LED_R0+LED_L, 3.15, PLK+0.02, PLK+1.6)

parts = {'lower': (lower, '#d97a2b'), 'upper': (upper, '#e8a15c'), 'ring': (ring, '#8a8f98'), 'top': (top, '#2e343d'), 'bot': (bot, '#2e343d'),
         'battery': (battery, '#3b6fd6'), 'switch': (switch, '#c9a227'), 'xt30': (xt30, '#e8c33a'), 'esc': (esc, '#aa3355'), 'rx': (rx, '#7a3fb0'),
         'pcb': (pcb, '#1f8a4c'), 'pcbcomp': (pcbcomp, '#48b36f'), 'ledT': (ledT, '#ff8c00'), 'ledB': (ledB, '#ff8c00'), 'liner': (liner, '#9be36a'), 'usbf': (usbf, '#555555')}
for s in 'RL':
    sg = 1 if s == 'R' else -1
    parts['motor'+s] = (motor(sg), '#222222'); parts['wheel'+s] = (wheel(sg), '#222222'); parts['hub'+s] = (hub(sg), '#9be36a'); parts['brg'+s] = (brg(sg), '#bbbbbb')
MASS = {'usbf': 1.5, 'hubR': 3.5, 'hubL': 3.5, 'brgR': 1.3, 'brgL': 1.3, 'battery': 32.0, 'switch': 2.15, 'xt30': 3.0, 'esc': 6.0, 'rx': 0.5, 'pcb': 12.0, 'pcbcomp': 0.0, 'ledT': 0.4, 'ledB': 0.4, 'motorR': 44.0, 'motorL': 44.0, 'wheelR': 5.0, 'wheelL': 5.0}   # battery = 3S 300 mAh (pocket kept at the 450 envelope)
DENS = {'lower': RHO, 'upper': RHO, 'ring': 7.85, 'top': 0.84, 'bot': 0.84, 'rindT': 1.21, 'rindB': 1.21, 'liner': 1.21}

if __name__ == '__main__':
    tot = 0; mx = np.zeros(3); mtot = 0
    for k, (v, c) in parts.items():
        so = v.val(); vol = so.Volume()/1000
        m = vol*DENS[k] if k in DENS else MASS.get(k, 0.0)
        cc = so.Center() if k not in DENS else cq.Shape.centerOfMass(so)
        mx += m*np.array([cc.x, cc.y, cc.z]); mtot += m
        print(f"{k:8s} valid={so.isValid()} solids={len(v.solids().vals()):2d} vol={vol:6.1f}cc  {m:6.1f} g")
        cq.exporters.export(v, f'{P}_{k}.step')
        if k in ('lower', 'upper', 'ring', 'top', 'bot', 'rindT', 'rindB', 'liner'):
            import gmsh
            gmsh.initialize(); gmsh.option.setNumber('General.Terminal', 0)
            gmsh.model.occ.importShapes(f'{P}_{k}.step'); gmsh.model.occ.synchronize()
            gmsh.option.setNumber('Mesh.MeshSizeMin', 0.3); gmsh.option.setNumber('Mesh.MeshSizeMax', 2.0); gmsh.option.setNumber('Mesh.MeshSizeFromCurvature', 12)
            gmsh.model.mesh.generate(2); gmsh.write(f'{P}_{k}.stl'); gmsh.finalize()
        else:
            cq.exporters.export(v, f'{P}_{k}.stl', tolerance=0.05, angularTolerance=0.15)
    wire_g = 6.5; fast_g = 12.4 + 2.0   # M3x25 -> M3x20 Ti ring bolts (-0.9 g)   # Ti ring+motor screws, nylon plate screws, steel PCB screws, inserts, M2 wheel screws; +2 g foam/tape/epoxy
    mtot += wire_g + fast_g
    com = mx/mtot
    print(f"dropped slivers: {dropped}/{d1}/{d2}")
    print(f"TOTAL (incl ~{wire_g:.0f} g wire, ~{fast_g:.0f} g fasteners/inserts): {mtot:.0f} g   limit 454")
    print(f"CoM offset: x {com[0]:+.2f} mm, y {com[1]:+.2f} mm, z {com[2]:.1f} -> imbalance {math.hypot(com[0], com[1])*mtot:.0f} g·mm = {math.hypot(com[0], com[1])*mtot/44:.1f} g at r=44")
    bad = []
    for a, b in ([] if '--overlap' not in sys.argv else itertools.combinations(parts, 2)):
        if {a, b} == {'pcb', 'pcbcomp'}: continue
        iv = parts[a][0].intersect(parts[b][0]).val().Volume()/1000
        if iv > 0.005: bad.append((a, b, round(iv, 3)))
    print('overlaps:', bad if bad else 'none')
