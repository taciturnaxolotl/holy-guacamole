// Holy Guacamole v3.4c wiring harness, hand-routed in bot frame mm (+y = N/switch, -y = S/ESC, z up from the bottom plate).
// Collision-checked by harness_check.py against the frame, parts, plug bodies and every other wire.
const RED=0xd8352b, BLK=0x2b2b2e, PH=[0x3f7fe0,0xf0c02e,0xe6e6e6];
const J6P=[[13.8,-15.8],[13.8,-10.8]], J7P=[[-13.8,-15.8],[-13.8,-10.8]];   // v3.4g: J7 mirrors J6 in the SW        // XT30s turned 90° (long axis along y): 5.6 wide fits between rib (x 10.75) and bay wall, no rib notch
const XT_CUP=23.3;                                           // top of the solder-cup heat-shrink on the mated plug
const T225=[0.7071,-0.7071];                                 // tangent to the 225° LED axis
const LEDIN=[-26.96,-26.96];                                 // TinySLED inner end (r 38.13)
const led=(dz,o)=>[LEDIN[0]+T225[0]*o, LEDIN[1]+T225[1]*o];
const L=(p,o,r)=>[p[0]+T225[0]*o+0.7071*r, p[1]+T225[1]*o+0.7071*r];   // radial-inward step r from the LED end, tangent offset o

// phases: ESC pad -> short pigtail -> female 2 mm bullet. Bullets lie along x in the slot between the ESC and the S-ledge face (y -32.1),
// stacked z 12.5 / 16.3 / 20.1, female E end (x 18.5) .. male W end (x 4.5). Motor side = the motor's own ~70 mm silicone leads,
// twisted 3-wire bundle: out of the male ends, U-turn into the S gap, E along it, a loose 3-layer serpentine in the corridor, through the lead channel to the motor.
const BUL={y:-32.1, x0:4.5, xm:11.0, x1:18.5, z:[12.5,16.3,20.1], r:1.8};
const phEsc=(s)=>[0,1,2].map(k=>{ const zp=10.75+6.5*k, zb=BUL.z[k];
  return {c:PH[k], r:.55, pts:[[13.6,-37.2,zp],[15.6,-37.3,zp],[18.4,-36.4,(zp+zb)/2],[19.6,-34.4,zb],[19.5,-32.6,zb],[BUL.x1,BUL.y,zb]].map(q=>[q[0]*s,q[1],q[2]])}; });
const phBundle=(s)=>({c:PH, r:.55, twist:.72, pitch:15, center:[[2.6,-30.4,16.3],[2.3,-28.9,15.2],[4.6,-27.6,12.8],[9,-27.6,12.2],[13.6,-27.4,12.1],[15.6,-25.6,12.0],[15.6,-22.8,12.0],[15.6,-21.4,13.0],[15.6,-21.6,15.0],[15.6,-23.0,16.0],[15.6,-26.3,16.2],[15.6,-27.8,18.1],[15.6,-26.3,20.0],[15.6,-23.4,20.0],[16.8,-21.9,18.8],[18.6,-21.1,16.6],[20.6,-20.8,14.8],[22.6,-20.7,14.5],[24.4,-20.6,14.5]].map(q=>[q[0]*s,q[1],q[2]]),
  fan:[0,1,2].map(k=>[[BUL.x0,BUL.y,BUL.z[k]],[3.9,-32.05,BUL.z[k]*.8+16.3*.2],[3.2,-31.6,BUL.z[k]*.45+16.3*.55]].map(q=>[q[0]*s,q[1],q[2]]))});
const ph=(s)=>[...phEsc(s), phBundle(s)];
// expand twisted bundles into individual wires (needs THREE): helix about the centreline, parallel-transport frames, fan-in from each bullet
function expandBundles(THREE){
  for (const h of HARNESS){ const out=[];
    for (const w of h.wires){ if (!w.center){ out.push(w); continue; }
      const cv=new THREE.CatmullRomCurve3(w.center.map(p=>new THREE.Vector3(...p)),false,'centripetal',.5), L=cv.getLength(), n=Math.round(L*1.5);
      const fr=cv.computeFrenetFrames(n,false);
      const z0=[0,1,2].map(j=>{ const th=2*Math.PI*j/3; return Math.cos(th)*fr.normals[0].z+Math.sin(th)*fr.binormals[0].z; });
      const p00=cv.getPointAt(0), st=j=>[0,1,2].map(a=>p00.getComponent(a)+w.twist*(Math.cos(2*Math.PI*j/3)*fr.normals[0].getComponent(a)+Math.sin(2*Math.PI*j/3)*fr.binormals[0].getComponent(a)));
      let order=[0,1,2], best=1e9;                                  // assign bullets to strands with the least total fan travel (no crossing)
      for (const pm of [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]]){ const d=pm.reduce((s,j,k)=>{ const S=st(j), P=w.fan[k][0]; return s+Math.hypot(S[0]-P[0],S[1]-P[1],S[2]-P[2])**2; },0); if(d<best){best=d; order=pm;} }
      for (let k=0;k<3;k++){ const j=order[k], th0=2*Math.PI*j/3, p0=cv.getPointAt(0);
        const S=[0,1,2].map(a=>p0.getComponent(a)+w.twist*(Math.cos(th0)*fr.normals[0].getComponent(a)+Math.sin(th0)*fr.binormals[0].getComponent(a)));
        const P0=w.fan[k][0], sg=Math.sign(P0[0]), A=[P0[0]-1.6*sg,P0[1],P0[2]];
        const pts=[P0, A, [.45*A[0]+.55*S[0], .45*A[1]+.55*S[1], .25*A[2]+.75*S[2]]];
        for (let i=0;i<=n;i++){ const t=i/n, p=cv.getPointAt(t), th=2*Math.PI*(t*L/w.pitch)+2*Math.PI*j/3, N=fr.normals[i], B=fr.binormals[i];
          pts.push([p.x+w.twist*(Math.cos(th)*N.x+Math.sin(th)*B.x), p.y+w.twist*(Math.cos(th)*N.y+Math.sin(th)*B.y), p.z+w.twist*(Math.cos(th)*N.z+Math.sin(th)*B.z)]); }
        out.push({c:w.c[k], r:w.r, pts, dense:1}); } }
    h.wires=out; } }

// ESC signal (4 pads on the ESC's bottom edge, x -3.5..2.5) -> nested L in the S groove -> J4 plug S face (rev-2 244dd04: J4 centre x 8.5, pins 6.625 + 1.25 i)
const sig=[0,1,2,3].map(i=>{ const x=[-3.5,-1.55,0.5,2.5][i], y=-38.75+0.85*(3-i), p=6.625+1.25*i;
  return {c:[0x2b2b2e,0xf2f2f2,0xf0c02e,0x2b2b2e][i], r:.32, pts:[[x,-37.2,7.25],[x,-37.3,6.2],[x,y+.2,4.6],[x+.9,y,4.1],[p-1.0,y,4.1],[p,y+.9,4.3],[p,-35.2,4.75],[p,-34.25,4.8]]}; });

// receiver (4 leads off its N face) -> upper groove over the ESC top -> down the gap N of the ESC -> J5 plug S face (J5 centre x -1.1, pins -2.975 + 1.25 i)
const rxw=[0,1,2,3].map(i=>{ const x=-2.375+1.25*i, p=x-0.6;   // stays in the tray groove at the old pitch, jogs 0.6 W in the drop to the moved J5
  return {c:[0xd94fb0,0xc23e9c,0xe36fc2,0xb0368c][i], r:.32, pts:[[x,-45.0,26.6],[x,-43.8,27.8],[x,-39.6,27.85],[x,-37.0,27.85],[x,-36.1,27.3],[x,-35.9,26.2],[x,-35.9,10.4],[p,-35.9,8.4],[p,-35.85,6.6],[p,-35.2,5.2],[p,-34.25,4.8]]}; });

// TinySLED leads as 2-core GH cables: straight out of the LED end along its radial axis, then routed
const LP=(z,dz)=>{ const a=L(LEDIN,0,0), b=L(LEDIN,0,1.6); return [[a[0],a[1],z],[b[0],b[1],z+dz]]; };
// v3.4g: J7 took J2's SW spot, so J2 (GH-2) moved to the old J7 spot in the NW, opening S: header x -17.48..-10.52, y 23.0..29.4; plug y 18.5..23.0,
// cable out of its S face. Y-splice sleeve (axis y, x -13.6, y 15.6..18.2, z 4.6) sits between L1 (moved to y 8..15.1) and the plug.
// Both LED leads leave the SW: the bottom one out of the channel mouth (z 3.3), the top one down the W corridor W of J7; they run N together along
// the W board edge (x -19.4 / -18.2, z 3.4 / 4.0, under the motor-screw key path at z >= 6.53), jog E N of U4 (y 6.5, box y <= 4.9) to x -11.6,
// and run N between L1 (x <= -12.45) and the buck (<= 1.2 tall) into the splice.
const SPL={x:-13.6, y0:15.6, y1:18.2, z:4.6};
const ledTop=[{c:0x3cc46a, r:.55, pts:[...LP(27.59,-.05),[-23.2,-26.95,26.9],[-19.4,-26.95,26.6],[-19.2,-24.6,24.4],[-18.6,-20.0,23.8],[-18.2,-12.6,22.0],[-18.2,-10.5,14.0],[-18.2,-9.0,5.0],[-18.2,-7.5,4.1],[-18.2,0.0,4.3],[-17.2,5.0,5.2],[-15.0,6.6,5.5],[-12.4,6.9,5.4],[-11.4,7.6,5.4],[-11.4,13.5,5.6],[-12.4,14.6,5.7],[-13.7,15.0,5.5],[-14.3,SPL.y0,SPL.z]]}];
const ledBot=[{c:0x2ea456, r:.55, pts:[...LP(1.41,.15),[-23.2,-26.95,3.1],[-21.2,-26.95,3.3],[-19.9,-26.6,3.35],[-19.4,-24.0,3.4],[-19.4,-12.0,3.4],[-19.4,0.0,3.4],[-18.8,4.8,3.6],[-16.4,6.8,4.0],[-12.6,6.9,4.2],[-11.4,7.6,4.2],[-11.4,13.5,4.2],[-11.9,14.8,4.3],[-12.9,SPL.y0,SPL.z]]},
  {c:0x34b85e, r:.55, pts:[[SPL.x,SPL.y1,SPL.z],[SPL.x,18.35,SPL.z],[SPL.x,18.5,SPL.z]]}];   // splice -> J2 plug S face

const HARNESS = [
  {id:'bat', l:'Battery → J6 (XT30, 20 AWG)', sw:[RED,BLK], wires:[
    {c:RED, r:.8, pts:[[-0.6,-23.25,22.4],[-0.6,-25.4,22.6],[1.6,-28.4,23.4],[13.6,-28.4,23.6],[16.2,-26.4,23.8],[16.6,-21.0,24.2],[16.7,-14.6,24.4],[15.6,-11.6,24.5],[13.8,-10.8,24.3],[13.8,-10.8,XT_CUP]]},
    {c:BLK, r:.8, pts:[[2.4,-23.25,22.4],[2.4,-24.6,22.6],[4.6,-26.6,23.4],[9.6,-26.6,23.6],[11.6,-24.6,23.8],[11.8,-21.0,24.2],[13.0,-18.4,24.4],[13.8,-16.6,24.3],[13.8,-15.8,XT_CUP]]}]},
  {id:'sw', l:'J7 (SW) ↔ switch loop, twisted pair up the W corridor (v3.4g)', sw:[0xff7a1a], wires:[
    {c:0xff7a1a, r:.75, pts:[[-13.8,-10.8,XT_CUP],[-13.8,-10.1,24.3],[-13.5,-7.0,24.3],[-13.5,10.0,24.3],[-13.5,24.0,24.3],[-13.8,30.2,24.3],[-13.6,32.6,24.0],[-12.6,35.0,22.8],[-10,36.6,21.9],[-7.2,37.1,21.6],[-5.9,37.5,21.5],[-5.9,38.6,21.5]]},
    {c:0xe0601a, r:.75, pts:[[-13.8,-15.8,XT_CUP],[-14.3,-15.2,24.3],[-15.9,-12.6,24.4],[-15.9,-7.0,24.4],[-15.9,10.0,24.4],[-16.2,24.0,24.4],[-16.6,27.6,24.2],[-16.6,30.6,23.6],[-15.4,33.4,22.2],[-12.6,35.6,20.4],[-9,36.2,19.7],[-5.4,36.3,19.9],[-4.1,36.9,20.3],[-4.1,38.6,20.5]]}]},
  {id:'escpwr', l:'J1 → ESC power (20 AWG, over the S ledge)', sw:[RED,BLK], wires:[
    // rev 2 (244dd04): J1 = two SMD lap pads S of the beam, GND (pad 2) x 13.7..16.3 W, VBUS (pad 1) x 16.9..19.5 E on the edge power strip, y -29.3..-25.3; leads drop down the ledge face and lie N along the pad
    {c:RED, r:.8, pts:[[11.1,-36.65,8.8],[11.1,-35.85,9.9],[12.6,-35.1,10.6],[16.0,-34.3,10.5],[18.0,-33.6,9.6],[18.4,-32.6,8.6],[18.4,-31.4,7.95],[18.4,-29.5,7.95],[18.3,-28.3,4.8],[18.2,-27.4,3.35],[18.2,-25.8,3.35]]},
    {c:BLK, r:.8, pts:[[7.1,-36.65,8.4],[7.1,-36.0,8.4],[7.6,-34.9,8.4],[13.6,-34.9,8.4],[15.2,-34.2,8.4],[15.6,-32.8,8.3],[15.6,-31.4,7.95],[15.6,-29.5,7.95],[15.3,-28.3,4.8],[15.0,-27.4,3.35],[15.0,-25.8,3.35]]}]},
  {id:'phE', l:'Motor E: 70 mm silicone leads (twisted) → 2 mm bullets → ESC', sw:PH, wires:ph(1)},
  {id:'phW', l:'Motor W: 70 mm silicone leads (twisted) → 2 mm bullets → ESC', sw:PH, wires:ph(-1)},
  {id:'escsig', l:'J4 → ESC: GND · DSHOT1 · DSHOT2 · GND (GH-4, S groove; EDT on the DSHOT lines)', sw:[0x2b2b2e,0xf2f2f2,0xf0c02e,0x2b2b2e], wires:sig},
  {id:'rx', l:'Receiver → J5 (GH-4, over the ESC, down the gap)', sw:[0xd94fb0], wires:rxw},
  {id:'ledT', l:'Top LED → W corridor → Y-splice → J2 (NW, opens S)', sw:[0x3cc46a], wires:ledTop},
  {id:'ledB', l:'Bottom LED → along the W board edge → Y-splice → J2 (NW)', sw:[0x2ea456], wires:ledBot},
  {id:'usb', l:'XIAO USB-C → port (FPC under the N ledge)', sw:[0xc9cdd3], wires:[
    {c:0xc9a64a, r:.12, w:7.6, pts:[[6.7,37.4,4.6],[6.7,42,4.6],[6.7,47.2,4.7],[6.7,50.6,5.6],[6.7,52.4,8.5],[6.7,52.9,14],[6.7,52.9,21.4]]}]},
  {id:'bal', l:'Balance lead (XH-4P), tucked high in the S gap', sw:[0xf2f2f2], wires:[-10.7,-8.2,-5.7,-3.2].map((x,i)=>({c:[RED,BLK,0xf2f2f2,0xf0c02e][i], r:.3,
    pts:[[-6.9+(i-1.5)*1.1,-23.25,19.6],[-6.9+(i-1.5)*1.6,-23.9,20.6],[x,-24.4,22.8],[x,-24.75,23.5],[x,-25.25,23.5]]}))},
];

// plug / connector bodies drawn with the harness (the CAD box for the XT30s is replaced by these)
const PLUGS = [
  // XT30 female PCB (XT30UPB-F) + mated male + solder-cup heat-shrink; D-face chamfers toward +y on J6, -y on J7
  {k:'xt30', id:'J6', pins:J6P, ch:1},
  {k:'xt30', id:'J7', pins:J7P, ch:-1},
  // GH plugs (1.25 pitch), drawn mated into the headers; wires leave the back face
  {k:'box', id:'J4p', b:[5.1,11.9,-34.25,-29.6,2.75,6.9], c:0xe8e2d0},
  {k:'box', id:'J5p', b:[-4.5,2.3,-34.25,-29.6,2.75,6.9], c:0xe8e2d0},
  {k:'box', id:'J2p', b:[-17.0,-11.0,18.5,23.0,2.55,6.8], c:0xe8e2d0},
  {k:'box', id:'U5', b:[-6.35,-2.35,-19.47,-15.47,2.5,3.5], c:0x1b1b1b, hidden:1},
  {k:'box', id:'J2h', b:[-17.48,-10.52,23.0,29.4,2.5,6.75], c:0x1b1b1b, hidden:1},
  {k:'sleeve', id:'SPL', of:'ledB', ay:1, x:SPL.x, y0:SPL.y0, y1:SPL.y1, z:SPL.z, r:.95, c:0x1c1c1e},
  {k:'box', id:'J1p', b:[13.7,19.5,-29.3,-25.3,2.5,2.55], c:0xc9a64a, hidden:1},
  {k:'box', id:'XH', b:[-11.9,-2.0,-29.45,-25.25,20.5,26.5], c:0xf3efe4},
  ...[1,-1].flatMap(s=>[0,1,2].map(k=>({k:'bullet', id:'B'+(s>0?'E':'W')+k, of:s>0?'phE':'phW', y:BUL.y, z:BUL.z[k], x0:s*BUL.x0, xm:s*BUL.xm, x1:s*BUL.x1, r:BUL.r, c:PH[k]}))),
  {k:'box', id:'USBp', b:[2.5,10.9,30.9,37.4,3.3,5.9], c:0x9aa0a8},
];
if (typeof module !== 'undefined') module.exports = {HARNESS, PLUGS, expandBundles};
