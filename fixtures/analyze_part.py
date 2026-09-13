import io, os, sys, math
import FreeCAD as App, Part
SRC = os.environ.get("HD_PART", "C:/dev/seamless/fixtures/cube_with_round_cut.FCStd")
OUT = io.open(os.environ["HD_OUT"], "w", encoding="utf-8")
def say(s): OUT.write(s + "\n"); OUT.flush()
import shutil, tempfile
work = os.path.join(tempfile.gettempdir(), "hd_analyze_%d.FCStd" % os.getpid())
shutil.copyfile(SRC, work)
doc = App.openDocument(work)
def bop(sh):
    try:
        return "clean" if sh.check(True) is None else "returned"
    except Exception as exc:
        return "DIRTY " + " ".join(str(exc).split())[:90]
def seam_ends(sh):
    pts = []
    for e in sh.Edges:
        faces = sh.ancestorsOfType(e, Part.Face)
        if len(faces) == 1 or any(hasattr(e, "isSeam") and e.isSeam(f) for f in faces):
            pts += [v.Point for v in e.Vertexes]
    return pts
for o in doc.Objects:
    if o.TypeId in ("PartDesign::Fillet", "PartDesign::Chamfer"):
        o.touch()
doc.recompute()
for body in [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]:
    say("BODY %s  tip=%s  valid=%s  bop=%s  faces=%d edges=%d vol=%.6f" % (
        body.Label, getattr(body.Tip, "Name", None), body.Shape.isValid(), bop(body.Shape),
        len(body.Shape.Faces), len(body.Shape.Edges), body.Shape.Volume))
    for f in body.Group:
        if not f.isDerivedFrom("PartDesign::Feature"): continue
        line = "  %-14s %-22s state=%s" % (f.Name, f.TypeId.split("::")[1], f.State)
        if f.TypeId in ("PartDesign::Fillet", "PartDesign::Chamfer"):
            base, subs = f.Base
            bsh = base.Shape
            r = float(getattr(f, "Radius", getattr(f, "Size", 0)))
            ends = seam_ends(bsh)
            worst = None
            for s in subs:
                try:
                    e = bsh.getElement(s)
                except Exception:
                    continue
                for v in e.Vertexes:
                    for p in ends:
                        d = (v.Point - p).Length
                        worst = d if worst is None else min(worst, d)
            planes = lambda sh: sorted(round(x.Area, 4) for x in sh.Faces if x.Surface.TypeId == "Part::GeomPlane")
            added = [a for a in planes(f.Shape) if a not in planes(bsh)]
            line += "  r=%.3f edges=%s  seam_d=%s (d/r=%s)  valid=%s bop=%s  faces %d->%d  dV=%.6f  new_plane_areas=%s" % (
                r, subs, "none" if worst is None else "%.6f" % worst,
                "-" if worst is None or not r else "%.3f" % (worst / r),
                f.Shape.isValid(), bop(f.Shape), len(bsh.Faces), len(f.Shape.Faces),
                bsh.Volume - f.Shape.Volume, added[:6])
        say(line)
App.closeDocument(doc.Name)
os.remove(work)
OUT.close()
