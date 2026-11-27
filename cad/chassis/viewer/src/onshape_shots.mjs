// Onshape-style README renders. usage: node onshape_shots.mjs <viewer.html> <outdir> [names]
import {createRequire} from 'module'; const {chromium} = createRequire(import.meta.url)('playwright');
import fs from 'fs';
const [,, PAGE, OUT = 'os', ONLY] = process.argv; fs.mkdirSync(OUT, {recursive: true});
const b = await chromium.launch({args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--js-flags=--max-old-space-size=4096']});
const p = await b.newPage({viewport: {width: 1200, height: 800}});
const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
await p.addInitScript(() => { window.__t = 0; performance.now = () => window.__t; window.requestAnimationFrame = cb => { window.__raf = cb; return 1; }; });
await p.goto('file://' + PAGE);
await p.waitForFunction(() => !document.getElementById('loading'), null, {timeout: 180000});
await p.addScriptTag({content: fs.readFileSync(new URL('./onshape_inject.js', import.meta.url), 'utf8')});
await p.evaluate(() => { document.getElementById('labels').checked = false; OS.setup(); });
const step = async (n) => { for (let i = 0; i < n; i++) await p.evaluate(() => { window.__t += 33; window.__raf(); }); };
const SHOTS = JSON.parse(fs.readFileSync(process.env.SHOTS || new URL('./onshape_shots.json', import.meta.url), 'utf8'));
for (const s of SHOTS) {
  if (ONLY && !ONLY.split(',').includes(s.name)) continue;
  await p.evaluate(o => {
    setView(o.view || 'assembled', true);
    for (const k of (o.hide || [])) if (meshes[k]) { meshes[k].grp.visible = false; meshes[k]._vis = false; }
    for (const k of (o.show || [])) if (meshes[k]) { meshes[k].grp.visible = true; meshes[k]._vis = true; }
    exTarget = o.ex ?? 0; exAmt = exTarget;
    OS.removeCaps();
  }, s);
  await step(3);
  const info = await p.evaluate(o => {
    let camera = cam;
    if (o.ortho) {
      const [hw, hh] = o.ortho; camera = new THREE.OrthographicCamera(-hw, hw, hh, -hh, 1, 3000); camera.up.set(...(o.up || [0, 0, 1]));
      camera.position.set(...o.cam); camera.lookAt(...o.tgt); camera.updateMatrixWorld(); camera.updateProjectionMatrix();
    } else { cam.fov = o.fov || 28; cam.position.set(...o.cam); controls.target.set(...o.tgt); cam.lookAt(...o.tgt); controls.update(); cam.near = 20; cam.far = 3000; cam.updateMatrixWorld(); }
    if (o.clip) { clipPlane.normal.set(...o.clip.n); clipPlane.constant = o.clip.c; root.traverse(x => { if (x.material && !x.userData.cap) { x.material.clippingPlanes = [clipPlane]; x.material.needsUpdate = true; } }); OS.addCaps(clipPlane); }
    else root.traverse(x => { if (x.material && x.material.clippingPlanes && x.material.clippingPlanes.length) { x.material.clippingPlanes = []; x.material.needsUpdate = true; } });
    const url = OS.render({w: o.w, h: o.h, camera, target: new THREE.Vector3(...o.tgt), wid: o.wid, kN: o.kN, kD: o.kD, noLines: o.noLines, hoff: o.hoff});
    const pts = {}; for (const [n, q] of Object.entries(o.pts || {})) pts[n] = OS.proj(q, camera, o.w, o.h);
    for (const k of (o.anchors || [])) { const m = meshes[k]; if (!m || !m.grp.visible) continue;
      const objs = (m.kids && m.kids.length > 1) ? m.kids.map(q => q.c).filter(c => c.visible) : [m.grp];
      pts[k] = objs.map(ob => { const c = new THREE.Box3().setFromObject(ob).getCenter(new THREE.Vector3()); return OS.proj([c.x, c.y, c.z], camera, o.w, o.h); }); }
    return {url, pts};
  }, s);
  fs.writeFileSync(`${OUT}/${s.name}.png`, Buffer.from(info.url.split(',')[1], 'base64'));
  fs.writeFileSync(`${OUT}/${s.name}.json`, JSON.stringify(info.pts));
  console.log('shot', s.name);
}
if (errs.length) console.log('ERR', errs.slice(0, 5));
await b.close();
