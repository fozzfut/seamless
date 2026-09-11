"""Shared helpers for the seam reproduction scripts.

Target: FreeCAD 1.1.1 (OCCT 7.8.1), run headless:

    "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" <script.py>

Nothing here opens a window, asks a question or waits.  Every script that
imports this module prints its numbers and exits.
"""

import math
import os
import sys
import time

import FreeCAD as App
import Part
from FreeCAD import Placement, Rotation, Vector

# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------

_T0 = time.perf_counter()


def say(fmt, *args):
    """Print one measurement line.

    Measurements go to STDERR on purpose.  FreeCAD's C++ side writes its banner
    and a carriage-return progress bar ("Recompute... (37 %)") to STDOUT and
    does not flush it until exit, which shreds anything Python prints there.
    stderr is untouched and unbuffered, so a run that is killed by `timeout`
    still shows every line it had reached.

        FreeCADCmd.exe 03_minimal_pair.py 2>&1 1>/dev/null   # measurements only
    """
    sys.stderr.write((fmt % args if args else fmt) + chr(10))
    sys.stderr.flush()


def head(title):
    say("")
    say("=" * 78)
    say(title)
    say("=" * 78)


def done(script):
    say("")
    say("[%s] finished in %.3f s", script, time.perf_counter() - _T0)


def fmtv(v):
    return "(%.4f, %.4f, %.4f)" % (v.x, v.y, v.z)


# --------------------------------------------------------------------------
# topology probes
# --------------------------------------------------------------------------

def seam_edges(shape):
    """Return the seam edges of `shape`.

    In a closed solid every ordinary edge is shared by exactly two faces.
    An edge with exactly ONE adjacent face is a seam: it is walked twice by
    the wire of that single face.  This is the cheapest reliable detector
    available from Python.
    """
    out = []
    for i, edge in enumerate(shape.Edges):
        anc = shape.ancestorsOfType(edge, Part.Face)
        if len(anc) == 1:
            face = anc[0]
            face_idx = [k + 1 for k, f in enumerate(shape.Faces) if f.isSame(face)][0]
            out.append(dict(edge_idx=i + 1, edge=edge, face=face,
                            face_idx=face_idx, surf=face.Surface))
    return out


def bop(shape):
    """Part.Shape.check(True) -- the BOP check -- as a one-line verdict.

    Returns "clean" or "RAISED <kinds>".  isValid() is NOT a substitute:
    script 04 shows shapes with isValid() == True that fail this check.
    """
    try:
        res = shape.check(True)
        return "clean" if res is None else ("returned %r" % (res,))
    except Exception as exc:
        kinds = {}
        for tok in str(exc).replace("\n", ";").split(";"):
            tok = tok.strip()
            if tok and not tok.lower().startswith("bop check found"):
                kinds[tok] = kinds.get(tok, 0) + 1
        return "RAISED " + ", ".join("%s x%d" % (k, v) for k, v in sorted(kinds.items()))


def u0_anchor(cyl_surface):
    """The point the seam of a cylindrical face is pinned to.

    The seam is the u = 0 iso-line of the surface frame, so it passes through
        Center + R * (Rotation applied to (1, 0, 0)).
    """
    return cyl_surface.Center + cyl_surface.Rotation.multVec(Vector(1, 0, 0)) * cyl_surface.Radius


# --------------------------------------------------------------------------
# the minimal fixture: a box with a tilted cylindrical pocket
# --------------------------------------------------------------------------
# Deliberately shaped after the user's real part: the pocket axis is tilted
# 45 deg about Y and crosses the top-front corner line of the box, so the
# pocket's cylindrical face meets the corner edge that we then try to fillet.

BX, BY, BZ = 25.0, 25.7184, 10.0        # the box
AXPT = Vector(BX, 12.7, BZ)             # where the pocket axis crosses the corner line
NRM = Vector(1, 0, 1)
NRM.normalize()
RAD = 6.647656                          # pocket radius
STANDOFF = 6.0                          # sketch plane offset along the axis
POCKET_LEN = 13.0


def build_fixture(doc, tag, angle_xu, prefillet=False, pocket_len=POCKET_LEN, rad=RAD):
    """Box + tilted cylindrical pocket.  `angle_xu` rotates ONLY the profile
    circle inside its own sketch plane -- the solid is unchanged, the seam moves.

    Returns (body, pocket, tip_feature, sketch).
    """
    body = doc.addObject("PartDesign::Body", "B" + tag)

    sk = doc.addObject("Sketcher::SketchObject", "S" + tag)
    body.addObject(sk)
    pts = [(0, 0), (BX, 0), (BX, BY), (0, BY)]
    for i in range(4):
        sk.addGeometry(Part.LineSegment(Vector(pts[i][0], pts[i][1], 0),
                                        Vector(pts[(i + 1) % 4][0], pts[(i + 1) % 4][1], 0)), False)
    doc.recompute()

    pad = doc.addObject("PartDesign::Pad", "Pad" + tag)
    body.addObject(pad)
    pad.Profile = sk
    pad.Length = BZ
    doc.recompute()

    sk2 = doc.addObject("Sketcher::SketchObject", "SC" + tag)
    body.addObject(sk2)
    sk2.AttachmentSupport = None
    sk2.Placement = Placement(AXPT + NRM * STANDOFF, Rotation(Vector(0, 1, 0), 45))
    circ = Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), rad)
    if angle_xu:
        # rotating a full circle about its own axis changes NOTHING about the
        # set of points it covers -- only where its parameter u = 0 sits.
        circ.rotate(Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), angle_xu)))
    sk2.addGeometry(circ, False)
    doc.recompute()

    pocket = doc.addObject("PartDesign::Pocket", "Pk" + tag)
    body.addObject(pocket)
    pocket.Profile = sk2
    pocket.Length = pocket_len
    doc.recompute()

    tip = pocket
    if prefillet:
        # fillet the pocket-bottom rim first: cylinder-to-plane edges whose
        # plane normal is the pocket axis.  This produces the toroidal face
        # that script 04 uses.
        sh = pocket.Shape
        names = []
        for i, edge in enumerate(sh.Edges):
            faces = sh.ancestorsOfType(edge, Part.Face)
            if len(faces) != 2:
                continue
            if sorted(f.Surface.TypeId for f in faces) != ["Part::GeomCylinder", "Part::GeomPlane"]:
                continue
            plane = [f for f in faces if f.Surface.TypeId == "Part::GeomPlane"][0]
            if abs(plane.Surface.Axis.dot(NRM)) > 0.99:
                names.append("Edge%d" % (i + 1))
        for n, name in enumerate(names):
            fl = doc.addObject("PartDesign::Fillet", "PreF%s%d" % (tag, n))
            body.addObject(fl)
            fl.Base = (tip, [name])
            fl.Radius = 1.0
            doc.recompute()
            tip = fl
    return body, pocket, tip, sk2


def solid_of(feature):
    sh = feature.Shape
    return sh.Solids[0] if sh.ShapeType == "Compound" else sh


def target_edge(shape):
    """The corner edge we try to fillet: the straight edge on x = BX, z = BZ
    that runs away from the pocket (its far end has y > 15)."""
    best = None
    for i, edge in enumerate(shape.Edges):
        if edge.Curve.TypeId != "Part::GeomLine":
            continue
        vs = [v.Point for v in edge.Vertexes]
        if len(vs) != 2:
            continue
        if not all(abs(v.x - BX) < 1e-6 and abs(v.z - BZ) < 1e-6 for v in vs):
            continue
        if max(v.y for v in vs) > 15.0:
            best = (i + 1, edge)
    return best


# analytic volume removed by a fillet / chamfer of radius r on a straight edge
# of length L between two perpendicular planes
def fillet_removed(r, length):
    return (1.0 - math.pi / 4.0) * r * r * length


def chamfer_removed(r, length):
    return 0.5 * r * r * length
