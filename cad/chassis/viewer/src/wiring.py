"""Wiring diagram for holy guacamole v3.4h + rev-2 carrier. Laid out clockwise around the carrier, following the power:
battery (W) -> J6 -> J7 -> switch (N) -> J7 -> J1 -> ESC (E) -> motors (SE); signals to receiver (S) and LEDs (SW)."""
W, H = 1810, 1090
INK, MUTE, LINE, CARD = '#22252a', '#646a74', '#d0d5dc', '#ffffff'
RED, VBUS, GND, WHT, YEL, BLU, GRN, ORG = '#d23b2f', '#e0742a', '#2a2c30', '#b8bec7', '#e2b714', '#3a6fd0', '#2f8f50', '#ff8c1a'
o = []
def box(x, y, w, h, title, sub=None, fill='#f6f7f9', stroke=INK, tc=INK, r=14, lines=()):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
    o.append(f'<text x="{x+18}" y="{y+34}" class="t" fill="{tc}">{title}</text>')
    if sub: o.append(f'<text x="{x+18}" y="{y+60}" class="s">{sub}</text>')
    for i, l in enumerate(lines): o.append(f'<text x="{x+18}" y="{y+(88 if sub else 62)+i*24}" class="s">{l}</text>')
def pin(x, y, label, anchor='start', col=MUTE):
    o.append(f'<text x="{x}" y="{y}" class="p" fill="{col}" text-anchor="{anchor}">{label}</text>')
def wire(pts, col, w=6, dash=None):
    d = 'M' + ' L'.join(f'{x},{y}' for x, y in pts)
    o.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-width="{w+5}" stroke-linejoin="round" stroke-linecap="round"/>')
    o.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"' + (f' stroke-dasharray="{dash}"' if dash else '') + '/>')
def conn(x, y, w, h, label, fill='#fff3c4', stroke='#b8901a', sub=None, anchor='middle'):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
    o.append(f'<text x="{x+w/2}" y="{y+h/2+7}" class="c" text-anchor="middle">{label}</text>')
    if sub: o.append(f'<text x="{x+w/2}" y="{y+h+22}" class="p" text-anchor="middle">{sub}</text>')
def tag(x, y, t, col=MUTE, anchor='middle', cls='p'):
    o.append(f'<text x="{x}" y="{y}" class="{cls}" fill="{col}" text-anchor="{anchor}">{t}</text>')

# ---- carrier board (centre) ----
CX, CY, CW, CH = 600, 330, 600, 460
o.append(f'<rect x="{CX}" y="{CY}" width="{CW}" height="{CH}" rx="22" fill="#e9f4ec" stroke="{GRN}" stroke-width="3"/>')
tag(790, 318, 'Rev-2 carrier · 40 × 76 · 4-layer · also the power board', INK, 'start', 'c')
def ib(x, y, w, h, t, s=None, fill='#ffffff'):
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{LINE}" stroke-width="2"/>')
    o.append(f'<text x="{x+w/2}" y="{y+(h/2+6 if not s else h/2-4)}" class="c" text-anchor="middle">{t}</text>')
    if s: o.append(f'<text x="{x+w/2}" y="{y+h/2+18}" class="p" fill="{MUTE}" text-anchor="middle">{s}</text>')
BX, BW = 885, 235
ib(BX, 420, BW, 56, 'XIAO RP2350', 'runtime IO on D0–D10')
ib(BX, 488, BW, 56, 'LSM6 + 2× H3LIS', "SPI Mode 0, '595 CS latch")
ib(BX, 556, BW, 56, 'AP63301 buck', 'VBUS → 5 V → D7 → XIAO')
ib(BX, 624, BW, 56, 'VBAT sense', '120k / 33.2k → A0')
ib(BX, 692, BW, 56, 'Q1 AO3402', 'LED low side, gate D1')
ib(760, 650, 115, 64, 'SMAJ15CA', '+ 47 µF bulk')
# board connectors
conn(560, 570, 120, 50, 'J6  XT30-M')
conn(560, 470, 120, 50, 'J7  XT30-F')
conn(1140, 715, 120, 50, 'J1  pads', fill='#ffe3dc', stroke=RED)
conn(1140, 505, 120, 50, 'J4  GH-4', fill='#e6ecf7', stroke=BLU)
conn(960, 765, 120, 50, 'J5  GH-4', fill='#e6ecf7', stroke=BLU)
conn(640, 765, 120, 50, 'J2  GH-2', fill='#ffeedd', stroke=ORG)
# board power path
wire([(680, 585), (705, 585), (705, 508), (680, 508)], RED, 6); tag(700, 552, 'VBAT_RAW', RED, 'end')
wire([(680, 482), (745, 482), (745, 757), (1140, 757)], VBUS, 6); tag(756, 520, 'VBUS', VBUS, 'start')
wire([(745, 584), (BX, 584)], VBUS, 3); wire([(745, 682), (760, 682)], VBUS, 3)

# ---- W: battery ----
box(60, 520, 300, 150, 'GNB 3S 380 HV', '11.4 V nom · 13.05 V full', lines=['XT30-F lead · XH balance plug'], fill='#e8eefb', stroke=BLU)
wire([(360, 585), (560, 585)], RED, 7); wire([(360, 610), (560, 610)], GND, 7)
tag(460, 572, 'pack leads', MUTE, 'middle')

# ---- N: switch ----
box(520, 130, 360, 120, 'Fingertech mini switch', 'in its frame socket, 3/32" hex key', lines=['~85 mm XT30-M pigtail, 20 AWG'], fill='#fbf5e2', stroke='#b8901a')
wire([(610, 250), (610, 265), (520, 265), (520, 508), (560, 508)], RED, 6); wire([(650, 250), (650, 282), (540, 282), (540, 482), (560, 482)], VBUS, 6)
tag(512, 400, 'pigtail up the W side, twisted', MUTE, 'end')

# ---- E: ESC + motors ----
EX, EY, EW, EH = 1330, 300, 420, 175
box(EX, EY, EW, EH, 'Repeat AM32 dual ESC', '28 × 20 · AM32_RR_ROBOT_DUAL_ESC_F421', lines=['DSHOT600 bidir + EDT · 4–5 A/ch limit', 'BEC isolated, not tied to the 5 V rail'], fill='#e6ecf7', stroke=BLU)
wire([(1260, 730), (1410, 730), (1410, EY+EH)], VBUS, 7); wire([(1260, 750), (1430, 750), (1430, EY+EH)], GND, 7)
tag(1335, 790, '20 AWG', MUTE, 'middle')
wire([(1260, 522), (1370, 522), (1370, EY+EH)], WHT, 4); wire([(1260, 540), (1395, 540), (1395, EY+EH)], YEL, 4)
tag(1272, 572, 'GND · D1 white', MUTE, 'start'); tag(1272, 594, 'D2 yellow · GND', MUTE, 'start')
for i, (lab, x) in enumerate((('Motor R', 1440), ('Motor L', 1610))):
    box(x, 640, 150, 130, lab, 'D2822 1100KV', lines=['2 mm bullets'], fill='#eeeeee', stroke=GND, r=12)
    for k, c in enumerate(('#3a3a3a', '#666', '#909090')):
        x0 = x+45+k*30; wire([(x0, EY+EH), (x0, 640)], c, 4)
tag(1600, 800, '3 phases each, 70 mm leads', MUTE, 'middle')

# ---- S: receiver ----
box(880, 900, 320, 140, 'BetaFPV ELRS Lite', 'flat antenna · S-pocket tray', lines=['CRSF 420 kbaud, non-inverted'], fill='#f1e8fa', stroke='#7b42b2')
for k, c in enumerate((GND, '#c93a3a', WHT, YEL)):
    x0 = 983+k*25; wire([(x0, 815), (x0, 900)], c, 4)
tag(1100, 852, 'GND · 5V · RX ← · TX →, twisted, &lt; 60 mm', MUTE, 'start')

# ---- SW: TinySLEDs ----
box(300, 900, 470, 140, 'Heading LEDs · 2 × TinySLED', 'top + bottom in parallel, orange', lines=['check the 2–3S part at 13.05 V'], fill='#fff1e3', stroke=ORG)
wire([(680, 815), (680, 900)], VBUS, 4); wire([(720, 815), (720, 900)], ORG, 4)
tag(668, 868, 'Y-spliced to both LEDs by the plug', MUTE, 'end')

# ---- legend + notes ----
lx, ly = 60, 730
tag(lx, ly, 'Wires', INK, 'start', 'c')
for k, (c, l) in enumerate(((RED, 'VBAT_RAW, battery side'), (VBUS, 'VBUS, switched'), (GND, 'GND'), (WHT, 'DSHOT1 / CRSF'), (YEL, 'DSHOT2 / CRSF'), (ORG, 'HEAD_SW'))):
    y = ly+28+k*26; wire([(lx, y-6), (lx+40, y-6)], c, 6); tag(lx+54, y, l, MUTE, 'start')
for k, t in enumerate(('J7 carries no ground: VBAT_RAW out, VBUS back.', 'Outer-layer VBUS ↔ VBAT_RAW kept 1 mm apart.', 'Zip-tie every lead through its slot.')):
    tag(1240, 880+k*28+120, '', MUTE, 'start')
for k, t in enumerate(('J7 (switch loop) sits beside J6 at the S end; only the pigtail runs N.', 'J7 carries no ground: VBAT_RAW out, VBUS back.', 'Outer-layer VBUS ↔ VBAT_RAW kept 1 mm apart.')):
    tag(940, 160+k*28+20, t, MUTE, 'start')
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>.t{{font:600 24px Inter,system-ui,sans-serif;fill:{INK}}} .s{{font:400 18px Inter,system-ui,sans-serif;fill:{MUTE}}}
.c{{font:600 18px Inter,system-ui,sans-serif;fill:{INK}}} .p{{font:500 16px Inter,system-ui,sans-serif}} .h{{font:700 30px Inter,system-ui,sans-serif;fill:{INK}}}</style>
<rect x="2" y="2" width="{W-4}" height="{H-4}" rx="28" fill="{CARD}" stroke="#d0d5dc" stroke-width="3"/>
<text x="60" y="64" class="h">Wiring</text><text x="60" y="94" class="s">v3.4h chassis · rev-2 carrier (3S only), J7 beside J6 · power runs clockwise</text>
{chr(10).join(o)}
</svg>'''
open('os/wiring.svg', 'w').write(svg); print('ok')
