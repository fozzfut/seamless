import io, os, math, shutil, tempfile
import FreeCAD as App, Part
OUT = io.open(os.environ["HD_OUT"], "w", encoding="utf-8")
def say(s): OUT.write(s + "\n"); OUT.flush()
work = os.path.join(tempfile.gettempdir(), "hd_edges_%d.FCStd" % os.getpid())
shutil.copyfile("C:/dev/seamless/fixtures/cube_with_round_cut.FCStd", work)
doc = App.openDocument(work)
body = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"][0]
sh = body.Shape
R = 1.0
ends = []
for e in sh.Edges:
    if len(sh.ancestorsOfType(e, Part.Face)) == 1:
        ends += [v.Point for v in e.Vertexes]
mode = os.environ.get("HD_EDGE", "")
if not mode:
    say("seam endpoints: %d" % len(ends))
    for i, e in enumerate(sh.Edges, 1):
        if not e.Vertexes or len(sh.ancestorsOfType(e, Part.Face)) != 2:
            continue
        d = min((v.Point - p).Length for v in e.Vertexes for p in ends) if ends else None
        say("Edge%d %s len=%.4f d=%s" % (i, e.Curve.TypeId.replace("Part::Geom", ""), e.Length,
                                         "none" if d is None else "%.6f" % d))
else:
    e = sh.getElement(mode)
    try:
        res = sh.makeFillet(R, [e])
        try:
            bop = "clean" if res.check(True) is None else "returned"
        except Exception as exc:
            bop = "DIRTY " + " ".join(str(exc).split())[:70]
        planes0 = sorted(round(f.Area, 4) for f in sh.Faces if f.Surface.TypeId == "Part::GeomPlane")
        planes1 = sorted(round(f.Area, 4) for f in res.Faces if f.Surface.TypeId == "Part::GeomPlane")
        say("%s r=%.1f valid=%s bop=%s faces %d->%d planes %d->%d dV=%.6f" % (
            mode, R, res.isValid(), bop, len(sh.Faces), len(res.Faces), len(planes0), len(planes1),
            sh.Volume - res.Volume))
    except Exception as exc:
        say("%s raised %s" % (mode, str(exc)[:80]))
App.closeDocument(doc.Name); os.remove(work); OUT.close()
