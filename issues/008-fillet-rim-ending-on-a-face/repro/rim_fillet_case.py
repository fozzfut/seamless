# One fillet case on the owner's cube: the whole floor rim of the round cut, one radius.
#
#   RIM_R=0.5 [RIM_ANGLE=90] [RIM_SHALLOWER=1.0] "<FreeCAD>/bin/FreeCADCmd.exe" rim_fillet_case.py
#
# RIM_ANGLE    turns the pocket circle's parameter origin (AngleXU, degrees); moves the seam, no material
# RIM_SHALLOWER makes the pocket that many mm shallower, so the floor rim becomes a whole circle
#
# Run each case in its own process with a deadline (run_rim_cases.sh does): a fillet that fails in
# the kernel can also fail to return. Measured 13 September 2026 on FreeCAD 1.1.1: every case here
# returned in under 0.1 s, on the stock and on the patched TKFillet.dll alike.
#
# The result line goes to stdout and is appended to rim_fillet_cases.txt in the system temp directory,
# because FreeCADCmd does not always pass a script's stdout through.
import io
import math
import os
import shutil
import sys
import tempfile
import time

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
PART = os.path.join(HERE, "..", "..", "001-occt-fillet-at-seam", "fixtures", "cube_with_round_cut.FCStd")
RIM_RADIUS = 4.337755
REPORT = os.path.join(tempfile.gettempdir(), "rim_fillet_cases.txt")

radius = float(os.environ.get("RIM_R", "1.0"))
angle = os.environ.get("RIM_ANGLE")
shallower = float(os.environ.get("RIM_SHALLOWER", "0"))


def say(text):
    with io.open(REPORT, "a", encoding="utf-8") as out:
        out.write(text + "\n")
    sys.stdout.write(text + "\n")


work = os.path.join(tempfile.gettempdir(), "rim_case_%d.FCStd" % os.getpid())
shutil.copyfile(PART, work)
doc = App.openDocument(work)
try:
    body = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"][0]
    before = body.Shape.copy()
    if angle is not None:
        sketch = doc.getObject("Sketch001")
        geometry = sketch.Geometry
        geometry[0].AngleXU = math.radians(float(angle))
        sketch.Geometry = geometry
    pocket = doc.getObject("Pocket")
    length0 = pocket.Length.Value
    if shallower:
        pocket.Length = length0 - shallower
    doc.recompute()
    shape = body.Shape
    moved = before.cut(shape).Volume + shape.cut(before).Volume
    rim = [e for e in shape.Edges
           if e.Curve.TypeId == "Part::GeomCircle" and abs(e.Curve.Radius - RIM_RADIUS) < 1e-4]
    seam_points = [v.Point for e in shape.Edges if len(shape.ancestorsOfType(e, Part.Face)) == 1
                   for v in e.Vertexes]
    on_seam = sum(1 for e in rim for v in e.Vertexes
                  if any((v.Point - p).Length < 1e-6 for p in seam_points))
    started = time.perf_counter()
    try:
        result = shape.makeFillet(radius, rim)
        try:
            bop = "clean" if result.check(True) is None else "returned"
        except Exception as exc:
            bop = "DIRTY " + " ".join(str(exc).split())[:50]
        verdict = "valid=%s bop=%s dV=%.6f faces %d->%d" % (
            result.isValid(), bop, shape.Volume - result.Volume, len(shape.Faces), len(result.Faces))
    except Exception as exc:
        verdict = "RAISED " + " ".join(str(exc).split())[:60]
    say("AngleXU=%s pocket %.3f->%.3f r=%.2f | material moved %.9f | rim edges %d closed=%s, "
        "rim vertices on a seam %d, lowest z %.4f | %s | %.3f s"
        % (angle if angle is not None else "as-is", length0, pocket.Length.Value, radius, moved,
           len(rim), [e.isClosed() for e in rim], on_seam,
           min(e.BoundBox.ZMin for e in rim) if rim else float("nan"), verdict,
           time.perf_counter() - started))
finally:
    App.closeDocument(doc.Name)
    os.remove(work)
