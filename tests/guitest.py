# SPDX-License-Identifier: LGPL-2.1-or-later
"""Helpers for tests that run inside the FreeCAD GUI as macros.

Screenshots render FreeCAD's own widgets, never the screen, so other
windows on the desktop are never captured.
"""

import json
import os
import sys
import time
import traceback

import FreeCADGui
from PySide import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt
app = QtWidgets.QApplication.instance()


def pump(ms=150):
    end = time.perf_counter() + ms / 1000.0
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.005)


def mouse(view, kind, pos, button=Qt.MouseButton.LeftButton, mods=Qt.KeyboardModifier.NoModifier):
    types = {"press": QtCore.QEvent.Type.MouseButtonPress, "move": QtCore.QEvent.Type.MouseMove,
             "release": QtCore.QEvent.Type.MouseButtonRelease,
             "double": QtCore.QEvent.Type.MouseButtonDblClick}
    held = Qt.MouseButton.NoButton if kind == "release" else button
    button = Qt.MouseButton.NoButton if kind == "move" else button
    vp = view.viewport()
    ev = QtGui.QMouseEvent(types[kind], QtCore.QPointF(pos), QtCore.QPointF(vp.mapToGlobal(pos)),
                           button, held, mods)
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
    return panel.view.mapFromScene(panel.scene.grip(param).scenePos())


class Run:
    """Collects checks and screenshots for one test run, then exits FreeCAD."""

    def __init__(self, name):
        import katydid
        addon = os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__)))
        runs = os.path.join(os.path.dirname(addon), "_runs")
        self.out = os.environ.get("KATYDID_OUT") or os.path.join(
            runs, time.strftime(f"{name}_%Y%m%d_%H%M%S"))
        os.makedirs(self.out, exist_ok=True)
        self.res = {"out": self.out, "checks": {}}
        sys.stderr = open(os.path.join(self.out, f"stderr_{name}.txt"), "w", encoding="utf-8")
        self.name = name
        # An exception inside a Qt callback (a timer, a signal) never reaches the
        # test body; record it so it fails the run instead of vanishing.
        self.res["callback_exceptions"] = []
        sys.excepthook = lambda *exc: self.res["callback_exceptions"].append(
            "".join(traceback.format_exception(*exc)))

    def check(self, label, ok, detail=None):
        self.res["checks"][label] = {"ok": bool(ok), "detail": detail}

    def grab(self, widget, filename):
        """Grab a widget; None composes the main window with the floating canvas."""
        path = os.path.join(self.out, filename)
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
        self.res.setdefault("grabs", {})[filename] = {"saved": ok, "size": [pm.width(), pm.height()]}
        return path

    def run_later(self, body, delay_ms=2500):
        def wrapped():
            try:
                body(self)
            except SystemExit:
                pass
            except Exception:
                self.res["exception"] = traceback.format_exc()
            finally:
                self.finish()
        QtCore.QTimer.singleShot(delay_ms, wrapped)

    def finish(self):
        self.check("no_callback_exceptions", not self.res["callback_exceptions"],
                   self.res["callback_exceptions"][:3])
        self.res["passed"] = sum(c["ok"] for c in self.res["checks"].values())
        self.res["total"] = len(self.res["checks"])
        with open(os.path.join(self.out, f"results_{self.name}.json"), "w", encoding="utf-8") as fh:
            json.dump(self.res, fh, indent=2)
        sys.stderr.flush()
        os._exit(0)  # no save prompts, no preference writes
