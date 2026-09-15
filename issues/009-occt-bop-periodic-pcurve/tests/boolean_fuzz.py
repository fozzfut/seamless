"""Defect 009 regression fuzz: the same generated Boolean cases on any FreeCAD, one JSON line per record.

Run it through tests/run_regression.ps1, which gives FreeCADCmd copies of the preferences:
    "<FreeCAD>/bin/FreeCADCmd.exe" -u <copy of user.cfg> -s <copy of system.cfg> boolean_fuzz.py
Environment: FUZZ_OUT  the result file (required)
             FUZZ_SEED default 9009
             FUZZ_PAIRS random primitive pairs, default 150 (each gives Cut, Common, Fuse and Section)
             FUZZ_PLACEMENTS bases per wide tool, default 12 (half of them turned about the tool's axis only)

Everything is generated from the seed - no owner data. Two families:

random  two primitives (box, cylinder, cone, sphere, torus) of random size, each at a random position and turned about
        a random axis: base.cut / common / fuse / section(tool), with the analytic volumes of both.
wide    a tool whose periodic side face is moved and widened in the BREP text (FreeCAD's Python API cannot set a
        pcurve), against random bases that cross that face:
          cyl-half   Part.makeCylinder, surface frame turned half a turn, every pcurve moved by -pi: UV [-pi, pi], the
                     layout of the owner's part (README section 2) and of the issue's repro;
          cone-half  Part.makeCone, the same;
          bspline    Part.makeCylinder(...).toNurbs(): every pcurve of the side face moved by minus one period;
        then the seam pcurve at the high end moved by `over` (0 = exactly one period wide; 1e-6 .. 1e-3 rad, scaled to
        the surface's own period for the B-spline), seam edge and its vertices given tolerance max(1e-3, 2 r over).
        The reference of every wide record is the same operation with the clean primitive (unedited, standard domain),
        computed in the same run.

compare_fuzz.py compares two result files and judges every record in which the kernels differ.
"""
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import traceback

import FreeCAD as App
import Part

V = App.Vector
OUT = os.environ.get("FUZZ_OUT")
SEED = int(os.environ.get("FUZZ_SEED", "9009"))
PAIRS = int(os.environ.get("FUZZ_PAIRS", "150"))
PLACEMENTS = int(os.environ.get("FUZZ_PLACEMENTS", "12"))
OVERS = [0.0, 1e-6, 1e-5, 1e-4, 1e-3]

# --------------------------------------------------------------------------- BREP text
# Reading and writing the records a pcurve edit needs. Adapted from HybridDesign's hybriddesign/ops/pcurve_repair.py
# (same author), which repairs the defect on imported parts; the format is OCCT's BRepTools_ShapeSet text.

_FLAGS = re.compile(r"^[01]{7}$")
_C2D_FIXED = {1: 4, 2: 7, 3: 8, 4: 7, 5: 8}


def _c2d_end(tokens, i):
    kind = int(tokens[i])
    if kind in _C2D_FIXED:
        return i + 1 + _C2D_FIXED[kind]
    if kind == 6:
        rational, degree = int(tokens[i + 1]), int(tokens[i + 2])
        return i + 3 + (degree + 1) * (2 + rational)
    if kind == 7:
        rational, nbpoles, nbknots = int(tokens[i + 1]), int(tokens[i + 4]), int(tokens[i + 5])
        return i + 6 + nbpoles * (2 + rational) + 2 * nbknots
    if kind == 8:
        return _c2d_end(tokens, i + 3)
    if kind == 9:
        return _c2d_end(tokens, i + 2)
    raise ValueError("2D curve type %d" % kind)


class Brep(object):
    def __init__(self, text):
        self.lines = text.split("\n")
        m = re.search(r"CASCADE Topology V(\d+)", text[:400])
        self.version = int(m.group(1)) if m else 1
        head = {}
        for i, line in enumerate(self.lines):
            parts = line.split()
            if len(parts) == 2 and parts[0] in ("Curve2ds", "Curves", "Surfaces", "TShapes") and parts[1].isdigit():
                head.setdefault(parts[0], (i, int(parts[1])))
        self.head = head
        c_line, count = head["Curve2ds"]
        tokens = " ".join(self.lines[c_line + 1:head["Curves"][0]]).split()
        self.c2d_span = (c_line, head["Curves"][0])
        self.curves = []
        i = 0
        while i < len(tokens):
            j = _c2d_end(tokens, i)
            self.curves.append(tokens[i:j])
            i = j
        if len(self.curves) != count:
            raise ValueError("read %d of %d 2D curves" % (len(self.curves), count))
        t_line, self.count = head["TShapes"]
        self.records = []
        i = t_line + 1
        for _ in range(self.count):
            kind = self.lines[i].strip()
            i += 1
            geom = []
            while not _FLAGS.match(self.lines[i].strip()):
                geom.append(i)
                i += 1
            i += 1
            refs = []
            while True:
                parts = self.lines[i].split()
                i += 1
                refs.extend(parts)
                if "*" in parts:
                    break
            refs = refs[:refs.index("*")]
            self.records.append((kind, geom, [(refs[k], int(refs[k + 1])) for k in range(0, len(refs), 2)]))
        while i < len(self.lines) and not self.lines[i].split():
            i += 1
        self.root = self.count - int(self.lines[i].split()[0][1:])

    def below(self, pos, kind):
        out, seen = [], set()

        def visit(p):
            k, _geom, refs = self.records[p]
            if k == kind:
                if p not in seen:
                    seen.add(p)
                    out.append(p)
                return
            for ref, _loc in refs:
                visit(self.count - int(ref[1:]))

        visit(pos)
        return out

    def face_surface(self, pos):
        first = self.lines[self.records[pos][1][0]].split()
        return int(first[2]), int(first[3])

    def pcurve_lines(self, edge_pos, surface):
        geom = self.records[edge_pos][1]
        found = []
        k = 1
        while k < len(geom):
            parts = self.lines[geom[k]].split()
            if parts == ["0"]:
                break
            if parts and parts[0] in ("2", "3"):
                surf = int(parts[2]) if parts[0] == "2" else int(parts[3])
                if surf == surface:
                    found.append((geom[k], parts))
                if self.version == 2:
                    k += 1
            k += 1
        return found

    def text(self, edits):
        lines = list(self.lines)
        for index, parts in edits.items():
            lines[index] = " ".join(parts)
        start, stop = self.c2d_span
        table = ["Curve2ds %d" % len(self.curves)] + [" ".join(c) for c in self.curves]
        return "\n".join(lines[:start] + table + lines[stop:])


def _curve_x(tokens):
    """The u of a pcurve that is an iso-u line: a line's origin, or a B-spline's first pole."""
    if tokens[0] == "1":
        return float(tokens[1])
    if tokens[0] == "7":
        return float(tokens[6])
    raise ValueError("pcurve type %s" % tokens[0])


def _shifted(tokens, du):
    out = list(tokens)
    if out[0] == "1":
        out[1] = repr(float(out[1]) + du)
        return out
    if out[0] == "7":
        rational, nbpoles = int(out[1]), int(out[4])
        step = 2 + rational
        for k in range(nbpoles):
            out[6 + k * step] = repr(float(out[6 + k * step]) + du)
        return out
    raise ValueError("pcurve type %s" % out[0])


def widened(shape, over, mode, radius):
    """shape with its periodic side face moved (mode 'half' or 'period') and its seam pcurve moved `over` rad further."""
    faces = shape.Faces
    k = [i for i, f in enumerate(faces) if f.Surface.isUPeriodic()]
    if len(k) != 1:
        raise ValueError("%d periodic faces" % len(k))
    k = k[0]
    period = faces[k].Surface.UPeriod()
    brep = Brep(shape.exportBrepToString())
    pos = brep.below(brep.root, "Fa")[k]
    surf, _loc = brep.face_surface(pos)
    edits = {}
    if mode == "half":
        s_line = brep.head["Surfaces"][0]
        record = brep.lines[s_line + surf].split()
        if record[0] not in ("2", "3"):
            raise ValueError("surface record %s cannot be turned" % record[0])
        for j in range(7, 13):
            record[j] = repr(-float(record[j]))
        edits[s_line + surf] = record
        shift = -math.pi
    else:
        shift = -period
    extra = over * period / (2 * math.pi)
    tol = max(1e-3, 2.0 * radius * over)
    for e in brep.below(pos, "Ed"):
        lines = brep.pcurve_lines(e, surf)
        seam = any(parts[0] == "3" for _i, parts in lines)
        for index, parts in lines:
            parts = list(parts)
            slots = [1] if parts[0] == "2" else [1, 2]
            curves = []
            for slot in slots:
                raw = parts[slot][:-2] if slot == 2 else parts[slot]
                curves.append((slot, brep.curves[int(raw) - 1]))
            high = max(curves, key=lambda sc: _curve_x(sc[1]))[0] if len(curves) == 2 else None
            for slot, tokens in curves:
                du = shift + (extra if (over and slot == high) else 0.0)
                brep.curves.append(_shifted(tokens, du))
                suffix = parts[slot][-2:] if slot == 2 else ""
                parts[slot] = str(len(brep.curves)) + suffix
            edits[index] = parts
        if seam and over:
            geom = brep.records[e][1]
            edits[geom[0]] = [repr(tol)] + brep.lines[geom[0]].split()[1:]
            for v in brep.below(e, "Ve"):
                edits[brep.records[v][1][0]] = [repr(tol)]
    out = Part.Shape()
    out.importBrepFromString(brep.text(edits), False)
    face = out.Faces[k]
    u0, u1, _v0, _v1 = face.ParameterRange
    return out, (u1 - u0) - face.Surface.UPeriod()


# --------------------------------------------------------------------------- records

def placement(rng, spread):
    axis = V(rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))
    if axis.Length < 1e-6:
        axis = V(0, 0, 1)
    axis.normalize()
    pos = V(rng.uniform(-spread, spread), rng.uniform(-spread, spread), rng.uniform(-spread, spread))
    return App.Placement(pos, App.Rotation(axis, rng.uniform(0, 360)))


def primitive(rng):
    kind = rng.choice(["box", "cylinder", "cone", "sphere", "torus"])
    if kind == "box":
        a, b, c = rng.uniform(4, 16), rng.uniform(4, 16), rng.uniform(4, 16)
        s, vol, p = Part.makeBox(a, b, c, V(-a / 2, -b / 2, -c / 2)), a * b * c, [a, b, c]
    elif kind == "cylinder":
        r, h = rng.uniform(2, 8), rng.uniform(4, 16)
        s, vol, p = Part.makeCylinder(r, h, V(0, 0, -h / 2)), math.pi * r * r * h, [r, h]
    elif kind == "cone":
        r1, h = rng.uniform(2, 8), rng.uniform(4, 16)
        r2 = 0.0 if rng.random() < 0.2 else rng.uniform(0.5, 0.9 * r1)
        s, vol, p = Part.makeCone(r1, r2, h, V(0, 0, -h / 2)), math.pi * h * (r1 * r1 + r1 * r2 + r2 * r2) / 3, [r1, r2, h]
    elif kind == "sphere":
        r = rng.uniform(3, 9)
        s, vol, p = Part.makeSphere(r), 4.0 / 3.0 * math.pi * r ** 3, [r]
    else:
        big = rng.uniform(4, 9)
        small = rng.uniform(1, 0.6 * big)
        s, vol, p = Part.makeTorus(big, small), 2 * math.pi ** 2 * big * small * small, [big, small]
    pl = placement(rng, 5.0)
    s.Placement = pl.multiply(s.Placement)
    return s, {"kind": kind, "params": p, "volume": vol, "placement": [list(pl.Base), list(pl.Rotation.Q)]}


def measure(base, tool, op):
    t0 = time.perf_counter()
    try:
        r = getattr(base, op)(tool)
        rec = {"valid": bool(r.isValid())}
        if op == "section":
            rec.update(edges=len(r.Edges), length=sum(e.Length for e in r.Edges))
        else:
            rec.update(volume=r.Volume, solids=len(r.Solids))
    except Exception as exc:
        rec = {"error": "%s: %s" % (type(exc).__name__, exc)}
    rec["seconds"] = round(time.perf_counter() - t0, 4)
    return rec


def main():
    out = open(OUT, "w", encoding="utf-8")

    def emit(obj):
        out.write(json.dumps(obj, sort_keys=True) + "\n")
        out.flush()

    bindir = os.path.dirname(sys.executable)
    tkbo = os.path.join(bindir, "TKBO.dll")
    md5 = hashlib.md5(open(tkbo, "rb").read()).hexdigest() if os.path.isfile(tkbo) else "absent"
    emit({"header": True, "freecad": ".".join(App.Version()[:3]), "occt": Part.OCC_VERSION, "exe": sys.executable,
          "tkbo_md5": md5, "seed": SEED, "pairs": PAIRS, "placements": PLACEMENTS})
    rng = random.Random(SEED)
    started = time.time()
    for n in range(PAIRS):
        base, bi = primitive(rng)
        tool, ti = primitive(rng)
        for op in ("cut", "common", "fuse", "section"):
            emit(dict(id="random-%03d-%s" % (n, op), family="random", op=op, base=bi, tool=ti, result=measure(base, tool, op)))
    overs = OVERS + sorted(10 ** rng.uniform(-6, -3) for _ in range(3))
    for kind in ("cyl-half", "cone-half", "bspline"):
        if kind == "cone-half":
            r1, h = rng.uniform(8, 14), rng.uniform(15, 30)
            r2 = rng.uniform(3, r1 - 2)
            clean, radius, params = Part.makeCone(r1, r2, h), r1, [r1, r2, h]
        else:
            r, h = rng.uniform(6, 14), rng.uniform(15, 30)
            clean, radius, params = Part.makeCylinder(r, h), r, [r, h]
            if kind == "bspline":
                clean = clean.toNurbs()
        bases = []
        for m in range(PLACEMENTS):
            a, b, c = rng.uniform(10, 40), rng.uniform(10, 40), rng.uniform(10, 40)
            theta = rng.uniform(0, 2 * math.pi)
            rad = radius + rng.uniform(-4, 4)
            centre = V(rad * math.cos(theta), rad * math.sin(theta), rng.uniform(0, h))
            if rng.random() < 0.35:
                shape = Part.makeCylinder(rng.uniform(3, 10), a, V(0, 0, -a / 2))
                bkind = "cylinder"
            else:
                shape = Part.makeBox(a, b, c, V(-a / 2, -b / 2, -c / 2))
                bkind = "box"
            if rng.random() < 0.5:
                # turned about the tool's axis only: the base's side faces meet the side face along lines u = const,
                # which is how the owner's block met his adapter (README section 2)
                rot, turn = App.Rotation(V(0, 0, 1), rng.uniform(0, 360)), "axis-parallel"
            else:
                rot, turn = App.Rotation(V(rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1) + 1e-9), rng.uniform(0, 360)), "any"
            pl = App.Placement(centre, rot)
            shape.Placement = pl.multiply(shape.Placement)
            bases.append((shape, {"kind": bkind, "turn": turn, "size": [a, b, c],
                                  "placement": [list(pl.Base), list(pl.Rotation.Q)]}))
        refs = [{op: measure(shape, clean, op) for op in ("cut", "common", "fuse", "section")} for shape, _bi in bases]
        mode = "period" if kind == "bspline" else "half"
        for over in overs:
            try:
                tool, width = widened(clean, over, mode, radius)
                ti = {"kind": kind, "params": params, "over": over, "width_over_period": width, "valid": bool(tool.isValid()),
                      "volume": tool.Volume}
            except Exception as exc:
                emit({"id": "wide-%s-%g-build" % (kind, over), "family": "wide", "error": traceback.format_exc()})
                continue
            for m, (shape, bi) in enumerate(bases):
                for op in ("cut", "common", "fuse", "section"):
                    emit(dict(id="wide-%s-%.3g-%d-%s" % (kind, over, m, op), family="wide", op=op, base=bi, tool=ti,
                              base_volume=shape.Volume, tool_volume=tool.Volume, clean_volume=clean.Volume,
                              reference=refs[m][op], result=measure(shape, tool, op)))
    emit({"footer": True, "seconds": round(time.time() - started, 2)})
    out.close()


try:
    main()
except Exception:
    with open(OUT + ".error.txt", "w") as f:
        f.write(traceback.format_exc())
os._exit(0)
