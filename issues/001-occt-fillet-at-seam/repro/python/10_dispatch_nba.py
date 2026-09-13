# Reproduce OCCT ChFi3d_NumberOfSharpEdges(Vtx, myVEMap, myEFMap) from Python.
# Settles which corner function the failing fillet dispatches to:
#   ChFi3d_Builder.cxx:690  if(nba>3) PerformIntersectionAtEnd else PerformOneCorner
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))
import FreeCAD as App, Part
from FreeCAD import Vector
import seamlib as SL
say = SL.say

def occurrences(shape):
    """TopExp_Explorer(S, TopAbs_EDGE) order, WITH duplicates.
    TopExp_Explorer keeps no map (src/TopExp/TopExp_Explorer.hxx has no member
    map), so every (face, wire, edge) occurrence is visited."""
    occ = []
    for fi, f in enumerate(shape.Faces):
        for w in f.Wires:
            for e in w.OrderedEdges:
                occ.append((fi, f, e))
    return occ

def same_edge(a, b):
    return a.isSame(b)

def conexfaces(e, occ):
    """ChFi3d_conexfaces, ChFi3d_Builder_0.cxx:296"""
    F1 = F2 = None; f1i = f2i = None
    for fi, f, ee in occ:
        if not same_edge(ee, e):
            continue
        if F1 is None:
            F1, f1i = f, fi
        else:
            F2, f2i = f, fi
            closed = len(set(k for k, _, x in occ if same_edge(x, e))) == 1
            if (not F2.isSame(F1)) or closed:
                break
            F2 = None; f2i = None
    return F1, f1i, F2, f2i

def tangency(e, F1, F2):
    """Measure what ChFi3d::IsTangentFaces(e,F1,F2,GeomAbs_G2) measures:
    G1 = normals agree, G2 = principal curvatures agree, along the edge."""
    t0, t1 = e.ParameterRange if hasattr(e, "ParameterRange") else (e.FirstParameter, e.LastParameter)
    maxdn = 0.0; maxdk = 0.0; n = 0
    for i in range(5):
        t = t0 + (t1 - t0) * i / 4.0
        try:
            P = e.valueAt(t)
        except Exception:
            continue
        try:
            u1, v1 = F1.Surface.parameter(P)
            u2, v2 = F2.Surface.parameter(P)
        except Exception:
            continue
        n1 = F1.Surface.normal(u1, v1); n2 = F2.Surface.normal(u2, v2)
        maxdn = max(maxdn, abs(1.0 - abs(n1.dot(n2))))
        try:
            k1 = F1.Surface.curvature(u1, v1, "Max"); K1 = F1.Surface.curvature(u1, v1, "Min")
            k2 = F2.Surface.curvature(u2, v2, "Max"); K2 = F2.Surface.curvature(u2, v2, "Min")
            maxdk = max(maxdk, abs(k1 - k2), abs(K1 - K2))
        except Exception:
            pass
        n += 1
    if n == 0:
        return None, None, "unmeasured"
    g1 = maxdn < 1e-7
    g2 = g1 and maxdk < 1e-7
    return maxdn, maxdk, ("G2" if g2 else ("G1-only" if g1 else "sharp"))

def analyse(angle_xu):
    SL.head("AngleXU = %d deg" % angle_xu)
    doc = App.newDocument("d%d" % angle_xu)
    body, pocket, tip, sk = SL.build_fixture(doc, "T%d" % angle_xu, angle_xu)
    sh = SL.solid_of(tip)
    ti, te = SL.target_edge(sh)
    say("target edge  Edge%d  length %.6f", ti, te.Length)
    seams = SL.seam_edges(sh)
    for s in seams:
        say("seam         Edge%d on Face%d (%s)", s["edge_idx"], s["face_idx"],
            s["surf"].TypeId.split("::")[-1])
    # the end vertex of the filleted edge that is nearest a seam
    best = None
    for vi, v in enumerate(te.Vertexes):
        for s in seams:
            d = v.distToShape(s["edge"])[0]
            if best is None or d < best[0]:
                best = (d, v, s)
    d, V, s = best
    say("filleted-edge end vertex at %s, distance to seam Edge%d = %.9f mm",
        SL.fmtv(V.Point), s["edge_idx"], d)

    occ = occurrences(sh)
    # VEMap(Vtx): every edge occurrence having V among its vertices
    entries = []
    for fi, f, e in occ:
        for vv in e.Vertexes:
            if vv.isSame(V):
                entries.append((fi, f, e))
                break
    say("")
    say("VEMap(Vtx).Extent() = %d   (ChFi3d_NbSharpEdges, Builder_0.cxx:4554)", len(entries))
    nba = len(entries)
    for k, (fi, f, e) in enumerate(entries):
        ei = [j + 1 for j, x in enumerate(sh.Edges) if x.isSame(e)]
        ei = ei[0] if ei else -1
        deg = getattr(e, "Degenerated", False)
        if deg:
            nba -= 1
            say("  [%d] Edge%-3d on Face%-2d  DEGENERATE            -> nba--", k, ei, fi + 1)
            continue
        F1, f1i, F2, f2i = conexfaces(e, occ)
        if F2 is None:
            say("  [%d] Edge%-3d on Face%-2d  F2 null                -> kept", k, ei, fi + 1)
            continue
        dn, dk, verdict = tangency(e, F1, F2)
        isseam = F1.isSame(F2)
        mark = ""
        if verdict == "G2":
            nba -= 1
            mark = "-> nba--"
        say("  [%d] Edge%-3d F%d/F%d %-6s dNormal=%.2e dCurv=%.2e %-8s %s",
            k, ei, f1i + 1, (f2i + 1), ("SEAM" if isseam else ""),
            (dn if dn is not None else -1), (dk if dk is not None else -1), verdict, mark)
    # ChFi3d_ChercheBordsLibres: closed solid -> no free boundary
    say("")
    say("after tangency decrements: %d ; closed solid -> bordlibre = False -> nba = %d",
        nba, nba // 2)
    nba2 = nba // 2
    say("DISPATCH  ChFi3d_Builder.cxx:690  nba=%d  -> %s", nba2,
        "PerformIntersectionAtEnd  (NO ChFi3d_Recale, NO seam split)" if nba2 > 3
        else "PerformOneCorner / PerformMoreSurfdata")
    App.closeDocument(doc.Name)
    return nba2

for a in (0, 90):
    analyse(a)
SL.done("nba")
