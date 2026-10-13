# SPDX-License-Identifier: LGPL-2.1-or-later
"""The attractor grid in the real FreeCAD GUI: builds, previews, follows a slider
dragged with real mouse events, survives save and reopen, and the ribbon and
search expose the whole library.

    freecad.exe tests/attractor_smoke.py      (KATYDID_OUT chooses the output dir)
"""

import os
import sys

import FreeCAD
import FreeCADGui
import katydid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__))), "tests"))
from guitest import Qt, QtCore, Run, app, empty_spot, mouse, pump  # noqa: E402


def smallest_circle_center(comp):
    circles = list(comp.outputs[0].data)
    return min(circles, key=lambda e: e.Curve.Radius).Curve.Center


def body(run):
    from katydid import components as lib
    from katydid import gui
    from PySide6 import QtTest
    check, res = run.check, run.res
    FreeCADGui.getMainWindow().showMaximized()
    FreeCADGui.activateWorkbench("KatydidWorkbench")
    pump(400)
    panel = gui.show_canvas()

    buttons = sum(panel.ribbon.widget(i).layout().count() - 1 for i in range(panel.ribbon.count()))
    check("ribbon_has_whole_library", buttons == len(lib.REGISTRY) and panel.ribbon.count() == len(lib.CATEGORIES),
          [buttons, len(lib.REGISTRY), panel.ribbon.count()])

    panel.load_attractor_demo()
    pump(800)
    d = panel.demo
    bad = {c.nickname: c.messages for c in panel.graph.components if c.state != "ok"}
    check("attractor_all_ok", not bad, bad)
    tubes = list(d["extrude"].outputs[0].data)
    check("hundred_tubes", len(tubes) == 100, len(tubes))
    check("grid_is_ten_branches", d["grid"].outputs[0].data.branch_count == 10)
    check("preview_attached", panel.preview._doc is not None)
    FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    pump(300)
    run.grab(None, "01_attractor.png")
    run.grab(panel, "02_canvas.png")
    FreeCADGui.ActiveDocument.ActiveView.saveImage(os.path.join(run.out, "05_view3d.png"), 1200, 700, "Current")

    # Drag "Attractor X" with real mouse events: the small circles must follow.
    view = panel.view
    before = smallest_circle_center(d["circle"])
    item = panel.scene.items_by_comp[d["ax"]]
    knob = view.mapFromScene(item.mapToScene(QtCore.QPointF(item.knob_x(), item.h / 2)))
    panel.timings.clear()
    mouse(view, "press", knob)
    for i in range(1, 31):
        mouse(view, "move", knob + QtCore.QPoint(i * 3, 0))
        app.processEvents()
    mouse(view, "release", knob + QtCore.QPoint(90, 0))
    pump(300)
    after = smallest_circle_center(d["circle"])
    target = FreeCAD.Vector(d["ax"].value, d["ay"].value, 0)
    nearest = min(d["grid"].outputs[0].data, key=lambda p: (p.Point - target).Length).Point
    check("small_circles_follow_the_attractor", after.x > before.x and (after - nearest).Length < 1e-6,
          [round(before.x, 2), round(after.x, 2), d["ax"].value])
    if panel.timings:
        res["solve_preview_ms_median"] = [round(sorted(t[i] for t in panel.timings)[len(panel.timings) // 2], 1)
                                          for i in (0, 1)]
    run.grab(None, "03_after_drag.png")

    # Search finds the new components.
    empty = empty_spot(view)
    mouse(view, "press", empty)
    mouse(view, "release", empty)
    mouse(view, "double", empty)
    mouse(view, "release", empty)
    pump(150)
    popup = view._search
    found = []
    if popup is not None:
        QtTest.QTest.keyClicks(popup.edit, "remap")
        pump(50)
        found = [popup.list.item(i).text() for i in range(popup.list.count())]
        QtTest.QTest.keyClick(popup.edit, Qt.Key.Key_Escape)
        pump(100)
    check("search_finds_new_components", any("Remap" in f for f in found), found)

    # Save, close, reopen: same radii, graft and flatten still set.
    radii = sorted(round(r, 6) for r in d["remap"].outputs[0].data)
    path = os.path.join(run.out, "attractor.FCStd")
    doc = FreeCAD.ActiveDocument
    doc.saveAs(path)
    FreeCADGui.runCommand("Std_Save", 0)
    pump(300)
    FreeCAD.closeDocument(doc.Name)
    pump(400)
    FreeCAD.openDocument(path)
    pump(1000)
    by = {c.nickname: c for c in panel.graph.components}
    grid, remap, bounds = by.get("Grid"), by.get("ReMap"), by.get("Bnd")
    check("reopened_same_radii", remap is not None
          and sorted(round(r, 6) for r in remap.outputs[0].data) == radii)
    check("reopened_modifiers", grid is not None and bounds is not None
          and grid.inputs[1].modifier == "graft" and bounds.inputs[0].modifier == "flatten")
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    pump(300)
    run.grab(None, "04_reopened.png")


Run("attractor").run_later(body)
