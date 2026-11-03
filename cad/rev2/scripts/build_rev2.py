"""Rev-2 carrier: outline, keepouts and proposed placements for holy guacamole v33 rev B (+ the agreed v34 changes).

Source of truth: /tmp/hg33b/holy_guacamole_v33b/ (README Z table, scripts/concept_v33.py, step/*.step), read-only.
Frame = the generator's: origin on the spin axis, +Y = N (switch/USB), -Y = S (ESC/rx), +Z up, viewed from +Z.
Board coordinates == chassis XY.  Board bottom z 0.9, thickness T (1.6 nominal, 1.2 also tabulated).

Run from cad/rev2 (after scripts/slice_v33b.py, which tessellates the STEPs to /tmp/hg33b_work):
  uv run --with cadquery --with shapely --with ezdxf --with trimesh --with matplotlib --with networkx --with scipy --with rtree \
      python scripts/build_rev2.py
"""
import math, ezdxf, trimesh, numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

WORK = "/tmp/hg33b_work/"
# ---------------- v33 rev B constants (concept_v33.py / README) ----------------
BAY = (-20.5, 20.5, -39.5, 39.5)
LEDGE_Y0 = 29.9; BAT_Z0 = 7.2; USB_Z1 = 7.2
USB_X = (0.7, 12.7); CHIM_Y = (48.0, 58.0)
BAT = (-6.0, 6.0, -33.95, 33.95)                          # 68x20x12 on edge, z 7.25..27.25 (step bbox)
RIB_X0, RIB_T = 6.5, 2.0; RIB_Y = ((11.0, 33.0), (-33.5, -11.0)); Z_SPLIT = 16.88; Z_SHELF = 25.5
Z_KEY = 6.53                                              # lowest point of the 2.5 mm L-key sweep (screw z 7.78 - 1.25)
LEADCH = (19.5, 31.5, -25.0, -15.0, 9.8, 19.2)
ESC = (-13.0, 13.0, -39.3, -34.3)                         # 5 mm envelope, z 7.25..27.25; real board y -39.3..-37.3
SGROOVE_V33B = (-13.5, 4.5, -39.45, -29.6)                # S-ledge wire groove in rev B, z PCB_Z+PCB_T+0.2 .. 7.3
SGROOVE_V34 = (-4.5, 13.5, -39.45, -29.6)                 # agreed v34 mirror (ESC turned 180°, BAT/GND on the E side)
RX = (-5.5, 5.5, -55.0, -45.0); RX_GROOVE = (-3.0, 3.0, -45.5, -39.0)   # rx leads: groove z>=27.35, down the 3 mm gap beside the ESC
LEDCH = (-28.5, -19.0, -28.5, -25.5)                      # TinySLED lead channel into the bay (lower z<4.0, upper z>=25.0)
SWITCH = (-8.18, -1.82, 37.8, 56.85); SW_SLOT = (-7.2, -2.8, 38.5, 44.45)   # switch body; terminal slot through the N bay wall (z>=17.7)
PCB_TABHOLES = [(-24.75, 24.0), (24.5, -24.0)]
TOPPLATE_BOT = 28.42
Z_BOT = 0.9

# ---------------- rev-2 board ----------------
X0, X1, Y0, Y1 = -20.0, 20.0, -38.0, 38.0
R = 1.5
NX0, NX1, NY = 0.4, 13.0, 29.2                            # USB notch (clears the plug channel x 0.7..12.7, y>=29.7)
RI, RM = 1.0, 0.5
HOLES = [(-16.6, 34.5), (16.6, 34.5), (-16.6, -34.5), (16.6, -34.5)]
DRILL, KEEP_D = 2.2, 4.5

def limits(T):
    top = Z_BOT + T
    return dict(top=top, bat=BAT_Z0 - top, key=Z_KEY - top, leads=LEADCH[4] - top, rib=Z_SPLIT - top,
                shelf=Z_SHELF - top, plate=TOPPLATE_BOT - top, groove=7.3 - top)
L16, L12 = limits(1.6), limits(1.2)
tag = lambda v: f"{v:.1f}".replace(".", "P")

segs = []
def L(a, b): segs.append(("L", a, b))
def A(c, r, a0, a1): segs.append(("A", c, r, a0, a1))
L((X0 + R, Y0), (X1 - R, Y0)); A((X1 - R, Y0 + R), R, 270, 360)
L((X1, Y0 + R), (X1, Y1 - R)); A((X1 - R, Y1 - R), R, 0, 90)
L((X1 - R, Y1), (NX1 + RM, Y1)); A((NX1 + RM, Y1 - RM), RM, 90, 180)
L((NX1, Y1 - RM), (NX1, NY + RI)); A((NX1 - RI, NY + RI), RI, 270, 360)
L((NX1 - RI, NY), (NX0 + RI, NY)); A((NX0 + RI, NY + RI), RI, 180, 270)
L((NX0, NY + RI), (NX0, Y1 - RM)); A((NX0 - RM, Y1 - RM), RM, 0, 90)
L((NX0 - RM, Y1), (X0 + R, Y1)); A((X0 + R, Y1 - R), R, 90, 180)
L((X0, Y1 - R), (X0, Y0 + R)); A((X0 + R, Y0 + R), R, 180, 270)
BOARD = box(X0 + R, Y0 + R, X1 - R, Y1 - R).buffer(R, 64).difference(box(NX0, NY, NX1, Y1 + 5))
BOARD = BOARD.buffer(RI, 64).buffer(-RI, 64).buffer(-RM, 64).buffer(RM, 64)

# ---------------- proposed placements (courtyard rectangles, top side) ----------------
# (name, x0, x1, y0, y1, height above board top, note)
XIAO_DX = 0.0                                              # receptacle centred on the channel (Rev A model: module x -2.17..15.61)
PL = [
    ("U1_XIAO",   -2.17 + XIAO_DX, 15.61 + XIAO_DX, 7.86, 28.82, 3.2, "XIAO RP2350 module (shield top +3.19), USB-C to N"),
    ("U1_USBC",    2.25 + XIAO_DX, 11.19 + XIAO_DX, 23.60, 30.90, 4.3, "XIAO USB-C receptacle, mouth y 30.9 in the plug channel"),
    ("J7_XT30_SW", -19.7, -8.5, 22.3, 28.5, None, "XT30UPB-F vertical, pins (-16.6,25.4)/(-11.6,25.4)"),
    ("L1",        -19.35, -12.45, 15.1, 22.2, 5.8, "SRP6060FA, centre (-15.9,18.65)"),
    ("C21",       -19.5, -10.1, 8.0, 15.1, 5.8, "CP_Elec_6.3x5.8, centre (-14.8,11.55) (no room at SE, see README)"),
    ("U2_BUCK",   -10.0, -2.7, 8.3, 22.1, 1.2, "AP63301 + Cin/Cout/boot/FB/EN divider, beside L1"),
    ("J6_XT30_BAT", 8.5, 19.7, -14.6, -8.4, None, "XT30UPB-M vertical, pins (11.6,-11.5)/(16.6,-11.5)"),
    ("D2",        12.6, 19.6, -20.4, -16.9, 2.2, "SMAJ15CA (D_SMA) horizontal, centre (16.1,-18.65)"),
    ("J1_ESC_PWR", 16.45, 19.75, -29.3, -20.7, 2.5, "2x 20AWG pads P4.8 vertical, pads (18.1,-27.4)/(18.1,-22.6)"),
    ("J4_ESC_SIG", 4.77, 14.23, -29.6, -23.2, 4.25, "JST-GH 4p horizontal, centre (9.5,-26.4), opening S: plug lies in the v34 S-ledge groove"),
    ("J5_RX",     -4.73, 4.73, -29.6, -23.2, 4.25, "JST-GH 4p horizontal, centre (0.0,-26.4), opening S: plug in the groove under the rx lead drop (x ±3)"),
    ("J3_LED_BOT", -19.5, -13.1, -29.6, -22.64, 4.25, "JST-GH 2p horizontal rotated 90°, centre (-16.3,-26.12), opening E"),
    ("J2_LED_TOP", -19.5, -13.1, -22.4, -15.44, 4.25, "JST-GH 2p horizontal rotated 90°, centre (-16.3,-18.92), opening E"),
    ("J2J3_PLUGS", -13.1, -7.2, -29.6, -15.44, 4.25, "J2/J3 mating plugs + cable exits"),
]
THT = [(11.6, -11.5), (16.6, -11.5), (-16.6, 25.4), (-11.6, 25.4), (18.1, -27.4), (18.1, -22.6)]   # J6, J7, J1 through-hole pins
IMU_NOM = [("U4", 12.0, 0.0), ("U5", 18.0, 90.0), ("U6", 18.0, 210.0)]   # (ref, r, angle) = firmware imu_geom.c
IMU_HALF = 2.0                                                          # 3x3 LGA + 0.5 courtyard

# ---------------- geometry checks against rev B ----------------
mesh = {n: trimesh.load(WORK + f"v33b_{n}.stl") for n in ("lower", "upper", "bot")}
def sec(n, z):
    s = mesh[n].section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    return unary_union([p.buffer(0) for p in s.to_2D(to_2D=np.eye(4))[0].polygons_full]) if s is not None else Polygon()
def bnds(v): return [tuple(round(c, 2) for c in p.bounds) for p in getattr(v, 'geoms', [v]) if p.area > 0.5]
rep = []
LEDGES = unary_union([box(BAY[0], LEDGE_Y0, USB_X[0], BAY[3]), box(USB_X[1], LEDGE_Y0, BAY[1], BAY[3]),
                      box(BAY[0], -BAY[3], BAY[1], -LEDGE_Y0)])
for z in (0.95, 1.5, 2.2, 2.45, 3.0, 4.5, 6.0, 7.15, 7.25, 7.5, 9.0, 12.0, 16.5):
    g = sec("lower", z).intersection(BOARD)
    rep.append(f"lower z={z:5.2f}: solid over board {g.area:7.2f} mm2; outside the end-ledge blocks {g.difference(LEDGES).area:.3f}")
for z in (17.0, 20.0, 25.0, 26.0, 28.0):
    g = sec("upper", z).intersection(BOARD)
    rep.append(f"upper z={z:5.2f}: solid over board {g.area:7.2f} mm2 {[tuple(round(v, 2) for v in p.bounds) for p in getattr(g, 'geoms', [g]) if p.area > 0.05]}")
pl = sec("bot", 0.1)
rep.append(f"bottom plate (z 0.1): open area under the board {BOARD.difference(pl).area:.3f} mm2; plate z {mesh['bot'].bounds[0][2]:.2f}..{mesh['bot'].bounds[1][2]:.2f}; gap to board bottom {Z_BOT - mesh['bot'].bounds[1][2]:.2f}")
for (x, y) in PCB_TABHOLES:
    rep.append(f"  old plate hole at {x, y}: open {Point(x, y).buffer(3.0).difference(pl).area:.1f} mm2 (to be removed)")
for z in (2.2, 3.0, 5.0, 7.0):
    rep.append(f"S ledge voids z={z}: {bnds(box(BAY[0], -BAY[3], BAY[1], -LEDGE_Y0).difference(sec('lower', z)))}")
for z in (2.2, 5.0):
    rep.append(f"N ledge voids z={z}: {bnds(box(BAY[0], LEDGE_Y0, BAY[1], BAY[3]).difference(sec('lower', z)))}")
rep.append(f"SW wall void (LED lead channel) z=3.0: {bnds(box(-30, -30, -20.5, -24).difference(sec('lower', 3.0)))}")
wall = sec("lower", 1.5).intersection(box(-30, -LEDGE_Y0 + 0.05, 30, LEDGE_Y0 - 0.05)).difference(BOARD)
rep.append(f"board edge -> bay wall at z 1.5 (|y|<29.9): {BOARD.exterior.distance(wall):.3f} mm")
rep.append(f"board ∩ USB plug channel: {BOARD.intersection(box(USB_X[0], LEDGE_Y0 - 0.2, USB_X[1], BAY[3])).area:.3f} mm2")
grooves = {"v33b": box(SGROOVE_V33B[0], SGROOVE_V33B[2], SGROOVE_V33B[1], SGROOVE_V33B[3]),
           "v34": box(SGROOVE_V34[0], SGROOVE_V34[2], SGROOVE_V34[1], SGROOVE_V34[3])}
chan = box(USB_X[0], LEDGE_Y0 - 0.2, USB_X[1], BAY[3])
for hx, hy in HOLES:
    c32, c52 = Point(hx, hy).buffer(1.6, 64), Point(hx, hy).buffer(2.6, 64)
    void = [round(c52.difference(sec("lower", z)).area, 3) for z in (3.0, 4.5, 6.0, 7.0)]
    d = {k: round(c32.distance(g), 2) for k, g in grooves.items()}
    rep.append(f"hole ({hx},{hy}): Ø5.2 void in rev B ledge at z 3/4.5/6/7 = {void}; Ø3.2 bore wall to groove v33b {d['v33b']} / v34 {d['v34']}, "
               f"to USB channel {round(c32.distance(chan), 2)}, to bay wall x±20.5 {20.5 - abs(hx) - 1.6:.2f}, to ledge face {abs(hy) - 1.6 - LEDGE_Y0:.2f}")

# ---------------- keepout regions ----------------
def R_(x0, x1, y0, y1): return box(x0, y0, x1, y1)
K = {
    f"BATTERY_{tag(L16['bat'])}": R_(-6.5, 6.5, -LEDGE_Y0, LEDGE_Y0),
    f"KEYBAND_{tag(L16['key'])}": unary_union([R_(3.75, X1, -8, 8), R_(X0, -3.75, -8, 8)]),
    f"MOTOR_LEADS_{tag(L16['leads'])}": unary_union([R_(8.5, X1, -29.6, -15.0), R_(X0, -8.5, -29.6, -15.0)]),
    f"RIB_{tag(L16['rib'])}": unary_union([R_(s * RIB_X0, s * (RIB_X0 + RIB_T), *y) for s in (1, -1) for y in RIB_Y]),
    f"CORRIDOR_{tag(L16['shelf'])}": unary_union([R_(8.5, X1, -LEDGE_Y0, LEDGE_Y0), R_(X0, -8.5, -LEDGE_Y0, LEDGE_Y0)]),
    "LEDGE_CLAMP_NO_PARTS": unary_union([R_(X0, X1, LEDGE_Y0 - 0.3, Y1), R_(X0, X1, Y0, -LEDGE_Y0 + 0.3)]).difference(
        R_(SGROOVE_V34[0], SGROOVE_V34[1], Y0, -LEDGE_Y0)),
    f"S_GROOVE_WIRES_{tag(L16['groove'])}": R_(SGROOVE_V34[0], SGROOVE_V34[1], Y0, -LEDGE_Y0),
    "BOTTOM_FLUSH_PADS_ONLY": R_(X0, X1, Y0, Y1),
    "XT30_BAT": R_(8.5, 19.7, -14.6, -8.4),
    "XT30_SW": R_(-19.7, -8.5, 22.3, 28.5),
    "ESC_EDGE": unary_union([R_(4.77, 19.75, -29.9, -23.2), R_(16.45, 19.75, -23.2, -16.9), R_(12.6, 16.45, -20.4, -16.9)]),
    "USB_CHIMNEY": unary_union([R_(USB_X[0], USB_X[1], 28.82, Y1), R_(NX0, NX1, NY, Y1)]),
    "LED_CORNER": unary_union([R_(-20.0, -7.2, -29.6, -15.44), R_(-20.0, -19.0, -28.5, -25.5)]),
    "RX_ENTRY": R_(RX_GROOVE[0], RX_GROOVE[1], -29.9, -23.2),
}
for k, v in K.items():
    g = v.intersection(BOARD)
    K[k] = unary_union([q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and q.area > 0.01])
KB = "KEYBAND_" + tag(L16['key'])

# ---------------- IMU rotation scan ----------------
def imu_boxes(theta):
    out = []
    for ref, r, a in IMU_NOM:
        x, y = r * math.cos(math.radians(a + theta)), r * math.sin(math.radians(a + theta))
        out.append((ref, x, y, box(x - IMU_HALF, y - IMU_HALF, x + IMU_HALF, y + IMU_HALF)))
    return out
OBST = unary_union([box(p[1], p[3], p[2], p[4]) for p in PL] + [K["LEDGE_CLAMP_NO_PARTS"], K["S_GROOVE_WIRES_" + tag(L16['groove'])]] +
                   [Point(h).buffer(KEEP_D / 2) for h in HOLES])
NOISY = unary_union([box(p[1], p[3], p[2], p[4]) for p in PL if p[0] in ("L1", "U2_BUCK")])
scan = []
for th in range(0, 360):
    bx = imu_boxes(th)
    ok = all(BOARD.contains(b) and not b.intersects(OBST) for _, _, _, b in bx)
    clr = min(b.distance(OBST) for _, _, _, b in bx) if ok else -1
    scan.append((th, ok, clr, min(b.distance(NOISY) for _, _, _, b in bx)))
okr = [s for s in scan if s[1]]
runs = []
for s in okr:
    if runs and s[0] == runs[-1][-1][0] + 1: runs[-1].append(s)
    else: runs.append([s])
rep.append("IMU rigid-rotation scan (deg CCW, relative to firmware 0/90/210): feasible ranges " +
           str([(r[0][0], r[-1][0]) for r in runs]) + f"; nominal 0° feasible: {scan[0][1]}")
nom = imu_boxes(0)
for ref, x, y, b in nom:
    hits = [p[0] for p in PL if b.intersects(box(p[1], p[3], p[2], p[4]))]
    rep.append(f"  nominal {ref} ({x:.2f},{y:.2f}) collides with {hits or 'nothing'}; in key band: {b.intersects(K[KB])}")
best = max(okr, key=lambda s: (round(s[2], 1), s[3])) if okr else None
TH = best[0] if best else 0
rep.append(f"  chosen rotation {TH}° (min clearance {best[2]:.2f} mm to placed parts/ledges/holes, {best[3]:.2f} mm to L1/buck)" if best else "  no feasible rotation")
IMUS = imu_boxes(TH)
for ref, x, y, b in IMUS:
    rep.append(f"  {ref} at ({x:.2f},{y:.2f}) r={math.hypot(x, y):.1f} angle={(math.degrees(math.atan2(y, x))) % 360:.0f}°  zones: " +
               str([k for k, v in K.items() if b.intersects(v) and k != 'BOTTOM_FLUSH_PADS_ONLY']))
for p in PL:
    bb = box(p[1], p[3], p[2], p[4])
    zones = [k for k, v in K.items() if bb.intersection(v).area > 0.05 and k != "BOTTOM_FLUSH_PADS_ONLY"]
    over = [q[0] for q in PL if q is not p and bb.intersection(box(q[1], q[3], q[2], q[4])).area > 0.01 and {p[0], q[0]} != {"U1_XIAO", "U1_USBC"} ]
    rep.append(f"{p[0]:12s} x[{p[1]:6.2f},{p[2]:6.2f}] y[{p[3]:6.2f},{p[4]:6.2f}] h={p[5]}  inside board: {BOARD.buffer(1e-6).contains(bb)}  "
               f"overlaps {over or '-'}  zones {zones}")
xi = box(PL[0][1], PL[0][3], PL[0][2], PL[0][4])
rep.append(f"XIAO in battery strip |x|<=6.5: {xi.intersection(K['BATTERY_' + tag(L16['bat'])]).area:.1f} mm2 of {xi.area:.1f} "
           f"(x {PL[0][1]:.2f}..6.5 = {6.5 - PL[0][1]:.2f} mm wide); directly under the battery (|x|<=6): {6.0 - PL[0][1]:.2f} mm wide")
print("\n".join(rep)); open("scripts/build_rev2_checks.txt", "w").write("\n".join(rep) + "\n")

# ---------------- DXF ----------------
def new_doc(layers):
    d = ezdxf.new("R2000", setup=False); d.units = ezdxf.units.MM; d.header["$INSUNITS"] = 4; d.header["$MEASUREMENT"] = 1
    for i, n in enumerate(layers): d.layers.add(n, color=(i % 7) + 1)
    return d, d.modelspace()
def draw_outline(msp, layer):
    for s in segs:
        if s[0] == "L": msp.add_line(s[1], s[2], dxfattribs={"layer": layer})
        else: msp.add_arc(s[1], s[2], s[3], s[4], dxfattribs={"layer": layer})
def poly(msp, g, layer):
    for p in getattr(g, "geoms", [g]):
        if p.is_empty or p.geom_type != "Polygon" or p.area < 0.01: continue
        msp.add_lwpolyline([(round(x, 4), round(y, 4)) for x, y in list(p.exterior.coords)[:-1]], close=True, dxfattribs={"layer": layer})
def rect(msp, x0, x1, y0, y1, layer): poly(msp, box(x0, y0, x1, y1), layer)

doc, msp = new_doc(["Edge.Cuts", "Holes"])
draw_outline(msp, "Edge.Cuts")
for h in HOLES: msp.add_circle(h, DRILL / 2, dxfattribs={"layer": "Holes"})
doc.saveas("board_outline.dxf")

REF = {
    "REF_BAY": [BAY], "REF_LEDGES": [(BAY[0], USB_X[0], LEDGE_Y0, BAY[3]), (USB_X[1], BAY[1], LEDGE_Y0, BAY[3]), (BAY[0], BAY[1], -BAY[3], -LEDGE_Y0)],
    "REF_LEDGE_RECESS_NEW": [(BAY[0], BAY[1], LEDGE_Y0, Y1 + 0.5), (BAY[0], BAY[1], Y0 - 0.5, -LEDGE_Y0)],
    "REF_USB_CHANNEL": [(USB_X[0], USB_X[1], LEDGE_Y0 - 0.2, CHIM_Y[1])], "REF_CHIMNEY": [(USB_X[0], USB_X[1], *CHIM_Y)],
    "REF_BATTERY": [BAT], "REF_ESC_ENVELOPE": [ESC], "REF_S_GROOVE_V33B": [SGROOVE_V33B], "REF_S_GROOVE_V34": [SGROOVE_V34],
    "REF_RX": [RX], "REF_RX_LEAD_GROOVE": [RX_GROOVE], "REF_LED_LEAD_CHANNEL": [LEDCH],
    "REF_SWITCH": [SWITCH], "REF_SWITCH_SLOT": [SW_SLOT],
    "REF_MOTOR_LEAD_CHANNEL": [(LEADCH[0], LEADCH[1], LEADCH[2], LEADCH[3]), (-LEADCH[1], -LEADCH[0], LEADCH[2], LEADCH[3])],
}
layers = (list(K) + ["MOUNT_KEEPOUT", "BOTTOM_PLATE_M2_HEAD_HOLES", "BOTTOM_PLATE_THT_RELIEF"] + [f"PLACEMENT_{p[0]}" for p in PL] +
          [f"PLACEMENT_{ref}" for ref, *_ in IMUS] + ["IMU_CENTRE", "REF_BOARD", "REF_OLD_TABHOLES"] + list(REF))
doc, msp = new_doc(layers)
for k, g in K.items(): poly(msp, g, k)
for h in HOLES:
    msp.add_circle(h, KEEP_D / 2, dxfattribs={"layer": "MOUNT_KEEPOUT"})
    msp.add_circle(h, 2.0, dxfattribs={"layer": "BOTTOM_PLATE_M2_HEAD_HOLES"})
for t in THT: msp.add_circle(t, 2.0, dxfattribs={"layer": "BOTTOM_PLATE_THT_RELIEF"})
for p in PL: rect(msp, p[1], p[2], p[3], p[4], f"PLACEMENT_{p[0]}")
for ref, x, y, b in IMUS:
    poly(msp, b, f"PLACEMENT_{ref}"); msp.add_point((x, y), dxfattribs={"layer": f"PLACEMENT_{ref}"})
msp.add_circle((0, 0), 1.0, dxfattribs={"layer": "IMU_CENTRE"})
msp.add_line((-3, 0), (3, 0), dxfattribs={"layer": "IMU_CENTRE"}); msp.add_line((0, -3), (0, 3), dxfattribs={"layer": "IMU_CENTRE"})
draw_outline(msp, "REF_BOARD")
for h in PCB_TABHOLES: msp.add_circle(h, 1.6, dxfattribs={"layer": "REF_OLD_TABHOLES"})
for lay, rs in REF.items():
    for r in rs: rect(msp, *r, lay)
doc.saveas("keepout.dxf")

# ---------------- overview PNGs ----------------
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
ZC = {"BATTERY": "#3b6fd6", "KEYBAND": "#8e44ad", "MOTOR_LEADS": "#c0392b", "RIB": "#000000", "CORRIDOR": "#bbbbbb",
      "LEDGE_CLAMP": "#777777", "S_GROOVE": "#16a085"}
for zname, part, zl in (("bay_z+01.50", "lower", 1.5), ("lower_z+04.50", "lower", 4.5), ("ribs_z+20.00", "upper", 20.0)):
    fig, ax = plt.subplots(figsize=(7.5, 11))
    g = sec(part, zl).intersection(box(-45, -72, 45, 62))
    for p in getattr(g, "geoms", [g]):
        ax.fill(*p.exterior.xy, color="#e8a15c", alpha=0.45, lw=0)
        for h in p.interiors: ax.fill(*h.xy, color="white", lw=0)
    for k, v in K.items():
        c = next((c for pre, c in ZC.items() if k.startswith(pre)), None)
        if c is None: continue
        for p in [q for q in getattr(v, "geoms", [v]) if q.geom_type == "Polygon"]: ax.fill(*p.exterior.xy, color=c, alpha=0.18, lw=0.5, ec=c)
        ax.plot([], [], color=c, lw=6, alpha=0.4, label=k)
    for p in PL:
        ax.add_patch(plt.Rectangle((p[1], p[3]), p[2] - p[1], p[4] - p[3], fill=False, ec="#006400", lw=1.0))
        ax.text((p[1] + p[2]) / 2, (p[3] + p[4]) / 2, p[0].split("_")[0], fontsize=6, ha="center", va="center", color="#006400")
    for ref, x, y, b in IMUS:
        ax.fill(*b.exterior.xy, color="red", alpha=0.6); ax.text(x, y + 2.6, ref, fontsize=6, ha="center", color="red")
    for ref, x, y, b in nom: ax.plot(*b.exterior.xy, "r:", lw=0.8)
    ax.plot(*BOARD.exterior.xy, "g-", lw=1.4)
    for h in HOLES: ax.add_patch(plt.Circle(h, KEEP_D / 2, fill=False, color="r")); ax.add_patch(plt.Circle(h, DRILL / 2, fill=False, color="k"))
    for r, c in ((BAT, "b"), (ESC, "m"), (RX, "purple"), (SWITCH, "brown"), (SGROOVE_V34, "teal"), (LEDCH, "orange"), (RX_GROOVE, "purple")):
        ax.plot(*box(r[0], r[2], r[1], r[3]).exterior.xy, "--", color=c, lw=0.8)
    ax.plot(0, 0, "k+", ms=12)
    ax.set_xlim(-45, 45); ax.set_ylim(-72, 62); ax.set_aspect("equal"); ax.grid(lw=0.3)
    ax.set_xticks(range(-45, 46, 5)); ax.set_yticks(range(-70, 61, 5)); ax.tick_params(labelsize=6)
    ax.legend(fontsize=5, loc="lower right")
    ax.set_title(f"rev2 (green) over v33b {part} z={zl}; red = IMUs rotated {TH}° (dotted = nominal); dashed: battery/ESC/rx/switch/S-groove v34/LED ch.", fontsize=6)
    fig.savefig(f"sections/rev2_overview_{zname}.png", dpi=85, bbox_inches="tight"); plt.close(fig)
