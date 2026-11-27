// Onshape-style renderer injected into the built viewer page.
// Phong shading + headlight, black feature edges, screen-space silhouettes (normal + depth discontinuities),
// optional hatched section caps, transparent background. OS.render() returns a PNG dataURL with real alpha.
window.OS = (() => {
  const CFG = Object.assign({L: [0.19, 0.59, 0.16], SPP: 0x5c5c5c, SHP: 56, SPM: 0x8c8c8c, SHM: 80}, window.OS_CFG || {});
  const PAL = {
    lower: 0x98c98a, upper: 0x98c98a, ring: 0x9a9ea2, top: 0xc6c6c6, bot: 0xc6c6c6, liner: 0xd6ef7a,
    wheelR: 0xf28a0a, wheelL: 0xf28a0a, hubR: 0x9a9a9a, hubL: 0x9a9a9a, motorR: 0x262626, motorL: 0x262626,
    brgR: 0xb4b6b8, brgL: 0xb4b6b8, bolts: 0x5e6266, pscrews: 0x5e6266, pcbscrews: 0x5e6266, mscrews: 0x5e6266, wscrews: 0x5e6266,
    inserts: 0xd2ad4c, nuts: 0xd2ad4c, battery: 0x3e6fd0, pcb: 0x2f8f50, pcbcomp: 0x3f4347, esc: 0x2c4f92,
    xt30f: 0xe9c23c, xt30j6: 0xe9c23c, xt30j7: 0xe9c23c, switch: 0xc9a227, swscrew: 0x5e6266, rx: 0x7b42b2,
    usbf: 0x56595c, ledT: 0xff8c1a, ledB: 0xff8c1a, hexkey: 0x1e1e1e, escfoam: 0x34373b, rxtape: 0x34373b,
    batfoam: 0x34373b, ledfoam: 0x34373b,
  };
  let rtC, rtN, rtO, quad, qscene, qcam, normMat, lights = [], capOn = false;
  const caps = [];
  const METAL = new Set(['ring', 'bolts', 'pscrews', 'pcbscrews', 'mscrews', 'wscrews', 'brgR', 'brgL', 'swscrew', 'inserts', 'nuts']);
  function phong(hex, clip, k) {
    const m = k && METAL.has(k);
    return new THREE.MeshPhongMaterial({color: new THREE.Color(hex).convertSRGBToLinear(), specular: new THREE.Color(m ? OS.SPM : OS.SPP), shininess: m ? OS.SHM : OS.SHP,
      side: THREE.FrontSide, clippingPlanes: clip || [], polygonOffset: false});
  }
  function setup() {
    // lights: soft hemisphere + camera headlight + a top key, like Onshape's default
    scene.children.filter(o => o.isLight).forEach(l => scene.remove(l));
    const hemi = new THREE.HemisphereLight(0xffffff, 0x3c3c3c, OS.L[0]); scene.add(hemi);
    const head = new THREE.DirectionalLight(0xffffff, OS.L[1]); scene.add(head); scene.add(head.target);
    const key = new THREE.DirectionalLight(0xffffff, OS.L[2]); key.position.set(-80, 60, 300); scene.add(key);
    lights = [hemi, head, key]; OS.head = head;
    scene.environment = null; scene.background = null;
    // materials
    for (const [k, m] of Object.entries(meshes)) {
      const hex = PAL[k] ?? 0x8a8d90;
      m.grp.traverse(o => {
        if (o.isMesh) { const nm = phong(hex, null, k); o.material = nm; o.userData.k = k; }
        if (o.isLineSegments) { o.material = new THREE.LineBasicMaterial({color: 0x000000, transparent: false}); }
      });
      m.mesh.material = m.grp.getObjectByProperty('isMesh', true)?.material || m.mesh.material;
      m.line.material = m.grp.getObjectByProperty('isLineSegments', true)?.material || m.line.material;
    }
    root.traverse(o => {           // harness, plugs, anything not in meshes
      if (o.isMesh && !(o.material && o.material.isMeshPhongMaterial)) o.material = phong(o.material && o.material.color ? '#' + o.material.color.clone().convertLinearToSRGB().getHexString() : 0x888888);
      if (o.isLineSegments && !(o.material.color && o.material.color.getHex() === 0)) o.material = new THREE.LineBasicMaterial({color: 0x000000});
    });
    normMat = new THREE.MeshNormalMaterial({side: THREE.FrontSide});
  }
  function targets(w, h) {
    if (rtC && rtC.width === w && rtC.height === h) return;
    [rtC, rtN, rtO].forEach(r => r && r.dispose());
    rtC = new THREE.WebGLRenderTarget(w, h, {type: THREE.HalfFloatType, samples: 4});
    rtN = new THREE.WebGLRenderTarget(w, h, {type: THREE.HalfFloatType});
    rtN.depthTexture = new THREE.DepthTexture(w, h); rtN.depthTexture.type = THREE.FloatType;
    rtO = new THREE.WebGLRenderTarget(w, h);
    if (!quad) {
      qscene = new THREE.Scene(); qcam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
      quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), new THREE.ShaderMaterial({
        uniforms: {tC: {value: null}, tN: {value: null}, tD: {value: null}, px: {value: new THREE.Vector2()}, near: {value: 1}, far: {value: 5000}, ortho: {value: 0},
                   kN: {value: 0.42}, kD: {value: 0.012}, wid: {value: 1.0}},
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = vec4(position.xy, 0., 1.); }',
        fragmentShader: `
          uniform sampler2D tC, tN, tD; uniform vec2 px; uniform float near, far, ortho, kN, kD, wid; varying vec2 vUv;
          float lin(float d){ if (ortho > .5) return near + d*(far-near); float z = d*2.-1.; return 2.*near*far/(far+near-z*(far-near)); }
          vec3 nrm(vec2 u){ return texture2D(tN, u).xyz*2.-1.; }
          float bg(vec2 u){ return texture2D(tD, u).x > .99999 ? 1. : 0.; }
          vec3 srgb(vec3 c){ c = clamp(c, 0., 1.); return mix(c*12.92, 1.055*pow(c, vec3(1./2.4))-.055, step(.0031308, c)); }
          void main(){
            vec4 c = texture2D(tC, vUv);
            float d0 = lin(texture2D(tD, vUv).x), b0 = bg(vUv); vec3 n0 = nrm(vUv);
            float e = 0.;
            for (int i = 0; i < 8; i++){
              float a = float(i)*0.7853982; vec2 o = vec2(cos(a), sin(a))*px*wid; vec2 u = vUv + o;
              float b1 = bg(u);
              if (b0 != b1) { e = 1.; continue; }
              if (b0 > .5) continue;
              float d1 = lin(texture2D(tD, u).x);
              if (abs(d1-d0) > kD*min(d0, d1) + .15) e = max(e, 1.);
              if (1.-dot(n0, nrm(u)) > kN) e = max(e, .9);
            }
            float a = max(c.a, b0 > .5 ? e : c.a);
            vec3 col = c.a > 0. ? c.rgb/max(c.a, 1e-4) : vec3(0.);
            vec3 o = mix(srgb(col), vec3(0.), e);
            gl_FragColor = vec4(o*a, a);   // premultiplied
          }`,
        depthTest: false, depthWrite: false, transparent: false}));
      qscene.add(quad);
    }
  }
  // section caps: back faces seen through the cut, flat part colour with 45° hatching in screen space
  function addCaps(plane) {
    removeCaps();
    for (const [k, m] of Object.entries(meshes)) {
      if (!m.grp.visible) continue;
      const hex = PAL[k] ?? 0x8a8d90; const col = new THREE.Color(hex).multiplyScalar(0.8).convertSRGBToLinear();
      const mat = new THREE.ShaderMaterial({uniforms: {c: {value: col}}, clipping: true, side: THREE.BackSide,
        vertexShader: ['#include <clipping_planes_pars_vertex>', 'void main(){', '#include <begin_vertex>', '#include <project_vertex>', '#include <clipping_planes_vertex>', '}'].join('\n'),
        fragmentShader: ['#include <clipping_planes_pars_fragment>', 'uniform vec3 c;', 'void main(){', '#include <clipping_planes_fragment>', 'float h = step(0.80, fract((gl_FragCoord.x+gl_FragCoord.y)/16.));', 'gl_FragColor = vec4(mix(c, c*0.3, h), 1.);', '}'].join('\n')});
      mat.clippingPlanes = [plane];
      m.grp.traverse(o => { if (o.isMesh && !o.userData.cap) { const cm = new THREE.Mesh(o.geometry, mat); cm.userData.cap = true; cm.renderOrder = -1; o.add(cm); caps.push(cm); } });
    }
    capOn = true;
  }
  function removeCaps() { for (const c of caps) c.parent && c.parent.remove(c); caps.length = 0; capOn = false; }
  function render(o = {}) {
    const W = o.w || 2400, H = o.h || 1400; targets(W, H);
    const camera = o.camera || cam;
    if (camera.isPerspectiveCamera) { camera.aspect = W / H; camera.updateProjectionMatrix(); }
    root.updateMatrixWorld(true);
    // headlight from the camera, a little above and to the left
    const v = new THREE.Vector3().subVectors(camera.position, o.target || controls.target).normalize();
    const up = camera.up.clone(), side = new THREE.Vector3().crossVectors(v, up).normalize();
    OS.head.position.copy(o.target || controls.target).addScaledVector(v, 400).addScaledVector(up, (o.hoff||[160,120])[0]).addScaledVector(side, (o.hoff||[160,120])[1]);
    OS.head.target.position.copy(o.target || controls.target);
    const bgc = scene.background; scene.background = null;
    const lineOff = []; if (o.noLines) root.traverse(x => { if (x.isLineSegments && x.visible) { x.visible = false; lineOff.push(x); } });
    renderer.setRenderTarget(rtC); renderer.setClearColor(0x000000, 0); renderer.clear(); renderer.render(scene, camera);
    // normal + depth pass: lines and caps off, clipping kept
    const hidden = []; root.traverse(x => { if ((x.isLineSegments || x.userData.cap) && x.visible) { x.visible = false; hidden.push(x); } });
    const saved = []; root.traverse(x => { if (x.isMesh && x.visible) { saved.push([x, x.material]); normMat.clippingPlanes = x.material.clippingPlanes; const nm = normMat.clone(); nm.clippingPlanes = x.material.clippingPlanes; x.material = nm; } });
    renderer.setRenderTarget(rtN); renderer.setClearColor(0x808080, 1); renderer.clear(); renderer.render(scene, camera);
    for (const [x, m] of saved) { x.material.dispose(); x.material = m; } for (const x of hidden) x.visible = true; for (const x of lineOff) x.visible = true;
    const u = quad.material.uniforms; u.tC.value = rtC.texture; u.tN.value = rtN.texture; u.tD.value = rtN.depthTexture;
    u.px.value.set(1 / W, 1 / H); u.near.value = camera.near; u.far.value = camera.far; u.ortho.value = camera.isOrthographicCamera ? 1 : 0;
    u.wid.value = o.wid || 1.2; u.kN.value = o.kN ?? 0.42; u.kD.value = o.kD ?? 0.012;
    renderer.setRenderTarget(rtO); renderer.setClearColor(0x000000, 0); renderer.clear(); renderer.render(qscene, qcam);
    const buf = new Uint8Array(W * H * 4); renderer.readRenderTargetPixels(rtO, 0, 0, W, H, buf);
    renderer.setRenderTarget(null); scene.background = bgc;
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const g = cv.getContext('2d'); const id = g.createImageData(W, H);
    for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {          // flip + un-premultiply
      const s = ((H - 1 - y) * W + x) * 4, d = (y * W + x) * 4, a = buf[s + 3];
      id.data[d] = a ? Math.min(255, buf[s] * 255 / a) : 0; id.data[d + 1] = a ? Math.min(255, buf[s + 1] * 255 / a) : 0; id.data[d + 2] = a ? Math.min(255, buf[s + 2] * 255 / a) : 0; id.data[d + 3] = a;
    }
    g.putImageData(id, 0, 0);
    return cv.toDataURL('image/png');
  }
  // world point -> pixel in the last render
  function proj(p, camera, W, H) { const v = new THREE.Vector3(...p).project(camera || cam); return [(v.x + 1) / 2 * W, (1 - v.y) / 2 * H]; }
  return Object.assign(CFG, {setup, render, addCaps, removeCaps, proj, PAL});
})();
