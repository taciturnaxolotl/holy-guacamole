"""Check for the rev-2 carrier: no via hole in or against an SMD pad's mask opening.

usage: <kicad python> scripts/check_vias_rev2.py guac.kicad_pcb    (exit status 1 if any is found)

A via inside a pad opening cannot be tented, so its hole wicks solder away from the joint during reflow; on an
0402 that can tombstone the part. KiCad's DRC does not flag it when the via and the pad share a net. The limit
is 0.1 mm from hole wall to pad edge, which keeps the hole under solder mask with the fab's registration.
Probe pads (TP*) carry no solder and are skipped.
"""
import sys

import pcbnew

MARGIN = 0.1
board = pcbnew.LoadBoard(sys.argv[1])
OX, OY = 80.0, 65.5
pads = [(f.GetReference(), p) for f in board.GetFootprints() for p in f.Pads()
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and not f.GetReference().startswith("TP")]
bad = 0
for v in board.GetTracks():
    if v.GetClass() != "PCB_VIA":
        continue
    hole = pcbnew.SHAPE_SEGMENT(v.GetPosition(), v.GetPosition(), v.GetDrillValue())
    for ref, p in pads:
        if p.GetNetCode() != v.GetNetCode():
            continue   # other nets keep the full copper clearance, which DRC checks
        for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
            if p.IsOnLayer(layer) and p.GetEffectiveShape(layer).Collide(hole, int(MARGIN * 1e6)):
                print("via hole at (%.2f, %.2f) is within %.1f mm of pad %s.%s [%s]" % (
                    v.GetPosition().x / 1e6 - OX, OY - v.GetPosition().y / 1e6, MARGIN, ref, p.GetNumber(), p.GetNetname()), flush=True)
                bad += 1
print("via-in-pad check:", "clean" if not bad else "%d found" % bad, flush=True)
sys.exit(1 if bad else 0)
