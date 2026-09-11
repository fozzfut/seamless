import os, math, sys, FreeCAD as App, Part
from FreeCAD import Vector as V

ANG   = float(os.environ.get("SEAM_ANGLE","0"))
RAD   = float(os.environ.get("FIL_R","0.5"))
BX,BY,BZ = 20.0,20.0,10.0
CX,CY,R  = 10.0,10.0,4.0

def make_solid(ang):
    box = Part.makeBox(BX,BY,BZ)
    cyl = Part.makeCylinder(R, BZ+2.0, V(CX,CY,-1.0), V(0,0,1), 360)
    if ang: cyl.rotate(V(CX,CY,0), V(0,0,1), ang)
    s = box.cut(cyl)
    # slot across the rim: splits the rim circle, creating vertices NOT tied to the seam
    if os.environ.get("NOSLOT"):
        return s
    hw = float(os.environ.get("SLOT_HW","0.6"))
    slot = Part.makeBox(BX+2.0, 2*hw, 2.0, V(-1.0, CY-hw, BZ-1.0))
    return s.cut(slot)

def cyl_seam_point(s):
    for f in s.Faces:
        su=f.Surface
        if hasattr(su,'Radius') and abs(su.Radius-R)<1e-9:
            return su.Center + su.Rotation.multVec(V(1,0,0))*su.Radius, f
    return None,None

s = make_solid(ANG)
seampt, cf = cyl_seam_point(s)
print("ANG=%.4f  base_volume=%.6f  base_valid=%s  faces=%d" % (ANG, s.Volume, s.isValid(), len(s.Faces)))
print("seam u=0 point (xy) = (%.6f, %.6f)" % (seampt.x, seampt.y))

# rim arcs: edges at z=BZ lying on the cylinder
cands=[]
for i,e in enumerate(s.Edges):
    if e.Length < 0.05: continue
    if not all(abs(v.Point.z-BZ)<1e-7 for v in e.Vertexes): continue
    mid = e.valueAt((e.FirstParameter+e.LastParameter)/2.0)
    if abs(math.hypot(mid.x-CX, mid.y-CY)-R) > 1e-6: continue
    dmin = min([math.hypot(v.Point.x-seampt.x, v.Point.y-seampt.y) for v in e.Vertexes]) if e.Vertexes else -1
    cands.append((i+1,e,dmin))
    print("  rim Edge%d len=%.4f nVert=%d closed=%s  min-dist(vertex->seam)=%.6f"
          % (i+1, e.Length, len(e.Vertexes), e.isClosed(), dmin))

tgt = os.environ.get("TARGET_EDGE")
if tgt:
    if tgt in ("auto","near","all"):
        if not cands:
            print("NO RIM ARC FOUND"); raise SystemExit
        if tgt=="near":
            c=sorted([c for c in cands if c[1].Length>1.0], key=lambda c:c[2])[0]
            idx=c[0]; dsel=c[2]
        elif tgt=="all":
            idx=-1; dsel=min(c[2] for c in cands)
        else:
            idx=cands[0][0]; dsel=cands[0][2]
    else:
        idx=int(tgt); dsel=[c[2] for c in cands if c[0]==idx][0] if any(c[0]==idx for c in cands) else -1
    print("SELECTED Edge%d  dist(vertex->seam)=%.6f" % (idx,dsel))
    e = [c[1] for c in cands] if idx==-1 else s.Edges[idx-1]
    import time
    t0=time.time()
    try:
        f = s.makeFillet(RAD, e if isinstance(e,list) else [e])
        dt = time.time()-t0
        chk = "n/a"
        try: chk = str(f.check(True))
        except Exception as ex: chk = "check-raised: %s" % ex
        print("FILLET Edge%d r=%.3f  time=%.2fs  valid=%s  volume=%.6f  dVol=%+.6f  BOPcheck=%s"
              % (idx, RAD, dt, f.isValid(), f.Volume, f.Volume-s.Volume, chk))
    except Exception as ex:
        print("FILLET Edge%d r=%.3f  time=%.2fs  RAISED: %s" % (idx, RAD, time.time()-t0, ex))
