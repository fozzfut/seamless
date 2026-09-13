import os, FreeCAD, Part
from FreeCAD import Vector as V
BX,BY,BZ=20.0,20.0,10.0; CX,CY,R=10.0,10.0,4.0
def mk(ang):
    box=Part.makeBox(BX,BY,BZ)
    cyl=Part.makeCylinder(R,BZ+2.0,V(CX,CY,-1.0),V(0,0,1),360)
    if ang: cyl.rotate(V(CX,CY,0),V(0,0,1),ang)
    s=box.cut(cyl)
    slot=Part.makeBox(BX+2.0,1.2,2.0,V(-1.0,CY-0.6,BZ-1.0))
    return s.cut(slot)
a=mk(6.0); b=mk(90.0)
print("vol(ANG=6)  = %.12f" % a.Volume)
print("vol(ANG=90) = %.12f" % b.Volume)
print("a.cut(b).Volume = %.12f" % a.cut(b).Volume)
print("b.cut(a).Volume = %.12f" % b.cut(a).Volume)
print("same solid:", abs(a.cut(b).Volume)<1e-9 and abs(b.cut(a).Volume)<1e-9)
