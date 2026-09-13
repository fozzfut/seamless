# The workaround for issue 008, measured: build the fillet of a cylinder/floor rim as a ring instead of
# asking the kernel for it.
#
#   RIM_R=0.5 [RIM_ROUTE=extend] [RIM_SHALLOWER=1.0] "<FreeCAD>/bin/FreeCADCmd.exe" ring_fillet_case.py
#
# ring route (default)
#   The concave fillet between a cylindrical wall of radius R and a floor square to its axis is a
#   torus: the section "square r x r minus a quarter disc" swept 360 degrees about the axis. The ring is
#   cut to the shape the pocket was cut from (Pocket.BaseFeature) and fused to the part, so it stops
#   where the part stops - the fillet runs up to the face the rim ends on.
# RIM_ROUTE=extend
#   The general alternative: glue a slab under the part, cut the pocket again so the rim is whole,
#   fillet with the kernel, cut back to the base shape. Compared with the ring by mutual cut.
# RIM_SHALLOWER
#   Control: makes the pocket that many mm shallower, so the rim is whole and the kernel fillets it;
#   the kernel's fillet is compared with the ring by mutual cut.
#
# Run each case in its own process with a deadline (run_rim_cases.sh does). The result line goes to
# stdout and is appended to rim_fillet_cases.txt in the system temp directory.
import io
import math
import os
import shutil
import sys
import tempfile
import time

import FreeCAD as App
import Part

V = App.Vector
HERE = os.path.dirname(os.path.abspath(__file__))
PART = os.path.join(HERE, "..", "..", "001-occt-fillet-at-seam", "fixtures", "cube_with_round_cut.FCStd")
RIM_RADIUS = 4.337755
REPORT = os.path.join(tempfile.gettempdir(), "rim_fillet_cases.txt")

radius = float(os.environ.get("RIM_R", "0.5"))
route = os.environ.get("RIM_ROUTE", "ring")
shallower = float(os.environ.get("RIM_SHALLOWER", "0"))


def say(text):
    with io.open(REPORT, "a", encoding="utf-8") as out:
        out.write(text + "\n")
    sys.stdout.write(text + "\n")


def bop(shape):
    try:
        return "clean" if shape.check(True) is None else "returned"
    except Exception as exc:
        return "DIRTY " + " ".join(str(exc).split())[:40]


def ring_fillet(part, base, rim, r):
    """part with the ring fillet on the cylinder/floor rim, cut to base."""
    circle = rim[0].Curve
    center = V(circle.Center)
    up = V(circle.Axis).normalize()
    floor = [f for e in rim for f in part.ancestorsOfType(e, Part.Face) if f.Surface.TypeId == "Part::GeomPlane"][0]
    if part.isInside(floor.CenterOfMass + up * 0.01, 1e-7, True):
        up = up * -1  # up points from the floor into the empty pocket
    u = V(1, 0, 0) if abs(up.x) < 0.9 else V(0, 1, 0)
    u = (u - up * u.dot(up)).normalize()
    corner = center + u * circle.Radius
    on_floor = center + u * (circle.Radius - r)
    on_wall = corner + up * r
    arc_center = on_floor + up * r
    section = Part.Face(Part.Wire([
        Part.LineSegment(corner, on_floor).toShape(),
        Part.Arc(on_floor, arc_center + (u - up).normalize() * r, on_wall).toShape(),
        Part.LineSegment(on_wall, corner).toShape()]))
    ring = section.revolve(center, up, 360)
    return part.fuse(ring.common(base)).removeSplitter()


def end_face_report(part, rim, shape):
    """Faces of shape lying in the plane the rim ends on: count, holes in them."""
    floor_and_wall = [f for e in rim for f in part.ancestorsOfType(e, Part.Face)]
    ends = [v for e in rim for v in e.Vertexes]
    end = None
    for v in ends:
        for f in part.ancestorsOfType(v, Part.Face):
            if f.Surface.TypeId == "Part::GeomPlane" and not any(f.isSame(g) for g in floor_and_wall):
                end = f
                break
        if end:
            break
    if end is None:
        return "rim ends on no plane", None
    normal = V(end.Surface.Axis).normalize()
    origin = V(end.Surface.Position)
    coplanar = [f for f in shape.Faces if f.Surface.TypeId == "Part::GeomPlane"
                and abs(abs(V(f.Surface.Axis).normalize().dot(normal)) - 1) < 1e-9
                and all(abs((v.Point - origin).dot(normal)) < 1e-7 for v in f.Vertexes)]
    holes = sum(len(f.Wires) - 1 for f in coplanar)
    angles = []
    for e in rim:
        for v in e.Vertexes:
            if abs((v.Point - origin).dot(normal)) < 1e-7:
                tangent = e.tangentAt(e.Curve.parameter(v.Point))
                angles.append(math.degrees(math.asin(min(1.0, abs(tangent.normalize().dot(normal))))))
    meets = ("rim meets it at %s deg, " % "/".join("%.4f" % a for a in angles)) if angles else ""
    return "end plane: %s%d face(s), %d hole(s)" % (meets, len(coplanar), holes), (origin, normal)


work = os.path.join(tempfile.gettempdir(), "ring_case_%d.FCStd" % os.getpid())
shutil.copyfile(PART, work)
doc = App.openDocument(work)
try:
    body = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"][0]
    pocket = doc.getObject("Pocket")
    length0 = pocket.Length.Value
    if shallower:
        pocket.Length = length0 - shallower
        doc.recompute()
    part = body.Shape.copy()
    base = pocket.BaseFeature.Shape.copy()
    rim = [e for e in part.Edges
           if e.Curve.TypeId == "Part::GeomCircle" and abs(e.Curve.Radius - RIM_RADIUS) < 1e-4]
    head = "ring route=%s pocket %.3f->%.3f r=%.2f | rim edges %d closed=%s" % (
        route, length0, pocket.Length.Value, radius, len(rim), [e.isClosed() for e in rim])
    started = time.perf_counter()
    ring = ring_fillet(part, base, rim, radius)
    elapsed = time.perf_counter() - started
    before, plane = end_face_report(part, rim, part)
    after, _ = end_face_report(part, rim, ring)
    tori = [f for f in ring.Faces if f.Surface.TypeId == "Part::GeomToroid"]
    gap = float("nan")
    if plane and tori:
        big = Part.makeCircle(1e4, plane[0], plane[1])
        gap = tori[0].distToShape(Part.Face(Part.Wire(big)))[0]
    line = ("%s | RING bop=%s solids %d removed from part %.9f added %.6f | torus faces %d, torus to end plane %.6f | "
            "before: %s, after: %s | %.3f s" % (
                head, bop(ring), len(ring.Solids), part.cut(ring).Volume, ring.cut(part).Volume, len(tori), gap,
                before, after, elapsed))
    if shallower:
        try:
            kernel = part.makeFillet(radius, rim)
            line += " | kernel fillet bop=%s, kernel vs ring mutual cut %.9f" % (
                bop(kernel), kernel.cut(ring).Volume + ring.cut(kernel).Volume)
        except Exception as exc:
            line += " | kernel fillet RAISED " + " ".join(str(exc).split())[:40]
    if route == "extend":
        box = base.BoundBox  # a planar base: its box is tight; a part with curved faces has a loose one
        slab = Part.makeBox(box.XLength + 20, box.YLength + 20, 3.0, V(box.XMin - 10, box.YMin - 10, box.ZMin - 3.0))
        extended = part.fuse(slab).removeSplitter().cut(pocket.AddSubShape).removeSplitter()
        whole = [e for e in extended.Edges if e.Curve.TypeId == "Part::GeomCircle"
                 and abs(e.Curve.Radius - RIM_RADIUS) < 1e-4 and (V(e.Curve.Center) - V(rim[0].Curve.Center)).Length < 1e-4]
        try:
            trimmed = extended.makeFillet(radius, whole).common(base).removeSplitter()
            line += " | EXTEND extended bop=%s, result bop=%s removed %.9f, extend vs ring mutual cut %.9f" % (
                bop(extended), bop(trimmed), part.cut(trimmed).Volume,
                trimmed.cut(ring).Volume + ring.cut(trimmed).Volume)
        except Exception as exc:
            line += " | EXTEND extended bop=%s, fillet RAISED %s" % (bop(extended), " ".join(str(exc).split())[:40])
    say(line)
finally:
    App.closeDocument(doc.Name)
    os.remove(work)
