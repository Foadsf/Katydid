# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Katydid panel (ribbon, canvas, actions) and its FreeCAD commands.

The canvas shows the definition of the active FreeCAD document. Edits are
written through to that document's Katydid object about 0.4 s after they stop
(and again just before a save), so saving the .FCStd saves the definition,
and opening it brings the canvas back.
"""

from __future__ import annotations

import time

from . import demo
from .commands import COMMANDS, register as register_commands  # noqa: F401  (kept for callers)
from .canvas import ComponentItem, KatydidScene, KatydidView, QtCore, QtWidgets, Ribbon
from .engine import Graph

Qt = QtCore.Qt
WRITE_DELAY_MS = 400
EXAMPLES = [  # (menu label, key); None draws a separator
    ("Quick start: one slider, one box", "first"), ("Row of boxes", "boxes"),
    ("Lofted rings (data trees)", "tree"), ("Attractor grid", "attractor"), (None, None),
    ("Voronoi screen", "voronoi"), ("Twisted tower", "tower"), ("Waffle dome", "waffle"),
    ("Wave surface with contours", "wave"), ("Sunflower (phyllotaxis)", "phyllotaxis"),
    ("Shukhov tower (hyperboloid)", "hyperboloid"), ("Spiral staircase", "staircase"),
    ("Voronoi city", "city"), ("Woven mat", "weave"), ("Torus knot", "knot"),
    ("Twisted lobed ring", "ring"), ("Frame tunnel", "frames"), ("Hypar umbrella", "hypar"),
    ("Slatted wave ceiling", "slats"), ("Carved monolith", "monolith"), ("Network-arch bridge", "bridge"),
    ("Spiral shell", "shell"), ("Miura-ori fold", "origami"), ("Guilloché rose", "rose"),
    ("Mashrabiya facade", "mashrabiya"), ("Mushroom columns", "columns"), ("Pendant cloud", "pendants"),
    ("Enneper surface", "enneper"), ("Woven-bowl stadium roof", "stadium"), ("Whirlpool ziggurat", "whirlpool"),
    ("Helicoid–catenoid morph", "morph"), ("Tensegrity tower", "tensegrity"), ("Blooming lotus", "lotus"),
    ("Auxetic lattice", "auxetic"), ("Stepped amphitheatre", "amphitheatre"),
    ("Tri-axial grid-shell", "gridshell"), ("Gaudí double-twist columns", "gaudi"), ("Pangolin-scale tower", "pangolin"),
    ("Dini's surface", "dini"), (None, None),
    ("Tolerance stack-up", "stackup"), ("GD&T calculators", "gdt"),
    ("Flange with tolerance zones", "flange"), ("Impeller with tip clearance", "impeller")]


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
        self.doc_name: str | None = None
        self.load_warnings: list[str] = []
        self._last_written: str | None = None
        self._loading = False

        bar = QtWidgets.QToolBar()
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.act_preview = bar.addAction("Preview")
        self.act_preview.setCheckable(True)
        self.act_preview.setChecked(True)
        self.act_preview.toggled.connect(self._toggle_preview)
        bar.addAction("Bake", self.bake).setToolTip("Bake the selected components (all if none)")
        bar.addAction("Zoom Extents", self.view.fit_all)
        bar.addSeparator()
        self.examples = QtWidgets.QToolButton()
        self.examples.setText("Examples")
        self.examples.setPopupMode(QtWidgets.QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QtWidgets.QMenu(self.examples)
        for label, key in EXAMPLES:
            if label is None:
                menu.addSeparator()
            else:
                menu.addAction(label, lambda k=key: self.load_example(k))
        self.examples.setMenu(menu)
        bar.addWidget(self.examples)
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
        self._write_timer = QtCore.QTimer(self)
        self._write_timer.setSingleShot(True)
        self._write_timer.setInterval(WRITE_DELAY_MS)
        self._write_timer.timeout.connect(self.write_definition)
        self.scene.edited.connect(self._on_edited)
        self.scene.solved.connect(self._on_solved)
        self.scene.selectionChanged.connect(self.refresh_preview)

    # document binding ---------------------------------------------------------
    def _doc(self):
        import FreeCAD
        return FreeCAD.listDocuments().get(self.doc_name) if self.doc_name else None

    def bind(self, doc, reload=False):
        """Show doc's definition on the canvas (saving the current one first)."""
        name = doc.Name if doc is not None else None
        if name == self.doc_name and not reload:
            return
        self.flush()
        if self.preview is not None:
            self.preview.detach()
        self.doc_name = name
        self._load(doc)

    def unbind(self, forget_preview=True):
        """The bound document is closing: drop the canvas without writing."""
        self._write_timer.stop()
        if self.preview is not None and forget_preview:
            self.preview.forget()
        self.doc_name = None
        self._load(None)

    def _load(self, doc):
        from . import feature
        self._loading = True
        try:
            text = feature.read(doc) if doc is not None else None
            if text:
                self.load_warnings = self.scene.load_json(text)
            else:
                self.load_warnings = []
                self.scene.clear_all()
            self._last_written = self.scene.to_json()
        finally:
            self._loading = False
        self._write_timer.stop()
        dock = self.parentWidget()
        if isinstance(dock, QtWidgets.QDockWidget):
            dock.setWindowTitle(f"Katydid — {doc.Label}" if doc is not None else "Katydid")
        if text:
            note = f"Loaded {len(self.graph.components)} components from {doc.Label}"
            if self.load_warnings:
                note += f" · {len(self.load_warnings)} warning(s), hover for details"
                self.status.setToolTip("\n".join(self.load_warnings))
            self.status.setText(note)
            QtCore.QTimer.singleShot(0, self.view.fit_all)

    def _on_edited(self):
        if not self._loading and self.doc_name is not None:
            self._write_timer.start()

    def flush(self):
        """Write a pending edit now (before a save or a document switch)."""
        if self._write_timer.isActive():
            self._write_timer.stop()
            self.write_definition()

    def write_definition(self):
        doc = self._doc()
        if doc is None or self._loading:
            return
        text = self.scene.to_json()
        if text == self._last_written:
            return
        from . import feature
        obj = feature.find(doc)
        if obj is None:
            if not self.graph.components:
                self._last_written = text
                return
            obj = feature.create(doc)
        setattr(obj, feature.PROPERTY, text)
        obj.purgeTouched()  # a definition change needs no recompute
        self._last_written = text

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

    def load_example(self, key):
        """Replace the canvas with one of the example definitions."""
        from . import showcase
        builders = {"first": demo.build_first, "boxes": demo.build, "tree": demo.build_tree,
                    "attractor": demo.build_attractor, "stackup": demo.build_stackup,
                    "gdt": demo.build_gdt, **showcase.SHOWCASE}
        self.scene.clear_all()
        self.demo = builders[key](self.scene)
        QtCore.QTimer.singleShot(0, self.view.fit_all)

    def load_demo(self):
        self.scene.clear_all()
        self.demo = demo.build(self.scene)
        QtCore.QTimer.singleShot(0, self.view.fit_all)

    def load_tree_demo(self):
        self.scene.clear_all()
        self.demo = demo.build_tree(self.scene)
        QtCore.QTimer.singleShot(0, self.view.fit_all)

    def load_stackup_demo(self):
        self.scene.clear_all()
        self.demo = demo.build_stackup(self.scene)
        QtCore.QTimer.singleShot(0, self.view.fit_all)

    def load_attractor_demo(self):
        self.scene.clear_all()
        self.demo = demo.build_attractor(self.scene)
        QtCore.QTimer.singleShot(0, self.view.fit_all)


# --------------------------------------------------------------------------
# FreeCAD integration
# --------------------------------------------------------------------------
class _DocumentObserver:
    """Keeps the canvas on the active document and in step with save/open/close."""

    def __init__(self, panel):
        self.panel = panel

    def slotActivateDocument(self, doc):
        QtCore.QTimer.singleShot(0, self._follow_active)

    def slotFinishRestoreDocument(self, doc):
        name = doc.Name
        QtCore.QTimer.singleShot(0, lambda: self._restored(name))

    def slotStartSaveDocument(self, doc, label):
        if doc.Name == self.panel.doc_name:
            self.panel.flush()  # synchronous: the save must include the last edit

    def slotDeletedDocument(self, doc):
        if doc.Name == self.panel.doc_name:
            self.panel.unbind()
            QtCore.QTimer.singleShot(0, self._follow_active)

    def _follow_active(self):
        import FreeCAD
        self.panel.bind(FreeCAD.ActiveDocument)

    def _restored(self, name):
        import FreeCAD
        doc = FreeCAD.listDocuments().get(name)
        if doc is not None and (doc is FreeCAD.ActiveDocument or name == self.panel.doc_name):
            self.panel.bind(doc, reload=True)


_dock = None
_observer = None


def show_canvas() -> KatydidPanel:
    """Show (creating once) the canvas window for the active document."""
    global _dock, _observer
    import FreeCAD
    import FreeCADGui
    if FreeCAD.ActiveDocument is None:
        FreeCAD.newDocument("Unnamed")  # the preview needs a 3D view
    mw = FreeCADGui.getMainWindow()
    if _dock is None:
        _dock = QtWidgets.QDockWidget("Katydid", mw)
        _dock.setObjectName("KatydidDock")
        panel = KatydidPanel(_dock)
        _dock.setWidget(panel)
        mw.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, _dock)
        # Float by default, like Grasshopper's canvas window. Measured on FreeCAD 1.1:
        # docked, every canvas repaint also recomposites the OpenGL main window,
        # which doubles the time per slider step (49 ms docked vs 24 ms floating).
        _dock.setFloating(True)
        geo = mw.geometry()
        _dock.resize(geo.width() - 360, max(460, geo.height() * 9 // 20))
        _dock.move(geo.x() + 330, geo.bottom() - _dock.height() - 40)
        _observer = _DocumentObserver(panel)
        FreeCAD.addDocumentObserver(_observer)
    panel = _dock.widget()
    panel.bind(FreeCAD.ActiveDocument)
    _dock.show()
    _dock.raise_()
    return panel
