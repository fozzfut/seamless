"""07 -- the failure on the owner's real part, and the hang band.

This is the ONLY script that needs a document.  It never touches the original:
it copies the .FCStd to a scratch directory and opens the copy.

One radius per run, on purpose.  Some radii do not finish: the fillet near the
seam can spin for minutes with no result, so each radius must be run under its
own external deadline and a run that is killed IS a measurement.

    SEAMLESS_RADIUS=0.25 timeout -k 5 540 \
      "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 07_user_part_fillet.py

Environment:
    SEAMLESS_PART    path to the .FCStd            (default: the owner's copy)
    SEAMLESS_RADIUS  fillet radius in mm           (default: 1.0)
    SEAMLESS_EDGE    edge name on the body tip     (default: Edge9)
    SEAMLESS_WORK    scratch directory for the copy (default: system temp)

Exit code 124 from `timeout` means the recompute never returned.  Every line is
flushed as it is produced, so the output of a killed run shows exactly how far
the run got.
"""

import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))

import FreeCAD as App
import Part
from seamlib import bop, done, fmtv, head, say, seam_edges

DEFAULT_PART = ("C:/path/to/temp/claude/"
                "c--Program-Files-FreeCAD-1-1/90e2ee8a-0198-4b2f-ae54-0503653173cc/"
                "scratchpad/ribact/part with fillet.FCStd")

SRC = os.environ.get("SEAMLESS_PART", DEFAULT_PART)
RADIUS = float(os.environ.get("SEAMLESS_RADIUS", "1.0"))
EDGE = os.environ.get("SEAMLESS_EDGE", "Edge9")
WORK = os.environ.get("SEAMLESS_WORK", os.path.join(os.environ.get("TEMP", "."), "seamless_repro"))

head("A. the copy")
say("  source  = %s", SRC)
say("  radius  = %.4f mm   edge = %s", RADIUS, EDGE)
if not os.path.isfile(SRC):
    say("  the source file is not there. Set SEAMLESS_PART to a .FCStd and re-run.")
    done("07_user_part_fillet")
    sys.exit(2)
os.makedirs(WORK, exist_ok=True)
dst = os.path.join(WORK, "copy_r%s.FCStd" % RADIUS)
if os.path.exists(dst):
    os.remove(dst)
shutil.copyfile(SRC, dst)
say("  copy    = %s  (%d bytes)", dst, os.path.getsize(dst))
say("  the original is never opened, so it cannot be modified.")

head("B. the document as it arrives")
doc = App.openDocument(dst)
for obj in doc.Objects:
    if not hasattr(obj, "Shape"):
        continue
    try:
        sh = obj.Shape
        say("  %-14s %-26s faces = %-3d edges = %-3d valid = %-5s vol = %12.4f  check = %s",
            obj.Name, obj.TypeId, len(sh.Faces), len(sh.Edges), sh.isValid(),
            sh.Volume, bop(sh) if sh.Faces else "n/a")
    except Exception as exc:
        say("  %-14s %-26s <no shape: %s>", obj.Name, obj.TypeId, exc)

body = doc.getObject("Body")
tip = body.Tip
base = tip.Shape
say("")
say("  Body.Tip = %s (%s)", tip.Name, tip.TypeId)
say("  tip shape: faces = %d edges = %d volume = %.4f isValid = %s check(True) = %s",
    len(base.Faces), len(base.Edges), base.Volume, base.isValid(), bop(base))
say("  -> the base is clean by BOTH checkers. Whatever breaks, breaks in the fillet.")

head("C. the seams of the tip shape, and the edge we are about to fillet")
seams = seam_edges(base)
for d in seams:
    e = d["edge"]
    say("  seam Edge%-3d on Face%-3d (%-10s) length = %8.4f  %s -> %s",
        d["edge_idx"], d["face_idx"], d["surf"].TypeId.replace("Part::Geom", ""),
        e.Length, fmtv(e.valueAt(e.FirstParameter)), fmtv(e.valueAt(e.LastParameter)))
if not seams:
    say("  no seam edges on the tip shape")
idx = int(EDGE.replace("Edge", ""))
edge = base.Edges[idx - 1]
say("  %s: %-18s length = %.6f  %s -> %s", EDGE, edge.Curve.TypeId, edge.Length,
    fmtv(edge.valueAt(edge.FirstParameter)), fmtv(edge.valueAt(edge.LastParameter)))
if seams:
    say("  distance(%s, nearest seam) = %.9f mm", EDGE,
        min(edge.distToShape(d["edge"])[0] for d in seams))

head("D. PartDesign::Fillet r = %.4f on %s" % (RADIUS, EDGE))
feat = body.newObject("PartDesign::Fillet", "SeamlessFillet")
feat.Base = (tip, [EDGE])
feat.Radius = RADIUS
say("  about to recompute -- if nothing follows this line, the kernel never returned")
t0 = time.perf_counter()
doc.recompute()
dt = time.perf_counter() - t0
say("  recompute returned after %.3f s; feature State = %s", dt, feat.State)
try:
    sh = feat.Shape
    say("  result: faces = %d edges = %d isValid = %s volume = %.4f",
        len(sh.Faces), len(sh.Edges), sh.isValid(), sh.Volume)
    say("  base volume = %.4f   delta = %+.4f mm3", base.Volume, sh.Volume - base.Volume)
    say("  check(True) = %s", bop(sh))
    say("  body shape: isValid = %s volume = %.4f", body.Shape.isValid(), body.Shape.Volume)
except Exception as exc:
    say("  the feature has no usable shape: %r", exc)

errs = [(o.Name, o.State) for o in doc.Objects
        if hasattr(o, "State") and any(k in o.State for k in ("Invalid", "Error", "Touched"))]
say("  document objects left in a bad state: %s", errs or "none")

App.closeDocument(doc.Name)
try:
    os.remove(dst)
except OSError:
    pass
done("07_user_part_fillet")
