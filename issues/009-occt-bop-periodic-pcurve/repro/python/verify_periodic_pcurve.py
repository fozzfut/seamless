"""Defect 009 inside FreeCAD: a cylinder whose side-face pcurve overshoots its seam by 2e-5 rad, cut by a box.

Run: "<FreeCAD>/bin/FreeCADCmd.exe" -u <copy of user.cfg> -s <copy of system.cfg> verify_periodic_pcurve.py
Reads fixtures/periodic_overshoot_cylinder.brep (written by repro/cpp/periodic_pcurve.cpp, synthetic geometry),
prints the numbers and writes them to verify_periodic_pcurve.txt next to this script; the last line is
PERIODIC-PCURVE: FIXED | BROKEN. The exact answer is computed on a clean cylinder in the same run.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "..", "..", "fixtures", "periodic_overshoot_cylinder.brep")
REPORT = os.path.join(HERE, "verify_periodic_pcurve.txt")
lines = []


def say(s):
    lines.append(str(s))
    print(s)


try:
    import FreeCAD as App
    import Part

    say("FreeCAD %s, OCCT %s, %s" % (".".join(App.Version()[:3]), Part.OCC_VERSION, sys.executable))
    tool = Part.Shape()
    tool.read(FIXTURE)
    side = [f for f in tool.Faces if isinstance(f.Surface, Part.Cylinder)][0]
    u0, u1, _v0, _v1 = side.ParameterRange
    say("tool valid %s volume %.6f; side face u in [%.9f, %.9f], wider than 2pi by %.3g"
        % (tool.isValid(), tool.Volume, u0, u1, (u1 - u0) - 2 * math.pi))
    box = Part.makeBox(60, 38, 20, App.Vector(-30, -30, -5))
    exact = box.common(Part.makeCylinder(15, 10)).Volume
    cut, common, fuse = box.cut(tool), box.common(tool), box.fuse(tool)
    say("cut %.6f (%d solids)  common %.6f (%d solids)  fuse %.6f  exact common %.6f"
        % (cut.Volume, len(cut.Solids), common.Volume, len(common.Solids), fuse.Volume, exact))
    e1 = abs(cut.Volume + common.Volume - box.Volume)
    e2 = abs(box.Volume + tool.Volume - common.Volume - fuse.Volume)
    e3 = abs(common.Volume - exact)
    say("|cut+common-box| %.6f  |box+tool-common-fuse| %.6f  |common-exact| %.6f" % (e1, e2, e3))
    say("PERIODIC-PCURVE: %s" % ("FIXED" if max(e1, e2, e3) < 1.0 else "BROKEN"))
except Exception as exc:  # noqa - the verdict must always be written
    say("PERIODIC-PCURVE: ERROR %s" % exc)
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
