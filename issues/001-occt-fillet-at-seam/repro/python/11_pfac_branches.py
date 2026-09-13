# Reproduce pfac1 / pfac2 as PerformOneCorner builds them
#   C1.cxx:783  pfac1 = BRep_Tool::CurveOnSurface(CV1.Arc(),Fv)->Value(CV1.ParameterOnArc())
#   C1.cxx:790  pfac2 = BRep_Tool::CurveOnSurface(CV2.Arc(),Fv)->Value(CV2.ParameterOnArc())
#   C1.cxx:807  if (onsame) ChFi3d_Recale(Bs,pfac1,pfac2,(IFadArc==1));   <-- gated
# and show whether ChFi3d_Recale's trigger |u2-u1| > 0.5*UPeriod fires.
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "common", "python"))
import FreeCAD as App, Part
from FreeCAD import Vector
import seamlib as SL
say = SL.say
R = 1.0   # fillet radius used in the minimal pair

def recale(u1, u2, uper, refon1):
    """ChFi3d_Recale, ChFi3d_Builder_C1.cxx:440-457, u part only."""
    if abs(u2 - u1) > 0.5 * uper:
        if   u2 < u1 and     refon1: u2 += uper
        elif u2 < u1 and not refon1: u1 -= uper
        elif u1 < u2 and     refon1: u2 -= uper
        elif u1 < u2 and not refon1: u1 += uper
    return u1, u2

def run(angle_xu):
    SL.head("AngleXU = %d deg   (fillet radius %.2f)" % (angle_xu, R))
    doc = App.newDocument("p%d" % angle_xu)
    body, pocket, tip, sk = SL.build_fixture(doc, "P%d" % angle_xu, angle_xu)
    sh = SL.solid_of(tip)
    ti, te = SL.target_edge(sh)
    seams = SL.seam_edges(sh)
    s = seams[0]
    Fv = s["face"]                       # face at end = the cylindrical face
    fvi = s["face_idx"]
    # the corner vertex of the filleted edge nearest the seam
    V = min(te.Vertexes, key=lambda v: v.distToShape(s["edge"])[0])
    dseam = V.distToShape(s["edge"])[0]
    say("face at end  Fv = Face%d (%s), UPeriod = %.6f",
        fvi, Fv.Surface.TypeId.split("::")[-1], 2 * math.pi)
    say("corner vertex %s   distance to seam = %.9f mm", SL.fmtv(V.Point), dseam)

    # CV1.Arc(), CV2.Arc(): the two edges of Fv meeting at that vertex,
    # other than the seam itself.
    arcs = []
    for i, e in enumerate(sh.Edges):
        if not any(f.isSame(Fv) for f in sh.ancestorsOfType(e, Part.Face)):
            continue
        if e.isSame(s["edge"]):
            continue
        if any(v.isSame(V) for v in e.Vertexes):
            arcs.append((i + 1, e))
    say("arcs of Fv at that vertex: %s", ", ".join("Edge%d" % i for i, _ in arcs))
    if len(arcs) != 2:
        say("  (expected 2 -- stopping)"); App.closeDocument(doc.Name); return

    us = []
    for label, (ei, e) in zip(("pfac1", "pfac2"), arcs):
        pc, f0, f1 = Fv.curveOnSurface(e)
        # ParameterOnArc: where the fillet boundary lands, R along the edge
        # from the corner vertex; and the corner vertex itself for reference.
        pv = e.Curve.parameter(V.Point)
        Pr = e.valueAt(min(f1, max(f0, pv + (R if abs(pv - f0) < abs(pv - f1) else -R))))
        pr = e.Curve.parameter(Pr)
        say("  %s  Edge%-3d  u(at vertex) = %.6f   u(at %.2f mm along) = %.6f",
            label, ei, pc.value(pv).x, R, pc.value(pr).x)
        us.append((pc.value(pv).x, pc.value(pr).x))

    for what, k in (("at the corner vertex", 0), ("at the fillet's landing points", 1)):
        u1, u2 = us[0][k], us[1][k]
        d = abs(u2 - u1)
        need = d > math.pi
        say("")
        say("  %s:  pfac1.u = %.6f   pfac2.u = %.6f   |du| = %.6f", what, u1, u2, d)
        say("  ChFi3d_Recale trigger |du| > 0.5*UPeriod (=%.6f) : %s",
            math.pi, "YES -- reconciliation REQUIRED" if need else "no")
        if need:
            for refon1 in (True, False):
                a, b = recale(u1, u2, 2 * math.pi, refon1)
                say("    Recale(refon1=%-5s) -> %.6f , %.6f   arc = %.6f rad",
                    refon1, a, b, abs(b - a))
            say("    WITHOUT Recale the arc handed to ChFi3d_ComputeCurves = %.6f rad"
                " (the long way round)", d)
    App.closeDocument(doc.Name)

for a in (0, 90):
    run(a)
SL.done("pfac")
