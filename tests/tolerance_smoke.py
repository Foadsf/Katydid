# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Stack-up demo (Fischer, Figures 8.9-8.14) in the real FreeCAD GUI.

    freecad.exe tests/tolerance_smoke.py      (KATYDID_OUT chooses the output dir)
"""

import os
import sys

import FreeCAD
import FreeCADGui
import katydid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__))), "tests"))
from guitest import QtCore, Run, app, mouse, pump  # noqa: E402


def first(param):
    return list(param.data)[0]


def body(run):
    from katydid import gui
    check, res = run.check, run.res
    FreeCADGui.getMainWindow().showMaximized()
    FreeCADGui.activateWorkbench("KatydidWorkbench")
    pump(400)
    panel = gui.show_canvas()
    panel.load_stackup_demo()
    pump(900)
    d = panel.demo
    bad = {c.nickname: c.messages for c in panel.graph.components if c.state != "ok"}
    check("stackup_all_ok", not bad, bad)
    s = d["stack"].outputs
    check("fischer_figure_8_9_numbers", round(first(s[0]), 4) == 11.5 and round(first(s[1]), 4) == 3.5
          and round(first(s[2]), 2) == 1.94, [first(s[0]), first(s[1]), first(s[2])])
    report = d["report"].text_lines
    check("report_in_panel", len(report) == 8 and "Worst case" in report[5], report)
    pct_before = first(d["mc"].outputs[2])
    check("monte_carlo_out_of_spec", 1.0 < pct_before < 3.0, pct_before)
    check("histogram_in_panel", len(d["hist"].text_lines) == 16)
    run.grab(None, "01_stackup.png")
    run.grab(panel, "02_canvas.png")

    # Tighten the 56.5 tolerance by dragging its slider left with the real mouse.
    view = panel.view
    item = panel.scene.items_by_comp[d["tol"]]
    knob = view.mapFromScene(item.mapToScene(QtCore.QPointF(item.knob_x(), item.h / 2)))
    mouse(view, "press", knob)
    for i in range(1, 21):
        mouse(view, "move", knob - QtCore.QPoint(i * 4, 0))
        app.processEvents()
    mouse(view, "release", knob - QtCore.QPoint(80, 0))
    pump(500)
    tol = d["tol"].value
    wc_after = first(s[1])
    pct_after = first(d["mc"].outputs[2])
    check("slider_drives_stack", tol < 1.5 and abs(wc_after - (tol + 2.0)) < 1e-9, [tol, wc_after])
    check("tighter_tolerance_fewer_rejects", pct_after < pct_before, [pct_before, pct_after])
    res["after_drag"] = {"tol": tol, "worst_case": wc_after, "out_of_spec_pct": pct_after}
    run.grab(panel, "03_after_drag.png")

    # Save, close, reopen: same answers, panel sizes kept.
    path = os.path.join(run.out, "stackup.FCStd")
    doc = FreeCAD.ActiveDocument
    doc.saveAs(path)
    FreeCADGui.runCommand("Std_Save", 0)
    pump(300)
    FreeCAD.closeDocument(doc.Name)
    pump(400)
    FreeCAD.openDocument(path)
    pump(1200)
    by = {c.nickname: c for c in panel.graph.components}
    stack = by.get("Stack")
    panels = sorted(tuple(c.size) for c in panel.graph.components if hasattr(c, "size"))
    check("reopened_same_worst_case", stack is not None and abs(first(stack.outputs[1]) - wc_after) < 1e-9)
    check("reopened_panel_sizes", panels == sorted([(470, 150), (330, 290), (190, 80)]), panels)
    run.grab(panel, "04_reopened.png")


Run("tolerance").run_later(body)
