import json, sys
from PIL import Image
from annot import *
im = Image.open('os/exploded.png'); A = json.load(open('os/exploded.json')); W, H = im.size
C = Cam([330,-400,250],[0,0,40],26,W,H)
def near(k, side):   # instance nearest the label column
    ps = A[k]; return min(ps, key=lambda p: p[0]) if side == 'L' else max(ps, key=lambda p: p[0])
L = [dict(t='Top plate', sub='MJF PA11, 0.8 mm', p=C([-45,-35,134])),
     dict(t='Upper half', sub='MJF PA11', p=C([-49,-53,90])),
     dict(t='AR550 weapon ring', sub='3/16", two teeth, 126 g', p=C([-56,-52,44.5])),
     dict(t='TPU ear liners', sub='printed at home, 3 fits', p=C([-49.7,-28.7,44.5])),
     dict(t='Lower half', sub='MJF PA11', p=C([-49,-53,6])),
     dict(t='Rev-2 carrier PCB', sub='40 × 76, 4-layer', p=C([0,-36.5,-16.3])),
     dict(t='Bottom plate', sub='MJF PA11, 0.8 mm', p=C([-35,-45,-40]))]
R = [dict(t='M2.5 plate screws', p=near('pscrews','R'), dy=-30),
     dict(t='ELRS Lite receiver', p=A['rx'][0]),
     dict(t='Repeat AM32 dual ESC', p=A['esc'][0]),
     dict(t='D2822 1100KV motor', p=A['motorR'][0]),
     dict(t='Ø42 wheel', sub='cast VytaFlex 40 tread', p=A['wheelR'][0]),
     dict(t='MR128 bearing', p=A['brgR'][0]),
     dict(t='Ti M3 × 20 ring bolts', p=near('bolts','R'))]
for i in L: i['side'] = 'L'
for i in R: i['side'] = 'R'
out = callouts(im, L+R, pad_l=330, pad_r=330, fs=40, min_dy=118)
out = trim(out, 30); half(out).save(sys.argv[1] if len(sys.argv) > 1 else 'os/exploded_labelled.png')
