"""Stage 5 for the rev-2 carrier: GND stitching vias.

usage: <kicad python> scripts/stitch_rev2.py guac.kicad_pcb

Candidates on a 3.5 mm grid, plus a ring 1.5 mm in from the board edge. A candidate is kept when it lands inside
the filled GND copper on F.Cu, In1 and B.Cu, keeps 0.215 mm from every other net's copper and pad, 0.41 mm
hole to hole from component holes and 0.3 mm from other vias, and stays out of keepouts. Then every B.Cu and
F.Cu GND piece still tied in by fewer than three vias gets more, where they fit. 0.64/0.25 mm vias,
near the smallest PCBWay normal-process via. Run after bridge_rev2.py; idempotent (removes its own vias
first, found by size and net).
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

for t in list(board.GetTracks()):
    if t.GetClass() == "PCB_VIA" and t.GetNetCode() == GND.GetNetCode() and t.GetWidth(pcbnew.F_Cu) == M(D) and t.GetDrillValue() == M(DRILL):
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
vias = [(t.GetPosition(), t.GetWidth(pcbnew.F_Cu) // 2) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
for f in board.GetFootprints():
    for p in f.Pads():
        if p.GetDrillSizeX() > 0:
            holes.append((p.GetPosition(), max(p.GetDrillSizeX(), p.GetDrillSizeY()) // 2))
        if p.GetNetCode() != GND.GetNetCode():
            foreign += [(L, p.GetEffectiveShape(L)) for L in pcbnew.LSET.AllCuMask().Seq() if p.IsOnLayer(L)]


def ok(pt):
    r = M(D / 2)
    if not outline.Contains(pt):
        return False
    for L in LAYERS:
        if not gnd_fill[L].Contains(pt):
            return False
    if keepout.Contains(pt):
        return False
    dot = pcbnew.SHAPE_CIRCLE(pt, r)
    if any(sh.Collide(dot, M(CLR)) for _, sh in foreign):
        return False
    if any((pt - c).EuclideanNorm() < M(DRILL / 2 + 0.41) + hr for c, hr in holes):
        return False
    return all((pt - c).EuclideanNorm() >= r + vr + M(0.3) for c, vr in vias)


def add(pt):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt)
    v.SetWidth(M(D))
    v.SetDrill(M(DRILL))
    v.SetNet(GND)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(v)
    vias.append((pt, M(D / 2)))


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
