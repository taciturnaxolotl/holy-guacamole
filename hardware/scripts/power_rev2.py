"""Stage 2 for the rev-2 carrier: power copper (zones), the 5V backbone, and GND pours.
Run after layout_rev2.py with KiCad's python. Idempotent: it removes any zone/track it previously created
(identified by the User_2 marker text) before adding them again.

Power scheme (see docs/spec.md): the battery loop runs up the E edge on B.Cu as two adjacent strips,
VBUS inner (x 14.4..16.8) and VBAT_RAW outer (x 17.1..19.45), then both turn west along the N end to the J7
switch-loop XT30 (VBUS y 20.5..22.8, VBAT_RAW y 26.5..28.9). South of U6 the VBUS strip is on F.Cu along the
edge from J1 up past D2, with a via field at y about -2.5 taking it to the B.Cu strip. 5V runs on B.Cu from
the buck output up the W edge and east along y 24.3 to the XIAO 5V pad, between the two power strips.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(os.path.dirname(HERE), "guac.kicad_pcb")
OX, OY = 80.0, 65.5
MARK = "rev2-power"


def mm(v):
    return int(round(v * 1e6))


def K(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY - y))


board = pcbnew.LoadBoard(PCB)
GND, VBUS, VBAT, V5 = (board.FindNet(n) for n in ("GND", "VBUS", "/Power Subsystem/VBAT_RAW", "5V"))

for z in list(board.Zones()):
    if z.GetZoneName().startswith(MARK):
        board.Remove(z)
for t in list(board.GetTracks()):
    if t.HasFlag(pcbnew.IS_NEW) or t.GetNetname() in ("5V", "VBUS", "GND", "/Power Subsystem/VBAT_RAW"):
        board.Remove(t)


def zone(net, layer, polys, name, priority, clearance=0.3, min_w=0.25, thermal=False):
    """One ZONE per polygon (same net, overlapping rectangles merge electrically)."""
    out = []
    for i, poly in enumerate(polys):
        z = pcbnew.ZONE(board)
        z.SetNet(net)
        ls = pcbnew.LSET()
        ls.AddLayer(layer)
        z.SetLayerSet(ls)
        z.SetZoneName("%s %s %d" % (MARK, name, i))
        z.SetAssignedPriority(priority + i)
        z.SetLocalClearance(mm(clearance))
        z.SetMinThickness(mm(min_w))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL if thermal else pcbnew.ZONE_CONNECTION_FULL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.4))
        z.SetIsFilled(False)
        outline = z.Outline()
        outline.NewOutline()
        for x, y in poly:
            outline.Append(K(x, y))
        board.Add(z)
        out.append(z)
    return out


def rect(x0, x1, y0, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def via(x, y, net, d=0.8, drill=0.4):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(K(x, y))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetWidth(mm(d))
    v.SetDrill(mm(drill))
    v.SetNet(net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetIsFree(False)
    board.Add(v)
    return v


def track(pts, net, layer, w):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(K(*a))
        t.SetEnd(K(*b))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(net)
        board.Add(t)


B, F = pcbnew.B_Cu, pcbnew.F_Cu

# VBAT_RAW: J6 pin 2 stub -> outer E strip -> N strip -> J7 pin 2
zone(VBAT, B, [rect(13.0, 19.45, -12.0, -9.6), rect(17.1, 19.45, -12.0, 28.9), rect(-15.3, 19.45, 26.5, 28.9)],
     "VBAT_RAW B", 3)
# VBUS: F.Cu E edge from J1 pad 1 up past D2 to the via field, then B.Cu inner strip and N strip to J7 pin 1
zone(VBUS, F, [rect(16.9, 19.45, -29.3, -1.3), rect(14.4, 19.45, -3.9, -1.3)], "VBUS F edge", 3)
zone(VBAT, F, [rect(17.3, 19.45, 8.6, 28.9)], "VBAT_RAW F edge", 6)
for y in (9.6, 12.4, 15.2, 18.0, 20.8, 23.6, 26.4, 28.2):
    via(18.4, y, VBAT, d=0.8, drill=0.4)
zone(VBUS, B, [rect(14.4, 16.8, -3.7, 22.8), rect(-15.3, 16.8, 20.5, 22.8)], "VBUS B", 3)
for x in (14.9, 15.6, 16.3):
    for y in (-1.9, -2.6, -3.3):
        via(x, y, VBUS, d=0.7, drill=0.35)
# J1 pad 1 is SMD on F.Cu and already in the F.Cu strip; add vias so the B.Cu GND/pour side can carry current too
# (not needed for VBUS). J7 pin 1 is THT and lands in the B.Cu strip directly.

# 5V: via from the buck output node into the In2 5V pour; the pour reaches the XIAO 5V pad and J5
track([(-18.3, 10.05), (-16.1, 10.05)], V5, F, 0.6)
track([(-18.33, 14.55), (-18.33, 10.05)], V5, F, 0.6)
via(12.6, 25.4, V5, d=0.6, drill=0.3)
track([(12.6, 25.4), (14.8, 25.96)], V5, F, 0.4)

# VBUS branches too wide for the autorouter: C21 bulk cap (B.Cu, under the J6 pin 1 pad clearance) and the J2 LED feed
via(7.87, -18.0, VBUS, d=0.8, drill=0.4)
track([(7.87, -16.8), (7.87, -18.0)], VBUS, F, 1.0)
track([(7.87, -18.0), (7.87, -21.0), (9.5, -21.6), (16.0, -21.6), (17.5, -20.1), (17.5, -17.9)], VBUS, B, 1.2)
via(17.5, -17.9, VBUS, d=0.8, drill=0.4)

# VBUS branches the autorouter is not allowed to touch (VBUS/VBAT_RAW are removed from its netlist):
# buck input caps + VIN, UVLO dividers, VBAT divider, TinySLED feed
# buck input: VIN pin -> C2 (HF) -> C1, then east to C19/C20 and a via into the N VBUS strip; GND pin -> C2/C1 GND
track([(-9.3, 15.45), (-9.3, 16.4), (-10.02, 17.0)], VBUS, F, 0.5)
track([(-9.3, 16.4), (-8.7, 17.2), (-7.65, 17.2), (-7.65, 22.75)], VBUS, F, 0.6)
via(-7.65, 21.6, VBUS, d=0.8, drill=0.4)
track([(-11.7, 15.45), (-11.45, 16.4), (-10.98, 17.0)], GND, F, 0.4)
track([(-10.98, 17.0), (-10.98, 17.95), (-9.55, 17.95), (-9.55, 22.75)], GND, F, 0.5)
via(-3.52, 14.5, VBUS, d=0.6, drill=0.3)
track([(-3.52, 13.2), (-3.52, 15.8)], VBUS, F, 0.4)
track([(-3.52, 14.5), (-3.52, 20.8)], VBUS, B, 0.6)
track([(-4.6, 25.52), (-4.6, 22.0)], VBUS, F, 0.4)
via(-4.6, 22.0, VBUS, d=0.6, drill=0.3)
track([(7.87, -18.0), (7.87, -21.0), (6.5, -21.6), (-12.6, -21.6), (-13.38, -21.1), (-13.38, -19.9)], VBUS, B, 0.5)
via(-13.38, -19.9, VBUS, d=0.6, drill=0.3)
track([(-13.38, -19.9), (-13.38, -18.15)], VBUS, F, 0.4)

# inner layers: In1 solid GND, In2 split between 3V3 (centre) and 5V (W strip, N band, S band to J5)
V3 = board.FindNet("3V3")
I1, I2 = pcbnew.In1_Cu, pcbnew.In2_Cu
zone(GND, I1, [rect(-20, 20, -38, 38)], "GND In1", 0, clearance=0.2, min_w=0.2)
zone(V3, I2, [rect(-16.0, 19.45, -27.5, 23.4), rect(13.6, 19.45, 23.0, 29.9)], "3V3 In2", 1, clearance=0.2, min_w=0.25)
zone(V5, I2, [rect(-19.45, -16.5, -30.0, 29.9), rect(-19.45, 13.3, 23.8, 29.9), rect(-19.45, 0.5, -30.0, -28.0), rect(-19.45, -6.6, 9.4, 11.3)], "5V In2", 2, clearance=0.2, min_w=0.25)
via(-1.725, -29.0, V5, d=0.6, drill=0.3)
track([(-1.725, -29.0), (-1.725, -24.55)], V5, F, 0.3)

# plane fanout: every 3V3 / 5V SMD pad gets a via to the In2 pour. Pads are grouped per footprint edge and
# only adjacent pads share a via; candidate spots and the stub path are checked against every other pad and via.
import math
FANOUT_SKIP = {("U1", "14"), ("U1", "12"), ("U1", "28"), ("J5", "2"), ("U6", "1"), ("U6", "14"), ("U6", "15"), ("C10", "1"),
               ("U6", "5"), ("C10", "2"), ("U4", "6"), ("D5", "2"), ("U6", "10"), ("U6", "12"), ("U6", "13"), ("U6", "16")}
VIA_R = 0.3
CLR = 0.17
STUB_W = 0.25
all_pads = []
for fp in board.GetFootprints():
    for pad in fp.Pads():
        all_pads.append(((pad.GetParentAsString(), pad.GetNumber()), pad.GetNetname(), pad.GetEffectiveShape(pcbnew.F_Cu)))
placed_vias = [(v.GetPosition().x / 1e6 - OX, OY - v.GetPosition().y / 1e6, v.GetWidth() / 2e6) for v in board.GetTracks() if v.GetClass() == "PCB_VIA"]


STRIPS = [(17.1, 19.45, -12.0, 28.9), (17.3, 19.45, 8.6, 28.9), (-15.3, 19.45, 26.5, 28.9), (14.4, 16.8, -1.0, 22.8), (-15.3, 16.8, 20.5, 22.8)]


def in_strip(x, y, m=0.55):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x0, x1, y0, y1 in STRIPS)


def clear(vx, vy, net, own, stubs):
    if not (abs(vx) < 19.15 and abs(vy) < 37.0) or in_strip(vx, vy):
        return False
    vshape = pcbnew.SHAPE_CIRCLE(K(vx, vy), mm(VIA_R))
    sshapes = [pcbnew.SHAPE_SEGMENT(K(sx, sy), K(vx, vy), mm(STUB_W)) for sx, sy in stubs]
    for key, pnet, shape in all_pads:
        if key in own or pnet == net.GetNetname():
            continue
        gap = mm(CLR)
        if shape.Collide(vshape, gap):
            return False
        for s in sshapes:
            if shape.Collide(s, gap):
                return False
    for x, y, r in placed_vias:
        if math.hypot(vx - x, vy - y) < VIA_R + r + CLR:
            return False
    for tnet, tshape, tlayer in existing_tracks:
        if tnet == net.GetNetname():
            continue
        gap = mm(CLR)
        if tshape.Collide(vshape, gap):
            return False
        if tlayer == pcbnew.F_Cu:
            for s in sshapes:
                if tshape.Collide(s, gap):
                    return False
    return True


def escape(ref, num, length=0.9, via_net=True, width=0.2):
    """Stub straight out of an IC pad along the pad's own normal, ending in a via."""
    fp = board.FindFootprintByReference(ref)
    pad = next(p for p in fp.Pads() if p.GetNumber() == num)
    px, py = pad.GetPosition().x / 1e6 - OX, OY - pad.GetPosition().y / 1e6
    cx, cy = fp.GetPosition().x / 1e6 - OX, OY - fp.GetPosition().y / 1e6
    sz = pad.GetSize()
    ang = math.radians(pad.GetOrientation().AsDegrees())
    ax = (math.cos(ang), math.sin(ang)) if sz.x >= sz.y else (-math.sin(ang), math.cos(ang))
    if ax[0] * (px - cx) + ax[1] * (py - cy) < 0:
        ax = (-ax[0], -ax[1])
    ex, ey = px + ax[0] * length, py + ax[1] * length
    track([(px, py), (ex, ey)], pad.GetNet(), F, width)
    if via_net:
        via(ex, ey, pad.GetNet(), d=0.5, drill=0.3)
        placed_vias.append((ex, ey, 0.25))
    return ex, ey


for ref, num in (("U4", "13"), ("U5", "4"), ("U4", "1")):
    escape(ref, num)
def padxy(ref, num):
    pad = next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    return pad.GetPosition().x / 1e6 - OX, OY - pad.GetPosition().y / 1e6


c10_1 = padxy("C10", "1")
# U6 (rotated so its SPI pins face the board centre) sits over the E power strips: no vias under it.
u6 = {n: padxy("U6", n) for n in ("1", "4", "6", "7", "8", "14", "15")}
XE = 19.15
track([u6["14"], (XE, u6["14"][1]), (XE, 7.3), (u6["1"][0], 7.3), u6["1"]], V3, F, 0.2)
track([u6["15"], (XE, u6["15"][1])], V3, F, 0.2)
track([(u6["1"][0], 7.3), (16.5, 7.3), (16.5, 23.6), (16.75, 24.2)], V3, F, 0.3)
via(16.75, 24.2, V3, d=0.6, drill=0.3)
placed_vias.append((16.75, 24.2, 0.3))
track([c10_1, (c10_1[0], -0.2), (13.6, -0.2)], V3, F, 0.25)
via(13.6, -0.2, V3, d=0.5, drill=0.3)
placed_vias.append((13.6, -0.2, 0.25))
# U6 pad 5 (GND) is boxed in by the SCK/MOSI escapes: tie it to a via under the chip centre
u6_5 = padxy("U6", "5")
track([u6_5, (15.39, 6.13), (17.3, 4.96)], GND, F, 0.15)
via(17.3, 4.96, GND, d=0.5, drill=0.3)
placed_vias.append((17.3, 4.96, 0.25))
SCK = board.FindNet("/SPI_SCK")
track([u6["4"], (u6["4"][0], 6.9), (14.3, 6.9), (14.0, 6.6)], SCK, F, 0.2)
via(14.0, 6.6, SCK, d=0.5, drill=0.3)
placed_vias.append((14.0, 6.6, 0.25))
escape("U6", "6", length=3.3, width=0.15)
escape("U6", "7", length=2.5, width=0.15)
escape("U6", "8", length=3.3, width=0.15)

escape("U4", "6", length=1.2)
escape("R22", "1", length=1.1)
escape("D5", "2", length=1.5)

existing_tracks = [(tr.GetNetname(), tr.GetEffectiveShape(), tr.GetLayer()) for tr in board.GetTracks() if tr.GetClass() == "PCB_TRACK"]
groups = {}
for fp in board.GetFootprints():
    cx, cy = fp.GetPosition().x / 1e6 - OX, OY - fp.GetPosition().y / 1e6
    for pad in fp.Pads():
        if pad.GetNetname() not in ("3V3", "5V", "GND") or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or (fp.GetReference(), pad.GetNumber()) in FANOUT_SKIP:
            continue
        px, py = pad.GetPosition().x / 1e6 - OX, OY - pad.GetPosition().y / 1e6
        dx, dy = px - cx, py - cy
        side = ("E" if dx > 0 else "W") if abs(dx) >= abs(dy) else ("N" if dy > 0 else "S")
        groups.setdefault((fp.GetReference(), pad.GetNetname(), side), []).append((px, py, pad))
SIDE_ANG = {"E": 0, "N": 90, "W": 180, "S": 270}
for (ref, netname, side), items in groups.items():
    items.sort()
    clusters = [[items[0]]]
    for it in items[1:]:
        if math.hypot(it[0] - clusters[-1][-1][0], it[1] - clusters[-1][-1][1]) <= 0.75:
            clusters[-1].append(it)
        else:
            clusters.append([it])
    net = board.FindNet(netname)
    for cl in clusters:
        pts = [(x, y) for x, y, _ in cl]
        own = {(p.GetParentAsString(), p.GetNumber()) for _, _, p in cl}
        mx, my = sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)
        base = math.radians(SIDE_ANG[side])
        spot = None
        for reach in (0.9, 1.1, 1.4, 1.8, 2.3, 2.8):
            for da in (0, 25, -25, 50, -50, 75, -75, 100, -100, 130, -130):
                ang = base + math.radians(da)
                vx, vy = mx + reach * math.cos(ang), my + reach * math.sin(ang)
                if clear(vx, vy, net, own, pts):
                    spot = (vx, vy)
                    break
            if spot:
                break
        if spot is None:
            print("no fanout spot for", ref, netname, side, pts)
            continue
        vx, vy = spot
        via(vx, vy, net, d=0.6, drill=0.3)
        placed_vias.append((vx, vy, VIA_R))
        for x, y in pts:
            track([(x, y), (vx, vy)], net, F, STUB_W)

# XIAO 3V3: edge pad 12 runs under the module between the underside pads to share a via with pad 28 (3V3_OUT)
via(9.6, 23.1, V3, d=0.6, drill=0.3)
track([(7.99, 21.91), (9.6, 21.91), (9.6, 23.1)], V3, F, 0.3)
track([(14.8, 20.88), (9.6, 20.88), (9.6, 21.91)], V3, F, 0.25)

# buck feedback 5V sense from the output caps, and the SPI_SCK trunk from the XIAO to the latch area


# power strips on B.Cu: no foreign tracks or vias (the VBUS via field below y -1.0 is left open)
for name, (x0, x1, y0, y1) in {"VBAT E": (17.1, 19.45, -12.0, 28.9), "VBAT N": (-15.3, 19.45, 26.5, 28.9),
                               "VBUS E": (14.4, 16.8, -1.0, 22.8), "VBUS N": (-2.0, 16.8, 21.2, 22.8), "VBUS NW": (-15.3, -10.0, 20.5, 22.8)}.items():
    ka = pcbnew.ZONE(board)
    ka.SetIsRuleArea(True)
    ka.SetDoNotAllowTracks(True)
    ka.SetDoNotAllowVias(True)
    ka.SetDoNotAllowZoneFills(False)
    ka.SetDoNotAllowPads(False)
    ka.SetDoNotAllowFootprints(False)
    ka.SetDoNotAllowVias(False)
    ka.SetZoneName("%s strip keepout %s" % (MARK, name))
    kls = pcbnew.LSET()
    kls.AddLayer(B)
    ka.SetLayerSet(kls)
    ko = ka.Outline()
    ko.NewOutline()
    for pt in rect(x0, x1, y0, y1):
        ko.Append(K(*pt))
    board.Add(ka)

# no autorouted tracks on the inner layers (they are pours), and no tracks across the VBUS via field on B.Cu
for name, layers, (x0, x1, y0, y1) in (("VBUS via field", (B,), (14.4, 16.8, -3.9, -1.0)), ("VBUS N feeds", (B,), (-10.0, -2.0, 21.4, 22.8)),
                                       ("USB notch edge", (F, B), (-0.25, 13.65, 28.55, 38.1))):
    ka = pcbnew.ZONE(board)
    ka.SetIsRuleArea(True)
    ka.SetDoNotAllowTracks(True)
    ka.SetDoNotAllowVias(False)
    ka.SetDoNotAllowZoneFills(False)
    ka.SetDoNotAllowPads(False)
    ka.SetDoNotAllowFootprints(False)
    ka.SetZoneName("%s %s" % (MARK, name))
    kls = pcbnew.LSET()
    for l in layers:
        kls.AddLayer(l)
    ka.SetLayerSet(kls)
    ko = ka.Outline()
    ko.NewOutline()
    for pt in rect(x0, x1, y0, y1):
        ko.Append(K(*pt))
    board.Add(ka)

# battery sense divider: short F.Cu net plus the bottom-side test pad, hand routed
SNS = board.FindNet("/VBAT_SNS")
r9_2, r10_1, c12_1, tp10 = padxy("R9", "2"), padxy("R10", "1"), padxy("C12", "1"), padxy("TP10", "1")
track([padxy("U1", "1"), (-3.6, 25.96), (-4.1, r9_2[1]), r9_2, r10_1, (c12_1[0], r10_1[1]), c12_1], SNS, F, 0.25)
track([c12_1, (-6.5, c12_1[1]), (-6.5, 25.0)], SNS, F, 0.25)
via(-6.5, 25.0, SNS, d=0.5, drill=0.3)
placed_vias.append((-6.5, 25.0, 0.25))
track([(-6.5, 25.0), tp10], SNS, B, 0.3)

# edge keepout ring for the autorouter (KiCad's own 0.5 mm edge clearance is a DRC rule, not a routing obstacle)
ring = pcbnew.ZONE(board)
ring.SetIsRuleArea(True)
ring.SetDoNotAllowTracks(True)
ring.SetDoNotAllowVias(True)
ring.SetDoNotAllowZoneFills(False)
ring.SetDoNotAllowPads(False)
ring.SetDoNotAllowFootprints(False)
ring.SetZoneName("%s edge keepout" % MARK)
ls = pcbnew.LSET()
ls.AddLayer(pcbnew.F_Cu)
ls.AddLayer(pcbnew.B_Cu)
ring.SetLayerSet(ls)
o = ring.Outline()
o.NewOutline()
for pt in rect(-20.1, 20.1, -38.1, 38.1):
    o.Append(K(*pt))
hole = pcbnew.SHAPE_LINE_CHAIN()
for pt in rect(-19.45, 19.45, -37.45, 37.45):
    hole.Append(K(*pt))
hole.SetClosed(True)
o.AddHole(hole)
board.Add(ring)

# GND pours, both layers, lowest priority, thermals on SMD pads except the big power pads
zone(GND, F, [rect(-20, 20, -38, 38)], "GND F", 0, clearance=0.2, min_w=0.2, thermal=False)
zone(GND, B, [rect(-20, 20, -38, 38)], "GND B", 0, clearance=0.2, min_w=0.2, thermal=False)

# stitching vias for the ESC return: J6 pin 1 <-> J1 pad 2 region, plus a sparse grid elsewhere
for x, y in [(12.0, -24.5), (15.0, -24.5), (12.5, -17.5),
             (-18.5, 2.0), (-18.5, -5.0), (-18.5, -12.0), (-18.5, -22.0), (-18.5, 30.5), (18.5, 30.5),
             (-10.0, -31.0), (10.0, -31.0), (0.0, -31.0), (-17.0, 7.0), (0.0, -8.0), (-7.0, -4.0), (7.0, -4.0),
             (-12.0, -8.0), (9.0, 8.0)]:
    via(x, y, GND, d=0.6, drill=0.3)

# chassis v3.4e harness: LED leads and Y-splice lie on/just above the board top. Bottom lead: no parts at all
# (rule area); top lead and splice: low parts only (drawn on User.2 for reference, checked in cad/rev2).
HARNESS = {
    "LED_BOT_LEAD": [(-20.0, -26.95), (-19.9, -26.6), (-19.4, -24.0), (-19.4, -12.0), (-19.0, -7.5), (-16.4, -3.7), (-13.35, -3.9), (-13.35, -5.8)],
    "LED_TOP_LEAD": [(-17.9, -10.5), (-17.8, -9.4), (-17.2, -6.8), (-15.6, -5.0), (-14.65, -5.0), (-14.65, -5.8)],
}
for name, pts in HARNESS.items():
    track_layer = pcbnew.User_2
    for a_, b_ in zip(pts, pts[1:]):
        sh = pcbnew.PCB_SHAPE(board)
        sh.SetShape(pcbnew.SHAPE_T_SEGMENT)
        sh.SetLayer(track_layer)
        sh.SetWidth(mm(1.6))
        sh.SetStart(K(*a_))
        sh.SetEnd(K(*b_))
        board.Add(sh)
spl = pcbnew.PCB_SHAPE(board)
spl.SetShape(pcbnew.SHAPE_T_RECT)
spl.SetLayer(pcbnew.User_2)
spl.SetWidth(mm(0.1))
spl.SetStart(K(-15.0, -5.6))
spl.SetEnd(K(-13.0, -8.6))
board.Add(spl)
ra = pcbnew.ZONE(board)
ra.SetIsRuleArea(True)
ra.SetDoNotAllowFootprints(True)
ra.SetDoNotAllowTracks(False)
ra.SetDoNotAllowVias(False)
ra.SetDoNotAllowPads(False)
ra.SetDoNotAllowZoneFills(False)
ra.SetZoneName("%s harness LED_BOT_LEAD no parts" % MARK)
rls = pcbnew.LSET()
rls.AddLayer(F)
ra.SetLayerSet(rls)
ro = ra.Outline()
ro.NewOutline()
pts = HARNESS["LED_BOT_LEAD"]
left = [(x - 0.8, y) for x, y in pts]
right = [(x + 0.8, y) for x, y in pts]
for x, y in left + right[::-1]:
    ro.Append(K(x, y))
board.Add(ra)

# silkscreen labels at the connectors and the board name under the S ledge
for txt, x, y, size, rot in (("BAT", 10.1, -12.8, 1.0, 90), ("SW", -18.7, 24.3, 1.0, 90), ("ESC", 8.5, -31.0, 0.8, 0), ("RX", -1.1, -31.0, 0.8, 0),
                             ("LED", -14.0, -20.7, 0.8, 0), ("HOLY GUACAMOLE rev2", 0.0, -33.2, 1.0, 0), ("SWD/VBAT pads on bottom", 0.0, -35.0, 0.8, 0)):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(txt)
    tx.SetLayer(pcbnew.F_SilkS)
    tx.SetTextAngleDegrees(rot)
    tx.SetPosition(K(x, y))
    tx.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    tx.SetTextThickness(mm(0.15))
    board.Add(tx)
for txt, x, y in (("DIO", 5.4, 10.6), ("CLK", 8.0, 9.4), ("GND", 10.6, 10.6), ("VBAT", -6.5, 22.6)):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(txt)
    tx.SetLayer(pcbnew.B_SilkS)
    tx.SetMirrored(True)
    tx.SetPosition(K(x, y))
    tx.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    tx.SetTextThickness(mm(0.12))
    board.Add(tx)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.Save(PCB)
print("zones", len(board.Zones()), "tracks", len(board.GetTracks()))
