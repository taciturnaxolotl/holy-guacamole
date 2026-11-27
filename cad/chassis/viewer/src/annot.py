"""Callout labels for Onshape-style renders: white pills with dark borders, leaders with a light halo so they read on
light and dark READMEs. Works at the 2x render resolution, downsamples at the end."""
import json, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
FONT = '/usr/share/fonts/opentype/inter/Inter-Medium.otf'
FONTB = '/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'
INK = (34, 36, 40, 255); HALO = (255, 255, 255, 230)

def font(sz, bold=False):
    import glob
    for f in ([FONTB] if bold else [FONT]) + glob.glob('/usr/share/fonts/**/Inter*%s*.tt*' % ('SemiBold' if bold else 'Medium'), recursive=True):
        try: return ImageFont.truetype(f, sz)
        except Exception: pass
    return ImageFont.truetype('DejaVuSans.ttf', sz)

class Cam:
    """perspective lookAt camera matching three.js (fov vertical, degrees)"""
    def __init__(s, pos, tgt, fov, W, H, up=(0, 0, 1)):
        s.p = np.array(pos, float); f = np.array(tgt, float)-s.p; s.f = f/np.linalg.norm(f)
        r = np.cross(s.f, up); s.r = r/np.linalg.norm(r); s.u = np.cross(s.r, s.f); s.t = math.tan(math.radians(fov)/2); s.W, s.H = W, H
    def __call__(s, q):
        d = np.array(q, float)-s.p; z = d @ s.f; x = d @ s.r/(z*s.t*s.W/s.H); y = d @ s.u/(z*s.t)
        return ((x+1)/2*s.W, (1-y)/2*s.H)

def callouts(img, items, pad_l=0, pad_r=0, pad_t=0, pad_b=0, fs=34, col_gap=40, min_dy=None):
    """items: dicts {t, p:(x,y) anchor px in img, side:'L'|'R', sub: optional 2nd line}. Returns new image with margins."""
    W, H = img.size; out = Image.new('RGBA', (W+pad_l+pad_r, H+pad_t+pad_b), (0, 0, 0, 0)); out.alpha_composite(img, (pad_l, pad_t))
    f, fsub = font(fs), font(int(fs*0.78))
    d = ImageDraw.Draw(out); min_dy = min_dy or fs*2.0
    for side in 'LR':
        its = sorted([i for i in items if i['side'] == side], key=lambda i: (i.get('order', round(i['p'][1]/60)), i['p'][0] if side == 'L' else -i['p'][0]))
        ys = [i['p'][1]+pad_t + i.get('dy', 0) for i in its]
        for k in range(1, len(ys)): ys[k] = max(ys[k], ys[k-1]+min_dy)          # push down to avoid overlap
        for k in range(len(ys)-2, -1, -1): ys[k] = min(ys[k], ys[k+1]-min_dy)   # and back up
        for i, y in zip(its, ys):
            ax, ay = i['p'][0]+pad_l, i['p'][1]+pad_t
            tw = d.textlength(i['t'], font=f); sw = d.textlength(i.get('sub', ''), font=fsub) if i.get('sub') else 0
            w = max(tw, sw)+fs*1.1; h = fs*1.55 + (fs*0.95 if i.get('sub') else 0)
            x0 = (i.get('x', col_gap) if side == 'L' else out.size[0]-col_gap-w)
            ex = x0+w if side == 'L' else x0; ey = y
            elbow = (ex+(fs*1.2 if side == 'L' else -fs*1.2), ey)
            pts = [(ax, ay), (elbow[0], ey) if abs(elbow[0]-ax) < abs(ex-ax) else (ax, ay), (ex, ey)]
            pts = [(ax, ay), elbow, (ex, ey)]
            d.line(pts, fill=HALO, width=9, joint='curve'); d.line(pts, fill=INK, width=4, joint='curve')
            r = 9; d.ellipse([ax-r-3, ay-r-3, ax+r+3, ay+r+3], fill=HALO); d.ellipse([ax-r, ay-r, ax+r, ay+r], fill=INK)
            d.rounded_rectangle([x0, ey-h/2, x0+w, ey+h/2], radius=h/2 if not i.get('sub') else fs*0.6, fill=(255, 255, 255, 250), outline=INK, width=3)
            ty = ey-h/2+fs*0.32
            d.text((x0+fs*0.55, ty), i['t'], font=f, fill=INK)
            if i.get('sub'): d.text((x0+fs*0.55, ty+fs*1.12), i['sub'], font=fsub, fill=(96, 100, 108, 255))
    return out

def trim(img, margin=24):
    bb = img.getbbox(); x0, y0, x1, y1 = bb
    return img.crop((max(0, x0-margin), max(0, y0-margin), min(img.size[0], x1+margin), min(img.size[1], y1+margin)))

def half(img): return img.resize((img.size[0]//2, img.size[1]//2), Image.LANCZOS)
