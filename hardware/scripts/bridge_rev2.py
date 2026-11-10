"""Stage 4 for the rev-2 carrier: finish what freerouting leaves open, then tidy.

usage: <kicad python> scripts/bridge_rev2.py guac.kicad_pcb

For every signal net still in more than one copper island, a grid router (0.05 mm cells, F.Cu and B.Cu) joins the
smallest island to the next one with a 0.18 mm track and 0.62/0.25 mm vias, keeping 0.215 mm from other copper,
power pours and keepouts (PCBWay normal process for 2 oz outer copper; GND pours refill around the result).
Then vias that freerouting left connected on one layer only are removed.
"""
import heapq
import math
import sys

import pcbnew

PCB = sys.argv[1]
STEP = 0.05
TW, CLR, VR = 0.18, 0.215, 0.31
VIA_COST = 40
POUR_NETS = ("GND", "VBUS", "/Power Subsystem/VBAT_RAW", "3V3", "5V")
LAYERS = [pcbnew.F_Cu, pcbnew.B_Cu]
# board outline in KiCad coordinates (chassis x -20..20, y -38..38; kx = 80 + x, ky = 65.5 - y), less 0.5 mm edge clearance
EX0, EX1, EY0, EY1 = 60.5, 99.5, 27.5, 103.5
EDGE = 0.5
X0, Y0 = EX0, EY0
NX, NY = int((EX1 - EX0) / STEP) + 1, int((EY1 - EY0) / STEP) + 1


def M(v):
    return int(round(v * 1e6))


def P(cell):
    return pcbnew.VECTOR2I(M(X0 + cell[1] * STEP), M(Y0 + cell[2] * STEP))


board = pcbnew.LoadBoard(PCB)


def islands(net):
    items = [t for t in board.GetTracks() if t.GetNetCode() == net.GetNetCode()]
    items += [p for f in board.GetFootprints() for p in f.Pads() if p.GetNetCode() == net.GetNetCode()]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            c = items[j]
            if any(a.IsOnLayer(L) and c.IsOnLayer(L) and a.GetEffectiveShape(L).Collide(c.GetEffectiveShape(L), 0) for L in LAYERS):
                parent[find(i)] = find(j)
    groups = {}
    for i in range(len(items)):
        groups.setdefault(find(i), []).append(items[i])
    return sorted(groups.values(), key=len)


def obstacles(net, radius, for_via):
    grid = {L: bytearray(NX * NY) for L in LAYERS}
    shapes = []
    for t in board.GetTracks():
        if t.GetNetCode() != net.GetNetCode():
            shapes += [(L, t.GetEffectiveShape(L), t.GetBoundingBox()) for L in LAYERS if t.IsOnLayer(L)]
    for f in board.GetFootprints():
        for p in f.Pads():
            if p.GetNetCode() != net.GetNetCode():
                shapes += [(L, p.GetEffectiveShape(L), p.GetBoundingBox()) for L in LAYERS if p.IsOnLayer(L)]
    for z in board.Zones():
        for L in LAYERS:
            if not z.IsOnLayer(L):
                continue
            if z.GetIsRuleArea():
                if z.GetDoNotAllowVias() if for_via else z.GetDoNotAllowTracks():
                    shapes.append((L, z.Outline(), z.GetBoundingBox()))
            elif z.GetNetname() != "GND" and z.GetNetCode() != net.GetNetCode():
                shapes.append((L, z.GetFilledPolysList(L), z.GetBoundingBox()))
    gap = M(radius + CLR)
    pad = radius + CLR
    for L, sh, box in shapes:
        ix0 = max(0, int((box.GetLeft() / 1e6 - X0 - pad) / STEP) - 1)
        ix1 = min(NX - 1, int((box.GetRight() / 1e6 - X0 + pad) / STEP) + 1)
        iy0 = max(0, int((box.GetTop() / 1e6 - Y0 - pad) / STEP) - 1)
        iy1 = min(NY - 1, int((box.GetBottom() / 1e6 - Y0 + pad) / STEP) + 1)
        g = grid[L]
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                k = iy * NX + ix
                if not g[k] and sh.Collide(pcbnew.VECTOR2I(M(X0 + ix * STEP), M(Y0 + iy * STEP)), gap):
                    g[k] = 1
    m = EDGE + radius
    for L in LAYERS:
        g = grid[L]
        for iy in range(NY):
            y = Y0 + iy * STEP
            for ix in range(NX):
                x = X0 + ix * STEP
                if not (EX0 + m <= x <= EX1 - m and EY0 + m <= y <= EY1 - m):
                    g[iy * NX + ix] = 1
    return grid


def cells_of(group):
    out = set()
    for it in group:
        bb = it.GetBoundingBox()
        for li, L in enumerate(LAYERS):
            if not it.IsOnLayer(L):
                continue
            sh = it.GetEffectiveShape(L)
            for iy in range(max(0, int((bb.GetTop() / 1e6 - Y0) / STEP)), min(NY, int((bb.GetBottom() / 1e6 - Y0) / STEP) + 1)):
                for ix in range(max(0, int((bb.GetLeft() / 1e6 - X0) / STEP)), min(NX, int((bb.GetRight() / 1e6 - X0) / STEP) + 1)):
                    if sh.Collide(pcbnew.VECTOR2I(M(X0 + ix * STEP), M(Y0 + iy * STEP)), 0):
                        out.add((li, ix, iy))
    return out


def route(net, src, dst):
    trk = obstacles(net, TW / 2, False)
    via = obstacles(net, VR, True)
    S, T = cells_of(src), cells_of(dst)
    dist, prev, pq = {}, {}, []
    for s in S:
        dist[s] = 0
        heapq.heappush(pq, (0, s))
    goal = None
    steps8 = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 1e18):
            continue
        if cur in T:
            goal = cur
            break
        li, ix, iy = cur
        nbrs = []
        for dx, dy, c in steps8:
            jx, jy = ix + dx, iy + dy
            if 0 <= jx < NX and 0 <= jy < NY and (not trk[LAYERS[li]][jy * NX + jx] or (li, jx, jy) in T):
                nbrs.append(((li, jx, jy), c))
        k = iy * NX + ix
        if not via[LAYERS[0]][k] and not via[LAYERS[1]][k]:
            nbrs.append(((1 - li, ix, iy), VIA_COST))
        for n, c in nbrs:
            if d + c < dist.get(n, 1e18):
                dist[n] = d + c
                prev[n] = cur
                heapq.heappush(pq, (d + c, n))
    if goal is None:
        return False
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()

    def visible(a, c):
        g = trk[LAYERS[a[0]]]
        n = int(max(abs(c[1] - a[1]), abs(c[2] - a[2])) * 4) + 1
        for s in range(n + 1):
            ix = int(round(a[1] + (c[1] - a[1]) * s / n))
            iy = int(round(a[2] + (c[2] - a[2]) * s / n))
            if g[iy * NX + ix] and (a[0], ix, iy) not in T and (a[0], ix, iy) not in S:
                return False
        return True

    # string-pull each single-layer run into the fewest straight segments the grid allows
    pts, i = [path[0]], 0
    while i < len(path) - 1:
        if path[i + 1][0] != path[i][0]:
            pts.append(path[i + 1])
            i += 1
            continue
        best, k = i + 1, i + 1
        while k < len(path) and path[k][0] == path[i][0]:
            if visible(path[i], path[k]):
                best = k
            k += 1
        pts.append(path[best])
        i = best
    for a, c in zip(pts, pts[1:]):
        if a[0] != c[0]:
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(P(a))
            v.SetWidth(M(2 * VR))
            v.SetDrill(M(0.25))
            v.SetNet(net)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            board.Add(v)
        elif (a[1], a[2]) != (c[1], c[2]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(a))
            t.SetEnd(P(c))
            t.SetWidth(M(TW))
            t.SetLayer(LAYERS[a[0]])
            t.SetNet(net)
            board.Add(t)
    return True


for code, net in sorted(board.GetNetsByNetcode().items()):
    name = net.GetNetname()
    if code == 0 or name in POUR_NETS or name.startswith("unconnected-"):
        continue
    groups = islands(net)
    while len(groups) > 1:
        ok = route(net, groups[0], groups[1])
        print("bridge", name, "ok" if ok else "NO PATH", flush=True)
        if not ok:
            break
        groups = islands(net)

# vias that only touch copper on one layer carry nothing: freerouting leaves them when it reaches a pre-placed
# escape via on the same layer as the escape track
one_sided = []
for v in [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() not in POUR_NETS]:
    used = []
    vid = v.m_Uuid.AsString()
    for L in LAYERS:
        shape = v.GetEffectiveShape(L)
        touch = any(o.m_Uuid.AsString() != vid and o.GetNetCode() == v.GetNetCode() and o.IsOnLayer(L) and o.GetEffectiveShape(L).Collide(shape, 0)
                    for o in board.GetTracks())
        touch = touch or any(p.GetNetCode() == v.GetNetCode() and p.IsOnLayer(L) and p.GetEffectiveShape(L).Collide(shape, 0)
                             for f in board.GetFootprints() for p in f.Pads())
        used.append(touch)
    if not all(used):
        print("removing one-sided via", v.GetNetname(), flush=True)
        one_sided.append(v)
for v in one_sided:
    board.Delete(v)


# then the escape stubs those vias ended, which now lead nowhere
def end_touches(t, pt):
    code, tid = t.GetNetCode(), t.m_Uuid.AsString()
    dot = pcbnew.SHAPE_CIRCLE(pt, t.GetWidth() // 2)
    for o in board.GetTracks():
        if o.GetNetCode() == code and o.m_Uuid.AsString() != tid and o.IsOnLayer(t.GetLayer()) and o.GetEffectiveShape(t.GetLayer()).Collide(dot, 0):
            return True
    return any(p.GetNetCode() == code and p.IsOnLayer(t.GetLayer()) and p.GetEffectiveShape(t.GetLayer()).Collide(dot, 0)
               for f in board.GetFootprints() for p in f.Pads())


while True:
    stubs = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() not in POUR_NETS
             and not (end_touches(t, t.GetStart()) and end_touches(t, t.GetEnd()))]
    if not stubs:
        break
    for t in stubs:
        print("removing dangling stub", t.GetNetname(), flush=True)
        board.Delete(t)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
board.Save(PCB)
