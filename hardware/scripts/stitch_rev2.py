"""Stage 5 for the rev-2 carrier: GND stitching vias.

usage: <kicad python> scripts/stitch_rev2.py guac.kicad_pcb

Candidates on a 3.5 mm grid, plus a ring 1.5 mm in from the board edge. A candidate is kept when it lands inside
the filled GND copper on F.Cu, In1 and B.Cu, keeps 0.215 mm from every other net's copper and pad, 0.41 mm
hole to hole from component holes, 0.3 mm from other vias and 0.1 mm from the opening of any GND SMD pad, and
stays out of keepouts. Then every B.Cu and
F.Cu GND piece still tied in by fewer than three vias gets more, where they fit. 0.64/0.25 mm vias,
near the smallest PCBWay normal-process via. Run after bridge_rev2.py; idempotent (removes its own vias
first, found by size and net).

Before the grid it places the signal tunnel's GND return vias (see power_rev2.py): up to three at each end of
the tunnel, as close to the lane vias as the routed fan-outs allow (GND on In1 and on at least one outer layer), so a signal's return current can change
planes where the signal does. They are 0.62 mm, which is how silk/clear_vias.py knows to leave them in place.
"""
import sys

import pcbnew

PCB = sys.argv[1]
OX, OY = 80.0, 65.5
D, DRILL = 0.64, 0.25   # 0.64 (not the 0.62 the router uses) so reruns can find and remove only these
CLR = 0.215
PITCH = 3.5


def M(v):
    return int(round(v * 1e6))


def K(x, y):
    return pcbnew.VECTOR2I(M(OX + x), M(OY - y))


board = pcbnew.LoadBoard(PCB)
GND = board.FindNet("GND")
LAYERS = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.B_Cu)

RETURN_D = 0.62
for t in list(board.GetTracks()):
    if t.GetClass() == "PCB_VIA" and t.GetNetCode() == GND.GetNetCode() and t.GetWidth(pcbnew.F_Cu) in (M(D), M(RETURN_D)) and t.GetDrillValue() == M(DRILL):
        board.Delete(t)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())

gnd_fill = {L: pcbnew.SHAPE_POLY_SET() for L in LAYERS}
keepout = pcbnew.SHAPE_POLY_SET()
for z in board.Zones():
    if z.GetIsRuleArea():
        if z.GetDoNotAllowVias():
            keepout.BooleanAdd(z.Outline())
        continue
    if z.GetNetCode() == GND.GetNetCode():
        for L in LAYERS:
            if z.IsOnLayer(L):
                gnd_fill[L].BooleanAdd(z.GetFilledPolysList(L))

# VBUS / VBAT_RAW copper on any layer, grown by the via radius and clearance: a GND via must not cut into it. (A
# grid via cannot, since it needs GND on all three layers; a tunnel return via only needs two.)
power_fill = []
for z in board.Zones():
    if not z.GetIsRuleArea() and z.GetNetname() in ("VBUS", "/Power Subsystem/VBAT_RAW"):
        for L in z.GetLayerSet().Seq():
            ps = pcbnew.SHAPE_POLY_SET(z.GetFilledPolysList(L))
            ps.Inflate(M(D / 2 + 0.3), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, M(0.005))
            power_fill.append(ps)

outline = pcbnew.SHAPE_POLY_SET()
board.GetBoardPolygonOutlines(outline, False)


def shrunk(ps, amount):
    out = pcbnew.SHAPE_POLY_SET(ps)
    out.Deflate(M(amount), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, M(0.005))
    return out


outline = shrunk(outline, D / 2 + 0.5)
gnd_fill = {L: shrunk(ps, D / 2) for L, ps in gnd_fill.items()}
keepout.Inflate(M(D / 2), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, M(0.005))
foreign = []
for t in board.GetTracks():
    if t.GetNetCode() != GND.GetNetCode():
        foreign += [(L, t.GetEffectiveShape(L)) for L in pcbnew.LSET.AllCuMask().Seq() if t.IsOnLayer(L)]
holes = []
gnd_pads = []
vias = [(t.GetPosition(), t.GetWidth(pcbnew.F_Cu) // 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
for f in board.GetFootprints():
    for p in f.Pads():
        if p.GetDrillSizeX() > 0:
            holes.append((p.GetPosition(), max(p.GetDrillSizeX(), p.GetDrillSizeY()) // 2))
        if p.GetNetCode() != GND.GetNetCode():
            foreign += [(L, p.GetEffectiveShape(L)) for L in pcbnew.LSET.AllCuMask().Seq() if p.IsOnLayer(L)]
        elif p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            # a via in or against a GND pad's mask opening cannot be tented and wicks the joint's solder
            gnd_pads += [p.GetEffectiveShape(L) for L in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(L)]


def ok(pt, need=3):
    """need: how many of F.Cu / In1 / B.Cu must have GND copper here (In1 always)"""
    r = M(D / 2)
    if not outline.Contains(pt):
        return False
    if not gnd_fill[pcbnew.In1_Cu].Contains(pt) or sum(gnd_fill[L].Contains(pt) for L in LAYERS) < need:
        return False
    if any(ps.Contains(pt) for ps in power_fill):
        return False
    if keepout.Contains(pt):
        return False
    dot = pcbnew.SHAPE_CIRCLE(pt, r)
    if any(sh.Collide(dot, M(CLR)) for _, sh in foreign):
        return False
    if any(sh.Collide(dot, M(0.1)) for sh in gnd_pads):
        return False
    if any((pt - c).EuclideanNorm() < M(DRILL / 2 + 0.41) + hr for c, hr in holes):
        return False
    return all((pt - c).EuclideanNorm() >= r + vr + M(0.3) for c, vr in vias)


def add(pt, d=D):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt)
    v.SetWidth(M(d))
    v.SetDrill(M(DRILL))
    v.SetNet(GND)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)
    vias.append((pt, M(D / 2)))


# tunnel return vias: lanes run x 1.0 .. 5.62 between via rows at y -4.95/-5.85 (N) and -13.95/-14.85 (S)
import math
returns = 0
for ya, ydir in ((-4.4, 1), (-15.4, -1)):
    got = []
    for xa in (0.3, 3.3, 6.3):
        best = None
        for iy in range(0, 31):
            for ix in range(-25, 26):
                x, y = xa + ix * 0.1, ya + ydir * iy * 0.1
                d = math.hypot(x - xa, y - ya)
                # In1 plus one outer GND pour is enough here: the via ties the pour beside the fan-out to the plane
                if (best is None or d < best[0]) and all(math.hypot(x - gx, y - gy) >= 1.2 for gx, gy in got) and ok(K(x, y), need=2):
                    best = (d, x, y)
        if best:
            add(K(best[1], best[2]), RETURN_D)
            got.append(best[1:])
            returns += 1
    print("tunnel return vias at y %.1f:" % ya, ["(%.1f, %.1f)" % g for g in got], flush=True)

cands = []
y = -36.5
while y <= 36.5:
    x = -18.5
    while x <= 18.5:
        cands.append((x, y))
        x += PITCH
    y += PITCH
for t in range(0, 201):
    s = t / 200.0
    cands += [(-18.5 + 37 * s, -36.5), (-18.5 + 37 * s, 36.5), (-18.5, -36.5 + 73 * s), (18.5, -36.5 + 73 * s)]
n = 0
for x, y in cands:
    pt = K(x, y)
    if ok(pt):
        add(pt)
        n += 1
print("stitching vias", n, flush=True)

# GND pieces on the outer layers that are still held by fewer than three vias: try a finer grid inside them
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
extra = 0
for L in (pcbnew.F_Cu, pcbnew.B_Cu):
    fill = pcbnew.SHAPE_POLY_SET()
    for z in board.Zones():
        if not z.GetIsRuleArea() and z.GetNetCode() == GND.GetNetCode() and z.IsOnLayer(L):
            fill.BooleanAdd(z.GetFilledPolysList(L))
    for i in range(fill.OutlineCount()):
        piece = pcbnew.SHAPE_POLY_SET(fill.Outline(i))
        held = sum(1 for c, _ in vias if piece.Contains(c))
        if held >= 3:
            continue
        bb = fill.Outline(i).BBox()
        y = bb.GetTop()
        while y <= bb.GetBottom() and held < 3:
            x = bb.GetLeft()
            while x <= bb.GetRight() and held < 3:
                pt = pcbnew.VECTOR2I(x, y)
                if piece.Contains(pt) and ok(pt):
                    add(pt)
                    held += 1
                    extra += 1
                x += M(0.5)
            y += M(0.5)
        if held < 3:
            c = bb.Centre()
            print("GND piece on %s near (%.1f, %.1f), %.1f mm2, only %d vias" % (board.GetLayerName(L), c.x / 1e6 - OX, OY - c.y / 1e6, piece.Area() / 1e12, held), flush=True)
print("extra vias for small pieces", extra, flush=True)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
