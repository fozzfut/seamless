"""14 -- read back, in FreeCAD, what the two kernels produced for Edge9.

The Edge9 measurement itself runs outside FreeCAD (repro/cpp/edge9_fillet.cpp), which is
what makes it trustworthy -- no PartDesign, no healing, no TopoShape wrapper. But the owner
does not use bare OCCT, he uses FreeCAD, so the result has to be shown in FreeCAD's own
terms as well: Shape.isValid() and Shape.check(True), the two checks every earlier document
in this repository quotes.

This script imports the BREP files the C++ program wrote and reports them. It opens no
document and touches no file of the owner.

    "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 14_verify_edge9_result.py

Environment:
    SEAMLESS_OUT  directory holding body_tip.brep, fillet_r1_stock.brep,
                  fillet_r1_patched.brep   (default: scratchpad/edge9)

Note that FreeCAD here runs on ITS OWN OCCT DLLs, not on the patched ones: the shapes were
already built, and reading a BREP does not re-run the fillet. So a clean verdict on
fillet_r1_patched.brep is the stock kernel agreeing that the patched kernel's solid is sound.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))

import Part
from seamlib import bop, done, head, say

DEFAULT_OUT = ("C:/path/to/temp/claude/"
               "c--Program-Files-FreeCAD-1-1/90e2ee8a-0198-4b2f-ae54-0503653173cc/"
               "scratchpad/edge9")
OUT = os.environ.get("SEAMLESS_OUT", DEFAULT_OUT)

FILES = [
    ("base (as exported)", "body_tip.brep"),
    ("r = 1.0, STOCK kernel", "fillet_r1_stock.brep"),
    ("r = 1.0, PATCHED kernel", "fillet_r1_patched.brep"),
]

BASE_VOLUME = 5456.580740
IDEAL_R1 = 5455.213593   # base minus the analytic (1 - pi/4) * r^2 * L

head("what the two kernels produced, checked by FreeCAD")
say("  base volume  = %.6f mm3", BASE_VOLUME)
say("  ideal at r=1 = %.6f mm3  (analytic removal 1.367147)", IDEAL_R1)
say("")

for title, name in FILES:
    path = os.path.join(OUT, name)
    if not os.path.isfile(path):
        say("  %-26s MISSING: %s", title, path)
        continue
    sh = Part.Shape()
    sh.importBrep(path)
    say("  %-26s faces = %-3d edges = %-3d solids = %-2d isValid = %-5s volume = %14.6f",
        title, len(sh.Faces), len(sh.Edges), len(sh.Solids), sh.isValid(), sh.Volume)
    say("  %-26s delta vs base = %+.6f   distance from ideal = %+.6f   check(True) = %s",
        "", sh.Volume - BASE_VOLUME, sh.Volume - IDEAL_R1, bop(sh))

done("14_verify_edge9_result")
