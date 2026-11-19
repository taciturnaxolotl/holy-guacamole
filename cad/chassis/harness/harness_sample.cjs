const THREE = require('./package/build/three.cjs');
const {HARNESS, PLUGS, expandBundles} = require('./harness.js'); expandBundles(THREE);
const out = [];
for (const h of HARNESS) h.wires.forEach((w, i) => {
  const c = new THREE.CatmullRomCurve3(w.pts.map(p => new THREE.Vector3(...p)), false, w.dense ? 'catmullrom' : 'centripetal', .5);
  const n = Math.max(60, Math.round(c.getLength() * 6));
  out.push({id: h.id, i, r: w.r, w: w.w || 0, len: c.getLength(), pts: c.getSpacedPoints(n).map(v => [v.x, v.y, v.z])});
});
require('fs').writeFileSync('harness_samples.json', JSON.stringify({wires: out, plugs: PLUGS}));
console.log('wires', out.length);
