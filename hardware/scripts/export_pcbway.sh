#!/bin/sh
# usage: scripts/export_pcbway.sh  (from hardware/)
# Writes the PCBWay order package to production/pcbway/ (gitignored; regenerate after every board change):
# gerbers + Excellon drills zipped, the top-side placement file, and the assembly BOM.
set -e
cd "$(dirname "$0")/.."
O=production/pcbway
rm -rf $O
mkdir -p $O/gerbers
kicad-cli pcb export gerbers --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,Edge.Cuts \
  --subtract-soldermask --no-protel-ext -o $O/gerbers/ guac.kicad_pcb >/dev/null
kicad-cli pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 \
  --drill-origin absolute -o $O/gerbers/ guac.kicad_pcb >/dev/null
kicad-cli pcb export pos --side front --format csv --units mm --exclude-dnp -o $O/positions_all.csv guac.kicad_pcb >/dev/null
# J1 is bare solder lap pads with no part
grep -v '^"J1"' $O/positions_all.csv > $O/positions_top.csv
rm $O/positions_all.csv
python3 scripts/pcbway_bom.py $O/positions_top.csv $O/bom_pcbway.csv
(cd $O/gerbers && zip -q ../guac-gerbers.zip *)
echo "wrote $O"
