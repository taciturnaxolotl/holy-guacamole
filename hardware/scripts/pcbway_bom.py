#!/usr/bin/env python3
"""Build the PCBWay assembly BOM from the board's top-side placement file.

Manufacturer part numbers come from hardware/procurement/bom_rev2.csv. The board is the source of truth for which
references exist; any reference missing from the BOM is reported and listed as TBD.
"""

import csv
import sys
from collections import OrderedDict
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
BOM = HW / "procurement" / "bom_rev2.csv"

# Which parts are in the placement file at all is decided in the schematic (exclude from BOM / position files, DNP):
# J1 (bare lap pads), the probe pads and U1 (the XIAO module, fitted by hand) are left out there.

# Per-part instructions for the assembler.
_IMU = "Rotated on purpose (U4, U5 166 deg; U6 -164 deg): align pin 1 to the footprint's pin-1 mark, see assembly_top.pdf"
_XT30 = "Through-hole, hand or selective solder; trim the tails flush with the bottom of the board (0.3 mm to the chassis plate)"
_BIDIR = "Bidirectional, no polarity"
NOTES = {
    "U4": _IMU, "U5": _IMU, "U6": _IMU,
    "D2": _BIDIR, "D3": _BIDIR, "D4": _BIDIR, "D5": _BIDIR, "D6": _BIDIR,
    "C21": "Polarised: + (pad 1) on the E side, toward J6",
    "J6": _XT30, "J7": _XT30,
}


def procurement_mpns():
    mpns = {}
    with BOM.open(newline="") as f:
        for row in csv.DictReader(f):
            for ref in row["Designators"].split():
                mpns[ref] = (row["Manufacturer"], row["Manufacturer Part Number"], row["Description"])
    return mpns


def main(positions, out):
    known = procurement_mpns()
    groups = OrderedDict()
    missing = []
    with open(positions, newline="") as f:
        for row in csv.DictReader(f):
            ref = row["Ref"]
            if ref in known:
                maker, mpn, desc = known[ref]
            else:
                maker, mpn, desc = "TBD", "TBD", row["Val"]
                missing.append(ref)
            note = NOTES.get(ref, "")
            if mpn == "TBD":
                note = "Part number not yet chosen"
                missing.append(ref)
            key = (maker, mpn, desc, row["Package"], note)
            groups.setdefault(key, []).append(ref)

    def ref_key(ref):
        head = ref.rstrip("0123456789")
        return head, int(ref[len(head):] or 0)

    with open(out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Item #", "Designator", "Qty", "Manufacturer", "Mfg Part #", "Description / Value", "Package/Footprint", "Type", "Your Instructions / Notes"])
        rows = sorted(groups.items(), key=lambda item: ref_key(sorted(item[1], key=ref_key)[0]))
        for item, ((maker, mpn, desc, package, note), refs) in enumerate(rows, 1):
            refs = sorted(refs, key=ref_key)
            mount = "THT" if refs[0] in ("J6", "J7") else "SMD"
            writer.writerow([item, ",".join(refs), len(refs), maker, mpn, desc, package, mount, note])

    if missing:
        sys.exit("no manufacturer part number for: " + " ".join(sorted(set(missing))) + " (fill in procurement/bom_rev2.csv)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
