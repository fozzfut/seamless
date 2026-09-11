"""04 -- isValid() lies; only check(True) tells the truth.

Part.Shape.isValid() asks OCCT's cheap structural checker (BRepCheck_Analyzer).
Part.Shape.check(True) runs the Boolean-Operation checker (BOPAlgo_ArgumentAnalyzer),
which is what every later boolean, section and export actually depends on.

Near a seam the two disagree, in the dangerous direction: isValid() says True on
shapes whose faces self-intersect and whose pcurves do not lie on their surfaces.
A pipeline that trusts isValid() ships a broken body.

Two independent demonstrations here:
  A/B  the plain pocket at the angles where the fillet is "valid" but wrong;
  C/D  the pocket with a pre-fillet torus, where the BASE shape itself -- before
       any further operation -- is isValid() True and BOP-dirty.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 04_isvalid_vs_bop.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import FreeCAD as App
import Part
from seamlib import (bop, build_fixture, done, fillet_removed, fmtv, head, say,
                     seam_edges, solid_of, target_edge)

doc = App.newDocument("P04")

head("A. a fillet result that isValid() calls good and BOP calls broken")
say("  %-9s %-7s %-13s %-13s %-11s %s", "AngleXU", "valid", "volume", "removed",
    "analytic", "check(True)")
for ang in (0.0, 90.0, 93.0, 95.0):
    body, pocket, tip, sk = build_fixture(doc, "A%d" % int(ang), ang, prefillet=False)
    sh = solid_of(tip)
    idx, edge = target_edge(sh)
    res = sh.makeFillet(1.0, [edge])
    say("  %7.1f   %-7s %13.4f %+13.4f %+11.4f %s", ang, res.isValid(), res.Volume,
        sh.Volume - res.Volume, fillet_removed(1.0, edge.Length), bop(res))
say("")
say("  AngleXU = 93 and 95: isValid() = True, yet check(True) reports")
say("  self-intersections, and the volume removed is twice the analytic amount.")
say("  A caller that only asks isValid() cannot tell these from the good ones.")

head("B. what each checker is actually asked")
body, pocket, tip, sk = build_fixture(doc, "B93", 93.0, prefillet=False)
sh = solid_of(tip)
idx, edge = target_edge(sh)
res = sh.makeFillet(1.0, [edge])
say("  shape after makeFillet(1.0) at AngleXU = 93:")
say("    isValid()                     = %s", res.isValid())
say("    Shells[0].isClosed()          = %s", res.Shells[0].isClosed() if res.Shells else "n/a")
say("    faces = %d  edges = %d  vertexes = %d  solids = %d",
    len(res.Faces), len(res.Edges), len(res.Vertexes), len(res.Solids))
bad = [i + 1 for i, f in enumerate(res.Faces) if not f.isValid()]
say("    faces failing their own isValid(): %s", bad or "none")
try:
    res.check(True)
    say("    check(True)                   = clean")
except Exception as exc:
    for line in str(exc).splitlines()[:6]:
        say("    check(True) -> %s", line)
    say("    ... (%d lines in total)", len(str(exc).splitlines()))

head("C. the base shape itself: pre-fillet the pocket rim, then look")
say("  a PartDesign fillet on the pocket-bottom rim creates a toroidal face.")
say("  The toroid is a doubly periodic surface; where the pocket seam crosses it,")
say("  the torus is delivered SPLIT and the result is BOP-dirty from birth.")
say("")
say("  %-9s %-9s %-13s %-7s %-9s %-9s %s", "AngleXU", "faces", "volume", "valid",
    "seams", "toroids", "check(True)")
for ang in (0.0, 45.0, 88.0, 90.0, 92.0, 135.0, 180.0, 270.0):
    body, pocket, tip, sk = build_fixture(doc, "C%d" % int(ang), ang, prefillet=True)
    sh = solid_of(tip)
    tor = [i + 1 for i, f in enumerate(sh.Faces) if f.Surface.TypeId == "Part::GeomToroid"]
    say("  %7.1f   %-9d %13.4f %-7s %-9d %-9s %s", ang, len(sh.Faces), sh.Volume,
        sh.isValid(), len(seam_edges(sh)), tor, bop(sh))
say("")
say("  every row has isValid() = True. The rows where the torus is delivered as")
say("  three faces instead of two are the rows that fail check(True).")

head("D. the areas show what happened to the torus")
for ang in (0.0, 90.0):
    body, pocket, tip, sk = build_fixture(doc, "D%d" % int(ang), ang, prefillet=True)
    sh = solid_of(tip)
    say("  AngleXU = %5.1f  isValid() = %s  check(True) = %s", ang, sh.isValid(), bop(sh))
    for i, f in enumerate(sh.Faces):
        if f.Surface.TypeId == "Part::GeomToroid":
            say("      Face%-3d toroid area = %.6f", i + 1, f.Area)

App.closeDocument(doc.Name)
done("04_isvalid_vs_bop")
