# SPDX-License-Identifier: LGPL-2.1-or-later
"""End-to-end smoke test inside the real FreeCAD GUI.

    freecad.exe tests/gui_smoke.py      (set KATYDID_OUT to choose the output dir)

Drives the canvas with real Qt mouse/key events, measures the slider-to-preview
loop, bakes, writes screenshots plus results.json, then exits without saving.
"""

import json
import os
import statistics
import sys
import tempfile
import time
import traceback

import FreeCAD
import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

try:  # FreeCAD may run this as a macro without __file__
    _RUNS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "_runs")
except NameError:
    _RUNS = tempfile.gettempdir()
OUT = os.environ.get("KATYDID_OUT") or os.path.join(_RUNS, time.strftime("smoke_%Y%m%d_%H%M%S"))
os.makedirs(OUT, exist_ok=True)
sys.stderr = open(os.path.join(OUT, "stderr.txt"), "w", encoding="utf-8")
Qt = QtCore.Qt
app = QtWidgets.QApplication.instance()
res = {"out": OUT, "checks": {}}


def pump(ms=150):
    end = time.perf_counter() + ms / 1000.0
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.005)


def check(name, ok, detail=None):
    res["checks"][name] = {"ok": bool(ok), "detail": detail}


def mouse(view, kind, pos, buttons=Qt.MouseButton.LeftButton, mods=Qt.KeyboardModifier.NoModifier):
    types = {"press": QtCore.QEvent.Type.MouseButtonPress, "move": QtCore.QEvent.Type.MouseMove,
             "release": QtCore.QEvent.Type.MouseButtonRelease,
             "double": QtCore.QEvent.Type.MouseButtonDblClick}
    button = Qt.MouseButton.NoButton if kind == "move" else Qt.MouseButton.LeftButton
    held = Qt.MouseButton.NoButton if kind == "release" else buttons
    vp = view.viewport()
    local = QtCore.QPointF(pos)
    ev = QtGui.QMouseEvent(types[kind], local, QtCore.QPointF(vp.mapToGlobal(pos)), button, held, mods)
    QtWidgets.QApplication.sendEvent(vp, ev)


def drag(view, a, b, steps=12, mods=Qt.KeyboardModifier.NoModifier):
    mouse(view, "press", a, mods=mods)
    for i in range(1, steps + 1):
        p = a + (b - a) * i / steps
        mouse(view, "move", QtCore.QPoint(int(p.x()), int(p.y())), mods=mods)
        pump(5)
    mouse(view, "release", b, mods=mods)
    pump(80)


def grip_pos(panel, param):
    grip = panel.scene.grip(param)
    return panel.view.mapFromScene(grip.scenePos())


def grab(widget, name):
    """Grab a widget; None composes the main window with the floating canvas on top.
    Widgets are rendered, never the screen, so other windows are never captured."""
    path = os.path.join(OUT, name)
    if widget is None:
        from katydid import gui
        mw = FreeCADGui.getMainWindow()
        pm = mw.grab()
        dock = gui._dock
        if dock is not None and dock.isFloating() and dock.isVisible():
            painter = QtGui.QPainter(pm)
            painter.drawPixmap(mw.mapFromGlobal(dock.frameGeometry().topLeft()), dock.grab())
            painter.end()
    else:
        pm = widget.grab()
    ok = pm.save(path, "PNG")
    res.setdefault("grabs", {})[name] = {"saved": ok, "size": [pm.width(), pm.height()]}
    return path


def profile_loop(panel, slider, n=30):
    """Split one slider update into its costs: solve+preview, canvas paint, 3D paint."""
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    gl = [w for w in FreeCADGui.getMainWindow().findChildren(QOpenGLWidget) if w.isVisible()]
    parts = {"solve": [], "preview": [], "canvas_paint": [], "view3d_paint": []}
    for i in range(n):
        slider.set_value(slider.minimum + (i % 10 + 1) * (slider.maximum - slider.minimum) / 12)
        panel.timings.clear()
        panel.scene.solve_now()
        solve, preview = panel.timings[-1]
        parts["solve"].append(solve)
        parts["preview"].append(preview)
        t0 = time.perf_counter()
        panel.view.viewport().repaint()
        parts["canvas_paint"].append((time.perf_counter() - t0) * 1000)
        t0 = time.perf_counter()
        for w in gl:
            w.repaint()
        parts["view3d_paint"].append((time.perf_counter() - t0) * 1000)
    return {k: round(statistics.median(v), 2) for k, v in parts.items()} | {"gl_widgets": len(gl)}


def drag_bench(panel, slider, steps=40):
    """Median ms per real mouse-move step while dragging a slider knob."""
    view = panel.view
    item = panel.scene.items_by_comp[slider]
    slider.set_value(slider.minimum)
    panel.scene.solve_now()
    pump(100)
    knob = view.mapFromScene(item.mapToScene(QtCore.QPointF(item.knob_x(), item.h / 2)))
    mouse(view, "press", knob)
    pump(30)
    times = []
    for i in range(1, steps + 1):
        t0 = time.perf_counter()
        mouse(view, "move", knob + QtCore.QPoint(i * 3, 0))
        app.processEvents()
        times.append((time.perf_counter() - t0) * 1000.0)
    mouse(view, "release", knob + QtCore.QPoint(steps * 3, 0))
    pump(100)
    return round(statistics.median(times), 2)


def experiments(panel):
    """Where does the frame time go? Floating (default) versus docked canvas."""
    from katydid import gui
    slider = panel.demo["spacing"]
    out = {"floating": drag_bench(panel, slider)}
    gui._dock.setFloating(False)
    pump(400)
    out["docked"] = drag_bench(panel, slider)
    return out


def run():
    try:
        mw = FreeCADGui.getMainWindow()
        mw.showMaximized()
        check("workbench_registered", "KatydidWorkbench" in FreeCADGui.listWorkbenches())
        FreeCADGui.activateWorkbench("KatydidWorkbench")
        pump(400)
        from katydid import gui
        from katydid import components as lib
        panel = gui.show_canvas()
        check("canvas_dock_shown", panel.isVisible())
        panel.load_demo()
        pump(500)
        d = panel.demo
        states = {c.nickname: c.state for c in panel.graph.components}
        check("demo_all_ok", all(s == "ok" for s in states.values()), states)
        check("demo_four_moved_boxes", len(d["move"].outputs[0].data) == 4,
              len(d["move"].outputs[0].data))
        check("panel_shows_series", d["panel"].text_lines == ["0", "32", "64", "96"],
              d["panel"].text_lines)
        check("preview_attached", panel.preview._doc is not None, panel.preview._doc)
        view3d = FreeCADGui.ActiveDocument.ActiveView
        view3d.viewIsometric()
        view3d.fitAll()
        pump(300)
        grab(None,"01_demo.png")

        # 1. slider drag through real mouse events: the interactivity gate
        view = panel.view
        width = d["width"]
        item = panel.scene.items_by_comp[width]
        knob = view.mapFromScene(item.mapToScene(QtCore.QPointF(item.knob_x(), item.h / 2)))
        before = width.value
        panel.timings.clear()
        steps = []
        mouse(view, "press", knob)
        pump(30)
        for i in range(1, 41):
            t0 = time.perf_counter()
            mouse(view, "move", knob + QtCore.QPoint(i * 2, 0))
            app.processEvents()  # runs the coalesced solve + preview rebuild
            steps.append((time.perf_counter() - t0) * 1000.0)
        mouse(view, "release", knob + QtCore.QPoint(80, 0))
        pump(100)
        box_x = d["move"].outputs[0].data[0].BoundBox.XLength
        check("slider_drag_changes_value", width.value > before, [before, width.value])
        check("geometry_follows_slider", abs(box_x - width.value) < 1e-6, [box_x, width.value])
        res["drag_step_ms"] = {"median": round(statistics.median(steps), 2),
                               "max": round(max(steps), 2), "n": len(steps)}
        if panel.timings:
            solve = [t[0] for t in panel.timings]
            prev = [t[1] for t in panel.timings]
            res["solve_ms"] = {"median": round(statistics.median(solve), 2), "max": round(max(solve), 2)}
            res["preview_ms"] = {"median": round(statistics.median(prev), 2), "max": round(max(prev), 2)}
            res["solves_during_drag"] = len(panel.timings)
        check("interactive_rate", statistics.median(steps) < 33, res["drag_step_ms"])
        res["profile_ms"] = profile_loop(panel, d["spacing"])
        if os.environ.get("KATYDID_EXPERIMENTS"):
            res["experiments_drag_ms"] = experiments(panel)
            raise SystemExit  # experiments change the layout; stop here
        pump(200)
        grab(None,"02_after_drag.png")

        # 2. error and warning states
        d["height"].set_value(0)
        panel.scene.request_solve()
        pump(200)
        check("zero_height_is_error", d["box"].state == "error", d["box"].messages)
        check("downstream_warns", d["move"].state == "warning", d["move"].messages)
        grab(panel, "03_error_state.png")
        d["height"].set_value(30)
        panel.scene.request_solve()
        pump(200)
        check("recovers_after_fix", d["box"].state == "ok" and d["move"].state == "ok")

        # 3. double-click search places a component
        empty = QtCore.QPoint(int(view.viewport().width() * 0.80), int(view.viewport().height() * 0.80))
        mouse(view, "press", empty)
        mouse(view, "release", empty)
        mouse(view, "double", empty)
        mouse(view, "release", empty)
        pump(150)
        popup = view._search
        check("search_popup_opens", popup is not None)
        if popup is not None:
            from PySide6 import QtTest
            QtTest.QTest.keyClicks(popup.edit, "sph")
            pump(50)
            grab(panel, "04_search.png")
            QtTest.QTest.keyClick(popup.edit, Qt.Key.Key_Return)
            pump(200)
        spheres = [c for c in panel.graph.components if isinstance(c, lib.Sphere)]
        check("search_adds_sphere", len(spheres) == 1)

        # 4. wire by dragging from an output grip to an input grip
        if spheres:
            sph = spheres[0]
            drag(view, grip_pos(panel, d["count"].outputs[0]), grip_pos(panel, sph.inputs[0]))
            check("drag_creates_wire", sph.inputs[0].sources == [d["count"].outputs[0]],
                  [repr(s) for s in sph.inputs[0].sources])
            check("sphere_solved", sph.state == "ok" and len(sph.outputs[0].data) == 1, sph.messages)
            # drag the wire off the input again: removes it
            off = grip_pos(panel, sph.inputs[0]) + QtCore.QPoint(-60, 70)
            drag(view, grip_pos(panel, sph.inputs[0]), off)
            check("drag_off_removes_wire", sph.inputs[0].sources == [])

        # 5. bake the selected Move component
        panel.scene.clearSelection()
        panel.scene.items_by_comp[d["move"]].setSelected(True)
        pump(100)
        baked = panel.bake()
        expected = width.value * width.value * 30
        vols = [round(o.Shape.Volume, 4) for o in baked]
        check("bake_four_solids", len(baked) == 4 and all(abs(v - expected) < 1e-3 for v in vols),
              {"volumes": vols, "expected_each": round(expected, 4)})
        doc = FreeCAD.ActiveDocument
        n_objects = len(doc.Objects)

        # 6. Delete on the canvas removes components, never document objects
        if spheres:
            panel.scene.clearSelection()
            panel.scene.items_by_comp[spheres[0]].setSelected(True)
            view.setFocus()
            pump(50)
            from PySide6 import QtTest
            QtTest.QTest.keyClick(view, Qt.Key.Key_Delete)
            pump(150)
            check("delete_removes_component", spheres[0] not in panel.graph.components)
            check("delete_spares_document", len(doc.Objects) == n_objects,
                  [n_objects, len(doc.Objects)])

        panel.scene.clearSelection()
        panel.view.fit_all()
        view3d.fitAll()
        pump(300)
        grab(None,"05_final.png")
        grab(panel, "06_canvas.png")
        view3d.saveImage(os.path.join(OUT, "07_view3d.png"), 1200, 800, "Current")
    except SystemExit:
        pass
    except Exception:
        res["exception"] = traceback.format_exc()
    finally:
        res["passed"] = sum(c["ok"] for c in res["checks"].values())
        res["total"] = len(res["checks"])
        with open(os.path.join(OUT, "results.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)
        sys.stderr.flush()
        os._exit(0)  # no save prompts, no preference writes


QtCore.QTimer.singleShot(2500, run)
