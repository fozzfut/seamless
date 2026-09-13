"""01 -- what a seam is, and how to find one.

Proves, on primitives only (no document, no user file):
  * a cylindrical face is periodic in u with period 2*pi, and S(0,v) == S(2pi,v);
  * exactly one edge of the lateral face has ONE adjacent face -- that is the seam;
  * the seam sits on the u = 0 iso-line, i.e. it passes through
        Center + R * (surface Rotation applied to (1,0,0));
  * the anchor follows the surface frame: rotate the cylinder, the seam turns with it;
  * a face that is not closed in u (a half cylinder) has no seam at all.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 01_seam_anatomy.py
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))

import Part
from FreeCAD import Placement, Rotation, Vector
from seamlib import done, fmtv, head, say, seam_edges, u0_anchor

head("A. the surface: a cylinder is periodic in u")
cyl = Part.makeCylinder(5.0, 10.0)
lat = [f for f in cyl.Faces if f.Surface.TypeId == "Part::GeomCylinder"][0]
srf = lat.Surface
say("Part.makeCylinder(5.0, 10.0)")
say("  surface        = %s  R = %.4f  Axis = %s", srf.TypeId, srf.Radius, fmtv(srf.Axis))
say("  isUPeriodic()  = %s        isVPeriodic() = %s", srf.isUPeriodic(), srf.isVPeriodic())
say("  UPeriod()      = %.6f  (== 2*pi: %s)", srf.UPeriod(), abs(srf.UPeriod() - 2 * math.pi) < 1e-12)
say("  face.ParameterRange = u[%.4f .. %.4f]  v[%.4f .. %.4f]", *lat.ParameterRange)
for u in (0.0, math.pi / 2, math.pi, 2 * math.pi):
    say("  S(u=%.4f, v=0) = %s", u, fmtv(srf.value(u, 0.0)))
say("  |S(0,0) - S(2pi,0)| = %.12f  -> the parameter square is glued along u",
    srf.value(0, 0).distanceToPoint(srf.value(2 * math.pi, 0)))

head("B. the topology: the seam is the edge with ONE adjacent face")
say("edges of the solid: %d, faces: %d", len(cyl.Edges), len(cyl.Faces))
for i, edge in enumerate(cyl.Edges):
    anc = cyl.ancestorsOfType(edge, Part.Face)
    say("  Edge%-2d %-20s len = %8.4f  adjacent faces = %d %s",
        i + 1, edge.Curve.TypeId, edge.Length, len(anc),
        "<- SEAM" if len(anc) == 1 else "")
seams = seam_edges(cyl)
say("seam_edges() found %d seam(s)", len(seams))

head("C. the anchor: the seam lies on the u = 0 iso-line")
for d in seams:
    edge = d["edge"]
    srf = d["surf"]
    p0 = edge.valueAt(edge.FirstParameter)
    p1 = edge.valueAt(edge.LastParameter)
    say("  seam Edge%d on Face%d (%s)", d["edge_idx"], d["face_idx"], srf.TypeId)
    say("    from %s to %s   len = %.4f", fmtv(p0), fmtv(p1), edge.Length)
    say("    Center = %s  Rotation.Q = %s", fmtv(srf.Center),
        tuple(round(x, 9) for x in srf.Rotation.Q))
    anchor = u0_anchor(srf)
    say("    Center + R*Rot*(1,0,0) = %s", fmtv(anchor))
    say("    distance(seam start, that point) = %.12f", p0.distanceToPoint(anchor))
    uv = srf.parameter(p0)
    say("    srf.parameter(seam start) = (u = %.9f, v = %.9f)", uv[0], uv[1])

head("D. the anchor follows the surface frame, not the solid")
for ang in (0.0, 30.0, 90.0, 180.0):
    c = Part.makeCylinder(5.0, 10.0)
    c.Placement = Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), ang))
    f = [x for x in c.Faces if x.Surface.TypeId == "Part::GeomCylinder"][0]
    s = f.Surface
    d = seam_edges(c)[0]
    p0 = d["edge"].valueAt(d["edge"].FirstParameter)
    anchor = u0_anchor(s)
    direction = (anchor - s.Center)
    direction.normalize()
    say("  spin about Z = %6.1f deg -> u=0 point %s  dir %s  dist(seam, u=0 point) = %.12f",
        ang, fmtv(anchor), fmtv(direction), p0.distanceToPoint(anchor))

head("E. a face that is not closed in u carries no seam")
for ang in (360.0, 180.0, 359.0):
    c = Part.makeCylinder(5.0, 10.0, Vector(0, 0, 0), Vector(0, 0, 1), ang)
    lf = [f for f in c.Faces if f.Surface.TypeId == "Part::GeomCylinder"][0]
    u0, u1 = lf.ParameterRange[0], lf.ParameterRange[1]
    say("  makeCylinder(5, 10, angle = %6.1f deg): solid faces = %d, u span = %.6f of period %.6f",
        ang, len(c.Faces), u1 - u0, lf.Surface.UPeriod())
    say("      closed in u = %s   seam edges = %d",
        abs((u1 - u0) - lf.Surface.UPeriod()) < 1e-9, len(seam_edges(c)))
say("  -> the seam appears exactly when the face spans the full period in u.")
say("  (a LONE face is useless for this test: every edge of a free face has one")
say("   adjacent face, so the seam must be counted inside a closed solid.)")

done("01_seam_anatomy")
