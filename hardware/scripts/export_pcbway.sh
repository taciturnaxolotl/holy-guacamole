#!/bin/sh
# usage: scripts/export_pcbway.sh  (from hardware/)
# Writes the PCBWay order package to production/pcbway/ (gitignored; regenerate after every board change):
# gerbers + Excellon drills zipped, the top-side placement file, the assembly BOM, an assembly drawing, and the
# fab notes to paste into the order remarks. Stops if the board fails DRC, has a via hole in a pad, or the BOM
# still has a part without a part number.
set -e
cd "$(dirname "$0")/.."
O=production/pcbway
P=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
rm -rf $O
mkdir -p $O/gerbers
kicad-cli pcb drc --severity-error --exit-code-violations -o $O/drc.rpt guac.kicad_pcb >/dev/null 2>&1 || { grep "^\[" $O/drc.rpt | sort | uniq -c; echo "DRC failed: see $O/drc.rpt"; exit 1; }
rm $O/drc.rpt
$P scripts/check_vias_rev2.py guac.kicad_pcb 2>/dev/null
kicad-cli pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts \
  --subtract-soldermask --no-protel-ext --check-zones -o $O/gerbers/ guac.kicad_pcb >/dev/null
kicad-cli pcb export drill --format excellon --excellon-separate-th --drill-origin absolute -o $O/gerbers/ guac.kicad_pcb >/dev/null
# the position file follows the footprints' own flags: J1 (bare lap pads), the probe pads and the mounting holes are
# excluded in the schematic
kicad-cli pcb export pos --side front --format csv --units mm --exclude-dnp -o $O/positions_top.csv guac.kicad_pcb >/dev/null
python3 scripts/pcbway_bom.py $O/positions_top.csv $O/bom_pcbway.csv
# assembly drawing: references, outlines and pin-1 marks, which the silkscreen art leaves off the board
kicad-cli pcb export pdf --layers F.Fab,Edge.Cuts --mode-single --black-and-white --exclude-value -o $O/assembly_top.pdf guac.kicad_pcb >/dev/null
cp scripts/pcbway_notes.txt $O/NOTES.txt
(cd $O/gerbers && zip -q ../guac-gerbers.zip *)
echo "wrote $O"
