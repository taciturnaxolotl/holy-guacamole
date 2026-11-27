"""inline harness.js, mesh metadata and base64 geometry into template.html.
usage: python3 build_page.py            -> holy-guacamole.html (geo.b64 / meta.json, from pack33.py)
       python3 build_page.py hi         -> page_hi.html (geo_hi.b64 / meta_hi.json, from pack_hi.py; used for the README renders)"""
import sys, os
hi = len(sys.argv) > 1 and sys.argv[1] == 'hi'
h = open(os.environ.get('HARNESS', '../../harness/harness.js')).read().replace("if (typeof module !== 'undefined') module.exports = {HARNESS, PLUGS};", "")
t = open('template.html').read().replace('__HARNESS__', h).replace('__META__', open('meta_hi.json' if hi else 'meta.json').read()).replace('__GEO__', open('geo_hi.b64' if hi else 'geo.b64').read())
out = 'page_hi.html' if hi else 'holy-guacamole.html'
open(out, 'w').write(t); print(out, round(len(t)/1e6, 2), 'MB')
