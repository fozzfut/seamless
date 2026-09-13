"""13 -- export the owner's real part once, so the Edge9 case can be run on bare OCCT.

The Edge9 measurement must be repeated against TWO kernels (stock TKFillet and patched
TKFillet). Copying the whole FreeCAD installation twice to swap a DLL costs gigabytes of
disk; reading the shape from a BREP file in a 200-line C++ program costs nothing and
removes the FreeCAD layer from the measurement entirely. So FreeCAD is used exactly once,
here, to hand the solid over.

The original .FCStd is NEVER opened: the file is copied to the scratchpad first.

    "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 13_export_user_part.py

Environment:
    SEAMLESS_PART  path to the .FCStd   (default: the owner's copy)
    SEAMLESS_OUT   output directory     (default: scratchpad/edge9)

Writes  <out>/body_tip.brep  and prints the facts a reader needs to trust it:
the volume of the exported solid (must equal the 5456.5806 mm3 measured in FreeCAD),
the endpoints of Edge9, and the distance from Edge9 to the nearest seam.
"""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))

import FreeCAD as App
import Part
from seamlib import bop, done, fmtv, head, say, seam_edges

DEFAULT_PART = ("C:/path/to/temp/claude/"
                "c--Program-Files-FreeCAD-1-1/90e2ee8a-0198-4b2f-ae54-0503653173cc/"
                "scratchpad/ribact/part with fillet.FCStd")
DEFAULT_OUT = ("C:/path/to/temp/claude/"
               "c--Program-Files-FreeCAD-1-1/90e2ee8a-0198-4b2f-ae54-0503653173cc/"
               "scratchpad/edge9")

SRC = os.environ.get("SEAMLESS_PART", DEFAULT_PART)
OUT = os.environ.get("SEAMLESS_OUT", DEFAULT_OUT)
EDGE = os.environ.get("SEAMLESS_EDGE", "Edge9")

head("A. the copy (the original is never opened)")
if not os.path.isfile(SRC):
    say("  no such file: %s", SRC)
    done("13_export_user_part")
    sys.exit(2)
os.makedirs(OUT, exist_ok=True)
dst = os.path.join(OUT, "part_copy.FCStd")
shutil.copyfile(SRC, dst)
say("  source = %s (%d bytes)", SRC, os.path.getsize(SRC))
say("  copy   = %s", dst)

head("B. the tip shape")
doc = App.openDocument(dst)
body = doc.getObject("Body")
tip = body.Tip
base = tip.Shape
say("  Body.Tip = %s (%s)", tip.Name, tip.TypeId)
say("  faces = %d  edges = %d  volume = %.4f  isValid = %s  check(True) = %s",
    len(base.Faces), len(base.Edges), base.Volume, base.isValid(), bop(base))

head("C. %s and the seam" % EDGE)
idx = int(EDGE.replace("Edge", ""))
edge = base.Edges[idx - 1]
p0 = edge.valueAt(edge.FirstParameter)
p1 = edge.valueAt(edge.LastParameter)
say("  %s: %-18s length = %.6f", EDGE, edge.Curve.TypeId, edge.Length)
say("    start = (%.9f, %.9f, %.9f)", p0.x, p0.y, p0.z)
say("    end   = (%.9f, %.9f, %.9f)", p1.x, p1.y, p1.z)
seams = seam_edges(base)
for d in seams:
    e = d["edge"]
    say("  seam Edge%-3d on Face%-3d (%-10s) length = %8.4f  %s -> %s",
        d["edge_idx"], d["face_idx"], d["surf"].TypeId.replace("Part::Geom", ""),
        e.Length, fmtv(e.valueAt(e.FirstParameter)), fmtv(e.valueAt(e.LastParameter)))
if seams:
    say("  distance(%s, nearest seam) = %.9f mm", EDGE,
        min(edge.distToShape(d["edge"])[0] for d in seams))

head("D. write the BREP")
brep = os.path.join(OUT, "body_tip.brep")
base.exportBrep(brep)
say("  wrote %s (%d bytes)", brep, os.path.getsize(brep))

back = Part.Shape()
back.importBrep(brep)
say("  read back: faces = %d edges = %d volume = %.4f isValid = %s check(True) = %s",
    len(back.Faces), len(back.Edges), back.Volume, back.isValid(), bop(back))
say("  volume difference across the round trip = %.9e mm3", abs(back.Volume - base.Volume))

App.closeDocument(doc.Name)
try:
    os.remove(dst)
except OSError:
    pass
done("13_export_user_part")
