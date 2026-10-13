# SPDX-License-Identifier: LGPL-2.1-or-later
"""Data trees in the real FreeCAD GUI: the lofted-rings demo, the grip menu
driven by real right-clicks, Flatten/Simplify, save and reopen, bake.

    freecad.exe tests/tree_smoke.py      (KATYDID_OUT chooses the output dir)
"""

import os
import sys
import time

import FreeCAD
import FreeCADGui
import katydid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__))), "tests"))
from guitest import Qt, QtCore, Run, grip_pos, mouse, pump  # noqa: E402

RIGHT = Qt.MouseButton.RightButton


def right_click(view, pos):
    mouse(view, "press", pos, button=RIGHT)
    mouse(view, "release", pos, button=RIGHT)
    pump(150)
    return view.menu


def trigger(menu, label):
    for act in menu.actions():
        if act.text() == label:
            act.trigger()
            menu.close()
            pump(250)
            return True
    return False


def paths(tree):
    from katydid.tree import format_path
    return [format_path(p) for p in tree.paths()]


def body(run):
    from katydid import feature, gui
    check, res = run.check, run.res
    FreeCADGui.getMainWindow().showMaximized()
    FreeCADGui.activateWorkbench("KatydidWorkbench")
    pump(400)
    panel = gui.show_canvas()
    panel.load_tree_demo()
    pump(600)
    d = panel.demo
    view = panel.view
    states = {c.nickname: (c.state, c.messages) for c in panel.graph.components}
    check("tree_demo_all_ok", all(s == "ok" for s, _ in states.values()), states)
    div = d["divide"].outputs[0].data
    check("divide_branch_per_ring", paths(div) == ["{0;0;0}", "{0;0;1}", "{0;0;2}", "{0;0;3}"]
          and all(len(items) == 6 for _, items in div.branches()), paths(div))
    plines = list(d["polyline"].outputs[0].data)
    check("closed_polyline_per_branch", len(plines) == 4 and all(p.isClosed() for p in plines),
          len(plines))
    lofts = list(d["loft"].outputs[0].data)
    check("one_loft_through_all_rings", len(lofts) == 1 and lofts[0].isValid()
          and len(lofts[0].Faces) == 6, [len(lofts), [len(s.Faces) for s in lofts]])
    check("panel_shows_branches", d["panel"].rows[:2] == [("path", "{0;0;0}"), ("item", 0, d["panel"].rows[1][2])]
          and sum(1 for r in d["panel"].rows if r[0] == "path") == 4, d["panel"].rows[:3])
    wire = next(w for w in panel.scene.wire_items if w.src.param is d["divide"].outputs[0]
                and w.dst.param is d["polyline"].inputs[0])
    check("tree_wire_detected", wire.src.param.data.branch_count == 4)
    FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    pump(300)
    run.grab(None, "01_tree_demo.png")
    run.grab(panel, "02_canvas.png")

    # Right-click the Loft input grip: the real menu, Flatten checked.
    loft_in = d["loft"].inputs[0]
    menu = right_click(view, grip_pos(panel, loft_in))
    flat = next((a for a in menu.actions() if a.text() == "Flatten"), None) if menu else None
    check("grip_menu_opens", menu is not None and menu.isVisible())
    check("menu_shows_flatten_checked", flat is not None and flat.isChecked())
    if menu is not None:
        run.grab(menu, "03_grip_menu.png")
        trigger(menu, "Flatten")  # turn it off
    check("without_flatten_loft_errors", d["loft"].state == "error"
          and any("two section curves" in m for m in d["loft"].messages), d["loft"].messages)
    run.grab(panel, "04_without_flatten.png")
    menu = right_click(view, grip_pos(panel, loft_in))
    trigger(menu, "Flatten")  # back on
    check("flatten_restores_loft", d["loft"].state == "ok" and loft_in.modifier == "flatten")

    # Simplify on the Divide output: {0;0;i} -> {i}
    menu = right_click(view, grip_pos(panel, d["divide"].outputs[0]))
    trigger(menu, "Simplify")
    check("simplify_from_menu", paths(d["divide"].outputs[0].data) == ["{0}", "{1}", "{2}", "{3}"]
          and d["panel"].rows[0] == ("path", "{0}"), paths(d["divide"].outputs[0].data))

    # A right-DRAG still pans and opens no menu.
    view.menu = None
    start = grip_pos(panel, d["divide"].outputs[0])
    before = view.horizontalScrollBar().value()
    mouse(view, "press", start, button=RIGHT)
    for i in range(1, 9):
        mouse(view, "move", start + QtCore.QPoint(i * 10, 0), button=RIGHT)
        pump(5)
    mouse(view, "release", start + QtCore.QPoint(80, 0), button=RIGHT)
    pump(100)
    check("right_drag_pans_without_menu", view.menu is None
          and view.horizontalScrollBar().value() != before)

    # Sliders still drive everything through the tree.
    d["points"].set_value(10)
    d["rings"].set_value(6)
    panel.timings.clear()
    panel.scene.request_solve()
    pump(400)
    lofts = list(d["loft"].outputs[0].data)
    check("sliders_reshape_tree", d["divide"].outputs[0].data.branch_count == 6
          and len(lofts) == 1 and len(lofts[0].Faces) == 10,
          [d["divide"].outputs[0].data.branch_count, [len(s.Faces) for s in lofts]])
    if panel.timings:
        res["solve_preview_ms_6x10"] = [round(v, 2) for v in panel.timings[-1]]

    # Save, close, reopen: the grip settings come back and the loft still solves.
    path = os.path.join(run.out, "tree.FCStd")
    doc = FreeCAD.ActiveDocument
    doc.saveAs(path)
    FreeCADGui.runCommand("Std_Save", 0)
    pump(300)
    name = doc.Name
    FreeCAD.closeDocument(name)
    pump(400)
    doc = FreeCAD.openDocument(path)
    pump(900)
    by_nick = {c.nickname: c for c in panel.graph.components}
    loft, divide = by_nick.get("Loft"), by_nick.get("Divide")
    check("modifiers_saved_and_reopened",
          loft is not None and divide is not None and loft.inputs[0].modifier == "flatten"
          and divide.outputs[0].modifier == "simplify",
          [loft and loft.inputs[0].modifier, divide and divide.outputs[0].modifier])
    check("reopened_loft_solves", loft is not None and loft.state == "ok"
          and len(list(loft.outputs[0].data)) == 1, loft and loft.messages)
    check("modifiers_in_saved_json", feature.find(doc) is not None
          and '"mods"' in feature.read(doc))

    # Bake the loft.
    panel.scene.clearSelection()
    panel.scene.items_by_comp[loft].setSelected(True)
    pump(100)
    baked = panel.bake()
    check("bake_loft", len(baked) == 1 and baked[0].Shape.isValid() and baked[0].Shape.Area > 0,
          [round(o.Shape.Area, 2) for o in baked])
    panel.scene.clearSelection()
    pump(200)
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    pump(200)
    run.grab(None, "05_reopened_baked.png")
    res["took_s"] = round(time.perf_counter() - T0, 1)


T0 = time.perf_counter()
Run("tree").run_later(body)
