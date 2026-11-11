"""Text -> shapely polygons from an OTF/TTF (outline fonts, even-odd fill). Units mm, baseline at y=0, y up."""
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import affinity
import os
_F = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
FONTS = {'black': f'{_F}/InterDisplay-Black.otf', 'xbold': f'{_F}/InterDisplay-ExtraBold.otf'}
_c = {}
def _font(k):
    if k not in _c:
        f = TTFont(FONTS.get(k) or (k if os.path.isabs(k) else os.path.join(_F, k))); gs = f.getGlyphSet(); cm = f.getBestCmap()
        from fontTools.pens.boundsPen import BoundsPen   # measure H: some display fonts carry a wrong sCapHeight
        bp = BoundsPen(gs); gs[cm[ord('H')]].draw(bp); cap = bp.bounds[3]
        _c[k] = (f, gs, cm, f['head'].unitsPerEm, cap)
    return _c[k]

class _Flat(BasePen):
    """flattens any glyph (cubic or TrueType quadratic, incl. all-off-curve contours) to point lists"""
    def __init__(s, gs, n=8): super().__init__(gs); s.c = []; s.cur = []; s.n = n
    def _moveTo(s, p): s.cur = [p]
    def _lineTo(s, p): s.cur.append(p)
    def _curveToOne(s, b, c, d):
        a = s.cur[-1]; n = s.n
        for k in range(1, n+1):
            t = k/n; u = 1-t
            s.cur.append((u**3*a[0]+3*u*u*t*b[0]+3*u*t*t*c[0]+t**3*d[0], u**3*a[1]+3*u*u*t*b[1]+3*u*t*t*c[1]+t**3*d[1]))
    def _qCurveToOne(s, b, c):
        a = s.cur[-1]; n = s.n
        for k in range(1, n+1):
            t = k/n; u = 1-t; s.cur.append((u*u*a[0]+2*u*t*b[0]+t*t*c[0], u*u*a[1]+2*u*t*b[1]+t*t*c[1]))
    def _closePath(s):
        if len(s.cur) > 2: s.c.append(s.cur)
        s.cur = []
    _endPath = _closePath

def text(s, cap, font='black', track=0.0, align='c'):
    """cap: cap height in mm. track: extra spacing in em. returns (geom, width_mm)."""
    f, gs, cmap, upm, capu = _font(font); sc = cap / capu; x = 0; out = []
    hm = f['hmtx']
    for ch in s:
        gn = cmap.get(ord(ch))
        if gn is None: continue
        pen = _Flat(gs); gs[gn].draw(pen)
        g = Polygon()
        for c in pen.c:
            P = Polygon([(x + px*sc, py*sc) for px, py in c]).buffer(0)
            g = g.symmetric_difference(P)
        out.append(g); x += hm[gn][0]*sc + track*upm*sc
    x -= track*upm*sc
    G = unary_union(out)
    dx = {'c': -x/2, 'l': 0, 'r': -x}[align]
    return affinity.translate(G, dx, 0), x
