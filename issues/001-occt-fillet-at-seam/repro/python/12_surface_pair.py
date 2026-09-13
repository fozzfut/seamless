# Which surface pair does ChFi3d_ComputeCurves see for a fillet vs a chamfer?
# Decides whether it takes the ANALYTIC cyl/plane branch (Builder_0.cxx:2991)
# or the general numeric path that trusts Pardeb/Parfin as seeds.
import os
import sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))
import FreeCAD as App, Part
import seamlib as SL
say = SL.say
doc = App.newDocument("st")
body, pocket, tip, sk = SL.build_fixture(doc, "ST", 0)
sh = SL.solid_of(tip)
ti, te = SL.target_edge(sh)
say("target Edge%d, length %.6f", ti, te.Length)
before = set(id(f) for f in sh.Faces)
for op, name in ((lambda s: s.makeFillet(1.0, [te]), "fillet"),
                 (lambda s: s.makeChamfer(1.0, [te]), "chamfer")):
    r = op(sh)
    olds = [f.Surface.TypeId for f in sh.Faces]
    news = [f.Surface.TypeId for f in r.Faces]
    # the face the operation added: types present in result but shaped new
    say("%-8s result faces = %d (was %d)", name, len(r.Faces), len(sh.Faces))
    # locate the new face: the one whose area matches the op's band
    cands = []
    for i, f in enumerate(r.Faces):
        if not any(f.isPartner(g) for g in sh.Faces):
            cands.append((i + 1, f.Surface.TypeId.split("::")[-1], f.Area))
    for i, t, a in cands:
        say("    new Face%-3d %-14s area %.6f", i, t, a)
say("")
say("face at end (pocket wall) = %s",
    SL.seam_edges(sh)[0]["surf"].TypeId.split("::")[-1])
App.closeDocument(doc.Name)
SL.done("surftype")
