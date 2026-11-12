"""Stage 2 for the rev-2 carrier: power copper (zones), the 5V backbone, GND pours, the In2 signal tunnel, the IMU
escapes and the other hand routes, the plane fanout vias, and the keepouts the autorouter works inside.
Run after layout_rev2.py with KiCad's python. Idempotent: it first removes its own zones (named rev2-power...),
its back-side probe-pad labels, and every track and via, routed ones included, so the board always goes on to the
autorouter from the same state.

Power scheme (see docs/spec.md): J6 (battery) and J7 (switch loop) mirror each other about x = 0 at the S end
(chassis v3.4g). VBAT_RAW runs straight across between their N pins on B.Cu; VBUS
comes back on top of it on F.Cu, then down the E edge to J1 on F, B and In2. The signals that cross the band go
through an In2 tunnel. A thin VBUS feed runs up the W edge to the buck, the dividers and J2 (now in the NW).
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

# Remove() hands the item to Python; if the wrapper is then collected, KiCad 10's swig layer breaks and
# board.Tracks() stops returning a list. Holding the removed items until exit avoids that.
removed = []
for z in list(board.Zones()):
    if z.GetZoneName().startswith(MARK):
        board.Remove(z)
        removed.append(z)
for t in list(board.GetTracks()):
    board.Remove(t)
    removed.append(t)
SILK_BOTTOM = (("DIO", 4.2, 14.9), ("CLK", 6.4, 13.63), ("GND", 8.6, 12.36), ("VBAT", 10.8, 11.09))
for d in list(board.GetDrawings()):
    if d.GetClass() == "PCB_TEXT" and d.GetLayer() == pcbnew.B_SilkS and d.GetText() in [s[0] for s in SILK_BOTTOM]:
        board.Remove(d)
        removed.append(d)


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

# The drive motors run for the whole match, so the loop is sized for sustained current, not bursts. J6 (battery)
# and J7 (switch loop) mirror each other about x = 0 at the S end (chassis v3.4g), with both VBAT_RAW pins on
# y -10.8. VBAT_RAW runs straight across between them in a band on B.Cu; VBUS
# comes back right over it on F.Cu, then down the E edge to J1 on F, B and In2. Going out and coming back on
# top of each other, the two currents' fields cancel, and nothing carrying ESC current runs N of y -4.6 (D2's
# VBUS pad, a TVS, sits at y -2.4).
# Different outer layers keep the 1 mm VBUS to VBAT_RAW rule (guac.kicad_dru); the zone fills cut it around
# the other net's through-hole pins.
VBAT_BAND = (-15.3, 15.3, -13.3, -7.5)      # B.Cu
VBUS_BAND = (-15.3, 19.45, -13.3, -6.5)     # F.Cu, over VBAT_RAW
VBUS_J7 = (-15.3, -8.0, -17.0, -13.3)       # F.Cu (and B.Cu below the band) from J7 pin 1 up into the band
VBUS_E = (15.5, 19.45, -29.3, -2.4)         # E edge to J1 pad 1, on F, B and In2; takes D2's VBUS pad
VBUS_NE = (6.9, 19.45, -6.5, -4.6)          # F and B over the E half of the band: VBUS gets round J6's VBAT pin
VBUS_TONGUE = (-15.6, -13.5, -6.5, -5.3)    # F.Cu: start of the thin VBUS feed to the buck and J2
VBUS_C21 = (6.9, 8.85, -17.0, -13.3)        # F.Cu: C21's VBUS pad, right off the band
zone(VBAT, B, [rect(*VBAT_BAND)], "VBAT_RAW B", 3)
zone(VBUS, F, [rect(*VBUS_BAND), rect(*VBUS_J7), rect(*VBUS_E), rect(*VBUS_NE), rect(*VBUS_TONGUE), rect(*VBUS_C21)], "VBUS F", 3)
# B.Cu VBUS: below the band at J7, and the E edge plus the strip over the band's E half; the fill keeps the
# 1 mm outer-layer gap to the VBAT_RAW band and J6 pin 2 by itself
zone(VBUS, B, [rect(-15.3, -8.0, -17.0, -14.3), rect(*VBUS_E), rect(*VBUS_NE)], "VBUS B", 3)
# In2: a VBAT_RAW piece at each end of the band, tied to its own J6/J7 pin barrel; the middle is left for the
# signal tunnel below. Each piece hangs on one pin, so it carries no current: it is there to keep the In2 3V3
# plane out from under the battery band (1 mm local clearance holds it well back). VBUS doubles the E edge.
zone(VBAT, pcbnew.In2_Cu, [rect(-15.3, -0.5, -13.3, -7.5), rect(6.6, 15.3, -13.3, -7.5)], "VBAT_RAW In2", 12, clearance=1.0)
zone(VBUS, pcbnew.In2_Cu, [rect(15.5, 19.45, -29.3, -13.8)], "VBUS In2", 10, clearance=1.0)
for y in (-6.8, -8.6, -10.4, -12.2, -15.0, -16.6, -19.6, -21.2, -22.8, -24.4):
    for x in (17.4, 18.7):
        via(x, y, VBUS, d=0.75, drill=0.35)
for x in (7.6, 9.2, 10.8, 12.4, 14.0, 15.6):
    via(x, -5.55, VBUS, d=0.75, drill=0.35)
for x, y in ((-11.2, -15.0), (-10.0, -15.0), (-11.2, -16.4), (-10.0, -16.4), (-8.8, -15.0), (-8.8, -16.4)):
    via(x, y, VBUS, d=0.75, drill=0.35)
# J1 pad 2 (GND) reaches In1 through vias along its N edge, outside the pad so they don't wick its lap joint
for x in (14.0, 16.0):
    via(x, -24.6, GND, d=0.7, drill=0.3)

# Signal tunnel: F and B are both power copper across the band, so the eight signals that run between the N
# and S halves of the board cross it on In2, in short lanes between two staggered via rows just outside the
# band. 0.66 mm lane pitch keeps each lane 0.26 mm from the other row's vias and leaves a 0.70 mm gap between
# same-row vias, so a track can reach the deeper row. 3V3 crosses as a wider In2 lane
# that joins the In2 3V3 plane on both sides. The router connects to the lane vias like any escape via.
TUNNEL = (-0.4, 6.4, -15.4, -4.4)
TUNNEL_NETS = ("/SPI_SCK", "/SPI_MOSI", "/IMU Array/CS_B", "/SPI_MISO", "/CRSF_TX", "/CRSF_RX", "/DS1_IO", "/DS2_IO")
for i, name in enumerate(TUNNEL_NETS):
    n = board.FindNet(name)
    x = 1.0 + 0.66 * i
    yn, ys = (-5.85, -13.95) if i % 2 == 0 else (-4.95, -14.85)
    via(x, yn, n, d=0.62, drill=0.25)
    via(x, ys, n, d=0.62, drill=0.25)
    track([(x, yn), (x, ys)], n, pcbnew.In2_Cu, 0.18)
track([(0.2, -3.6), (0.2, -16.2)], board.FindNet("3V3"), pcbnew.In2_Cu, 0.4)
# (GND return vias for the tunnel go in after routing, where the fan-outs leave room: stitch_rev2.py)
ta = pcbnew.ZONE(board)
ta.SetIsRuleArea(True)
ta.SetDoNotAllowZoneFills(True)
ta.SetDoNotAllowTracks(False)
ta.SetDoNotAllowVias(False)
ta.SetDoNotAllowPads(False)
ta.SetDoNotAllowFootprints(False)
ta.SetZoneName("%s signal tunnel In2" % MARK)
tls = pcbnew.LSET()
tls.AddLayer(pcbnew.In2_Cu)
ta.SetLayerSet(tls)
to = ta.Outline()
to.NewOutline()
for pt in rect(*TUNNEL):
    to.Append(K(*pt))
board.Add(ta)

# The router does not see the In2 lanes as obstacles for its own vias, so fence the tunnel's outer edges
for name, (x0, x1, y0, y1) in (("tunnel W fence", (-0.25, -0.1, -16.4, -3.4)), ("tunnel E fence", (6.2, 6.4, -15.4, -4.4))):
    fz = pcbnew.ZONE(board)
    fz.SetIsRuleArea(True)
    fz.SetDoNotAllowVias(True)
    fz.SetDoNotAllowTracks(False)
    fz.SetDoNotAllowZoneFills(False)
    fz.SetDoNotAllowPads(False)
    fz.SetDoNotAllowFootprints(False)
    fz.SetZoneName("%s %s" % (MARK, name))
    fls = pcbnew.LSET()
    fls.AddLayer(F)
    fls.AddLayer(B)
    fz.SetLayerSet(fls)
    fo = fz.Outline()
    fo.NewOutline()
    for pt in rect(x0, x1, y0, y1):
        fo.Append(K(*pt))
    board.Add(fz)

# heading-LED driver: the gate node is three pads in 2 mm, so it is hand-routed (R16 pad 2, R17 pad 1, Q1 gate)
QG = board.FindNet("Net-(Q1-G)")
_r16, _r17, _q1 = (next(p for p in board.FindFootprintByReference(r).Pads() if p.GetNumber() == n) for r, n in (("R16", "2"), ("R17", "1"), ("Q1", "1")))
_xy = lambda p: (p.GetPosition().x / 1e6 - OX, OY - p.GetPosition().y / 1e6)
track([_xy(_r16), _xy(_r17), _xy(_q1)], QG, F, 0.25)

# 5V: L1 pad 2 straight N to C4; C5 and the rest of the rail through the In2 5V pour
track([(-18.33, 11.55), (-18.33, 15.95)], V5, F, 0.6)
via(12.6, 25.4, V5, d=0.7, drill=0.3)
track([(12.6, 25.4), (14.8, 25.96)], V5, F, 0.4)

# Thin VBUS feed (about 0.5 A: buck input, UVLO and VBAT dividers, TinySLEDs), B.Cu from the band's NW tongue up
# the W board edge (under the LED leads, clear of U4's fanout) to the buck input caps, then on to J2 pin 1. The autorouter never sees VBUS.
via(-14.8, -5.9, VBUS, d=0.75, drill=0.35)
track([(-14.8, -5.9), (-18.6, -5.9), (-18.6, 21.6), (-7.5, 21.6), (-6.6, 21.7)], VBUS, B, 0.8)
track([(-9.3, 15.45), (-9.3, 16.4), (-10.02, 17.0)], VBUS, F, 0.5)
track([(-9.3, 16.4), (-8.7, 17.2), (-7.65, 17.2), (-7.65, 22.75)], VBUS, F, 0.6)
# the feed's via sits just E of C19/C20 (between their pads its hole would be 0.03 mm from C19's opening)
track([(-7.65, 21.7), (-6.6, 21.7)], VBUS, F, 0.6)
via(-6.6, 21.7, VBUS, d=0.8, drill=0.4)
track([(-11.7, 15.45), (-11.45, 16.4), (-10.98, 17.0)], GND, F, 0.4)
track([(-10.98, 17.0), (-10.98, 17.95), (-9.55, 17.95), (-9.55, 22.75)], GND, F, 0.5)
via(-3.52, 14.5, VBUS, d=0.7, drill=0.3)
track([(-3.52, 14.5), (-3.52, 15.8)], VBUS, F, 0.4)
track([(-3.52, 14.5), (-3.52, 21.7), (-6.6, 21.7)], VBUS, B, 0.6)
track([(-4.6, 25.52), (-4.6, 22.0)], VBUS, F, 0.4)
via(-4.6, 22.0, VBUS, d=0.7, drill=0.3)
j2_1 = next(p for p in board.FindFootprintByReference("J2").Pads() if p.GetNumber() == "1")
_jx, _jy = j2_1.GetPosition().x / 1e6 - OX, OY - j2_1.GetPosition().y / 1e6
track([(-13.5, 21.6), (-13.5, 25.3), (_jx, 26.4)], VBUS, B, 0.6)
via(_jx, 26.4, VBUS, d=0.7, drill=0.3)
track([(_jx, 26.4), (_jx, _jy)], VBUS, F, 0.4)

# inner layers: In1 solid GND, In2 split between 3V3 (centre) and 5V (W strip, N band, S band to J5). GND takes
# whatever In2 the rails leave, which is the N and S ends of the board: it evens up the copper between the two
# inner layers. Lowest priority, so it never displaces a rail, and the gaps between rails are too narrow for it.
V3 = board.FindNet("3V3")
I1, I2 = pcbnew.In1_Cu, pcbnew.In2_Cu
zone(GND, I1, [rect(-20, 20, -38, 38)], "GND In1", 0, clearance=0.2, min_w=0.2)
zone(GND, I2, [rect(-20, 20, -38, 38)], "GND In2", 0, clearance=0.2, min_w=0.25)
zone(V3, I2, [rect(-16.0, 19.45, -27.5, 23.4), rect(13.6, 19.45, 23.0, 29.9)], "3V3 In2", 1, clearance=0.2, min_w=0.25)
zone(V5, I2, [rect(-19.45, -16.5, -30.0, 29.9), rect(-19.45, 13.3, 23.8, 29.9), rect(-19.45, 0.5, -30.0, -28.0), rect(-19.45, -6.6, 9.4, 11.3)], "5V In2", 2, clearance=0.2, min_w=0.25)
via(-1.725, -29.0, V5, d=0.7, drill=0.3)
track([(-1.725, -29.0), (-1.725, -24.55)], V5, F, 0.3)

# plane fanout: every 3V3 / 5V SMD pad gets a via to the In2 pour. Pads are grouped per footprint edge and
# only adjacent pads share a via; candidate spots and the stub path are checked against every other pad and via.
import math
FANOUT_SKIP = {("J1", "2"), ("C13", "2"), ("U1", "14"), ("U1", "12"), ("U1", "28"), ("J5", "2"), ("U6", "1"), ("U6", "14"), ("U6", "15"), ("C10", "1"),
               ("U6", "5"), ("C10", "2"), ("U4", "6"), ("D5", "2"), ("U6", "10"), ("U6", "12"), ("U6", "13"), ("U6", "16")}
VIA_R = 0.35
CLR = 0.22
STUB_W = 0.25
PAD_GAP = 0.1   # via copper to the edge of any SMD pad, its own included: a via in or against a pad's mask opening
                # cannot be tented and wicks the joint's solder down the hole
all_pads = []
smd_pads = []
for fp in board.GetFootprints():
    for pad in fp.Pads():
        all_pads.append(((pad.GetParentAsString(), pad.GetNumber()), pad.GetNetname(), pad.GetEffectiveShape(pcbnew.F_Cu)))
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and pad.IsOnLayer(pcbnew.F_Cu):
            smd_pads.append(pad.GetEffectiveShape(pcbnew.F_Cu))
placed_vias = [(v.GetPosition().x / 1e6 - OX, OY - v.GetPosition().y / 1e6, v.GetWidth() / 2e6) for v in board.GetTracks() if v.GetClass() == "PCB_VIA"]


STRIPS = [VBAT_BAND, VBUS_BAND, VBUS_J7, VBUS_E, VBUS_NE, VBUS_TONGUE, VBUS_C21, TUNNEL]


def in_strip(x, y, m=0.85):
    return any(x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m for x0, x1, y0, y1 in STRIPS)


def clear(vx, vy, net, own, stubs):
    if not (abs(vx) < 19.45 - VIA_R and abs(vy) < 37.45 - VIA_R) or in_strip(vx, vy):
        return False
    vshape = pcbnew.SHAPE_CIRCLE(K(vx, vy), mm(VIA_R))
    if any(shape.Collide(vshape, mm(PAD_GAP)) for shape in smd_pads):
        return False
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
        via(ex, ey, pad.GetNet(), d=0.7, drill=0.3)
        placed_vias.append((ex, ey, 0.35))
    return ex, ey


for ref, num in (("U5", "4"), ("U4", "1")):
    escape(ref, num)
def padxy(ref, num):
    pad = next(p for p in board.FindFootprintByReference(ref).Pads() if p.GetNumber() == num)
    return pad.GetPosition().x / 1e6 - OX, OY - pad.GetPosition().y / 1e6


c10_1 = padxy("C10", "1")
# U6 (rotated so its SPI pins face the board centre) is fanned out by hand, with one GND via under its centre.
u6 = {n: padxy("U6", n) for n in ("1", "4", "6", "7", "8", "14", "15")}
XE = 19.15
track([u6["14"], (XE, u6["14"][1]), (XE, 7.3), (u6["1"][0], 7.3), u6["1"]], V3, F, 0.2)
track([u6["15"], (XE, u6["15"][1])], V3, F, 0.2)
track([(u6["1"][0], 7.3), (16.75, 7.3), (16.75, 8.45)], V3, F, 0.3)
via(16.75, 8.45, V3, d=0.7, drill=0.3)
placed_vias.append((16.75, 8.45, 0.35))
track([c10_1, (c10_1[0], -0.2), (13.6, -0.2)], V3, F, 0.25)
via(13.6, -0.2, V3, d=0.7, drill=0.3)
placed_vias.append((13.6, -0.2, 0.35))
via(17.3, 4.96, GND, d=0.7, drill=0.3)
placed_vias.append((17.3, 4.96, 0.35))
SCK = board.FindNet("/SPI_SCK")
# leave pad 4 along its own (tilted) axis so the 0.2 mm track keeps the pad-to-pad gap to pad 3
_s = math.radians(next(p for p in board.FindFootprintByReference("U6").Pads() if p.GetNumber() == "4").GetOrientation().AsDegrees())
_sx, _sy = -math.sin(_s), math.cos(_s)
if _sy < 0:
    _sx, _sy = -_sx, -_sy
_l = (6.9 - u6["4"][1]) / _sy
track([u6["4"], (u6["4"][0] + _l * _sx, 6.9), (14.3, 6.9), (14.0, 6.6)], SCK, F, 0.2)
via(14.0, 6.6, SCK, d=0.7, drill=0.3)
placed_vias.append((14.0, 6.6, 0.35))
# Three SPI pads in a row at 0.5 mm pitch are too close for three vias in a row: the middle pad escapes
# straight out and the outer two step out 0.5 mm, then fan off at 45 degrees on either side of it
def fan3(ref, mid, outer, diag=1.0):
    fp = board.FindFootprintByReference(ref)
    pm = next(p for p in fp.Pads() if p.GetNumber() == mid)
    a = math.radians(pm.GetOrientation().AsDegrees())
    sz = pm.GetSize()
    nx, ny = (math.cos(a), math.sin(a)) if sz.x >= sz.y else (-math.sin(a), math.cos(a))
    cx, cy = padxy(ref, mid)
    fx, fy = fp.GetPosition().x / 1e6 - OX, OY - fp.GetPosition().y / 1e6
    if nx * (cx - fx) + ny * (cy - fy) < 0:
        nx, ny = -nx, -ny
    for num in (mid,) + outer:
        pad = next(p for p in fp.Pads() if p.GetNumber() == num)
        px, py = padxy(ref, num)
        if num == mid:
            ex, ey = px + 1.6 * nx, py + 1.6 * ny
            pts = [(px, py), (ex, ey)]
        else:
            side = 1 if (-ny * (px - cx) + nx * (py - cy)) > 0 else -1
            kx, ky = px + 0.5 * nx, py + 0.5 * ny
            ex, ey = kx + diag * 0.707 * (nx - side * ny), ky + diag * 0.707 * (ny + side * nx)
            pts = [(px, py), (kx, ky), (ex, ey)]
        track(pts, pad.GetNet(), F, 0.18)
        via(ex, ey, pad.GetNet(), d=0.7, drill=0.3)
        placed_vias.append((ex, ey, 0.35))


# U6's W side: GND pad 5 (boxed in by the SCK escape, and the chip interior is too tight for a 0.18 mm track)
# and SPI pads 6-8 run out as four
# parallel lanes, each jogging 45 degrees to a 0.95 mm lane spacing so the 0.7 mm vias sit side by side.
def lanes(ref, mid, reach, plan):
    fp = board.FindFootprintByReference(ref)
    pm = next(p for p in fp.Pads() if p.GetNumber() == mid)
    a = math.radians(pm.GetOrientation().AsDegrees())
    sz = pm.GetSize()
    nx, ny = (math.cos(a), math.sin(a)) if sz.x >= sz.y else (-math.sin(a), math.cos(a))
    cx, cy = padxy(ref, mid)
    fx, fy = fp.GetPosition().x / 1e6 - OX, OY - fp.GetPosition().y / 1e6
    if nx * (cx - fx) + ny * (cy - fy) < 0:
        nx, ny = -nx, -ny
    px_, py_ = -ny, nx
    # lateral axis points from the middle pad toward the first pad in the plan
    fx0, fy0 = padxy(ref, plan[0][0])
    if (fx0 - cx) * px_ + (fy0 - cy) * py_ < 0:
        px_, py_ = -px_, -py_
    world = lambda n, p: (cx + n * nx + p * px_, cy + n * ny + p * py_)
    for num, pt, jog in plan:
        pad = next(p for p in fp.Pads() if p.GetNumber() == num)
        x, y = padxy(ref, num)
        n0, p0 = (x - cx) * nx + (y - cy) * ny, (x - cx) * px_ + (y - cy) * py_
        pts = [(x, y), world(jog, p0), world(jog + abs(pt - p0), pt), world(reach, pt)]
        track(pts, pad.GetNet(), F, 0.18)
        ex, ey = pts[-1]
        via(ex, ey, pad.GetNet(), d=0.7, drill=0.3)
        placed_vias.append((ex, ey, 0.35))


# (pad, lane offset from pad 7, where its 45 degree jog starts): the outer lane on each side jogs first
lanes("U6", "7", 2.9, (("5", 1.6, 0.5), ("6", 0.65, 0.8), ("7", -0.3, 1.3), ("8", -1.25, 0.5)))
fan3("U5", "7", ("6", "8"), diag=0.85)  # keeps the CS_B via off R7
fan3("U4", "13", ("12", "14"))

escape("U4", "6", length=1.1)
# U5 SCK: its escape via is boxed in by U5's own fanout and C13, so it gets a hand-routed B.Cu run to its tunnel
# via, along the S edge of the power band
def via_near(netname, x, y):
    v = next(v for v in board.GetTracks() if v.GetClass() == "PCB_VIA" and v.GetNetname() == netname
             and abs(v.GetPosition().x / 1e6 - OX - x) < 0.6 and abs(OY - v.GetPosition().y / 1e6 - y) < 0.6)
    return v.GetPosition().x / 1e6 - OX, OY - v.GetPosition().y / 1e6


_vx, _vy = via_near("/SPI_SCK", -4.3, -15.2)
track([(_vx, _vy), (_vx + (_vy + 13.95), -13.95), (1.0, -13.95)], SCK, B, 0.18)
# The S end of the tunnel is as tight as the lanes themselves, and left to itself the autorouter strands one
# or two of the signals there (they then went 60 mm round the W end of the band, past the switch pins). So the
# rest of U5's SPI lines are drawn too, on B.Cu. MOSI comes in from the W under SCK. MISO_B drops S past the
# CS_B via to a via of its own and doubles back on F.Cu to R7; CS_B and MISO (from a via W of R7) go S round
# that, then E and up between the deeper row's vias. DSHOT 1 drops straight out of its lane on F.Cu, under C21,
# to R12.
track([via_near("/SPI_MOSI", -6.46, -15.81), (-5.9, -15.86), (-3.45, -15.86), (-2.44, -14.85), (1.66, -14.85)], board.FindNet("/SPI_MOSI"), B, 0.18)
MISO_B, MISO = board.FindNet("/IMU Array/MISO_B"), board.FindNet("/SPI_MISO")
_r7_1, _r7_2 = padxy("R7", "1"), padxy("R7", "2")
track([via_near("/IMU Array/MISO_B", -7.21, -16.75), (-6.18, -17.78), (-6.18, -20.3)], MISO_B, B, 0.18)
via(-6.18, -20.3, MISO_B, d=0.62, drill=0.25)
track([(-6.18, -20.3), (-6.18 - (_r7_1[1] + 20.3), _r7_1[1]), _r7_1], MISO_B, F, 0.18)
_cx, _cy = via_near("/IMU Array/CS_B", -6.99, -17.94)
track([(_cx, _cy), (_cx, -21.2), (_cx + 0.4, -21.6), (0.3, -21.6), (2.32, -19.58), (2.32, -13.95)], board.FindNet("/IMU Array/CS_B"), B, 0.18)
_mx = _r7_2[0] - 1.0
via(_mx, _r7_2[1], MISO, d=0.62, drill=0.25)
track([_r7_2, (_mx, _r7_2[1])], MISO, F, 0.18)
track([(_mx, _r7_2[1]), (_mx, -21.6), (_mx + 0.5, -22.1), (1.2, -22.1), (2.98, -20.32), (2.98, -14.85)], MISO, B, 0.18)
for _p in ((-6.18, -20.3, 0.31), (_mx, _r7_2[1], 0.31)):
    placed_vias.append(_p)
# N end: CS_B's lane via sits in the middle of the row with U11 pin 1 straight above it, and the autorouter boxes
# it in with its neighbours' fan-outs about one run in three, so it goes straight up on F.Cu between the two
# upper-row vias
track([(2.32, -5.85), (2.32, padxy("U11", "1")[1])], board.FindNet("/IMU Array/CS_B"), F, 0.18)
# and the other three vias of the lower row get a short F.Cu stub out past the upper row, so a neighbour's
# fan-out cannot close the 0.7 mm gap they leave through; the autorouter picks each one up at its N end
for _n, _x in (("/SPI_SCK", 1.0), ("/CRSF_TX", 3.64), ("/DS1_IO", 4.96)):
    track([(_x, -5.85), (_x, -3.9)], board.FindNet(_n), F, 0.18)
_r12 = padxy("R12", "1")
track([(4.96, -13.95), (4.96, -18.6), (4.96 + (-18.6 - _r12[1]), _r12[1]), _r12], board.FindNet("/DS1_IO"), F, 0.18)
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
# IC pads first: they have the fewest places to put a via, and a capacitor next door can take another spot
for (ref, netname, side), items in sorted(groups.items(), key=lambda g: not g[0][0].startswith("U")):
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
        # on rotated parts (the IMUs) the pad axis is off the compass side; a stub along the true axis keeps
        # the pad-to-pad gap to its neighbours
        tilt = (board.FindFootprintByReference(ref).GetOrientationDegrees() + 45) % 90 - 45
        spot = None
        for reach in (0.9, 1.1, 1.4, 1.8, 2.3, 2.8, 3.3):
            for da in (0, tilt, 25, -25, 50, -50, 75, -75, 100, -100, 130, -130, 155, -155, 180):
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
        via(vx, vy, net, d=0.7, drill=0.3)
        placed_vias.append((vx, vy, VIA_R))
        for x, y in pts:
            track([(x, y), (vx, vy)], net, F, STUB_W)

# XIAO 3V3: edge pad 12 runs under the module between the underside pads to share a via with pad 28 (3V3_OUT)
via(9.6, 23.1, V3, d=0.7, drill=0.3)
track([(7.99, 21.91), (9.6, 21.91), (9.6, 23.1)], V3, F, 0.3)
track([(14.8, 20.88), (9.6, 20.88), (9.6, 21.91)], V3, F, 0.25)

# power copper: no autorouted tracks on it (keepouts are net-blind, so they allow vias; the pours themselves
# keep foreign vias out). VBAT_RAW is on B.Cu (and In2 at the band ends) with VBUS on F.Cu over it, so signals
# cross the band only through the In2 tunnel.
G = 0.5


def grow(r, w=G, s=G, e=G, n=G):
    return (r[0] - w, r[1] + e, r[2] - s, r[3] + n)


for name, layers, (x0, x1, y0, y1) in (("VBAT_RAW B", (B,), grow(VBAT_BAND)), ("VBUS band F", (F,), grow(VBUS_BAND, e=0)),
                                       ("VBUS J7", (F, B), grow(VBUS_J7)), ("VBUS E", (F, B), grow(VBUS_E, e=0, s=0)), ("VBUS NE", (F, B), grow(VBUS_NE, e=0)),
                                       ("VBUS tongue", (F,), grow(VBUS_TONGUE)), ("VBUS C21", (F,), grow(VBUS_C21)),
                                       ("USB notch edge", (F, B), (-0.25, 13.65, 28.55, 38.1)),
                                       # the only way round the band is the strip W of J7: closed, so every signal that
                                       # crosses takes its tunnel lane instead of a 60 mm detour past the switch pins
                                       ("W bypass", (F, B), (-19.6, -15.8, -17.6, -6.8))):
    ka = pcbnew.ZONE(board)
    ka.SetIsRuleArea(True)
    ka.SetDoNotAllowTracks(True)
    ka.SetDoNotAllowVias(False)
    ka.SetDoNotAllowZoneFills(False)
    ka.SetDoNotAllowPads(False)
    ka.SetDoNotAllowFootprints(False)
    ka.SetZoneName("%s keepout %s" % (MARK, name))
    kls = pcbnew.LSET()
    for l in layers:
        kls.AddLayer(l)
    ka.SetLayerSet(kls)
    ko = ka.Outline()
    ko.NewOutline()
    for pt in rect(x0, x1, y0, y1):
        ko.Append(K(*pt))
    board.Add(ka)

# ESD clamp to connector pin, both connectors: four 2 mm hops the autorouter sometimes leaves open, so they are
# drawn here: down out of the diode pad, across below the diode, down into the pin (1.25 mm pin pitch, 0.18 mm)
for d, j, n in (("D5", "J5", "3"), ("D6", "J5", "4"), ("D3", "J4", "2"), ("D4", "J4", "3")):
    dp = next(p for p in board.FindFootprintByReference(d).Pads() if p.GetNumber() == "1")
    jp = next(p for p in board.FindFootprintByReference(j).Pads() if p.GetNumber() == n)
    (dx, dy), (jx, jy) = padxy(d, "1"), padxy(j, n)
    track([(dx, dy), (dx, dy - 1.0), (jx, dy - 1.0), (jx, jy)], dp.GetNet(), F, 0.18)

# battery sense divider: the short F.Cu net is hand routed; the autorouter takes it on to the TP10 test pad
SNS = board.FindNet("/VBAT_SNS")
r9_2, r10_1, c12_1 = padxy("R9", "2"), padxy("R10", "1"), padxy("C12", "1")
track([padxy("U1", "1"), (-3.6, 25.96), (-4.1, r9_2[1]), r9_2, r10_1, (c12_1[0], r10_1[1]), c12_1], SNS, F, 0.25)

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

# GND pours, both layers, lowest priority, solid pad connections
zone(GND, F, [rect(-20, 20, -38, 38)], "GND F", 0, clearance=0.21, min_w=0.2, thermal=False)
zone(GND, B, [rect(-20, 20, -38, 38)], "GND B", 0, clearance=0.21, min_w=0.2, thermal=False)

# stitching vias: a sparse grid for the pours (stitch_rev2.py adds the dense stitching after routing)
for x, y in [(12.0, -24.5), (12.5, -19.5), (-18.5, 30.5), (18.5, 30.5),
             (0.0, -6.0), (-7.0, -4.0), (-12.0, -6.5), (9.0, 8.0), (17.5, 12.0), (17.5, 20.0)]:
    if not in_strip(x, y):
        via(x, y, GND, d=0.7, drill=0.3)

# probe-pad labels on the back (the top-side legend is all drawn by silk/silk_rev2.py)
for txt, x, y in SILK_BOTTOM:
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(txt)
    tx.SetLayer(pcbnew.B_SilkS)
    tx.SetMirrored(True)
    tx.SetTextAngleDegrees(-30)
    tx.SetPosition(K(x - 1.3 * math.cos(math.radians(60)), y - 1.3 * math.sin(math.radians(60))))
    tx.SetTextSize(pcbnew.VECTOR2I(mm(0.8), mm(0.8)))
    tx.SetTextThickness(mm(0.15))
    board.Add(tx)

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.Save(PCB)
print("zones", len(board.Zones()), "tracks", len(board.GetTracks()))
