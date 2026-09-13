# Measures how PartDesign::Boolean treats a target body that has a placement.
#
#   "<FreeCAD>/bin/FreeCADCmd.exe" boolean_placed_target.py
#
# Target: a 20 x 20 x 10 box body. Tool: a 10 x 10 x 30 box body through the target's middle,
# added with Boolean.addObjects. Measured 13 September 2026 on FreeCAD 1.1.1: with the target
# placed at (30,0,0) a Cut with the tool in WORLD coordinates removes nothing (4000.0000 instead
# of 3000.0000) and a Fuse gives 2 disjoint solids (7000.0000 instead of 6000.0000), all
# 'Up-to-date'; the same tool placed in the target's LOCAL frame gives the right answer.
#
# The table is written to stdout and to boolean_placed_target.txt in the system temp directory,
# because FreeCADCmd does not always pass a script's stdout through.
import io
import os
import sys
import tempfile

import FreeCAD as App

V = App.Vector
REPORT = io.open(os.path.join(tempfile.gettempdir(), "boolean_placed_target.txt"), "w", encoding="utf-8")


def say(text):
    REPORT.write(text + "\n")
    REPORT.flush()
    sys.stdout.write(text + "\n")


def case(tag, operation, target_placement, tool_frame):
    doc = App.newDocument("BooleanPlaced")
    target = doc.addObject("PartDesign::Body", "Target")
    target.Placement = target_placement
    box = target.newObject("PartDesign::AdditiveBox", "Box")
    box.Length, box.Width, box.Height = 20, 20, 10
    tool = doc.addObject("PartDesign::Body", "Tool")
    tool_box = tool.newObject("PartDesign::AdditiveBox", "ToolBox")
    tool_box.Length, tool_box.Width, tool_box.Height = 10, 10, 30
    if tool_frame == "world":
        tool.Placement = App.Placement(target_placement.multVec(V(5, 5, -10)), target_placement.Rotation)
    else:
        tool.Placement = App.Placement(V(5, 5, -10), App.Rotation())
    doc.recompute()
    boolean = target.newObject("PartDesign::Boolean", operation)
    boolean.Type = operation
    boolean.addObjects([tool])
    doc.recompute()
    shape = target.Shape
    say("%-44s state=%s solids=%d vol=%.4f"
        % (tag, boolean.State, len(shape.Solids), shape.Volume))
    App.closeDocument(doc.Name)


try:
    placed = App.Placement(V(30, 0, 0), App.Rotation())
    say("FreeCAD %s" % ".".join(App.Version()[:3]))
    say("expected: Cut 3000.0000 with 1 solid; Fuse of overlapping boxes 6000.0000 with 1 solid")
    case("Cut  control, no placement, tool world", "Cut", App.Placement(), "world")
    case("Cut  target at (30,0,0), tool in WORLD", "Cut", placed, "world")
    case("Cut  target at (30,0,0), tool TARGET-LOCAL", "Cut", placed, "target-local")
    case("Fuse control, no placement, tool world", "Fuse", App.Placement(), "world")
    case("Fuse target at (30,0,0), tool in WORLD", "Fuse", placed, "world")
    case("Fuse target at (30,0,0), tool TARGET-LOCAL", "Fuse", placed, "target-local")
finally:
    REPORT.close()
