# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Katydid panel (ribbon, canvas, actions) and its FreeCAD commands."""

from __future__ import annotations

import time

from . import demo, resource
from .canvas import ComponentItem, KatydidScene, KatydidView, QtCore, QtWidgets, Ribbon
from .engine import Graph

Qt = QtCore.Qt


class KatydidPanel(QtWidgets.QWidget):
    def __init__(self, parent=None, with_preview=True):
        super().__init__(parent)
        self.setObjectName("KatydidPanel")
        self.graph = Graph()
        self.scene = KatydidScene(self.graph, self)
        self.view = KatydidView(self.scene)
        self.ribbon = Ribbon(self.view)
        self.demo: dict = {}
        self.timings: list[tuple[float, float]] = []

        bar = QtWidgets.QToolBar()
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.act_preview = bar.addAction("Preview")
        self.act_preview.setCheckable(True)
        self.act_preview.setChecked(True)
        self.act_preview.toggled.connect(self._toggle_preview)
        bar.addAction("Bake", self.bake).setToolTip("Bake the selected components (all if none)")
        bar.addAction("Zoom Extents", self.view.fit_all)
        bar.addSeparator()
        bar.addAction("Demo", self.load_demo)
        bar.addAction("Clear", self.scene.clear_all)
        bar.addSeparator()
        self.status = QtWidgets.QLabel("Double-click the canvas to search")
        self.status.setMinimumWidth(260)
        bar.addWidget(self.status)
        self.ribbon.setCornerWidget(bar, Qt.Corner.TopRightCorner)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.ribbon)
        lay.addWidget(self.view, 1)

        self.preview = None
        if with_preview:
            from .preview import Preview
            self.preview = Preview()
        self.scene.solved.connect(self._on_solved)
        self.scene.selectionChanged.connect(self.refresh_preview)

    # preview ----------------------------------------------------------------
    def _on_solved(self, solved):
        t0 = time.perf_counter()
        self.refresh_preview()
        preview_ms = (time.perf_counter() - t0) * 1000.0
        if solved:
            self.timings.append((self.graph.last_solve_ms, preview_ms))
            self.status.setText(f"{len(solved)} solved · solve {self.graph.last_solve_ms:.1f} ms"
                                f" · preview {preview_ms:.1f} ms")

    def refresh_preview(self):
        if self.preview is None:
            return
        selected = {i.comp for i in self.scene.selectedItems() if isinstance(i, ComponentItem)}
        normal, chosen = [], []
        for comp in self.graph.components:
            if comp.preview:
                (chosen if comp in selected else normal).extend(comp.shapes())
        self.preview.update(normal, chosen)

    def _toggle_preview(self, on):
        if self.preview is not None:
            self.preview.enabled = on
            self.refresh_preview()

    # actions ----------------------------------------------------------------
    def bake(self):
        from .bake import bake
        selected = [i.comp for i in self.scene.selectedItems() if isinstance(i, ComponentItem)]
        comps = [c for c in (selected or self.graph.components) if c.preview or c in selected]
        baked = bake(comps)
        self.status.setText(f"Baked {len(baked)} object(s) into the document")
        return baked

    def load_demo(self):
        self.scene.clear_all()
        self.demo = demo.build(self.scene)
        QtCore.QTimer.singleShot(0, self.view.fit_all)


# --------------------------------------------------------------------------
# FreeCAD integration
# --------------------------------------------------------------------------
_dock = None


def show_canvas() -> KatydidPanel:
    """Show (creating once) the canvas dock in FreeCAD's main window."""
    global _dock
    import FreeCAD
    import FreeCADGui
    if FreeCAD.ActiveDocument is None:
        FreeCAD.newDocument("Unnamed")  # the preview needs a 3D view
    mw = FreeCADGui.getMainWindow()
    if _dock is None:
        _dock = QtWidgets.QDockWidget("Katydid", mw)
        _dock.setObjectName("KatydidDock")
        _dock.setWidget(KatydidPanel(_dock))
        mw.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, _dock)
        # Float by default, like Grasshopper's canvas window. Measured on FreeCAD 1.1:
        # docked, every canvas repaint also recomposites the OpenGL main window,
        # which doubles the time per slider step (49 ms docked vs 24 ms floating).
        _dock.setFloating(True)
        geo = mw.geometry()
        _dock.resize(geo.width() - 360, max(460, geo.height() * 9 // 20))
        _dock.move(geo.x() + 330, geo.bottom() - _dock.height() - 40)
    _dock.show()
    _dock.raise_()
    return _dock.widget()


class _CanvasCommand:
    def GetResources(self):
        return {"Pixmap": resource("katydid.svg"), "MenuText": "Canvas",
                "ToolTip": "Show the Katydid visual programming canvas"}

    def Activated(self):
        show_canvas()

    def IsActive(self):
        return True


class _BakeCommand:
    def GetResources(self):
        return {"Pixmap": resource("bake.svg"), "MenuText": "Bake",
                "ToolTip": "Bake the selected canvas components into the document"}

    def Activated(self):
        show_canvas().bake()

    def IsActive(self):
        return True


COMMANDS = ["Katydid_Canvas", "Katydid_Bake"]


def register_commands():
    import FreeCADGui
    FreeCADGui.addCommand("Katydid_Canvas", _CanvasCommand())
    FreeCADGui.addCommand("Katydid_Bake", _BakeCommand())
