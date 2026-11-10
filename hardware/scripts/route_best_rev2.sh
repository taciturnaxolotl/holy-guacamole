#!/bin/sh
# Freerouting 2.5 needs JDK 25+ and the jar at ~/.cache/freerouting/freerouting-2.5.0.jar; work files go to /tmp/fr
mkdir -p /tmp/fr
# usage: route_best.sh <pcb> [attempts]  ; reruns $(dirname "$0")/autoroute_rev2.sh until KiCad DRC (errors) is clean, keeps best, then runs bridge_rev2.py and stitch_rev2.py
PCB=$1; N=${2:-5}
cp $PCB /tmp/fr/prerouted.kicad_pcb
best=999
for i in $(seq 1 $N); do
  cp /tmp/fr/prerouted.kicad_pcb $PCB
  $(dirname "$0")/autoroute_rev2.sh $PCB >/tmp/fr/attempt_$i.log 2>&1
  kicad-cli pcb drc --severity-error -o /tmp/fr/drc_$i.rpt $PCB >/dev/null 2>&1
  n=$(grep -c "^\[" /tmp/fr/drc_$i.rpt)
  echo "attempt $i: $n error-level violations"
  if [ "$n" -lt "$best" ]; then best=$n; cp $PCB /tmp/fr/best.kicad_pcb; fi
  [ "$n" -eq 0 ] && break
done
cp /tmp/fr/best.kicad_pcb $PCB; rm -f ${PCB%.kicad_pcb}.prerouted.bak
echo "best: $best"
# join whatever freerouting left open and drop its one-sided vias
P=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$P $(dirname "$0")/bridge_rev2.py $PCB 2>/dev/null
# GND stitching grid
$P $(dirname "$0")/stitch_rev2.py $PCB 2>/dev/null
kicad-cli pcb drc --severity-error -o /tmp/fr/drc_final.rpt $PCB >/dev/null 2>&1
echo "after bridge: $(grep -c "^\[" /tmp/fr/drc_final.rpt) error-level violations"
