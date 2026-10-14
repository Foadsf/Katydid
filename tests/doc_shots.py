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


LOW_VIEW = {"tower-render.png", "tower-preview.png", "hyperboloid-render.png", "hyperboloid-preview.png",
            "staircase-render.png", "staircase-preview.png", "origami-render.png", "origami-preview.png"}


ZOOM = {"voronoi": 0.88, "waffle": 0.72, "wave": 0.7, "phyllotaxis": 0.78, "city": 0.8, "weave": 0.75,
        "staircase": 0.85, "knot": 0.8, "ring": 0.8, "frames": 0.85, "hypar": 0.8, "slats": 0.8,
        "monolith": 0.95, "flange": 0.85, "bridge": 0.75, "shell": 0.85, "origami": 0.85, "rose": 0.85}
TILT = {"phyllotaxis": 35, "knot": 30, "ring": 50, "rose": 25}   # degrees back from a top view
SMOOTH = {"knot", "ring"}   # not "shell": its big loft hung the render at this deviation
SHADED = {"shell"}          # no edge lines, default mesh
SPIN = {"ring": 270}   # turn the closed loft's seam (on +X) to the back   # fitAll fits a bounding sphere: close in


def view3d(name, run, w=1200, h=640):
    v = FreeCADGui.ActiveDocument.ActiveView
    tilt = TILT.get(name.split("-")[0])
    if tilt is not None:   # from above, tipped back: a pattern in plan reads best
        spin = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), SPIN.get(name.split("-")[0], 0))
        v.setCameraOrientation(spin.multiply(FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), tilt)))
    elif name in LOW_VIEW:
        v.viewDimetric()   # a lower eye: tall towers and stacked ribs read better
    else:
        v.viewIsometric()
    v.fitAll()
    zoom = ZOOM.get(name.split("-")[0]) if name.endswith("-render.png") else None
    cam = v.getCameraNode()
    if zoom and hasattr(cam, "height"):   # orthographic camera
        cam.height.setValue(cam.height.getValue() * zoom)
    pump(200)
    path = os.path.join(IMAGES, name)
    v.saveImage(path, w, h, "Current")
    run.check(f"saved {name}", os.path.getsize(path) > 5000)


RENDERS = {  # showcase key -> [(component, colour, transparency %, lift in mm)]
    "voronoi": [("stand", (0.74, 0.46, 0.24), 0, 0.0)],
    "tower": [("facade", (0.56, 0.74, 0.88), 55, 0.0), ("slabs", (0.93, 0.93, 0.91), 0, 0.0)],
    "waffle": [("x_ribs", (0.87, 0.72, 0.53), 0, 0.0), ("y_ribs", (0.80, 0.64, 0.45), 0, 0.0)],
    "wave": [("surface", (0.91, 0.92, 0.94), 0, 0.0), ("contours", (0.13, 0.36, 0.62), 0, 0.15)],
    "phyllotaxis": [("seed", (0.96, 0.70, 0.16), 0, 0.0)],
    "hyperboloid": [("pipes_l", (0.72, 0.30, 0.18), 0, 0.0), ("pipes_r", (0.72, 0.30, 0.18), 0, 0.0),
                    ("ring_pipes", (0.85, 0.85, 0.82), 0, 0.0)],
    "staircase": [("stair", (0.80, 0.58, 0.36), 0, 0.0), ("column", (0.92, 0.92, 0.90), 0, 0.0),
                  ("balusters", (0.20, 0.21, 0.23), 0, 0.0), ("handrail", (0.20, 0.21, 0.23), 0, 0.0)],
    "city": [("blocks", (0.90, 0.88, 0.84), 0, 0.0), ("ground", (0.42, 0.52, 0.40), 0, 0.0)],
    "weave": [("warp", (0.12, 0.55, 0.60), 0, 0.0), ("weft", (0.93, 0.47, 0.36), 0, 0.0)],
    "knot": [("tube", (0.32, 0.62, 0.88), 0, 0.0)],
    "ring": [("ring", (0.86, 0.88, 0.92), 0, 0.0)],
    "frames": [("tunnel", (0.80, 0.56, 0.32), 0, 0.0)],
    "hypar": [("rot1", (0.86, 0.86, 0.84), 0, 0.0), ("rot2", (0.86, 0.86, 0.84), 0, 0.0),
              ("roof", (0.30, 0.70, 0.78), 55, 0.0), ("column", (0.86, 0.86, 0.84), 0, 0.0)],
    "slats": [("slat", (0.82, 0.62, 0.40), 0, 0.0)],
    "monolith": [("carved", (0.88, 0.80, 0.68), 0, 0.0)],
    "flange": [("flange", (0.72, 0.74, 0.78), 0, 0.0), ("hub_bored", (0.72, 0.74, 0.78), 0, 0.0),
               ("pins", (0.25, 0.75, 0.35), 70, 0.0), ("zones", (0.92, 0.20, 0.15), 0, 0.0)],
    "bridge": [("deck", (0.62, 0.62, 0.60), 0, 0.0), ("arch_p", (0.93, 0.93, 0.92), 0, 0.0),
               ("arch_m", (0.93, 0.93, 0.92), 0, 0.0), ("hp1", (0.80, 0.82, 0.86), 0, 0.0),
               ("hp2", (0.80, 0.82, 0.86), 0, 0.0), ("hm1", (0.80, 0.82, 0.86), 0, 0.0),
               ("hm2", (0.80, 0.82, 0.86), 0, 0.0)],
    "shell": [("shell", (0.94, 0.89, 0.82), 0, 0.0), ("lines", (0.68, 0.42, 0.22), 0, 0.0)],
    "origami": [("sheet", (0.95, 0.94, 0.90), 0, 0.0)],
    "rose": [("pp", (0.86, 0.70, 0.36), 0, 0.0), ("pn", (0.86, 0.70, 0.36), 0, 0.0),
             ("inner", (0.86, 0.70, 0.36), 0, 0.0), ("outer", (0.86, 0.70, 0.36), 0, 0.0)],
}


def render(panel, d, parts, name, run):
    """Bake the chosen components with material colours, picture them without
    the red preview, then remove them again."""
    from katydid.bake import bake
    doc = FreeCAD.ActiveDocument
    objs = []
    for key, colour, transparency, lift in parts:
        for o in bake([d[key]]):
            vo = o.ViewObject
            if name.split("-")[0] in SMOOTH:
                # FreeCAD's default 0.5 % deviation shows facets on one big smooth form. Only
                # here: on 400 spheres it made one render take two minutes, then crashed.
                vo.Deviation = 0.05
                vo.AngularDeflection = 8.0
                vo.DisplayMode = "Shaded"  # no edge lines: seams on a smooth form are distracting
            elif name.split("-")[0] in SHADED and o.Shape.Faces:
                vo.DisplayMode = "Shaded"
            if o.Shape.Faces:
                vo.ShapeColor = colour
                vo.LineColor = tuple(c * 0.45 for c in colour)
            else:
                vo.LineColor = colour
                vo.LineWidth = 2.5
            if transparency:
                vo.Transparency = transparency
            if lift:  # curves lying on a surface: lift them clear of it
                o.Placement.Base.z += lift
            objs.append(o)
    panel.preview.enabled = False
    panel.refresh_preview()
    view3d(name, run, 1400, 800)
    for o in objs:
        doc.removeObject(o.Name)
    panel.preview.enabled = True
    panel.refresh_preview()
    pump(100)


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

    # The Examples menu, painted next to its button
    menu = panel.examples.menu()
    anchor = panel.examples.mapTo(panel, QtCore.QPoint(0, panel.examples.height()))
    menu.popup(panel.examples.mapToGlobal(QtCore.QPoint(0, panel.examples.height())))
    pump(200)
    pm = panel.grab()
    painter = QtGui.QPainter(pm)
    painter.drawPixmap(anchor - QtCore.QPoint(menu.sizeHint().width() // 2, 0), menu.grab())
    painter.end()
    save(pm, "ui-examples-menu.png", run)
    menu.close()
    pump(100)

    # Showcase: canvas, red preview and a material render of each
    from katydid import showcase
    for key, builder in showcase.SHOWCASE.items():
        d, bad = load(panel, builder)
        while panel.scene._pending:
            pump(50)
        run.check(f"{key} ok", not bad, bad)
        canvas(panel, f"{key}-canvas.png", run)
        view3d(f"{key}-preview.png", run)
        render(panel, d, RENDERS[key], f"{key}-render.png", run)
    FreeCAD.closeDocument(FreeCAD.ActiveDocument.Name)


Run("docshots").run_later(body)
