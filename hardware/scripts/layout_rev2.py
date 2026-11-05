"""Rebuild guac.kicad_pcb for the rev-2 carrier: footprints and nets from the schematic netlist,
outline from the cad/rev2 geometry, placement from cad/rev2/README.md.

Run with KiCad's own python (it ships pcbnew):
  cd hardware && kicad-cli sch export netlist -o /tmp/rev2.net guac.kicad_sch
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 scripts/layout_rev2.py

Board coordinates: chassis frame, origin on the spin axis, +Y = N. KiCad coordinates: kx = OX + x, ky = OY - y.
Rotations are CCW in the chassis frame, which is also CCW on screen, so they map 1:1 to pcbnew orientations.
"""
import math
import os
import re
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from ksch import parse  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.dirname(HERE)
PCB = os.path.join(HW, "guac.kicad_pcb")
NETLIST = sys.argv[1] if len(sys.argv) > 1 else "/tmp/rev2.net"
KICAD_FP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
OX, OY = 80.0, 65.5

# ---------------- outline (same constants as cad/rev2/scripts/build_rev2.py) ----------------
X0, X1, Y0, Y1 = -20.0, 20.0, -38.0, 38.0
R = 1.5
NX0, NX1, NY = 0.4, 13.0, 29.2
RI, RM = 1.0, 0.5
HOLES = [(-16.6, 34.5), (16.6, 34.5), (-17.0, -34.5), (17.0, -34.5)]
IMU_ROT = 166.0


def mm(v):
    return int(round(v * 1e6))


def K(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))


segs = []


def L(a, b):
    segs.append(("L", a, b))


def A(c, r, a0, a1):
    segs.append(("A", c, r, a0, a1))


L((X0 + R, Y0), (X1 - R, Y0)); A((X1 - R, Y0 + R), R, 270, 360)
L((X1, Y0 + R), (X1, Y1 - R)); A((X1 - R, Y1 - R), R, 0, 90)
L((X1 - R, Y1), (NX1 + RM, Y1)); A((NX1 + RM, Y1 - RM), RM, 90, 180)
L((NX1, Y1 - RM), (NX1, NY + RI)); A((NX1 - RI, NY + RI), RI, 270, 360)
L((NX1 - RI, NY), (NX0 + RI, NY)); A((NX0 + RI, NY + RI), RI, 180, 270)
L((NX0, NY + RI), (NX0, Y1 - RM)); A((NX0 - RM, Y1 - RM), RM, 0, 90)
L((NX0 - RM, Y1), (X0 + R, Y1)); A((X0 + R, Y1 - R), R, 90, 180)
L((X0, Y1 - R), (X0, Y0 + R)); A((X0 + R, Y0 + R), R, 180, 270)


def imu_xy(r, a):
    t = math.radians(a + IMU_ROT)
    return (r * math.cos(t), r * math.sin(t))


# ---------------- placement: ref -> (x, y, rot, side) in chassis mm / degrees ----------------
U4 = imu_xy(12, 0)
U5 = imu_xy(18, 90)
U6 = imu_xy(18, 210)
XIAO = (6.72, 18.4)
U2 = (-10.5, 14.5)
PLACE = {
    # compute module, USB-C north into the plug channel
    "U1": (*XIAO, 90, "F"),
    # buck: U2 rotated so SW/BST/GND face west toward L1, FB/EN/VIN face east
    "U2": (*U2, 90, "F"),
    "L1": (-16.3, 14.55, 180, "F"),
    # buck input loop: HF cap then first bulk cap stacked straight off U2 VIN (pin 3) / GND (pin 4)
    "C2": (-10.5, 17.0, 180, "F"),
    "C1": (-8.6, 18.55, 180, "F"),
    "C19": (-8.6, 20.65, 180, "F"),
    "C20": (-8.6, 22.75, 180, "F"),
    "C3": (-11.5, 11.9, 180, "F"),
    "C4": (-18.3, 9.1, -90, "F"),
    "C5": (-16.1, 9.1, -90, "F"),
    "R27": (-8.5, 11.5, 90, "F"),
    "C18": (-7.4, 11.5, -90, "F"),
    "R28": (-6.3, 11.5, -90, "F"),
    "JP1": (-6.5, 14.9, 90, "F"),
    "R23": (-4.0, 13.2, 180, "F"),
    "R24": (-4.0, 12.1, 0, "F"),
    "R25": (-4.0, 15.8, 180, "F"),
    "R26": (-4.0, 16.9, 0, "F"),
    # power connectors
    "J7": (-13.8, 21.8, 90, "F"),
    "J6": (13.8, -15.8, 90, "F"),
    "J1": (16.6, -27.3, 180, "F"),
    "C21": (4.75, -16.8, 180, "F"),
    "D2": (16.1, -5.7, 180, "F"),
    # battery sense near XIAO A0 (pin 1, west column, north end)
    "R9": (-4.6, 26.0, 90, "F"),
    "R10": (-4.6, 28.1, 90, "F"),
    "C12": (-6.0, 28.1, 90, "F"),
    # IMU array, chip X radial outward (see footprint pin-edge notes in the README)
    "U4": (*U4, IMU_ROT, "F"),
    "U5": (*U5, IMU_ROT, "F"),
    "U6": (*U6, (IMU_ROT + 30) % 360, "F"),
    # latch between XIAO and the array
    "U11": (-1.2, 3.0, 90, "F"),
    "C7": (-2.7, 7.2, 0, "F"),
    "R1": (-8.0, 7.0, 90, "F"),
    "R18": (-8.0, 5.0, 90, "F"),
    "R22": (-8.0, 3.0, 90, "F"),
    "R11": (3.6, 6.4, 90, "F"),
    "R4": (3.6, 4.4, 90, "F"),
    "R5": (3.6, 2.4, 90, "F"),
    # IMU decoupling / series resistors
    "C8": (U4[0] - 0.2, U4[1] + 3.0, 180, "F"),
    "C11": (U4[0] - 2.2, U4[1] + 3.0, 0, "F"),
    "R6": (U4[0] + 1.94, U4[1] + 3.0, 0, "F"),
    "C9": (U5[0] + 3.6, U5[1] - 0.8, 90, "F"),
    "R7": (U5[0] - 3.6, U5[1] - 0.8, 90, "F"),
    "C13": (U5[0] + 3.6, U5[1] + 2.0, 90, "F"),
    "C10": (17.3, 1.2, 0, "F"),
    "R8": (12.0, 3.16, 90, "F"),
    "C6": (11.6, 6.6, 0, "F"),
    # heading LED driver beside J2 (which opens N)
    "J2": (-14.0, -16.3, 180, "F"),
    "Q1": (-8.2, -12.3, 90, "F"),
    "R16": (-7.6, -9.6, 0, "F"),
    "R17": (-7.6, -8.5, 0, "F"),
    # S edge connectors, opening S into the groove
    "J4": (8.5, -26.4, 0, "F"),
    "J5": (-1.1, -26.4, 0, "F"),
    "R12": (7.8, -20.9, 0, "F"),
    "R13": (10.6, -20.9, 0, "F"),
    "D3": (7.8, -22.4, 0, "F"),
    "D4": (10.6, -22.4, 0, "F"),
    "D5": (-1.7, -22.4, 0, "F"),
    "D6": (0.9, -22.4, 0, "F"),
    # debug pads: bottom copper, flush, under the XIAO SWD pads / beside A0
    "TP13": (5.4, 12.0, 0, "B"),
    "TP14": (8.0, 12.0, 0, "B"),
    "TP15": (10.6, 12.0, 0, "B"),
    "TP10": (-6.5, 24.0, 0, "B"),
}

# ---------------- netlist ----------------
root = parse(open(NETLIST).read())
comps = {}
for c in root.child("components").children("comp"):
    ref = c.child("ref").items[1]
    sp = c.child("sheetpath")
    path = (sp.child("tstamps").items[1] if sp else "/") + c.child("tstamps").items[1]
    comps[ref] = dict(fp=c.child("footprint").items[1], value=c.child("value").items[1], path=path.replace("//", "/"))
nets = {}
for n in root.child("nets").children("net"):
    nets[n.child("name").items[1]] = [(x.child("ref").items[1], x.child("pin").items[1]) for x in n.children("node")]

# ---------------- footprint library resolution ----------------
LIBS = {}
for line in open(os.path.join(HW, "fp-lib-table")):
    m = re.search(r'\(name "([^"]+)"\).*\(uri "([^"]+)"\)', line)
    if m:
        LIBS[m.group(1)] = m.group(2).replace("${KIPRJMOD}", HW).replace("${KICAD8_FOOTPRINT_DIR}", KICAD_FP)


def load_fp(fpid):
    lib, name = fpid.split(":", 1)
    try:
        f = pcbnew.FootprintLoad(LIBS[lib], name)
    except Exception as e:
        raise SystemExit("footprint load failed: %s from %s (%s)" % (fpid, LIBS.get(lib), e))
    if f is None:
        raise SystemExit("footprint not found: " + fpid)
    return f


# ---------------- rebuild ----------------
board = pcbnew.LoadBoard(PCB)
board.RemoveAll()
board.SetCopperLayerCount(4)
board.RemoveUnusedNets(None)

netinfo = {}
for name in nets:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    netinfo[name] = ni

missing = [r for r in comps if r not in PLACE]
if missing:
    raise SystemExit("no placement for: %s" % missing)

fps = {}
for ref, c in comps.items():
    f = load_fp(c["fp"])
    f.SetReference(ref)
    f.SetValue(c["value"])
    f.SetPath(pcbnew.KIID_PATH(c["path"]))
    x, y, rot, side = PLACE[ref]
    board.Add(f)
    if side == "B":
        f.Flip(K(0, 0), False)
    f.SetPosition(K(x, y))
    f.SetOrientationDegrees(rot if side == "F" else -rot)
    f.Reference().SetVisible(True)
    f.Reference().SetLayer(pcbnew.B_Fab if side == "B" else pcbnew.F_Fab)
    f.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6)))
    f.Reference().SetTextThickness(mm(0.1))
    fps[ref] = f

for name, nodes in nets.items():
    for ref, pin in nodes:
        f = fps[ref]
        for pad in f.Pads():
            if pad.GetNumber() == pin:
                pad.SetNet(netinfo[name])

for ref in ("J2", "J4", "J5"):
    for pad in fps[ref].Pads():
        if pad.GetNumber() == "MP":
            pad.SetNet(netinfo["GND"])

for i, (x, y) in enumerate(HOLES):
    f = pcbnew.FootprintLoad(LIBS["MountingHole"], "MountingHole_2.2mm_M2")
    f.SetReference("H%d" % (i + 1))
    f.SetValue("M2 to ledge heat-set")
    f.SetAttributes(f.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    board.Add(f)
    f.SetPosition(K(x, y))
    f.Reference().SetVisible(False)

# outline
for s in segs:
    sh = pcbnew.PCB_SHAPE(board)
    sh.SetLayer(pcbnew.Edge_Cuts)
    sh.SetWidth(mm(0.1))
    if s[0] == "L":
        sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
        sh.SetStart(K(*s[1]))
        sh.SetEnd(K(*s[2]))
    else:
        (cx, cy), r, a0, a1 = s[1], s[2], s[3], s[4]
        pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in (a0, (a0 + a1) / 2, a1)]
        sh.SetShape(pcbnew.SHAPE_T_ARC)
        sh.SetArcGeometry(K(*pts[0]), K(*pts[1]), K(*pts[2]))
    board.Add(sh)

# spin-axis mark and origins
for layer in (pcbnew.User_1,):
    for a, b in (((-2, 0), (2, 0)), ((0, -2), (0, 2))):
        sh = pcbnew.PCB_SHAPE(board)
        sh.SetLayer(layer)
        sh.SetWidth(mm(0.1))
        sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
        sh.SetStart(K(*a))
        sh.SetEnd(K(*b))
        board.Add(sh)
ds = board.GetDesignSettings()
ds.SetAuxOrigin(K(0, 0))
ds.SetGridOrigin(K(0, 0))

board.Save(PCB)

# KiCad ships no 3D model for the vertical XT30s: point J6/J7 at the AMASS vendor STEPs in libs/3DModels,
# transformed into the footprint frame (pad 1 at the origin, chamfered end on the pad-1 side). Done as a text
# edit because FP_3DMODEL changes made through the python bindings do not persist.
XT30_MODELS = {
    "Connector_AMASS.3dshapes/AMASS_XT30UPB-M_1x02_P5.0mm_Vertical.step": ("XT30UPB-M_AMASS.step", "2.5 0 0", "-90 0 180"),
    "Connector_AMASS.3dshapes/AMASS_XT30UPB-F_1x02_P5.0mm_Vertical.step": ("XT30UPB-F_AMASS.step", "2.5 0 3.42", "0 0 180"),
}
txt = open(PCB).read()
for old, (new, off, rot) in XT30_MODELS.items():
    i = txt.index('(model "${KICAD10_3DMODEL_DIR}/' + old)
    j = txt.index("\n\t\t)\n", i)
    txt = txt[:i] + ('(model "${KIPRJMOD}/libs/3DModels/%s"\n\t\t\t(offset\n\t\t\t\t(xyz %s)\n\t\t\t)\n\t\t\t(scale\n'
                     '\t\t\t\t(xyz 1 1 1)\n\t\t\t)\n\t\t\t(rotate\n\t\t\t\t(xyz %s)\n\t\t\t)' % (new, off, rot)) + txt[j:]
open(PCB, "w").write(txt)

# report
print("footprints", len(board.GetFootprints()), "nets", len(nets))
crt = {}
for f in board.GetFootprints():
    bb = f.GetCourtyard(pcbnew.F_CrtYd if f.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd).BBox()
    crt[f.GetReference()] = (f.GetLayer(), bb)
refs = sorted(crt)
for i, a in enumerate(refs):
    for b in refs[i + 1:]:
        la, ba = crt[a]
        lb, bb = crt[b]
        if la == lb and ba.Intersects(bb) and ba.GetWidth() and bb.GetWidth():
            ov = ba.Intersect(bb)
            print("courtyard overlap", a, b, round(ov.GetWidth() / 1e6, 2), round(ov.GetHeight() / 1e6, 2))
for ref, pins in (("U4", ("1", "8", "5", "12")), ("U5", ("1", "6", "9", "14")), ("U6", ("1", "6", "9", "14"))):
    f = fps[ref]
    c = f.GetPosition()
    print(ref, "pad dirs (deg, chassis):", {n: round(math.degrees(math.atan2(-(p.GetPosition().y - c.y), p.GetPosition().x - c.x)) % 360) for p in f.Pads() for n in pins if p.GetNumber() == n})
for ref in ("U2",):
    f = fps[ref]
    print(ref, {p.GetNumber(): (round(p.GetPosition().x / 1e6 - OX, 2), round(OY - p.GetPosition().y / 1e6, 2)) for p in f.Pads()})
edge = board.GetBoardEdgesBoundingBox()
print("edges x %.2f..%.2f y %.2f..%.2f" % ((edge.GetLeft() / 1e6 - OX), (edge.GetRight() / 1e6 - OX), OY - edge.GetBottom() / 1e6, OY - edge.GetTop() / 1e6))
