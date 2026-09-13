"""06 -- what the FreeCAD Python layer can and cannot reach.

The question that decides whether the seam can be handled from a script at all:
which OCCT shape-healing classes are exposed?

Measured answer:
  * ShapeUpgrade is exposed as Part.ShapeUpgrade and contains exactly ONE class,
    UnifySameDomain -- the one that MERGES faces.  ShapeUpgrade_ShapeDivideClosed,
    the class that SPLITS a closed face and thereby removes a seam, is absent.
  * ShapeFix IS reachable, as Part.ShapeFix (not as a top-level module).  It can
    add, repair and re-place a seam (Wire.fixSeam, Face.fixMissingSeam) but it
    has nothing that removes one.
  * BRepBuilderAPI, BRepTools, ShapeAnalysis, ShapeBuild, ShapeCustom are not
    importable at all.  Part.BRepOffsetAPI exposes two classes out of the
    module's dozens.

So: from Python you can observe a seam, you can move it (script 03), you can
avoid creating one (script 05), and you can repair a missing one.  You cannot
ask OCCT to split a closed face.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 06_python_reach.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))

import FreeCAD as App
import Part
from FreeCAD import Vector
from seamlib import bop, done, head, say, seam_edges

head("A. the build under test")
say("  FreeCAD.Version()  = %s", App.Version())
say("  Part.OCC_VERSION   = %s", getattr(Part, "OCC_VERSION", "n/a"))
say("  sys.version        = %s", sys.version.replace("\n", " "))

head("B. top-level OCCT modules: none of them import")
for mod in ("ShapeUpgrade", "ShapeFix", "ShapeAnalysis", "ShapeBuild", "ShapeCustom",
            "BRepBuilderAPI", "BRepTools", "BRepAlgoAPI", "BRepFilletAPI", "TopoDS"):
    try:
        __import__(mod)
        verdict = "imported"
    except Exception as exc:
        verdict = "%s: %s" % (type(exc).__name__, exc)
    say("  import %-16s -> %s", mod, verdict)

head("C. what Part re-exports instead")
for name in sorted(n for n in dir(Part) if n[0].isupper() and not n.startswith("_")):
    obj = getattr(Part, name)
    if type(obj).__name__ == "module":
        say("  Part.%-18s (module) -> %s", name,
            [n for n in dir(obj) if not n.startswith("_")])

head("D. the one class that would remove a seam is not there")
say("  Part.ShapeUpgrade contents: %s",
    [n for n in dir(Part.ShapeUpgrade) if not n.startswith("_")])
for wanted in ("ShapeDivideClosed", "ShapeDivide", "ShapeDivideContinuity",
               "ShapeDivideArea", "ShapeConvertToBezier", "RemoveLocations",
               "UnifySameDomain"):
    say("  Part.ShapeUpgrade.%-22s present = %s", wanted,
        hasattr(Part.ShapeUpgrade, wanted))
say("")
say("  ShapeUpgrade_ShapeDivideClosed is the OCCT class that cuts a closed face")
say("  in two and so eliminates the seam. It is not bound. UnifySameDomain, the")
say("  class bound instead, does the exact opposite (proved in script 05).")

head("E. Part.ShapeFix: reachable, and full of seam machinery -- none of it removes one")
say("  Part.ShapeFix classes: %s",
    [n for n in dir(Part.ShapeFix) if not n.startswith("_") and n[0].isupper()])
for cls_name in ("Wire", "Face"):
    cls = getattr(Part.ShapeFix, cls_name)
    seamish = [m for m in dir(cls) if "eam" in m]
    say("  Part.ShapeFix.%-6s methods mentioning 'seam': %s", cls_name, seamish)
say("  -> fixSeam / fixMissingSeam ADD or repair a seam on a face that is missing")
say("     one. There is no 'removeSeam'.")

head("F. what UnifySameDomain actually does to a seamless cylinder")
srf = [f for f in Part.makeCylinder(5.0, 10.0).Faces
       if f.Surface.TypeId == "Part::GeomCylinder"][0].Surface
import math
halves = [srf.toShape(0.0, math.pi, 0.0, 10.0).Faces[0],
          srf.toShape(math.pi, 2 * math.pi, 0.0, 10.0).Faces[0]]
caps = [Part.Face(Part.Wire(Part.makeCircle(5.0, Vector(0, 0, z), Vector(0, 0, 1))))
        for z in (0.0, 10.0)]
split = Part.Solid(Part.Shell(halves + caps))
say("  before: faces = %d seams = %d", len(split.Faces), len(seam_edges(split)))
for linear, angular in ((1e-7, 1e-7), (1e-3, 1e-3)):
    usd = Part.ShapeUpgrade.UnifySameDomain(split)
    usd.setLinearTolerance(linear)
    usd.setAngularTolerance(angular)
    usd.build()
    res = usd.shape()
    say("  UnifySameDomain(linear = %g, angular = %g) -> faces = %d seams = %d",
        linear, angular, len(res.Faces), len(seam_edges(res)))
say("  there is no option that makes it leave the two halves alone.")

head("G. can ShapeFix be used to strip the seam pcurve?")
cyl = Part.makeCylinder(5.0, 10.0)
lat = [f for f in cyl.Faces if f.Surface.TypeId == "Part::GeomCylinder"][0]
seam = seam_edges(cyl)[0]["edge"]
say("  seam edge before: adjacent faces = %d", len(cyl.ancestorsOfType(seam, Part.Face)))
try:
    fx = Part.ShapeFix.Edge()
    ok = fx.fixRemovePCurve(seam, lat)
    say("  Part.ShapeFix.Edge().fixRemovePCurve(seam, face) -> %s", ok)
    say("  the edited copy: seam edge adjacent faces = %d",
        len(cyl.ancestorsOfType(seam, Part.Face)))
    say("  solid after the call: faces = %d seams = %d valid = %s check = %s",
        len(cyl.Faces), len(seam_edges(cyl)), cyl.isValid(), bop(cyl))
    say("  -> the call returns False and changes nothing: the seam pcurve of a")
    say("     periodic face is not removable this way either.")
except Exception as exc:
    say("  fixRemovePCurve raised %s: %s", type(exc).__name__, exc)

done("06_python_reach")
