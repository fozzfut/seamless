"""09 -- PartDesign::AdditiveHelix: the failure that really hurts threads.

Nothing here is about the seam.  It is recorded because it was found while
chasing the seam, and because it silently destroys parts.

Three measured failures of AdditiveHelix, on the classic ISO-style triangular
profile swept about the Z axis over a cylindrical pad:

  A  when the AXIAL size of the profile reaches the pitch (2h == pitch -- which
     is exactly what an ISO thread asks for), the tool shape comes out invalid
     and FreeCAD prints "Tool shape is not valid for boolean operation";
  B  further above that ratio the feature reports State = ['Up-to-date'] and the
     body quietly LOSES its core: the resulting volume is a fraction of the pad
     it was grown on;
  C  higher still it finally fails honestly, with State = ['Touched','Invalid'].

Part's own sweep (Part.makePipeShell + fuse) does the same job on the same
profile without any of this.

Each case is built in its own document, so a failed case cannot leak console
noise into the next one.  FreeCAD writes its own error text to stderr as well,
so lines like "Tool shape is not valid for boolean operation" in the output are
the kernel talking, not this script.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 09_helix_profile.py
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))

import FreeCAD as App
import Part
from FreeCAD import Vector
from seamlib import bop, done, head, say, seam_edges

RC = 9.0          # core radius
TURNS = 2
_N = [0]


def build(profile_pts, pitch, turns=TURNS, pad_length=None):
    """A cylindrical pad plus an AdditiveHelix, in a document of its own.

    Returns (doc, body, helix, pad_volume, pad_seams, seconds).
    """
    _N[0] += 1
    height = pitch * turns
    doc = App.newDocument("H%d" % _N[0])
    body = doc.addObject("PartDesign::Body", "Body")
    sk0 = body.newObject("Sketcher::SketchObject", "S0")
    sk0.AttachmentSupport = [(doc.XY_Plane, "")]
    sk0.MapMode = "FlatFace"
    sk0.addGeometry(Part.Circle(Vector(0, 0, 0), Vector(0, 0, 1), RC), False)
    pad = body.newObject("PartDesign::Pad", "Pad")
    pad.Profile = sk0
    pad.Length = pad_length or height
    doc.recompute()
    pad_volume = body.Shape.Volume
    pad_seams = len(seam_edges(body.Shape))

    sk1 = body.newObject("Sketcher::SketchObject", "S1")
    sk1.AttachmentSupport = [(doc.XZ_Plane, "")]
    sk1.MapMode = "FlatFace"
    n = len(profile_pts)
    for i in range(n):
        a, b = profile_pts[i], profile_pts[(i + 1) % n]
        sk1.addGeometry(Part.LineSegment(Vector(a[0], a[1], 0), Vector(b[0], b[1], 0)), False)
    doc.recompute()

    hx = body.newObject("PartDesign::AdditiveHelix", "Helix")
    hx.Profile = sk1
    hx.ReferenceAxis = (body.Origin.OriginFeatures[2], [""])
    hx.Mode = "pitch-height-angle"
    hx.Pitch = pitch
    hx.Height = height
    hx.Angle = 0.0
    t0 = time.perf_counter()
    doc.recompute()
    return doc, body, hx, pad_volume, pad_seams, time.perf_counter() - t0


def free_edges(shape):
    return sum(1 for e in shape.Edges if len(shape.ancestorsOfType(e, Part.Face)) == 1)


def triangle(h):
    return [(8.8, -h), (8.8, h), (10.0, 0.0)]


head("A. profile half-height h against pitch p: the tool breaks exactly at 2h == p")
say("  profile: the triangle (8.8, -h) (8.8, +h) (10.0, 0), swept about Z,")
say("  %d turns, over a pad of radius %.1f and the same height.", TURNS, RC)
say("")
say("  %-7s %-7s %-9s %-11s %-7s %-7s %-13s %-13s %s",
    "h", "pitch", "2h/p", "tool valid", "free", "faces", "body volume", "pad volume", "t")
for pitch in (2.0, 3.0):
    for ratio in (0.50, 0.75, 0.90, 0.95, 0.99, 1.00, 1.01, 1.05):
        h = ratio * pitch / 2.0
        doc, body, hx, pad_v, pad_s, dt = build(triangle(h), pitch)
        tool = hx.AddSubShape
        alive = tool is not None and not tool.isNull()
        sh = body.Shape
        say("  %-7.3f %-7.1f %-9.3f %-11s %-7s %-7d %13.4f %13.4f %.3f s",
            h, pitch, ratio, tool.isValid() if alive else "NULL",
            free_edges(tool) if alive else "-", len(sh.Faces), sh.Volume, pad_v, dt)
        App.closeDocument(doc.Name)
    say("")
say("  Below the ratio 1.0 the tool is a clean closed solid (free edges = 0).")
say("  AT the ratio 1.0 -- the classic ISO triangle, which exactly fills the")
say("  pitch -- the tool comes out with free edges and isValid() = False.")

head("B. above the boundary the body silently loses its core")
say("  pitch = 3.0, %d turns, pad volume = pi * %.1f^2 * %.1f", TURNS, RC, 3.0 * TURNS)
say("")
say("  %-9s %-11s %-7s %-11s %-13s %-13s %-9s %s",
    "2h/p", "tool valid", "free", "body valid", "body volume", "pad volume",
    "kept", "State")
for ratio in (0.93, 0.99, 1.00, 1.01, 1.07, 1.17, 1.18, 1.19, 1.20, 1.21, 1.22, 1.25,
              1.33, 1.50, 1.75, 2.00):
    h = ratio * 3.0 / 2.0
    doc, body, hx, pad_v, pad_s, dt = build(triangle(h), 3.0)
    tool = hx.AddSubShape
    alive = tool is not None and not tool.isNull()
    sh = body.Shape
    say("  %-9.4f %-11s %-7s %-11s %13.4f %13.4f %8.1f%% %s%s",
        ratio, tool.isValid() if alive else "NULL",
        free_edges(tool) if alive else "-", sh.isValid(), sh.Volume, pad_v,
        100.0 * sh.Volume / pad_v, hx.State,
        "  <-- CORE GONE" if sh.Volume < pad_v - 1.0 else "")
    App.closeDocument(doc.Name)
say("")
say("  Adding material must never reduce the volume. Where 'kept' drops far")
say("  below 100 %, the core cylinder has been eaten -- and the feature still")
say("  reports Up-to-date. Only at the largest ratios does it fail honestly")
say("  with State = ['Touched', 'Invalid'].")

head("C. the same profile through Part's own sweep, which works")
pitch = 2.0
h = pitch / 2.0
spine = Part.Wire(Part.makeHelix(pitch, pitch * TURNS, RC).Edges)
prof = Part.Wire(Part.makePolygon([Vector(8.8, 0, -h), Vector(8.8, 0, h),
                                   Vector(10.0, 0, 0.0), Vector(8.8, 0, -h)]))
t0 = time.perf_counter()
swept = spine.makePipeShell([prof], True, True)
dt = time.perf_counter() - t0
say("  the SAME 2h == pitch triangle, Part.makePipeShell:")
say("    faces = %d  isValid = %s  free edges = %d  volume = %.4f  t = %.3f s",
    len(swept.Faces), swept.isValid(), free_edges(swept), swept.Volume, dt)
rod = Part.makeCylinder(RC, pitch * TURNS)
t0 = time.perf_counter()
fused = rod.fuse(swept)
dt = time.perf_counter() - t0
say("  rod.fuse(that): faces = %d isValid = %s volume = %.4f  (rod alone %.4f, kept %.1f%%)  t = %.3f s",
    len(fused.Faces), fused.isValid(), fused.Volume, rod.Volume,
    100.0 * fused.Volume / rod.Volume, dt)
say("    check(True) = %s", bop(fused))
say("  -> same geometry, same ratio, no invalid tool and no lost core.")

head("D. what the seam does across the boundary")
say("  the bare pad is a plain cylinder and carries one seam. After the helix")
say("  is fused the cylindrical face is cut up, so the seam count changes --")
say("  and it changes at the SAME place the tool goes invalid.")
say("")
say("  %-9s %-13s %-13s %-13s %-13s %s",
    "2h/p", "pad seams", "body seams", "body faces", "body volume", "check(True)")
for ratio in (0.90, 1.00, 1.33):
    h = ratio * 2.0 / 2.0
    doc, body, hx, pad_v, pad_s, dt = build(triangle(h), 2.0)
    sh = body.Shape
    say("  %-9.2f %-13d %-13d %-13d %13.4f %s",
        ratio, pad_s, len(seam_edges(sh)), len(sh.Faces), sh.Volume, bop(sh))
    App.closeDocument(doc.Name)
say("")
say("  The four free edges at ratio 1.0 are the tool's own open boundary leaking")
say("  into the body, not a seam of the core: at ratio 0.90 the fused body has")
say("  none at all, although its pad had one.")

done("09_helix_profile")
