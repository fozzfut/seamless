# Prints whether the OCCT inside this FreeCAD rounds an edge that ends on a cylinder seam.
#
#   "<FreeCAD>/bin/FreeCADCmd.exe" verify-seam-fillet.py
#
# The fixture is the minimal pair from repro/python/03_minimal_pair.py, built with Part alone:
# a 25 x 25.7184 x 10 box, a pocket of R 6.647656 tilted 45 deg about Y, and the profile circle
# turned so the pocket's seam lands on the end vertex of the corner edge. Measured 13 September
# 2026 on FreeCAD 1.1.1: stock TKFillet.dll (md5 6d9915af...) removed -374.970181 mm3 and failed
# the BOP check; the patched one (md5 4e89e519..., patches/0002) removed 1.368075 against an
# analytic 1.367173 and was clean. The control half, seam 11.514078 mm away, is correct on both.
#
# The verdict goes to stdout AND to verify-seam-fillet.txt next to this script, because
# FreeCADCmd does not always pass a script's stdout through.
import io
import math
import os
import sys

import FreeCAD as App
import Part

BOX = (25.0, 25.7184, 10.0)
AXIS_POINT = App.Vector(25.0, 12.7, 10.0)
POCKET_RADIUS, STANDOFF, DEPTH, FILLET = 6.647656, 6.0, 13.0, 1.0

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = io.open(os.path.join(HERE, "verify-seam-fillet.txt"), "w", encoding="utf-8")


def say(text):
    REPORT.write(text + "\n")
    REPORT.flush()
    sys.stdout.write(text + "\n")


def fixture(angle_xu):
    normal = App.Vector(1, 0, 1)
    normal.normalize()
    circle = Part.Circle(App.Vector(0, 0, 0), App.Vector(0, 0, 1), POCKET_RADIUS)
    if angle_xu:
        circle.rotate(App.Placement(App.Vector(0, 0, 0), App.Rotation(App.Vector(0, 0, 1), angle_xu)))
    face = Part.Face(Part.Wire([circle.toShape()]))
    face.Placement = App.Placement(AXIS_POINT + normal * STANDOFF, App.Rotation(App.Vector(0, 1, 0), 45))
    return Part.makeBox(*BOX).cut(face.extrude(normal * -DEPTH))


def corner_edge(shape):
    for edge in shape.Edges:
        pts = [v.Point for v in edge.Vertexes]
        if (edge.Curve.TypeId == "Part::GeomLine" and len(pts) == 2
                and all(abs(p.x - BOX[0]) < 1e-6 and abs(p.z - BOX[2]) < 1e-6 for p in pts)
                and max(p.y for p in pts) > 15.0):
            return edge
    return None


def fillet(angle_xu):
    shape = fixture(angle_xu)
    edge = corner_edge(shape)
    ideal = (1.0 - math.pi / 4.0) * FILLET * FILLET * edge.Length
    result = shape.makeFillet(FILLET, [edge])
    try:
        clean = result.check(True) is None
    except Exception:
        clean = False
    removed = shape.Volume - result.Volume
    ok = bool(result.isValid()) and clean and abs(removed - ideal) <= 0.05 * ideal
    return ok, "valid=%s bop=%s removed=%.6f ideal=%.6f" % (
        result.isValid(), "clean" if clean else "DIRTY", removed, ideal)


try:
    control_ok, control = fillet(0.0)
    seam_ok, on_seam = fillet(90.0)
    say("OCC %s" % Part.OCC_VERSION)
    say("control (seam far away): %s  %s" % ("correct" if control_ok else "WRONG", control))
    say("edge ending on the seam: %s  %s" % ("correct" if seam_ok else "WRONG", on_seam))
    if not control_ok:
        say("SEAM-FILLET: UNKNOWN (the control fillet is wrong, so this probe proves nothing)")
    else:
        say("SEAM-FILLET: %s" % ("FIXED" if seam_ok else "STOCK"))
except Exception as exc:
    say("SEAM-FILLET: ERROR %s" % exc)
finally:
    REPORT.close()
