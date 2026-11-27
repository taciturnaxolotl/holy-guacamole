"""Dimensioned drawing sheet (top + front views, third-angle) and section A-A with callouts, Onshape-drawing flavour."""
import json, math, sys, numpy as np
from PIL import Image, ImageDraw
from annot import font, INK, callouts, half
PX = 15.0                       # render px/mm (ortho half-width 100 mm over 3000 px)
S = 0.8                         # scale onto the sheet
INK2 = (60, 64, 72, 255); DIM = (30, 90, 170, 255)

class Ortho:
    """mm -> sheet px for an ortho render placed at (ox, oy) on the sheet. axes: (h, v) world-axis picks"""
    def __init__(s, ox, oy, W, H, ax_h, ax_v, c=(0, 0, 14.5)):
        s.ox, s.oy, s.W, s.H, s.ah, s.av, s.c = ox, oy, W, H, ax_h, ax_v, c
    def __call__(s, h, v):
        return (s.ox + (s.W/2 + (h - s.c[s.ah[0]])*PX*S*s.ah[1]), s.oy + (s.H/2 - (v - s.c[s.av[0]])*PX*S*s.av[1]))

def arrow(d, tip, ang, col=DIM, L=26, w=9):
    a = math.radians(ang); x, y = tip
    p1 = (x - L*math.cos(a) + w*math.sin(a), y - L*math.sin(a) - w*math.cos(a)); p2 = (x - L*math.cos(a) - w*math.sin(a), y - L*math.sin(a) + w*math.cos(a))
    d.polygon([tip, p1, p2], fill=col)

def text_c(d, xy, t, f, col=DIM, rot=0, bg=True, img=None):
    if rot == 0:
        w = d.textlength(t, font=f); x, y = xy
        if bg: d.rectangle([x-w/2-8, y-f.size*0.62, x+w/2+8, y+f.size*0.62], fill=(255, 255, 255, 255))
        d.text((x-w/2, y-f.size*0.58), t, font=f, fill=col)
    else:                      # vertical text: render to a tile and paste rotated
        w = int(d.textlength(t, font=f))+20; h = int(f.size*1.4)
        tile = Image.new('RGBA', (w, h), (255, 255, 255, 255 if bg else 0)); ImageDraw.Draw(tile).text((10, h*0.1), t, font=f, fill=col)
        tile = tile.rotate(rot, expand=True); img.alpha_composite(tile, (int(xy[0]-tile.size[0]/2), int(xy[1]-tile.size[1]/2)))

def dim_lin(img, d, a, b, off, f, label, vertical=False):
    """linear dimension between sheet points a, b; offset 'off' px perpendicular (sign picks the side)."""
    (ax, ay), (bx, by) = a, b
    if vertical:
        x = ax + off; e = 14 if off > 0 else -14
        d.line([(ax, ay), (x+e, ay)], fill=DIM, width=3); d.line([(bx, by), (x+e, by)], fill=DIM, width=3)
        d.line([(x, ay), (x, by)], fill=DIM, width=3); arrow(d, (x, ay), -90 if ay < by else 90); arrow(d, (x, by), 90 if ay < by else -90)
        text_c(d, (x, (ay+by)/2), label, f, rot=90, img=img)
    else:
        y = ay + off; e = 14 if off > 0 else -14
        d.line([(ax, ay), (ax, y+e)], fill=DIM, width=3); d.line([(bx, by), (bx, y+e)], fill=DIM, width=3)
        d.line([(ax, y), (bx, y)], fill=DIM, width=3); arrow(d, (ax, y), 180 if ax < bx else 0); arrow(d, (bx, y), 0 if ax < bx else 180)
        text_c(d, ((ax+bx)/2, y), label, f)

def dia(d, ctr, r_px, ang, f, label, ext=150):
    a = math.radians(ang); p = (ctr[0]+r_px*math.cos(a), ctr[1]-r_px*math.sin(a)); q = (ctr[0]+(r_px+ext)*math.cos(a), ctr[1]-(r_px+ext)*math.sin(a))
    side = 1 if math.cos(a) >= 0 else -1; t = (q[0]+side*60, q[1])
    d.line([p, q, t], fill=DIM, width=3); arrow(d, p, 180-ang if False else (math.degrees(math.atan2(p[1]-q[1], p[0]-q[0]))))
    w = d.textlength(label, font=f); tx = t[0]+12 if side > 0 else t[0]-12-w
    d.text((tx, t[1]-f.size*0.62), label, font=f, fill=DIM)

def place(sheet, im, x, y):
    im = im.resize((int(im.size[0]*S), int(im.size[1]*S)), Image.LANCZOS); sheet.alpha_composite(im, (int(x), int(y))); return im.size

def drawing(out):
    top, side = Image.open('os/dw_top.png'), Image.open('os/dw_side.png')
    WS, HS = 3600, 3900; sheet = Image.new('RGBA', (WS, HS), (255, 255, 255, 255)); d = ImageDraw.Draw(sheet)
    f, fs, ft = font(46), font(38), font(60, True)
    tw, th = int(3000*S), int(3000*S); sw, sh = int(3000*S), int(900*S)
    tx, ty = (WS-tw)//2 + 60, 40; sx, sy = tx, ty+th+200
    place(sheet, top, tx, ty); place(sheet, side, sx, sy)
    T = Ortho(tx, ty, tw, th, (0, 1), (1, 1)); F = Ortho(sx, sy, sw, sh, (0, 1), (2, 1))
    # top view: teeth tip to tip (tooth tips on the y axis), wheel track, ring / frame diameters
    dim_lin(sheet, d, T(6, 90), T(6, -90), T(110, 0)[0]-T(6, 0)[0], f, 'Ø180 over teeth', vertical=True)
    dim_lin(sheet, d, T(-57.45, -40), T(57.45, -40), T(0, -104)[1]-T(0, -40)[1], f, '114.9 wheel centres')
    c = T(0, 0)
    dia(d, c, 78*PX*S, 140, f, 'Ø156 AR550 ring, 3/16"', ext=260)
    dia(d, c, 72.5*PX*S, 222, f, 'Ø145 MJF PA11 frame', ext=330)
    # front view: frame height, overall with wheels
    dim_lin(sheet, d, F(80, 0), F(80, 29), F(104, 0)[0]-F(80, 0)[0], f, '29 frame', vertical=True)
    dim_lin(sheet, d, F(-56, -6.5), F(-56, 35.5), -(F(-56, 0)[0]-F(-104, 0)[0]), f, '42 wheels', vertical=True)
    dim_lin(sheet, d, F(-72.5, 0), F(72.5, 0), F(0, -14)[1]-F(0, 0)[1], f, '145')
    # view labels + note + title block
    for (x, y), t in ((T(-98, 96), 'TOP'), (F(-98, 32), 'FRONT')):
        d.text((x, y), t, font=ft, fill=INK2)
    note = 'Wheels stand 6.5 proud of both faces, so it drives either way up.'
    d.text((sx, F(0, -30)[1]), note, font=fs, fill=INK2)
    bx0, by0, bx1, by1 = WS-1500, HS-330, WS-60, HS-60
    d.rectangle([bx0, by0, bx1, by1], outline=INK, width=4); d.line([(bx0, by0+120), (bx1, by0+120)], fill=INK, width=3)
    d.text((bx0+40, by0+26), 'HOLY GUACAMOLE  v3.4h', font=ft, fill=INK)
    d.text((bx0+40, by0+150), '1 lb meltybrain · 447 g CAD (limit 454)', font=fs, fill=INK2)
    d.text((bx0+40, by0+200), 'mm · third-angle · not to scale on screen', font=fs, fill=INK2)
    bb = sheet.getbbox(); sheet = sheet.crop((0, 0, WS, HS))
    card(sheet).save(out)

def card(sheet):
    """rounded white card with a light border, transparent outside (reads on light and dark READMEs)"""
    W, H = sheet.size; m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, W-1, H-1], radius=48, fill=255)
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.paste(sheet, (0, 0), m)
    ImageDraw.Draw(out).rounded_rectangle([1, 1, W-2, H-2], radius=48, outline=(208, 213, 220, 255), width=4)
    return half(out)

def section(out):
    sec = Image.open('os/dw_sec.png'); W, H = sec.size
    def P(x, z): return ((x/100+1)/2*W, (1-(z-14.5)/30)/2*H)
    L = [dict(t='Ø42 wheel', sub='cast VytaFlex 40 on a PA11 hub', p=P(-56, 32)),
         dict(t='MR128 bearing', sub='outboard, seat reamed to 12', p=P(-63.5, 19)),
         dict(t='AR550 ring', sub='4.76 thick, clamped at the split', p=P(-76.5, 14.5)),
         dict(t='Lower half', sub='MJF PA11', p=P(-68, 4)),
         dict(t='Bottom plate', sub='MJF PA11 0.8', p=P(-30, 0.2))]
    R = [dict(t='Top plate', sub='MJF PA11 0.8', p=P(30, 28.8)),
         dict(t='Upper half', sub='MJF PA11', p=P(68, 25)),
         dict(t='GNB 3S 380 HV', sub='on the spin axis, z 7.2–27.2', p=P(0, 22)),
         dict(t='D2822 1100KV', p=P(42, 20)),
         dict(t='Rev-2 carrier', sub='1.6 mm, z 0.9–2.5', p=P(12, 1.7)),
         dict(t='L1 buck inductor', sub='5.6 µH, behind the cut', p=P(-15.9, 6))]
    for i in L: i['side'] = 'L'
    for i in R: i['side'] = 'R'
    im = Image.new('RGBA', (W, H+260), (0, 0, 0, 0)); im.alpha_composite(sec, (0, 120))
    for i in L+R: i['p'] = (i['p'][0], i['p'][1]+120)
    o = callouts(im, L+R, pad_l=820, pad_r=820, pad_t=40, pad_b=40, fs=40, min_dy=150)
    sheet = Image.new('RGBA', o.size, (255, 255, 255, 255)); sheet.alpha_composite(o)
    d = ImageDraw.Draw(sheet); f = font(46, True)
    d.text((60, 50), 'SECTION A–A  (through the wheel axis, y = 0)', font=f, fill=INK)
    card(sheet).save(out)

if __name__ == '__main__':
    drawing('os/drawing.png'); section('os/section_aa.png')
