"""03 -- the minimal pair, and the distance at which a fillet breaks.

Two bodies that differ in ONE number: the parameter origin of the profile
circle of the pocket (AngleXU).  Rotating a full circle about its own axis
does not move a single point of it, so both bodies are the same region of
space -- proved here by cutting each with the other and getting 0.000000000000
both ways.  The only difference is where the seam of the pocket's cylindrical
face lands.

  * seam far from the end vertex of the filleted edge -> the fillet is correct;
  * seam ON that vertex                               -> the volume GROWS.

Then a sweep of AngleXU maps distance(seam, filleted edge) to the verdict, so
the width of the danger band is a measured number, not a guess.

Run:  "C:/Program Files/FreeCAD 1.1/bin/FreeCADCmd.exe" 03_minimal_pair.py
"""

import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import FreeCAD as App
import Part
from seamlib import (bop, build_fixture, chamfer_removed, done, fillet_removed,
                     fmtv, head, say, seam_edges, solid_of, target_edge)

RADIUS = 1.0

doc = App.newDocument("P03")


def case(tag, angle_xu):
    body, pocket, tip, sk = build_fixture(doc, tag, angle_xu, prefillet=False)
    return solid_of(tip)


head("A. the two bodies are the same solid")
shapes = {}
for tag, ang in (("A0", 0.0), ("A90", 90.0)):
    shapes[ang] = case(tag, ang)
for ang, sh in sorted(shapes.items()):
    say("  AngleXU = %5.1f deg: volume = %.9f  area = %.9f  faces = %d edges = %d",
        ang, sh.Volume, sh.Area, len(sh.Faces), len(sh.Edges))
    say("      isValid() = %s   check(True) = %s", sh.isValid(), bop(sh))
a, b = shapes[0.0], shapes[90.0]
say("  A0.cut(A90).Volume  = %.12f", a.cut(b).Volume)
say("  A90.cut(A0).Volume  = %.12f", b.cut(a).Volume)
say("  -> neither solid contains a point the other does not: the SAME region.")

head("B. where the seam sits in each of them")
for ang, sh in sorted(shapes.items()):
    for d in seam_edges(sh):
        e = d["edge"]
        say("  AngleXU = %5.1f deg: seam Edge%d on Face%d (%s) from %s to %s",
            ang, d["edge_idx"], d["face_idx"], d["surf"].TypeId.replace("Part::Geom", ""),
            fmtv(e.valueAt(e.FirstParameter)), fmtv(e.valueAt(e.LastParameter)))

head("C. the edge we fillet is byte-for-byte the same edge in both")
for ang, sh in sorted(shapes.items()):
    idx, e = target_edge(sh)
    say("  AngleXU = %5.1f deg: Edge%d length = %.9f  from %s to %s",
        ang, idx, e.Length, fmtv(e.valueAt(e.FirstParameter)), fmtv(e.valueAt(e.LastParameter)))

head("D. the same fillet on the same edge of the same solid")
for ang, sh in sorted(shapes.items()):
    idx, e = target_edge(sh)
    seams = seam_edges(sh)
    dist = min(e.distToShape(d["edge"])[0] for d in seams)
    expect = fillet_removed(RADIUS, e.Length)
    t0 = time.perf_counter()
    try:
        res = sh.makeFillet(RADIUS, [e])
        dt = time.perf_counter() - t0
        say("  AngleXU = %5.1f deg  dist(seam, edge) = %11.9f mm", ang, dist)
        say("      makeFillet(%.2f) -> isValid() = %-5s volume %.4f -> %.4f",
            RADIUS, res.isValid(), sh.Volume, res.Volume)
        say("      removed = %+10.4f mm3   analytic (1 - pi/4)*r^2*L = %+.4f mm3",
            sh.Volume - res.Volume, expect)
        say("      check(True) = %s      t = %.3f s", bop(res), dt)
    except Exception as exc:
        say("  AngleXU = %5.1f deg  dist = %.9f  makeFillet RAISED %s (t = %.3f s)",
            ang, dist, str(exc)[:90], time.perf_counter() - t0)

head("E. control: a chamfer of the same size on the same edge is unharmed")
for ang, sh in sorted(shapes.items()):
    idx, e = target_edge(sh)
    expect = chamfer_removed(RADIUS, e.Length)
    try:
        res = sh.makeChamfer(RADIUS, [e])
        say("  AngleXU = %5.1f deg  makeChamfer(%.2f) -> isValid() = %-5s removed = %+.4f mm3 "
            "(analytic %.4f) check = %s", ang, RADIUS, res.isValid(),
            sh.Volume - res.Volume, expect, bop(res))
    except Exception as exc:
        say("  AngleXU = %5.1f deg  makeChamfer RAISED %s", ang, str(exc)[:90])
say("  -> only the fillet is affected; the defect is in the fillet code path.")

head("F. sweep: distance(seam, filleted edge) vs the verdict (r = %.2f)" % RADIUS)
say("  %-9s %-13s %-7s %-12s %-12s %s", "AngleXU", "dist(mm)", "valid", "volume", "removed", "check(True)")
rows = []
for ang in (0.0, 45.0, 60.0, 75.0, 80.0, 82.0, 84.0, 85.0, 86.0, 87.0, 88.0, 89.0,
            90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 100.0, 135.0, 180.0, 270.0):
    sh = case("S%d" % int(ang * 10), ang)
    idx, e = target_edge(sh)
    seams = seam_edges(sh)
    dist = min(e.distToShape(d["edge"])[0] for d in seams)
    try:
        res = sh.makeFillet(RADIUS, [e])
        ok, vol, removed = res.isValid(), res.Volume, sh.Volume - res.Volume
        chk = bop(res)
    except Exception as exc:
        ok, vol, removed, chk = "RAISED", float("nan"), float("nan"), str(exc)[:40]
    rows.append((ang, dist, ok, removed))
    say("  %7.1f   %11.6f  %-7s %12.4f %+12.4f %s", ang, dist, ok, vol, removed, chk)

good = [r for r in rows if r[2] is True]
bad = [r for r in rows if r[2] is not True]
if bad:
    say("")
    say("  broken at distances: %s", ", ".join("%.6f" % r[1] for r in bad))
    say("  intact  at distances: %s", ", ".join("%.6f" % r[1] for r in good))
    say("  widest broken distance = %.6f mm ; narrowest intact distance = %.6f mm",
        max(r[1] for r in bad), min(r[1] for r in good))
    say("  -> with r = %.2f mm the fillet fails while the seam endpoint is closer", RADIUS)
    say("     than about %.2f mm to the end vertex of the filleted edge.",
        min(r[1] for r in good))

head("G. does the danger band scale with the fillet radius?")
say("  classification: OK      = isValid True, check(True) clean, removed within 2% of analytic")
say("                  SILENT  = isValid True but check(True) dirty -- the lie of isValid()")
say("                  OFF     = isValid True, check clean, but removed off by more than 2%")
say("                  BROKEN  = isValid False")
say("")
say("  %-7s %-10s %-10s %-12s %-12s %s", "r", "band lo", "band hi", "max broken",
    "min intact", "verdict")


def verdict(sh, edge, r):
    expect = fillet_removed(r, edge.Length)
    try:
        res = sh.makeFillet(r, [edge])
    except Exception as exc:
        return "RAISED", float("nan")
    removed = sh.Volume - res.Volume
    if not res.isValid():
        return "BROKEN", removed
    if bop(res) != "clean":
        return "SILENT", removed
    if abs(removed - expect) > 0.02 * abs(expect):
        return "OFF", removed
    return "OK", removed


for r in (0.25, 0.5, 1.0, 2.0):
    bad_angles, bad_dists, good_dists = [], [], []
    for ang10 in range(600, 1205, 10):
        ang = ang10 / 10.0
        sh = case("G%d_%d" % (int(r * 100), ang10), ang)
        idx, e = target_edge(sh)
        dist = min(e.distToShape(d["edge"])[0] for d in seam_edges(sh))
        kind, removed = verdict(sh, e, r)
        if kind in ("OK", "OFF"):
            good_dists.append(dist)
        else:
            bad_angles.append((ang, kind))
            bad_dists.append(dist)
    if bad_angles:
        say("  %-7.2f %-10.1f %-10.1f %-12.6f %-12.6f %s", r,
            bad_angles[0][0], bad_angles[-1][0], max(bad_dists),
            min(d for d in good_dists if d > max(bad_dists)) if any(d > max(bad_dists) for d in good_dists) else float("nan"),
            ",".join(sorted(set(k for _a, k in bad_angles))))
    else:
        say("  %-7.2f %-10s %-10s %-12s %-12s %s", r, "-", "-", "-", "-", "no failure in 60..120 deg")
say("")
say("  control -- the same radius with the seam far away (AngleXU = 0 and 180):")
for r in (0.25, 0.5, 1.0, 2.0, 3.0):
    for ang in (0.0, 180.0):
        sh = case("K%d_%d" % (int(r * 100), int(ang)), ang)
        idx, e = target_edge(sh)
        dist = min(e.distToShape(d["edge"])[0] for d in seam_edges(sh))
        kind, removed = verdict(sh, e, r)
        say("    r = %-5.2f AngleXU = %5.1f  dist = %9.6f  %-7s removed = %+.4f (analytic %+.4f)",
            r, ang, dist, kind, removed, fillet_removed(r, e.Length))
say("")
say("  per-angle detail for each radius:")
for r in (0.25, 0.5, 1.0, 2.0):
    line = []
    for ang10 in range(820, 1005, 10):
        ang = ang10 / 10.0
        sh = case("H%d_%d" % (int(r * 100), ang10), ang)
        idx, e = target_edge(sh)
        kind, removed = verdict(sh, e, r)
        line.append("%d:%s" % (int(ang), {"OK": ".", "OFF": "o", "SILENT": "s", "BROKEN": "X", "RAISED": "!"}[kind]))
    say("    r = %-5.2f  %s", r, " ".join(line))
say("    legend: . OK   o volume off >2%   s isValid True but BOP dirty   X invalid   ! raised")

App.closeDocument(doc.Name)
done("03_minimal_pair")
