"""08 -- threads: which builder actually delivers the turns you ask for.

The complaint that started this: "a thread comes out as one turn, from seam to
seam".  Measured, that is a property of exactly ONE function, Part.makeThread,
and it has nothing to do with the seam -- makeThread is a one-turn primitive
that ignores the height it is given.  Every other path (Part.makeHelix,
Part.makeLongHelix, makePipeShell along a helix) delivers the full count.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 08_thread_turns.py
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))

import Part
from FreeCAD import Vector
from seamlib import bop, done, head, say, seam_edges

R = 9.0
PITCH = 2.0


def turns_of(wire, pitch, radius):
    """A helix of one turn has length hypot(2*pi*R, pitch); divide by it."""
    return wire.Length / math.hypot(2 * math.pi * radius, pitch)


head("A. Part.makeThread ignores the height it is given")
say("  one turn at pitch %.1f, radius %.1f is %.6f mm of helix.",
    PITCH, R, math.hypot(2 * math.pi * R, PITCH))
say("")
say("  %-10s %-12s %-11s %-11s %-9s %s", "asked h", "asked turns", "ZLength",
    "ang. span", "delivered", "volume")
for height in (1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0):
    th = Part.makeThread(PITCH, 1.0, height, R)
    angs = [math.degrees(math.atan2(v.Y, v.X)) % 360 for v in th.Vertexes]
    span = max(angs) - min(angs)
    say("  %-10.1f %-12.2f %-11.4f %-11.1f %-9.4f %+.4f",
        height, height / PITCH, th.BoundBox.ZLength, span, span / 360.0, th.Volume)
say("")
say("  The delivered turn count does not follow the request at all, and past")
say("  8 asked turns the volume goes NEGATIVE -- the solid is inside out.")

head("B. the request that started this: 32 turns")
th = Part.makeThread(PITCH, 1.0, PITCH * 32, R)
angs = [math.degrees(math.atan2(v.Y, v.X)) % 360 for v in th.Vertexes]
span = max(angs) - min(angs)
say("  Part.makeThread(%.1f, 1.0, %.1f, %.1f)  -- 32 turns asked", PITCH, PITCH * 32, R)
say("    faces = %d edges = %d vertexes = %d", len(th.Faces), len(th.Edges), len(th.Vertexes))
say("    ZLength = %.4f mm (asked %.1f)", th.BoundBox.ZLength, PITCH * 32)
say("    angular span = %.4f deg = %.4f turns  (asked 32)", span, span / 360.0)
say("    volume = %+.4f   isValid = %s   seams = %d", th.Volume, th.isValid(), len(seam_edges(th)))
say("    -> %.4f of 32 turns.", span / 360.0)

head("C. every other helix builder delivers the full count")
say("  turns are read back two ways: from the wire length, and from the height")
say("  the wire actually spans (ZLength / pitch).")
say("")
say("  %-7s %-11s %-11s %-7s %-11s %-11s %-7s %s", "asked",
    "mkHelix L", "mkHelix Z", "edges", "mkLong L", "mkLong Z", "edges", "r deviation")
for n in (1, 2, 5, 10, 16, 32, 50, 100):
    h = Part.makeHelix(PITCH, PITCH * n, R)
    hl = Part.makeLongHelix(PITCH, PITCH * n, R, 0.0)
    dev = 0.0
    e = hl.Edges[0]
    for k in range(101):
        p = e.valueAt(e.FirstParameter + (e.LastParameter - e.FirstParameter) * k / 100.0)
        dev = max(dev, abs(math.hypot(p.x, p.y) - R))
    say("  %-7d %-11.4f %-11.4f %-7d %-11.4f %-11.4f %-7d %.9f", n,
        turns_of(h, PITCH, R), h.BoundBox.ZLength / PITCH, len(h.Edges),
        turns_of(hl, PITCH, R), hl.BoundBox.ZLength / PITCH, len(hl.Edges), dev)
say("")
say("  Both builders span the full requested height at every count: the geometry")
say("  is right. What breaks past ~32 turns is Shape.Length on makeHelix's single")
say("  analytic edge -- at 100 turns it reports 33.09 turns worth of arc length")
say("  for a curve that plainly spans 100 pitches. makeLongHelix, which emits one")
say("  B-spline edge per turn, measures correctly at every count and stays on the")
say("  cylinder to the deviation shown.")

head("D. a real 32-turn thread, swept and cut, still has the full count")
turns = 32
length = PITCH * turns
t0 = time.perf_counter()
helix = Part.makeHelix(PITCH, length, R)
prof = Part.Wire(Part.makePolygon([Vector(R, 0, -PITCH / 2.0),
                                   Vector(R + 0.65 * PITCH, 0, 0.0),
                                   Vector(R, 0, PITCH / 2.0),
                                   Vector(R, 0, -PITCH / 2.0)]))
ps = Part.BRepOffsetAPI.MakePipeShell(helix)
ps.setFrenetMode(True)
ps.add(prof, True, True)
ps.build()
ps.makeSolid()
tool = ps.shape()
t_sweep = time.perf_counter() - t0
say("  sweep of %d turns: faces = %d isValid = %s volume = %.4f  t = %.3f s",
    turns, len(tool.Faces), tool.isValid(), tool.Volume, t_sweep)
say("  swept ZLength = %.4f mm (asked %.1f) -> %.4f turns",
    tool.BoundBox.ZLength, length, tool.BoundBox.ZLength / PITCH)
t0 = time.perf_counter()
rod = Part.makeCylinder(R, length)
res = rod.fuse(tool)
t_fuse = time.perf_counter() - t0
say("  rod.fuse(thread): faces = %d isValid = %s volume = %.4f  t = %.3f s",
    len(res.Faces), res.isValid(), res.Volume, t_fuse)
say("  seams on the result = %d ; check(True) = %s", len(seam_edges(res)), bop(res))

head("E. so where does 'one turn from seam to seam' come from?")
say("  Part.makeThread is a one-turn primitive and always was; the seam of the")
say("  rod it is meant to be cut from happens to be one turn apart from itself,")
say("  which is why the symptom looks seam-shaped. It is not.")
say("  The seam damage in threads is a different thing entirely -- see script 09.")

done("08_thread_turns")
