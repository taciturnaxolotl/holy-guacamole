import {createRequire} from 'module'; const {chromium} = createRequire(import.meta.url)('playwright');
const [,, src, out, w, h] = process.argv;
const b = await chromium.launch(); const p = await b.newPage({viewport: {width: +w, height: +h}, deviceScaleFactor: 2});
await p.goto('file://' + src); await p.screenshot({path: out, omitBackground: true}); await b.close();
