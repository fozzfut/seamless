"""05 -- can the seam be removed from inside FreeCAD?

Three questions, each answered by a measurement:

  A  If the closed face is built from two half faces instead of one periodic
     face, is there a seam?  (No.)
  B  Do the operations that matter -- booleans, Refine, STEP round trip --
     keep it that way?  (Booleans and STEP do. Refine does NOT: removeSplitter
     and UnifySameDomain merge the halves back and the seam returns.)
  C  On the real fixture: split the pocket profile circle into arcs and switch
     PartDesign Refine off.  Does the fillet that failed in script 03 now work?

This is the one place where the project starting note was wrong.  The note said
"splitting the profile circle into two arcs does not remove the seam -- the
kernel glues the faces of one surface back together".  That is true only while
Refine is on.  With Refine off the seam is gone and stays gone.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 05_removing_the_seam.py
"""

import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import FreeCAD as App
import Part
from FreeCAD import Placement, Rotation, Vector
from seamlib import (AXPT, BX, BY, BZ, NRM, POCKET_LEN, RAD, STANDOFF, bop,
                     build_fixture, done, fillet_removed, fmtv, head, say,
                     seam_edges, solid_of, target_edge)

head("A. a cylinder built from two half faces has no seam")
ref = Part.makeCylinder(5.0, 10.0)
lat = [f for f in ref.Faces if f.Surface.TypeId == "Part::GeomCylinder"][0]
srf = lat.Surface
halves = [srf.toShape(0.0, math.pi, 0.0, 10.0).Faces[0],
          srf.toShape(math.pi, 2 * math.pi, 0.0, 10.0).Faces[0]]
caps = [Part.Face(Part.Wire(Part.makeCircle(5.0, Vector(0, 0, z), Vector(0, 0, 1))))
        for z in (0.0, 10.0)]
shell = Part.Shell(halves + caps)
split = Part.Solid(shell)
say("  reference Part.makeCylinder(5, 10) : faces = %d edges = %d seams = %d vol = %.4f valid = %s",
    len(ref.Faces), len(ref.Edges), len(seam_edges(ref)), ref.Volume, ref.isValid())
say("  built from two half faces          : faces = %d edges = %d seams = %d vol = %.4f valid = %s",
    len(split.Faces), len(split.Edges), len(seam_edges(split)), split.Volume, split.isValid())
say("  shell closed = %s   check(True) = %s", shell.isClosed(), bop(split))
say("  |volume difference| = %.12f   -> the same solid, no seam", abs(ref.Volume - split.Volume))

head("B. what survives, and what puts the seam back")
box = Part.makeBox(20, 20, 20, Vector(-10, -10, -5))
small = Part.makeBox(1, 1, 1, Vector(-0.5, -0.5, -0.5))
trials = [
    ("cut:       box.cut(split)", box.cut(split)),
    ("common:    box.common(split)", box.common(split)),
    ("fuse:      split.fuse(small)", split.fuse(small)),
    ("copy:      split.copy()", split.copy()),
    ("transform: split.rotated(...)", split.rotated(Vector(0, 0, 0), Vector(0, 0, 1), 37.0)),
    ("removeSplitter()", split.removeSplitter()),
]
usd = Part.ShapeUpgrade.UnifySameDomain(split)
usd.build()
trials.append(("UnifySameDomain", usd.shape()))
for name, res in trials:
    say("  %-28s faces = %-3d edges = %-3d seams = %d %s", name, len(res.Faces),
        len(res.Edges), len(seam_edges(res)),
        "<- the seam is back" if seam_edges(res) else "")
step = os.path.join(tempfile.gettempdir(), "seamless_05_roundtrip.step")
split.exportStep(step)
back = Part.Shape()
back.read(step)
say("  %-28s faces = %-3d edges = %-3d seams = %d  vol = %.4f",
    "STEP export + read back", len(back.Faces), len(back.Edges),
    len(seam_edges(back)), back.Solids[0].Volume if back.Solids else float("nan"))
say("  (STEP file: %s)", step)
try:
    os.remove(step)
except OSError:
    pass
say("")
say("  -> booleans, copies, transforms and STEP all keep the seamless form.")
say("     Only removeSplitter / UnifySameDomain -- which is exactly what")
say("     PartDesign Refine runs -- merge the halves and restore the seam.")


def build_split_pocket(doc, tag, angle_xu, n_arcs, refine, pocket_len=POCKET_LEN, rad=RAD):
    """The same fixture as script 03, but the pocket profile is n_arcs arcs."""
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
    pad.Refine = refine
    doc.recompute()
    sk2 = doc.addObject("Sketcher::SketchObject", "SC" + tag)
    body.addObject(sk2)
    sk2.AttachmentSupport = None
    sk2.Placement = Placement(AXPT + NRM * STANDOFF, Rotation(Vector(0, 1, 0), 45))
    a0 = math.radians(angle_xu)
    step_a = 2 * math.pi / n_arcs
    for k in range(n_arcs):
        sk2.addGeometry(Part.ArcOfCircle(Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), rad),
                                         a0 + k * step_a, a0 + (k + 1) * step_a), False)
    doc.recompute()
    pk = doc.addObject("PartDesign::Pocket", "Pk" + tag)
    body.addObject(pk)
    pk.Profile = sk2
    pk.Length = pocket_len
    pk.Refine = refine
    doc.recompute()
    return body, pk


head("C. the fixture of script 03 with a split profile and Refine off")
say("  AngleXU = 90 deg -- the angle at which script 03 measured -356.4531 mm3.")
say("")
say("  %-7s %-8s %-7s %-7s %-7s %-13s %-13s %s",
    "arcs", "Refine", "faces", "seams", "valid", "pocket vol", "removed", "check(True)")
doc = App.newDocument("P05")
for refine in (True, False):
    for n_arcs in (1, 2, 3, 4):
        tag = "C%d%s" % (n_arcs, "R" if refine else "N")
        if n_arcs == 1:
            body, pocket, tip, sk2 = build_fixture(doc, tag, 90.0, prefillet=False)
            pocket.Refine = refine
            doc.recompute()
            pk = pocket
        else:
            body, pk = build_split_pocket(doc, tag, 90.0, n_arcs, refine)
        sh = solid_of(pk)
        idx, edge = target_edge(sh)
        try:
            res = sh.makeFillet(1.0, [edge])
            removed = sh.Volume - res.Volume
            verdict = "%s %s" % (res.isValid(), bop(res))
        except Exception as exc:
            removed = float("nan")
            verdict = "RAISED %s" % str(exc)[:50]
        say("  %-7d %-8s %-7d %-7d %-7s %13.4f %+13.4f %s", n_arcs, refine,
            len(sh.Faces), len(seam_edges(sh)), sh.isValid(), sh.Volume, removed, verdict)
say("")
say("  analytic removal for r = 1.0 on this edge: %+.4f mm3",
    fillet_removed(1.0, 6.370744))
say("")
say("  one arc  = one closed periodic face = one seam = the fillet is destroyed.")
say("  two arcs + Refine on : PartDesign merges them back; a seam exists again,")
say("      but its u = 0 lands elsewhere, so this particular fillet survives.")
say("  two arcs + Refine off: no seam at all, and the fillet is exactly right.")

head("D. the cost of switching Refine off")
for refine in (True, False):
    tag = "D2%s" % ("R" if refine else "N")
    body, pk = build_split_pocket(doc, tag, 90.0, 2, refine)
    sh = solid_of(pk)
    say("  Refine = %-5s : faces = %d, edges = %d, vertexes = %d, area = %.6f",
        refine, len(sh.Faces), len(sh.Edges), len(sh.Vertexes), sh.Area)
say("  -> the extra faces are the price: one seam-free cylinder costs one extra")
say("     face and two extra edges per split.")

App.closeDocument(doc.Name)
done("05_removing_the_seam")
