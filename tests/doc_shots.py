# SPDX-License-Identifier: LGPL-2.1-or-later
"""Regenerate the documentation screenshots in docs/images (FreeCAD GUI).

    python tests/run_gui_tests.py --only docshots      (hidden desktop)

Every tutorial definition is built from katydid.demo, so the pictures always
match the code. Report and Python-console panels are hidden before window
shots, so nothing about the machine that made them is visible.
"""

import os
import sys

import FreeCAD
import FreeCADGui
import katydid

ADDON = os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__)))
sys.path.insert(0, os.path.join(ADDON, "tests"))
from guitest import QtCore, QtGui, QtWidgets, Run, empty_spot, grip_pos, mouse, pump  # noqa: E402

IMAGES = os.path.join(ADDON, "docs", "images")
Qt = QtCore.Qt


def save(pm, name, run):
    path = os.path.join(IMAGES, name)
    ok = pm.save(path, "PNG")
    run.check(f"saved {name}", ok and pm.width() > 50, [pm.width(), pm.height()])


def canvas(panel, name, run):
    save(panel.grab(), name, run)


def view3d(name, run, w=1200, h=640):
    v = FreeCADGui.ActiveDocument.ActiveView
    v.viewIsometric()
    v.fitAll()
    pump(200)
    path = os.path.join(IMAGES, name)
    v.saveImage(path, w, h, "Current")
    run.check(f"saved {name}", os.path.getsize(path) > 5000)


def load(panel, builder):
    panel.scene.clear_all()
    panel.demo = builder(panel.scene)
    pump(600)
    panel.view.fit_all()
    pump(200)
    bad = {c.nickname: c.messages for c in panel.graph.components if c.state != "ok"}
    return panel.demo, bad


def window_with_callouts(panel, run):
    """Main window plus the floating canvas, with numbered callouts."""
    from katydid import gui
    mw = FreeCADGui.getMainWindow()
    pm = mw.grab()
    painter = QtGui.QPainter(pm)
    dock_pos = mw.mapFromGlobal(gui._dock.frameGeometry().topLeft())
    painter.drawPixmap(dock_pos, gui._dock.grab())
    painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

    def at(widget):
        top_left = widget.mapTo(gui._dock, QtCore.QPoint(0, 0)) + dock_pos
        return QtCore.QRect(top_left, widget.size())

    ribbon_tabs = at(panel.ribbon.tabBar())
    toolbar = at(panel.ribbon.cornerWidget(Qt.Corner.TopRightCorner))
    canvas_rect = at(panel.view)
    view_widget = [w for w in mw.findChildren(QtWidgets.QWidget, "View3DInventor") if w.isVisible()] or \
                  [mw.centralWidget()]
    view_rect = QtCore.QRect(view_widget[0].mapTo(mw, QtCore.QPoint(0, 0)), view_widget[0].size())
    marks = [(1, ribbon_tabs.topLeft() + QtCore.QPoint(-20, 14)),
             (2, toolbar.topLeft() + QtCore.QPoint(-14, 14)),
             (3, canvas_rect.topLeft() + QtCore.QPoint(24, 30)),
             (4, view_rect.topLeft() + QtCore.QPoint(view_rect.width() // 2, 40))]
    font = QtGui.QFont()
    font.setPixelSize(18)
    font.setBold(True)
    painter.setFont(font)
    for n, p in marks:
        r = QtCore.QRectF(p.x() - 15, p.y() - 15, 30, 30)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 2.5))
        painter.setBrush(QtGui.QColor(47, 138, 76))
        painter.drawEllipse(r)
        painter.drawText(r, Qt.AlignmentFlag.AlignCenter, str(n))
    painter.end()
    save(pm, "ui-window.png", run)


def body(run):
    from katydid import demo, gui
    from PySide6 import QtTest
    mw = FreeCADGui.getMainWindow()
    mw.showMaximized()
    FreeCADGui.activateWorkbench("KatydidWorkbench")
    pump(400)
    for dock in mw.findChildren(QtWidgets.QDockWidget):
        title = dock.windowTitle().lower()
        if "report" in title or "python" in title:
            dock.hide()
    panel = gui.show_canvas()
    pump(300)

    # Quick start
    d, bad = load(panel, demo.build_first)
    run.check("first ok", not bad, bad)
    v = FreeCADGui.ActiveDocument.ActiveView
    v.viewIsometric()
    v.fitAll()
    pump(300)
    window_with_callouts(panel, run)
    canvas(panel, "first-canvas.png", run)
    view3d("first-3d.png", run)
    dlg = panel.view.edit_slider(d["size"])
    pump(200)
    save(dlg.grab(), "ui-slider-dialog.png", run)
    dlg.reject()
    pump(100)

    # The canvas tour: search box, error state, grip menu, ribbon
    view = panel.view
    spot = empty_spot(view)
    mouse(view, "press", spot)
    mouse(view, "release", spot)
    mouse(view, "double", spot)
    mouse(view, "release", spot)
    pump(150)
    if view._search is not None:
        QtTest.QTest.keyClicks(view._search.edit, "cir")
        pump(100)
        canvas(panel, "ui-search.png", run)
        QtTest.QTest.keyClick(view._search.edit, Qt.Key.Key_Escape)
        pump(100)
    panel.graph.disconnect(d["size"].outputs[0], d["box"].inputs[2])
    d["box"].inputs[2].default = -1.0   # a negative height: the Box turns red
    panel.scene.rebuild_wires()
    panel.scene.request_solve()
    pump(300)
    run.check("error state shown", d["box"].state == "error", d["box"].messages)
    canvas(panel, "ui-error.png", run)

    # Lists: the box row
    d, bad = load(panel, demo.build)
    run.check("lists ok", not bad, bad)
    canvas(panel, "lists-canvas.png", run)
    view3d("lists-3d.png", run)
    start = d["series"].inputs[0]
    pos = grip_pos(panel, start)
    mouse(view, "press", pos, button=Qt.MouseButton.RightButton)
    mouse(view, "release", pos, button=Qt.MouseButton.RightButton)
    pump(200)
    if view.menu is not None:
        pm = panel.grab()
        painter = QtGui.QPainter(pm)
        painter.drawPixmap(view.mapTo(panel, pos) + QtCore.QPoint(12, 8), view.menu.grab())
        painter.end()
        save(pm, "ui-set-value-menu.png", run)
        view.menu.close()
        pump(100)
    dlg = view.edit_default(start)
    pump(200)
    save(dlg.grab(), "ui-set-value.png", run)
    dlg.reject()
    pump(100)

    # Data trees
    d, bad = load(panel, demo.build_tree)
    run.check("tree ok", not bad, bad)
    canvas(panel, "tree-canvas.png", run)
    view3d("tree-3d.png", run)
    pos = grip_pos(panel, d["loft"].inputs[0])
    mouse(view, "press", pos, button=Qt.MouseButton.RightButton)
    mouse(view, "release", pos, button=Qt.MouseButton.RightButton)
    pump(200)
    if view.menu is not None:
        # The menu is its own window: paint it onto the canvas next to the grip.
        pm = panel.grab()
        painter = QtGui.QPainter(pm)
        painter.drawPixmap(view.mapTo(panel, pos) + QtCore.QPoint(12, 8), view.menu.grab())
        painter.end()
        save(pm, "ui-grip-menu.png", run)
        view.menu.close()
        pump(100)

    # Attractor
    d, bad = load(panel, demo.build_attractor)
    run.check("attractor ok", not bad, bad)
    canvas(panel, "attractor-canvas.png", run)
    view3d("attractor-3d.png", run)

    # Tolerance
    d, bad = load(panel, demo.build_stackup)
    run.check("stack-up ok", not bad, bad)
    canvas(panel, "stackup-canvas.png", run)
    d, bad = load(panel, demo.build_gdt)
    run.check("gdt ok", not bad, bad)
    canvas(panel, "gdt-canvas.png", run)
    FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)


Run("docshots").run_later(body)
