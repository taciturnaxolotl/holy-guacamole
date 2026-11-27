import os, trimesh, numpy as np, base64, json, struct
import os; SRC = os.environ.get('SRC', '../../scripts/v33m_')   # generator output prefix (concept_v33.py writes v33m_*.stl next to itself)
TGT={'lower':160000,'upper':160000,'ring':14000,'top':16000,'bot':16000,'motorR':12000,'motorL':12000,'pcbcomp':12000,'pcb':4000}
names=['lower','upper','ring','top','bot','motorR','motorL','wheelR','wheelL','hubR','hubL','brgR','brgL','usbf','pcb','pcbcomp','battery','esc','switch','rx','ledT','ledB','liner','bolts','nuts','pscrews','inserts','pcbscrews','mscrews','wscrews','hexkey']
ALIAS={'esc':'escd','upper':'upperfine','lower':'lowerfine'}
blob=bytearray(); meta=[]
for n in names:
    m=trimesh.load(SRC+ALIAS.get(n,n)+'.stl'); m.merge_vertices()
    f0=len(m.faces)
    if n in TGT and f0>TGT[n]:
        m=m.simplify_quadric_decimation(face_count=TGT[n])
    v=np.round(m.vertices/0.003).astype(np.int16); f=m.faces.astype(np.uint32 if len(m.vertices)>65535 else np.uint16)
    off=len(blob); blob+=v.tobytes()
    while len(blob)%4: blob+=b'\0'
    foff=len(blob); blob+=f.tobytes()
    while len(blob)%4: blob+=b'\0'
    meta.append(dict(n=n,vo=off,vn=len(v),fo=foff,fn=len(f),u32=bool(f.dtype==np.uint32)))
    print(n,f0,'->',len(f))
open('geo.b64','w').write(base64.b64encode(bytes(blob)).decode()); json.dump(meta,open('meta.json','w'))
print('bytes',len(blob))
