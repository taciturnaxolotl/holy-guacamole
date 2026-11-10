#!/bin/sh
# Freerouting 2.5 needs JDK 25+ and the jar at ~/.cache/freerouting/freerouting-2.5.0.jar; work files go to /tmp/fr
mkdir -p /tmp/fr
# usage: run.sh <pcb> ; exports DSN, relaxes class widths for the autorouter, routes, imports SES into <pcb>.routed.kicad_pcb
set -e
PCB=$1; OUT=$PCB; cp $PCB ${PCB%.kicad_pcb}.prerouted.bak
P=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
$P -c "import pcbnew; b=pcbnew.LoadBoard('$PCB'); pcbnew.ExportSpecctraDSN(b,'/tmp/fr/guac.dsn')" 2>/dev/null
python3 - <<'PY'
import re
p='/tmp/fr/guac.dsn'; t=open(p).read()
def fix(cls, w, c):
    global t
    t=re.sub(r'(\(class %s[^\n]*\n(?:[^\n]*\n)*?\s*\(rule\n\s*\(width )\d+(\)\n\s*\(clearance )\d+' % re.escape(cls), lambda m: m.group(1)+str(w)+m.group(2)+str(c), t, count=1)
fix('kicad_default', 180, 207); fix('Power_Heavy,Default', 400, 207); fix('Power_Light,Default', 250, 207); fix('Power_Main,Default', 600, 207); fix('GND,Default', 400, 207); fix('Analog,Default', 250, 207)
# freerouting sees the 0.5 mm pitch pads of the 166-degree IMUs as violating 0.207 mm between each other (actual
# gap 0.22 mm) and then gives up on every net touching them. Their signal pads are all escaped by power_rev2.py,
# so the router never connects to them directly: narrow them (full length, so vias still keep off the pad
# ends) in its copy only. KiCad DRC checks the real pads.
for w, h in ((280, 600), (600, 280), (280, 680), (680, 280)):
    t=t.replace('(padstack Rect[T]Pad_%d.000000x%d.000000_um\n      (shape (rect F.Cu %d %d %d %d))' % (w, h, -w//2, -h//2, w//2, h//2),
                '(padstack Rect[T]Pad_%d.000000x%d.000000_um\n      (shape (rect F.Cu %d %d %d %d))' % (w, h, -(100 if w == 280 else w//2), -(100 if h == 280 else h//2), 100 if w == 280 else w//2, 100 if h == 280 else h//2))
# drop the hand-routed power nets from the autorouter's netlist
for net in ('VBUS', '"/Power Subsystem/VBAT_RAW"', '3V3', '5V'):
    i=t.find('    (net %s\n' % net); j=t.find('\n    )\n', i)
    assert i>0 and j>i, net
    t=t[:i]+t[j+7:]
t=t.replace('(class Power_Main,Default "/Power Subsystem/VBAT_RAW" VBUS', '(class Power_Main,Default')
t=t.replace('(class Power_Light,Default 3V3', '(class Power_Light,Default').replace('(class Power_Heavy,Default 5V ', '(class Power_Heavy,Default ')
# inner layers are pours: freerouting must route on F.Cu/B.Cu only
import re as _re
def drop_balanced(text, start_pat):
    out=[]; i=0
    while True:
        m=_re.search(start_pat, text[i:])
        if not m: out.append(text[i:]); break
        s=i+m.start(); out.append(text[i:s])
        depth=0; j=s
        while True:
            c=text[j]
            if c=='(': depth+=1
            elif c==')':
                depth-=1
                if depth==0: j+=1; break
            j+=1
        while j<len(text) and text[j] in ' \t': j+=1
        if j<len(text) and text[j]=='\n': j+=1
        i=j
    return ''.join(out)
# In2 wires are the hand-placed signal tunnel lanes under the power band (power_rev2.py): they stay, as fixed
# wiring, so the router knows each tunnel via is joined to its twin across the band
t=_re.sub(r'(\(layer In[12]\.Cu\n\s*\(type )signal', r'\1power', t)
assert t.count('(type power)')==2
# everything already on the board was placed by the scripts: freerouting must not rip it up
t=t.replace('(type route)', '(type protect)')
open(p,'w').write(t)
PY
grep -A6 "(class Power" /tmp/fr/guac.dsn | grep -E "class|width|clearance"
rm -f /tmp/fr/guac.ses
/opt/homebrew/opt/openjdk@25/bin/java -jar ~/.cache/freerouting/freerouting-2.5.0.jar -de /tmp/fr/guac.dsn -do /tmp/fr/guac.ses -mp 100 -mt 6 > /tmp/fr/fr.log 2>&1 || true
grep -E "Stopping|unrouted\)|could not be routed" /tmp/fr/fr.log | tail -3
$P - "$PCB" 2>/dev/null <<'IMP' | grep import
import pcbnew, sys
pcb = sys.argv[1]
OWN = ('VBUS', '/Power Subsystem/VBAT_RAW', '3V3', '5V')
pre = pcbnew.LoadBoard(pcb)
own = [t.Duplicate() for t in pre.GetTracks()]
b = pcbnew.LoadBoard(pcb)
print('import', pcbnew.ImportSpecctraSES(b, '/tmp/fr/guac.ses'))
def key(t):
    r = lambda v: int(round(v / 20000.0))
    if t.GetClass() == 'PCB_VIA':
        return ('V', r(t.GetPosition().x), r(t.GetPosition().y))
    return ('T', t.GetLayer(), r(t.GetStart().x), r(t.GetStart().y), r(t.GetEnd().x), r(t.GetEnd().y))
have = {key(t) for t in b.GetTracks()}
# SES import rebuilds the hand-placed vias of nets it was not given (VBUS) with the netclass drill; put the
# original pad and drill back so the annular ring stays at what power_rev2.py chose
size = {key(t): (t.GetWidth(pcbnew.F_Cu), t.GetDrillValue()) for t in own if t.GetClass() == 'PCB_VIA'}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA' and key(t) in size:
        t.SetWidth(size[key(t)][0])
        t.SetDrill(size[key(t)][1])
for t in own:
    if key(t) not in have:
        t.SetNet(b.FindNet(t.GetNetname()))
        b.Add(t)
for t in b.GetTracks():
    if t.GetClass() == 'PCB_TRACK' and t.GetWidth() < 180000:
        t.SetWidth(180000)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(pcb)
IMP
kicad-cli pcb drc --severity-error -o /tmp/fr/drc.rpt $OUT >/dev/null 2>&1; grep -E "^\[" /tmp/fr/drc.rpt | sed 's/(.*//' | sort | uniq -c | sort -rn
