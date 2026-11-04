import math
import re
import uuid as uuidlib


def tokenize(text):
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in " \t\r\n":
            i += 1
        elif c in "()":
            yield (c, i, i + 1)
            i += 1
        elif c == '"':
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            yield ("s", i, j + 1)
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n()":
                j += 1
            yield ("a", i, j)
            i = j


class Node:
    def __init__(self, start):
        self.start, self.end, self.items = start, None, []

    @property
    def tag(self):
        return self.items[0] if self.items else None

    def children(self, tag=None):
        return [x for x in self.items if isinstance(x, Node) and (tag is None or x.tag == tag)]

    def child(self, tag):
        c = self.children(tag)
        return c[0] if c else None

    def prop(self, name):
        for p in self.children("property"):
            if p.items[1] == name:
                return p.items[2]
        return None


def parse(text):
    stack, root = [], None
    for kind, s, e in tokenize(text):
        if kind == "(":
            node = Node(s)
            if stack:
                stack[-1].items.append(node)
            stack.append(node)
        elif kind == ")":
            node = stack.pop()
            node.end = e
            if not stack:
                root = node
        else:
            tok = text[s:e]
            stack[-1].items.append(tok[1:-1] if kind == "s" else tok)
    return root


def r(v):
    return round(float(v), 3)


def point_of(node):
    at = node.child("at")
    return (r(at.items[1]), r(at.items[2]))


class Sheet:
    def __init__(self, path):
        self.path = path
        self.text = open(path).read()
        self.reparse()

    def reparse(self):
        self.root = parse(self.text)
        self.libs = {s.items[1]: s for s in self.root.child("lib_symbols").children("symbol")}

    def blocks(self, tag):
        return self.root.children(tag)

    def symbols(self):
        return self.blocks("symbol")

    def ref_of(self, sym):
        return sym.prop("Reference")

    def find_symbol(self, ref):
        for s in self.symbols():
            if self.ref_of(s) == ref:
                return s
        raise KeyError(ref)

    def lib_pins(self, lib_id, unit):
        pins = []

        def walk(node):
            for sub in node.children("symbol"):
                m = re.match(r".*_(\d+)_(\d+)$", sub.items[1])
                if m and int(m.group(1)) not in (0, unit):
                    continue
                walk(sub)
            for p in node.children("pin"):
                at = p.child("at")
                pins.append((p.child("number").items[1], float(at.items[1]), float(at.items[2])))

        walk(self.libs[lib_id])
        return pins

    def symbol_pins(self, sym):
        lib_id = sym.child("lib_id").items[1]
        unit = int(sym.child("unit").items[1]) if sym.child("unit") else 1
        at = sym.child("at")
        x, y = float(at.items[1]), float(at.items[2])
        rot = float(at.items[3]) if len(at.items) > 3 else 0.0
        mirror = sym.child("mirror")
        mirror = mirror.items[1] if mirror else None
        out = []
        for num, px, py in self.lib_pins(lib_id, unit):
            py = -py
            a = math.radians(-rot)
            qx = px * math.cos(a) - py * math.sin(a)
            qy = px * math.sin(a) + py * math.cos(a)
            if mirror == "x":
                qy = -qy
            elif mirror == "y":
                qx = -qx
            out.append((num, (r(x + qx), r(y + qy))))
        return out

    def wires(self):
        out = []
        for w in self.blocks("wire"):
            pts = w.child("pts").children("xy")
            out.append((w, (r(pts[0].items[1]), r(pts[0].items[2])), (r(pts[1].items[1]), r(pts[1].items[2]))))
        return out

    def remove_nodes(self, nodes):
        t = self.text
        for s, e in sorted(((n.start, n.end) for n in nodes), reverse=True):
            ls = t.rfind("\n", 0, s) + 1
            le = t.find("\n", e)
            le = len(t) if le == -1 else le + 1
            t = t[:ls] + t[le:] if t[ls:s].strip() == "" and t[e:le].strip() == "" else t[:s] + t[e:]
        self.text = t
        self.reparse()

    def set_fields(self, ref, fields):
        sym = self.find_symbol(ref)
        t = self.text[sym.start:sym.end]
        for k, v in fields.items():
            t, n = re.subn(r'\(property "%s" "[^"]*"' % re.escape(k), '(property "%s" "%s"' % (k, v.replace('"', '\\"')), t)
            if n == 0:
                raise KeyError(k)
        self.text = self.text[:sym.start] + t + self.text[sym.end:]
        self.reparse()

    def save(self):
        open(self.path, "w").write(self.text)


def on_segment(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    if p in (a, b):
        return False
    if abs((bx - ax) * (py - ay) - (by - ay) * (px - ax)) > 1e-6:
        return False
    return min(ax, bx) - 1e-6 <= px <= max(ax, bx) + 1e-6 and min(ay, by) - 1e-6 <= py <= max(ay, by) + 1e-6


def prune(sheet, keep_hier=()):
    removed = 0
    while True:
        ends = {}

        def add(p, what):
            ends.setdefault(p, []).append(what)

        for s in sheet.symbols():
            for num, p in sheet.symbol_pins(s):
                add(p, s)
        wires = sheet.wires()
        for w, a, b in wires:
            add(a, w)
            add(b, w)
        for tag in ("label", "global_label", "hierarchical_label"):
            for l in sheet.blocks(tag):
                add(point_of(l), l)

        def degree(p, me):
            return len([x for x in ends.get(p, []) if x is not me]) + sum(1 for w, a, b in wires if w is not me and on_segment(p, a, b))

        dead = [w for w, a, b in wires if degree(a, w) == 0 or degree(b, w) == 0]
        for tag in ("label", "hierarchical_label"):
            for l in sheet.blocks(tag):
                if tag == "hierarchical_label" and l.items[1] in keep_hier:
                    continue
                if degree(point_of(l), l) == 0:
                    dead.append(l)
        for s in sheet.symbols():
            if sheet.ref_of(s).startswith("#PWR"):
                p = sheet.symbol_pins(s)[0][1]
                if degree(p, s) == 0:
                    dead.append(s)
        for j in sheet.blocks("junction"):
            p = point_of(j)
            if len(ends.get(p, [])) + 2 * sum(1 for w, a, b in wires if on_segment(p, a, b)) < 3:
                dead.append(j)
        for nc in sheet.blocks("no_connect"):
            if not any(x in sheet.symbols() for x in ends.get(point_of(nc), [])):
                dead.append(nc)
        if not dead:
            return removed
        removed += len(dead)
        sheet.remove_nodes(dead)


def nets(path):
    root = parse(open(path).read())
    return {n.child("name").items[1]: sorted((x.child("ref").items[1], x.child("pin").items[1]) for x in n.children("node"))
            for n in root.child("nets").children("net")}
