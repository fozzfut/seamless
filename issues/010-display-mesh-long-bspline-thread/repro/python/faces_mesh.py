"""Per-face meshing cost of one object, headless (FreeCADCmd).
Env: PERF_FILE, PERF_OUT, PERF_OBJ (object name), PERF_ANGLES (comma list, degrees), PERF_DEV (0.5),
PERF_FACE_BUDGET_S (skip the slow angle for the rest of the faces once one face exceeds it).
Uses MeshPart.meshFromShape -> BRepMesh_IncrementalMesh(shape, deflection, relative=False, angle), single thread
(Mod/MeshPart/App/Mesher.cpp:231 at 1.1.1), with the deflection ViewProviderPartExt computes for the WHOLE
object (Part::Tools::getDeflection: (dx+dy+dz)/300*deviation, Mod/Part/App/Tools.cpp:896)."""
import os, sys, time, json, math
import FreeCAD as App
import Part, MeshPart

path = os.environ["PERF_FILE"]
out = os.environ["PERF_OUT"]
name = os.environ.get("PERF_OBJ", "Part__Feature014")
angles = [float(a) for a in os.environ.get("PERF_ANGLES", "28.5,6.4").split(",")]
dev = float(os.environ.get("PERF_DEV", "0.5"))
budget = float(os.environ.get("PERF_FACE_BUDGET_S", "30"))

doc = App.openDocument(path)
obj = doc.getObject(name)
shape = obj.Shape.copy()
shape.Placement = App.Placement()
bb = shape.BoundBox
defl = (bb.XLength + bb.YLength + bb.ZLength) / 300.0 * dev
res = {"file": path, "obj": name, "label": obj.Label, "deflection": defl, "bbox": [bb.XLength, bb.YLength, bb.ZLength],
       "n_faces": len(shape.Faces), "angles": angles, "faces": []}
surf_types = {}
for i, f in enumerate(shape.Faces):
    s = f.Surface
    t = type(s).__name__
    surf_types[t] = surf_types.get(t, 0) + 1
    row = {"i": i + 1, "type": t, "area": f.Area, "n_edges": len(f.Edges)}
    if t == "BSplineSurface":
        row.update({"udeg": s.UDegree, "vdeg": s.VDegree, "upoles": s.NbUPoles, "vpoles": s.NbVPoles,
                    "uknots": s.NbUKnots, "vknots": s.NbVKnots})
    for e in f.Edges:
        c = e.Curve
        if type(c).__name__ == "BSplineCurve":
            row["max_edge_poles"] = max(row.get("max_edge_poles", 0), c.NbPoles)
    res["faces"].append(row)
res["surface_types"] = surf_types

slow_skip = set()
totals = {}
for a in angles:
    tot = 0.0
    for row, f in zip(res["faces"], shape.Faces):
        if a in slow_skip:
            row["t_%g" % a] = None
            continue
        ff = f.copy()
        t0 = time.perf_counter()
        m = MeshPart.meshFromShape(Shape=ff, LinearDeflection=defl, AngularDeflection=math.radians(a), Relative=False)
        dt = time.perf_counter() - t0
        row["t_%g" % a] = dt
        row["tri_%g" % a] = m.CountFacets
        tot += dt
        if dt > budget:
            slow_skip.add(a)
            row["budget_hit"] = True
        with open(out, "w") as fh:
            json.dump(res, fh, indent=1)
    totals["%g" % a] = tot
    res["totals"] = totals
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)

# whole object in one call, like the view provider (but single-threaded MeshPart path)
whole = {}
for a in angles:
    t0 = time.perf_counter()
    m = MeshPart.meshFromShape(Shape=shape.copy(), LinearDeflection=defl, AngularDeflection=math.radians(a), Relative=False)
    whole["%g" % a] = {"s": time.perf_counter() - t0, "tri": m.CountFacets}
    res["whole"] = whole
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
print("PERF-DONE", json.dumps({"totals": totals, "whole": whole}))
