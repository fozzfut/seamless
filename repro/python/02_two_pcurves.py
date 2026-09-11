"""02 -- one edge, two parametric curves.

The seam edge is the only edge in a closed solid that carries TWO pcurves on
the SAME face: one at u = 0 and one at u = 2*pi.  An ordinary edge belongs to
two different faces and carries one pcurve on each.  That asymmetry is the
whole difficulty: every algorithm that walks "edge -> its pcurve on a face"
has to special-case the seam, and the fillet code is where it shows.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 02_two_pcurves.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import Part
from FreeCAD import Vector
from seamlib import done, fmtv, head, say, seam_edges

head("A. the seam edge: two pcurves on one face")
cyl = Part.makeCylinder(5.0, 10.0)
lat = [f for f in cyl.Faces if f.Surface.TypeId == "Part::GeomCylinder"][0]
seam = seam_edges(cyl)[0]["edge"]
say("solid: faces = %d, edges = %d; seam = the edge with one adjacent face",
    len(cyl.Faces), len(cyl.Edges))
say("the SAME edge, asked for its pcurve twice, in the two orientations:")
for tag, edge in (("as-is    ", seam), ("reversed ", seam.reversed())):
    c2d, first, last = lat.curveOnSurface(edge)
    a, b = c2d.value(first), c2d.value(last)
    say("  %s Face.curveOnSurface(edge) -> %-8s from (u = %.4f, v = %.4f) to (u = %.4f, v = %.4f)",
        tag, c2d.__class__.__name__, a.x, a.y, b.x, b.y)
say("-> two Line2d, at u = 2*pi and at u = 0. One edge, one face, two pcurves.")

head("B. an ordinary edge: two faces, one pcurve each")
circ = [e for e in cyl.Edges if e.Curve.TypeId == "Part::GeomCircle"][0]
faces = cyl.ancestorsOfType(circ, Part.Face)
say("the top/bottom circle belongs to %d faces", len(faces))
for i, f in enumerate(faces, 1):
    c2d, first, last = f.curveOnSurface(circ)
    a, b = c2d.value(first), c2d.value(last)
    say("  face %d (%-20s) -> %-12s from (%.4f, %.4f) to (%.4f, %.4f)",
        i, f.Surface.TypeId, c2d.__class__.__name__, a.x, a.y, b.x, b.y)
say("-> one pcurve per face; nothing is doubled.")

head("C. the wire of the lateral face walks the seam twice")
wire = lat.OuterWire
say("  Face.Edges        = %d   (distinct edges of the face)", len(lat.Edges))
say("  OuterWire.Edges   = %d   (Python de-duplicates here)", len(wire.Edges))
say("  OuterWire.OrderedEdges = %d   <- the traversal, and it is one longer",
    len(wire.OrderedEdges))
say("")
say("  the ordered traversal, with the orientation of each step:")
for k, e in enumerate(wire.OrderedEdges):
    which = [i + 1 for i, x in enumerate(cyl.Edges) if x.isSame(e)]
    say("    step %d: Edge%s  %-18s orientation = %-8s length = %.4f",
        k + 1, which[0] if which else "?", e.Curve.TypeId, e.Orientation, e.Length)
say("")
say("  the boundary of the parameter square is a rectangle with FOUR sides")
say("  (u=0, v=0, u=2pi, v=10) but the solid has only THREE distinct edges.")
say("  The seam is the side that is used twice, once in each orientation.")

head("D. the same rule on the other closed surfaces")
cases = [
    ("cylinder  Part.makeCylinder(5, 10)", Part.makeCylinder(5.0, 10.0)),
    ("sphere    Part.makeSphere(5)", Part.makeSphere(5.0)),
    ("torus     Part.makeTorus(10, 3)", Part.makeTorus(10.0, 3.0)),
    ("cone      Part.makeCone(5, 2, 10)", Part.makeCone(5.0, 2.0, 10.0)),
]
for name, shape in cases:
    ss = seam_edges(shape)
    kinds = []
    for d in ss:
        s = d["surf"]
        kinds.append("Edge%d on %s (uPer=%s vPer=%s)" % (
            d["edge_idx"], s.TypeId.replace("Part::Geom", ""),
            s.isUPeriodic(), s.isVPeriodic()))
    say("  %-36s faces = %d  edges = %d  seams = %d", name,
        len(shape.Faces), len(shape.Edges), len(ss))
    for k in kinds:
        say("        %s", k)

head("E. how many pcurves does each face of a solid hold?")
say("  counting the pcurves of every face: a seam edge contributes two to its")
say("  one face, every other edge contributes one to each of its two faces.")
total_pc = 0
for fi, face in enumerate(cyl.Faces, 1):
    n = len(face.OuterWire.OrderedEdges)
    total_pc += n
    say("    Face%-3d %-20s ordered edges (= pcurves) = %d",
        fi, face.Surface.TypeId, n)
say("  Face1 borders %d distinct edges and holds %d pcurves; the odd one out is",
    len(cyl.Faces[0].Edges), len(cyl.Faces[0].OuterWire.OrderedEdges))
say("  the seam's second pcurve. Every algorithm that assumes 'one pcurve per")
say("  (edge, face) pair' is wrong on exactly this face.")
say("  Script 05 shows what the seam costs and how to build the same solid")
say("  without it.")

done("02_two_pcurves")
