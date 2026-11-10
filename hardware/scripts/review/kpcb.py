"""minimal .kicad_pcb reader -> footprints/pads, segments, arcs, vias, zones (filled polygons)"""
import re, math
TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')
def parse(txt):
    st = [[]]
    for m in TOK.finditer(txt):
        t = m.group(0)
        if t == '(': st.append([])
        elif t == ')': x = st.pop(); st[-1].append(x)
        else: st[-1].append(t[1:-1] if t[0] == '"' else t)
    return st[0][0]
def find(n, key): return [c for c in n if isinstance(c, list) and c and c[0] == key]
def one(n, key):
    r = find(n, key); return r[0] if r else None
def netname(n):
    x = one(n, 'net')
    if x is None: return None
    return x[-1] if len(x) > 1 else None
def xy(n): return float(n[1]), float(n[2])
def load(path):
    B = parse(open(path).read())
    out = {'fp': [], 'seg': [], 'via': [], 'zone': []}
    for f in find(B, 'footprint'):
        at = one(f, 'at'); fx, fy = xy(at); fr = float(at[3]) if len(at) > 3 else 0.
        ref = None
        for p in find(f, 'property'):
            if p[1] == 'Reference': ref = p[2]
        lay = one(f, 'layer')[1]
        pads = []
        for p in find(f, 'pad'):
            pa = one(p, 'at'); px, py = xy(pa); pr = float(pa[3]) if len(pa) > 3 else 0.  # KiCad pad angle is absolute; absent = 0
            a = math.radians(-fr); X = fx + px*math.cos(a) - py*math.sin(a); Y = fy + px*math.sin(a) + py*math.cos(a)
            sz = one(p, 'size'); lays = one(p, 'layers')[1:]
            pads.append({'num': p[1], 'type': p[2], 'shape': p[3], 'x': X, 'y': Y, 'w': float(sz[1]), 'h': float(sz[2]), 'rot': pr, 'net': netname(p), 'layers': lays})
        out['fp'].append({'ref': ref, 'x': fx, 'y': fy, 'rot': fr, 'layer': lay, 'pads': pads, 'name': f[1]})
    for s in find(B, 'segment') + find(B, 'arc'):
        st = xy(one(s, 'start')); en = xy(one(s, 'end'))
        out['seg'].append({'a': st, 'b': en, 'w': float(one(s, 'width')[1]), 'layer': one(s, 'layer')[1], 'net': netname(s), 'arc': s[0] == 'arc'})
    for v in find(B, 'via'):
        out['via'].append({'p': xy(one(v, 'at')), 'd': float(one(v, 'size')[1]), 'drill': float(one(v, 'drill')[1]), 'net': netname(v), 'layers': one(v, 'layers')[1:]})
    for z in find(B, 'zone'):
        nm = one(z, 'name'); lay = one(z, 'layer') or one(z, 'layers')
        fills = []
        for fp in find(z, 'filled_polygon'):
            L = one(fp, 'layer')[1]; pts = [xy(q) for q in one(fp, 'pts') if q[0] == 'xy']
            fills.append((L, pts))
        out['zone'].append({'name': nm[1] if nm else '', 'net': netname(z), 'layers': lay[1:] if lay else [], 'fills': fills,
                            'outline': [xy(q) for q in one(one(z, 'polygon'), 'pts') if q[0] == 'xy'] if one(z, 'polygon') else []})
    return out
