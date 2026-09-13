import os, math, FreeCAD, Part
from FreeCAD import Vector as V
BX,BY,BZ=20.0,20.0,10.0; CX,CY,R=10.0,10.0,4.0
def mk(ang):
    box=Part.makeBox(BX,BY,BZ)
    cyl=Part.makeCylinder(R,BZ+2.0,V(CX,CY,-1.0),V(0,0,1),360)
    if ang: cyl.rotate(V(CX,CY,0),V(0,0,1),ang)
    s=box.cut(cyl)
    slot=Part.makeBox(BX+2.0,1.2,2.0,V(-1.0,CY-0.6,BZ-1.0))
    return s.cut(slot)
def seampt(s):
    for f in s.Faces:
        su=f.Surface
        if hasattr(su,'Radius') and abs(su.Radius-R)<1e-9:
            return su.Center+su.Rotation.multVec(V(1,0,0))*su.Radius
    return None
def pick(s,sp):
    best=None
    for e in s.Edges:
        if e.Length<1.0: continue
        if not all(abs(v.Point.z-BZ)<1e-7 for v in e.Vertexes): continue
        m=e.valueAt((e.FirstParameter+e.LastParameter)/2.0)
        if abs(math.hypot(m.x-CX,m.y-CY)-R)>1e-6: continue
        d=min(math.hypot(v.Point.x-sp.x,v.Point.y-sp.y) for v in e.Vertexes)
        if best is None or d<best[0]: best=(d,e)
    return best
for ang in (6.0, 90.0):
    s=mk(ang); sp=seampt(s); d,e=pick(s,sp)
    print("="*70); print("ANG=%.5f  dist(vertex->seam)=%.6f"%(ang,d))
    try:
        f=s.makeFillet(2.0,[e])
    except Exception as ex:
        print("  fillet RAISED: %s"%ex); continue
    print("  fillet done: valid=%s vol=%.6f dVol=%+.6f"%(f.isValid(), f.Volume, f.Volume-s.Volume))
    for i,fc in enumerate(f.Faces):
        su=fc.Surface
        if not (hasattr(su,'Radius') and abs(su.Radius-R)<1e-9): continue
        u0,u1,v0,v1=fc.ParameterRange
        print("  cylindrical Face%d  u-range=[%.6f, %.6f]  span=%.6f (2pi=%.6f)  v=[%.3f,%.3f]"
              %(i+1,u0,u1,u1-u0,2*math.pi,v0,v1))
        for j,ed in enumerate(fc.Edges):
            try:
                cs=fc.curveOnSurface(ed)
            except Exception:
                cs=None
            if cs is None: continue
            c2d,a,b=cs[0],cs[1],cs[2]
            p0=c2d.value(a); p1=c2d.value(b)
            print("     edge%d pcurve %s u:[%.6f -> %.6f]  v:[%.3f -> %.3f]"
                  %(j+1,type(c2d).__name__,p0.x,p1.x,p0.y,p1.y))
