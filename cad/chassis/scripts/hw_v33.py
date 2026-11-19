# viewer-only fastener models for the 6 ring bolts (not part of the structural model)
import math, cadquery as cq
ZC = 14.5; Z_PADT = 29.0+0.3+0.8+0.3; Z_PADB = 2*ZC-Z_PADT
bolts = [(68.5*math.cos(math.radians(a)), 68.5*math.sin(math.radians(a))) for a in (30, 90, 150, 210, 270, 330)]
def cyl(x, y, r, z0, z1): return cq.Workplane('XY').center(x, y).circle(r).extrude(z1-z0).translate((0, 0, z0))
def hexp(x, y, af, z0, z1):
    r = af/math.sqrt(3); pts = [(x+r*math.cos(math.radians(60*k+30)), y+r*math.sin(math.radians(60*k+30))) for k in range(6)]
    return cq.Workplane('XY').workplane(offset=z0).polyline(pts).close().extrude(z1-z0)
bolt = washer = nut = None
U = lambda a, b: b if a is None else a.union(b)
for x, y in bolts:
    head = cyl(x, y, 2.85, 1.15, 2.8)                                   # ISO 7380 button head on a Ø7 x 0.5 washer (DIN 125) on the bottom spot face (v3.4f)
    wsh = cyl(x, y, 3.5, 2.8, 3.3).cut(cyl(x, y, 1.6, 2.7, 3.4))
    bolt = U(bolt, head.union(cyl(x, y, 1.5, 2.8, 2.8+20.0)).union(wsh))  # Ti M3x20 (3.5 mm into the insert)
    nut = U(nut, cyl(x, y, 2.1, 19.3, 25.0).cut(cyl(x, y, 1.5, 18.8, 25.5)))   # brass heat-set insert, flush with the top spot face
ps = None                                                              # M2.5x6 ISO 7380 button heads (dk 4.7, k 1.3) for both plates
for a in (30, 150, 210, 330):
    x, y = 59.5*math.cos(math.radians(a)), 59.5*math.sin(math.radians(a))
    ps = U(ps, cyl(x, y, 2.35, 29.33, 30.63).union(cyl(x, y, 1.25, 23.33, 29.33)))
    ps = U(ps, cyl(x, y, 2.35, -1.63, -0.33).union(cyl(x, y, 1.25, -0.33, 5.67)))
for n, v in (('bolts', bolt), ('nuts', nut), ('pscrews', ps)):
    cq.exporters.export(v, f'v33m_{n}.stl', tolerance=0.03, angularTolerance=0.2)
print('ok')

# ---------- everything else that wasn't modelled (viewer-only) ----------
H, PLK, PCB_Z, PCB_T = 29.0, 0.6, 0.9, 1.6
TOPS = [(59.5*math.cos(math.radians(a)), 59.5*math.sin(math.radians(a))) for a in (30, 150, 210, 330)]
PCB_TABHOLES = [(-16.6, 34.5), (16.6, 34.5), (-17.0, -34.5), (17.0, -34.5)]
WALL0, W0 = 20.5, 51.4
MOUNT = {1: [(-6.72, -6.72), (6.72, 6.72), (-5.66, 5.66), (5.66, -5.66)], -1: [(-6.72, 6.72), (6.72, -6.72), (-5.66, -5.66), (5.66, 5.66)]}
def cylx(x0, x1, r, y, z): return cq.Workplane('YZ').workplane(offset=min(x0, x1)).center(y, z).circle(r).extrude(abs(x1-x0))
def bx(x0, x1, y0, y1, z0, z1): return cq.Workplane('XY').box(abs(x1-x0), abs(y1-y0), abs(z1-z0)).translate(((x0+x1)/2, (y0+y1)/2, (z0+z1)/2))
ins = None
for x, y in TOPS:                                                       # M2.5 x 5 heat-sets, flush with the plate-pocket floors
    ins = U(ins, cyl(x, y, 1.75, H-PLK-5.0, H-PLK).cut(cyl(x, y, 1.25, H-PLK-6, H)))
    ins = U(ins, cyl(x, y, 1.75, PLK, PLK+5.0).cut(cyl(x, y, 1.25, 0, PLK+6)))
for x, y in PCB_TABHOLES:                                               # M2 x 3 heat-sets in the end-ledge undersides
    ins = U(ins, cyl(x, y, 1.6, PCB_Z+PCB_T+0.1, PCB_Z+PCB_T+3.1).cut(cyl(x, y, 1.0, 0, 9)))
pcs = None
for x, y in PCB_TABHOLES:                                               # M2 x 4 wafer heads (k 0.9) from below, heads in the Ø4 bottom-plate holes
    pcs = U(pcs, cyl(x, y, 1.9, PCB_Z-0.9, PCB_Z).union(cyl(x, y, 1.0, PCB_Z, PCB_Z+4.0)))
ms = None
for s in (1, -1):                                                       # 4x M3 x 6 SHCS per motor, heads in the Ø6.2 c-bores on the bay side
    for (y, dz) in MOUNT[s]:
        z = 14.5+dz; xs = s*(WALL0+3.0)
        ms = U(ms, cylx(s*WALL0, xs, 2.75, y, z).union(cylx(xs, s*(WALL0+9.0), 1.5, y, z)))
ws = None
for s in (1, -1):                                                       # 3x M2 x 5 button heads per wheel, seated in the hub boss c-bores (local z 2.6)
    for k in range(3):
        a = math.radians(120*k+90); lx, ly = 6.0*math.cos(a), 6.0*math.sin(a)
        g = lambda lz: (s*lz+s*(W0+0.05), ly, -s*lx+14.5)
        h0, h1, t = g(2.6), g(3.7), g(-2.4)
        ws = U(ws, cylx(h0[0], h1[0], 1.75, ly, h0[2]).union(cylx(t[0], h0[0], 1.0, ly, h0[2])))
# hex key in the switch: FingerTech mini switch socket measures 2.39 mm AF = 3/32"
def hexbar(p0, p1, af=2.38):
    r = af/math.sqrt(3); d = cq.Vector(*p1)-cq.Vector(*p0); L = d.Length
    pr = cq.Workplane('XY').polygon(6, 2*r).extrude(L)
    ax = cq.Vector(0, 0, 1).cross(d.normalized())
    if ax.Length > 1e-6: pr = pr.rotate((0, 0, 0), ax.toTuple(), math.degrees(math.acos(d.normalized().z)))
    return pr.translate(p0)
SWX, SWY, SWT = -5.0, 50.5, 28.2
key = hexbar((SWX, SWY, SWT-0.6), (SWX, SWY, SWT+14.0)).union(hexbar((SWX, SWY, SWT+14.0), (SWX-45.0, SWY, SWT+14.0)))
key = key.union(cq.Workplane('XY').sphere(1.19).translate((SWX, SWY, SWT+14.0)))
# Repeat AM32 dual ESC, laid out from the vendor photos (Palm Beach Bots): black board 26 x 20, 3 motor pads down each 20 mm edge,
# BAT + GND pads and the 4 through-hole signal pads (GND, 5V, CH1, CH2) along one 26 mm edge with the R001 shunt; 3 FETs per channel.
# In the bot the board stands on edge on the S ledge, pad edge DOWN (the only edge with room for wires to leave).
EY0, EY1, EZ0 = -38.7, -36.7, 7.25                                     # ~2 mm overall (measured by Kieran): 1.0 board + ~1.0 parts
yc = EY0+0.5; yf = yc+0.5                                               # board against the S bay wall, components on the N face
esc = bx(-14, 14, yc-0.5, yc+0.5, EZ0, EZ0+20)            # Repeat lists 28 x 20 x 5 (5 = with wires); Kieran confirms 28
for sx in (1, -1):                                                      # 3 FETs per channel in a column beside each motor-pad edge
    for k in range(3):
        z = EZ0+4.0+k*5.6
        esc = esc.union(bx(sx*6.0, sx*10.0, yf, yf+1.0, z-1.6, z+1.6))
esc = esc.union(bx(-4.5, 1.5, yf, yf+0.9, EZ0+7.0, EZ0+13.0))           # MCU / gate driver
esc = esc.union(bx(-1.5, 2.5, yf, yf+1.0, EZ0+2.2, EZ0+6.2))            # BEC inductor
esc = esc.union(bx(4.0, 9.5, yf, yf+0.9, EZ0+0.6, EZ0+3.0))             # R001 shunt
pads = None
for sx in (1, -1):                                                      # motor pads, 3 per 20 mm edge
    for k in range(3):
        z = EZ0+3.5+k*6.5
        pads = U(pads, bx(sx*11.6, sx*14.0, yc-0.55, yc+0.55, z-1.25, z+1.25))
pads = U(pads, bx(-12.6, -9.6, yc-0.55, yc+0.55, EZ0, EZ0+3.0)).union(bx(-8.6, -5.6, yc-0.55, yc+0.55, EZ0, EZ0+3.0))   # BAT, GND
esc = esc.union(pads)
ew = None
for sx in (1, -1):                                                      # motor phases out the ends into the side corridors
    for k in range(3):
        ew = U(ew, cylx(sx*13.0, sx*15.0, 0.55, yf+0.6, EZ0+3.5+k*6.5))
for x in (-11.1, -7.1):                                                 # battery leads (20 AWG is plenty at the 4-8 A/ch ant current limit) straight down off the pad edge
    ew = U(ew, cyl(x, yf+0.6, 0.75, EZ0-5.0, EZ0+1.5))
for i in range(4):                                                      # GND / 5V / CH1 / CH2 signal pads, ~2 mm pitch, also down
    x = -2.5+i*2.0
    ew = U(ew, cyl(x, yc, 0.35, EZ0-5.0, EZ0+1.0))
_mir = cq.Matrix([[-1, 0, 0, 0], [0, -1, 0, 2*(EY0+EY1)/2], [0, 0, 1, 0]])   # 180 deg about the ESC's own vertical axis: BAT/GND + signal edge stays down, pads move to the E (SE)
esc = cq.Workplane('XY').newObject([esc.val().transformGeometry(_mir)]); ew = cq.Workplane('XY').newObject([ew.val().transformGeometry(_mir)])
# 20 AWG ESC battery leads: off the (now E) pads into the 3 mm gap, E along the ledge top, N to the ledge face, down to J1 (18.1, -27.4 / -22.6)
def tube(pts, r):
    t = None
    for p0, p1 in zip(pts[:-1], pts[1:]):
        seg = hexbar(p0, p1, af=2*r).union(cq.Workplane('XY').sphere(r).translate(p1)); t = U(t, seg)
    return t
for xp, yj in ((11.1, -27.4), (7.1, -22.6)):
    ew = ew.union(tube([(xp, -35.8, 8.4+(xp-7.1)*0.3), (19.0 if yj < -25 else 17.4, -35.8, 8.4+(xp-7.1)*0.3), (19.0 if yj < -25 else 17.4, -29.0, 8.4), (18.1, yj+(1.2 if yj < -25 else -1.2), PCB_Z+PCB_T+2.0), (18.1, yj, PCB_Z+PCB_T+0.3)], 0.8))
for n, v in (('inserts', ins), ('pcbscrews', pcs), ('mscrews', ms), ('wscrews', ws), ('hexkey', key), ('escd', esc), ('escwires', ew)):
    cq.exporters.export(v, f'v33m_{n}.stl', tolerance=0.03, angularTolerance=0.2)
print('ok2')
