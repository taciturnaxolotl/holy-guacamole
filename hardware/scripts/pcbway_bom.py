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

NOT_PLACED = {
    "U1": "Do not place: customer hand-solders the XIAO RP2350 module",
}

# Footprints with no component: J1 is bare solder lap pads for 20 AWG wire.
NO_PART = {"J1"}


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
            if ref in NO_PART:
                continue
            if ref in known:
                maker, mpn, desc = known[ref]
            else:
                maker, mpn, desc = "TBD", "TBD", row["Val"]
                missing.append(ref)
            note = NOT_PLACED.get(ref, "")
            if mpn == "TBD" and not note:
                note = "Part number not yet chosen"
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
        print("no manufacturer part number for: " + " ".join(missing), file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
