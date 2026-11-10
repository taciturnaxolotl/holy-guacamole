#!/usr/bin/env python3
"""Build the PCBWay assembly BOM from the board's top-side placement file.

Manufacturer part numbers come from hardware/procurement/ where the part is
listed there; parts added in rev 2 are listed in EXTRA below. The board is the
source of truth for which references exist.
"""

import csv
import sys
from collections import OrderedDict
from pathlib import Path

HW = Path(__file__).resolve().parent.parent
PROCUREMENT = [
    HW / "procurement" / "digikey_upload_3boards.csv",
    HW / "procurement" / "mouser_user_confirmed_3boards.csv",
]

EXTRA = {
    "D5": ("onsemi", "ESD5B5.0ST1G", "Bidirectional 5V ESD diode SOD-523"),
    "D6": ("onsemi", "ESD5B5.0ST1G", "Bidirectional 5V ESD diode SOD-523"),
    "J2": ("JST", "SM02B-GHS-TB(LF)(SN)", "JST-GH 2-pin SMD right-angle header"),
    "J4": ("JST", "SM04B-GHS-TB(LF)(SN)", "JST-GH 4-pin SMD right-angle header"),
    "J5": ("JST", "SM04B-GHS-TB(LF)(SN)", "JST-GH 4-pin SMD right-angle header"),
    "J6": ("AMASS", "XT30UPB-M", "XT30 male vertical PCB connector, through-hole"),
    "J7": ("AMASS", "XT30UPB-F", "XT30 female vertical PCB connector, through-hole"),
    "C21": ("TBD", "TBD", "100uF 25V polymer tantalum, EIA 7343-43, max 4.3 mm tall"),
}

NOT_PLACED = {
    "U1": "Do not place: customer hand-solders the XIAO RP2350 module",
}

# Footprints with no component: J1 is bare solder lap pads for 20 AWG wire.
NO_PART = {"J1"}


def procurement_mpns():
    mpns = {}
    for path in PROCUREMENT:
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                for ref in row["Customer Reference"].split():
                    mpns[ref] = (row["Manufacturer"], row["Manufacturer Part Number"], row["Description"])
    return mpns


def main(positions, out):
    known = procurement_mpns()
    known.update(EXTRA)
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
