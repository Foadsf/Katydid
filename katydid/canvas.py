# SPDX-License-Identifier: LGPL-2.1-or-later
"""Node canvas on Qt's Graphics View framework.

Interaction follows the conventions Grasshopper users expect: drag from the
ribbon or double-click the canvas to search, drag between grips to wire (Shift
adds a wire instead of replacing), drag a wire off an input to remove it,
right-drag pans, the wheel zooms about the cursor, Ctrl+Q toggles preview and
Delete removes the selection.
"""

from __future__ import annotations

try:  # FreeCAD's PySide shim maps to PySide6 on FreeCAD 1.1
    from PySide import QtCore, QtGui, QtWidgets
except ImportError:  # standalone use outside FreeCAD
    from PySide6 import QtCore, QtGui, QtWidgets

from . import components as lib
from . import document
from .engine import ERROR, OK, WARNING

Qt = QtCore.Qt
QColor = QtGui.QColor
QPointF = QtCore.QPointF
QRectF = QtCore.QRectF
GIF = QtWidgets.QGraphicsItem.GraphicsItemFlag
MIME = "application/x-katydid-component"

CANVAS_BG = QColor(212, 212, 212)
GRID_MINOR = QColor(203, 203, 203)
GRID_MAJOR = QColor(190, 190, 190)
OUTLINE = QColor(38, 38, 38)
BAND = QColor(58, 58, 58)
TEXT = QColor(20, 20, 20)
FILLS = {
    OK: (QColor(246, 246, 246), QColor(196, 196, 196)),
    WARNING: (QColor(255, 196, 120), QColor(238, 138, 36)),
    ERROR: (QColor(244, 120, 108), QColor(198, 36, 30)),
    "selected": (QColor(206, 244, 168), QColor(104, 190, 52)),
    "nopreview": (QColor(176, 176, 176), QColor(132, 132, 132)),
}
WIRE = QColor(36, 36, 36, 215)
WIRE_EMPTY = QColor(230, 128, 26, 230)
WIRE_HOT = QColor(70, 170, 30, 235)
PANEL_FILL = QColor(252, 248, 196)
CATEGORY_COLOURS = {
    "Params": QColor(90, 90, 90), "Maths": QColor(40, 110, 170),
    "Sets": QColor(120, 80, 160), "Vector": QColor(150, 110, 40), "Curve": QColor(30, 130, 150),
    "Tolerance": QColor(60, 90, 120),
    "Surface": QColor(40, 140, 90),
    "Transform": QColor(190, 110, 30), "Intersect": QColor(170, 50, 60),
}


def make_icon(cls, size=32) -> QtGui.QIcon:
    """An original glyph: category-coloured tile with the nickname."""
    pm = QtGui.QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
    p.setBrush(CATEGORY_COLOURS.get(cls.category, BAND))
    p.setPen(QtGui.QPen(OUTLINE, 1))
    p.drawRoundedRect(QRectF(1.5, 1.5, size - 3, size - 3), 6, 6)
    glyph = getattr(cls, "glyph", cls.nickname[:3])
    font = QtGui.QFont()
    font.setBold(True)
    font.setPixelSize(int(size * (0.56 if len(glyph) == 1 else 0.36 if len(glyph) < 4 else 0.28)))
    p.setFont(font)
    p.setPen(QColor(255, 255, 255))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, glyph)
    p.end()
    return QtGui.QIcon(pm)


def _gradient(height, top, bottom):
    g = QtGui.QLinearGradient(0, 0, 0, height)
    g.setColorAt(0, top)
    g.setColorAt(1, bottom)
    return QtGui.QBrush(g)


def value_kind(value) -> str | None:
    """What kind of value an input default is, for "Set value…" (None: not editable)."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, (tuple, list)) and len(value) == 3 and all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
        return "point"
    return None


def param_kind(param) -> str | None:
    """The kind of value Set value… offers for an input: its default's, else its declared kind."""
    return value_kind(param.default) or getattr(param, "kind", None)


def format_value(kind, value) -> str:
    if value is None:
        return ""
    if kind == "point":
        return ", ".join(f"{v:g}" for v in value)
    if kind == "number":
        return f"{value:g}"
    return str(value)


def parse_value(kind, text: str):
    """Text from the dialog to a value of the same kind; ValueError if it is not one."""
    text = text.strip()
    if kind == "number":
        return float(text)
    if kind == "bool":
        if text.lower() not in ("true", "false"):
            raise ValueError("Expected True or False")
        return text.lower() == "true"
    if kind == "point":
        parts = [float(t) for t in text.replace(";", ",").split(",") if t.strip()]
        if len(parts) != 3:
            raise ValueError("Expected three numbers: x, y, z")
        return tuple(parts)
    return text


def _pen(colour, width, style=Qt.PenStyle.SolidLine) -> QtGui.QPen:
    pen = QtGui.QPen(colour, width, style)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    return pen


def _lod(painter) -> float:
    return QtWidgets.QStyleOptionGraphicsItem.levelOfDetailFromTransform(painter.worldTransform())


# --------------------------------------------------------------------------
# Grips and wires
# --------------------------------------------------------------------------
class GripItem(QtWidgets.QGraphicsEllipseItem):
    R = 4.0

    def __init__(self, param, parent):
        super().__init__(-self.R, -self.R, 2 * self.R, 2 * self.R, parent)
        self.param = param
        self.setBrush(QColor(255, 255, 255))
        self.setPen(QtGui.QPen(OUTLINE, 1.2))
        self.setAcceptHoverEvents(True)
        self.setZValue(2)

    def shape(self):  # generous hit area
        path = QtGui.QPainterPath()
        path.addEllipse(QPointF(0, 0), 8, 8)
        return path

    def hoverEnterEvent(self, event):
        p = self.param
        lines = [f"{p.name} ({p.nickname}) · {p.access} access", p.description]
        if not p.is_input:
            lines.append(p.data.describe())
        mods = [m for m in (p.modifier, "reverse" if p.reverse else None) if m]
        if mods:
            lines.append("Modifiers: " + ", ".join(mods))
        lines.append("Right-click for Flatten / Graft / Simplify / Reverse")
        self.setToolTip("\n".join(line for line in lines if line))
        self.setBrush(WIRE_HOT)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QColor(255, 255, 255))
        super().hoverLeaveEvent(event)


def wire_path(p1: QPointF, p2: QPointF) -> QtGui.QPainterPath:
    dx = max(abs(p2.x() - p1.x()) * 0.5, 40.0)
    path = QtGui.QPainterPath(p1)
    path.cubicTo(QPointF(p1.x() + dx, p1.y()), QPointF(p2.x() - dx, p2.y()), p2)
    return path


class WireItem(QtWidgets.QGraphicsPathItem):
    """Solid for one item, double for a list, dashed for a tree of several
    branches, thin dashed orange when empty."""

    def __init__(self, src: GripItem, dst: GripItem):
        super().__init__()
        self.src, self.dst = src, dst
        self.setZValue(-1)
        self.setPen(QtGui.QPen(WIRE, 5))  # bounding rect only; paint() draws
        self.update_path()

    def update_path(self):
        self.setPath(wire_path(self.src.scenePos(), self.dst.scenePos()))

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        hot = self.src.parentItem().isSelected() or self.dst.parentItem().isSelected()
        colour = WIRE_HOT if hot else WIRE
        data = self.src.param.data
        n = len(data)
        path = self.path()
        if n == 0:
            painter.strokePath(path, _pen(WIRE_EMPTY, 1.5, Qt.PenStyle.DashLine))
        elif data.branch_count > 1:
            pen = _pen(colour, 3.0, Qt.PenStyle.CustomDashLine)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            pen.setDashPattern([2.5, 1.5])
            painter.strokePath(path, pen)
        elif n == 1:
            painter.strokePath(path, _pen(colour, 2.0))
        else:
            painter.strokePath(path, _pen(colour, 4.6))
            painter.strokePath(path, _pen(CANVAS_BG, 1.6))


# --------------------------------------------------------------------------
# Components
# --------------------------------------------------------------------------
class ComponentItem(QtWidgets.QGraphicsItem):
    ROW = 20
    BAND_W = 20

    def __init__(self, comp, scene):
        super().__init__()
        self.comp = comp
        self.kscene = scene
        self.font = QtGui.QFont(scene.font)
        self.setFlags(GIF.ItemIsMovable | GIF.ItemIsSelectable | GIF.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)
        self.setCacheMode(QtWidgets.QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.grips: dict = {}
        self.layout()

    # geometry ---------------------------------------------------------------
    def layout(self):
        fm = QtGui.QFontMetrics(self.font)
        c = self.comp
        lw = max((fm.horizontalAdvance(p.nickname) for p in c.inputs), default=0)
        rw = max((fm.horizontalAdvance(p.nickname) for p in c.outputs), default=0)
        self.left_w = lw + 14 if c.inputs else 8
        self.right_w = rw + 14 if c.outputs else 8
        rows = max(len(c.inputs), len(c.outputs), 1)
        self.w = self.left_w + self.BAND_W + self.right_w
        self.h = max(rows * self.ROW + 6, fm.horizontalAdvance(c.nickname) + 18)
        self._place_grips()

    def _place_grips(self):
        for side, params, x in ((0, self.comp.inputs, 0.0), (1, self.comp.outputs, self.w)):
            for i, p in enumerate(params):
                grip = self.grips.get(p) or GripItem(p, self)
                grip.setPos(x, self.h * (i + 0.5) / len(params))
                self.grips[p] = grip

    def boundingRect(self):
        return QRectF(-24, -22, self.w + 48, self.h + 32)

    def shape(self):
        path = QtGui.QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.w, self.h), 6, 6)
        return path

    def fill(self):
        if self.isSelected():
            return FILLS["selected"]
        if self.comp.state != OK:
            return FILLS[self.comp.state]
        if not self.comp.preview and self.comp.shapes():
            return FILLS["nopreview"]
        return FILLS[OK]

    # painting -----------------------------------------------------------------
    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        top, bottom = self.fill()
        body = QRectF(0, 0, self.w, self.h)
        painter.setPen(QtGui.QPen(OUTLINE, 1.2))
        painter.setBrush(_gradient(self.h, top, bottom))
        painter.drawRoundedRect(body, 6, 6)
        band = QRectF(self.left_w, 3, self.BAND_W, self.h - 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(BAND)
        painter.drawRoundedRect(band, 4, 4)
        if _lod(painter) < 0.45:
            return  # zoomed out: shapes only, like Grasshopper
        painter.setFont(self.font)
        painter.setPen(TEXT)
        for params, align, x0, x1 in ((self.comp.inputs, Qt.AlignmentFlag.AlignLeft, 7, self.left_w),
                                      (self.comp.outputs, Qt.AlignmentFlag.AlignRight,
                                       self.left_w + self.BAND_W, self.w - 7)):
            for p in params:
                y = self.grips[p].pos().y()
                painter.drawText(QRectF(x0, y - 9, x1 - x0, 18),
                                 align | Qt.AlignmentFlag.AlignVCenter, p.nickname)
        painter.save()
        painter.translate(band.center())
        painter.rotate(-90)
        bold = QtGui.QFont(self.font)
        bold.setBold(True)
        painter.setFont(bold)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(-self.h / 2, -self.BAND_W / 2, self.h, self.BAND_W),
                         Qt.AlignmentFlag.AlignCenter, self.comp.nickname)
        painter.restore()
        self._paint_balloon(painter)
        self._paint_modifiers(painter)

    def _paint_modifiers(self, painter):
        """Badges outside a grip: F flatten, G graft, S simplify, R reverse."""
        font = QtGui.QFont(self.font)
        font.setPointSizeF(self.font.pointSizeF() * 0.85)
        font.setBold(True)
        painter.setFont(font)
        for p, grip in self.grips.items():
            letters = {"flatten": "F", "graft": "G", "simplify": "S"}.get(p.modifier, "")
            letters += "R" if p.reverse else ""
            if not letters:
                continue
            w = 9 + 6 * len(letters)
            x = grip.pos().x() - 8 - w if p.is_input else grip.pos().x() + 8
            rect = QRectF(x, grip.pos().y() - 6, w, 12)
            painter.setPen(QtGui.QPen(OUTLINE, 1))
            painter.setBrush(QColor(255, 236, 140))
            painter.drawRoundedRect(rect, 3, 3)
            painter.setPen(TEXT)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, letters)

    def _paint_balloon(self, painter):
        if self.comp.state == OK:
            return
        colour = FILLS[self.comp.state][1]
        rect = QRectF(self.w / 2 - 9, -20, 18, 15)
        painter.setPen(QtGui.QPen(OUTLINE, 1))
        painter.setBrush(colour)
        painter.drawRoundedRect(rect, 4, 4)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "!" if self.comp.state == WARNING else "×")

    # behaviour ----------------------------------------------------------------
    def itemChange(self, change, value):
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.kscene.update_wires(self)
            self.kscene.edited.emit()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        c = self.comp
        tip = f"{c.name}\n{c.description}"
        if c.messages:
            tip += "\n\n" + "\n".join(c.messages)
        self.setToolTip(tip)
        super().hoverEnterEvent(event)


class SliderItem(ComponentItem):
    H = 24
    W = 250

    def layout(self):
        fm = QtGui.QFontMetrics(self.font)
        self.label_w = max(fm.horizontalAdvance(self.comp.nickname) + 18, 52)
        self.w, self.h = self.W, self.H
        self.x0, self.x1 = self.label_w + 12, self.w - 14
        self._sliding = False
        self._place_grips()

    def knob_x(self):
        c = self.comp
        t = (c.value - c.minimum) / ((c.maximum - c.minimum) or 1)
        return self.x0 + t * (self.x1 - self.x0)

    def slide_to(self, x):
        c = self.comp
        t = min(max((x - self.x0) / (self.x1 - self.x0), 0.0), 1.0)
        if c.set_value(c.minimum + t * (c.maximum - c.minimum)):
            self.update()
            self.kscene.request_solve()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        top, bottom = self.fill()
        painter.setPen(QtGui.QPen(OUTLINE, 1.2))
        painter.setBrush(_gradient(self.h, top, bottom))
        painter.drawRoundedRect(QRectF(0, 0, self.w, self.h), 5, 5)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(BAND)
        painter.drawRoundedRect(QRectF(3, 3, self.label_w, self.h - 6), 3, 3)
        if _lod(painter) < 0.45:
            return
        painter.setFont(self.font)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(3, 3, self.label_w, self.h - 6), Qt.AlignmentFlag.AlignCenter,
                         self.comp.nickname)
        y = self.h / 2
        painter.setPen(QtGui.QPen(QColor(90, 90, 90), 1))
        painter.drawLine(QPointF(self.x0, y), QPointF(self.x1, y))
        for i in range(11):
            x = self.x0 + i * (self.x1 - self.x0) / 10
            painter.drawLine(QPointF(x, y - (3 if i % 5 else 5)), QPointF(x, y))
        kx = self.knob_x()
        painter.setPen(QtGui.QPen(OUTLINE, 1))
        painter.setBrush(QColor(40, 40, 40))
        painter.drawPolygon(QtGui.QPolygonF([QPointF(kx, y - 7), QPointF(kx + 5, y),
                                             QPointF(kx, y + 7), QPointF(kx - 5, y)]))
        text = f"{self.comp.value:.{self.comp.decimals}f}"
        tw = QtGui.QFontMetrics(self.font).horizontalAdvance(text) + 8
        tx = kx + 8 if kx + 8 + tw < self.x1 + 10 else kx - 8 - tw
        tag = QRectF(tx, y - 8, tw, 16)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(tag, 3, 3)
        painter.setPen(TEXT)
        painter.drawText(tag, Qt.AlignmentFlag.AlignCenter, text)

    def _on_rail(self, pos):
        return self.x0 - 8 <= pos.x() <= self.x1 + 8

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_rail(event.pos()):
            self._sliding = True
            self.slide_to(event.pos().x())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._sliding:
            self.slide_to(event.pos().x())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._sliding:
            self._sliding = False
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        views = self.kscene.views()
        if views:
            views[0].edit_slider(self.comp)
        event.accept()


class PanelItem(ComponentItem):
    W, H = 190, 150

    def layout(self):
        self.w, self.h = getattr(self.comp, "size", (self.W, self.H))
        self._place_grips()

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        fill = FILLS["selected"][0] if self.isSelected() else PANEL_FILL
        painter.setPen(QtGui.QPen(OUTLINE, 1.1))
        painter.setBrush(fill)
        painter.drawRoundedRect(QRectF(0, 0, self.w, self.h), 2, 2)
        if _lod(painter) < 0.45:
            return
        font = QtGui.QFont("Consolas")
        font.setPointSizeF(self.font.pointSizeF())
        painter.setFont(font)
        rows = getattr(self.comp, "rows", [])
        fm = QtGui.QFontMetrics(font)
        y = 5
        for n, row in enumerate(rows):
            if y + fm.height() > self.h - 4:
                left = sum(1 for r in rows[n:] if r[0] == "item")
                painter.setPen(QColor(120, 120, 120))
                painter.drawText(QPointF(8, y + fm.ascent()), f"… {left} more item(s)")
                break
            if row[0] == "path":  # branch header, as in Grasshopper's panel
                painter.fillRect(QRectF(3, y, self.w - 6, fm.height()), QColor(232, 224, 150))
                painter.setPen(QColor(90, 80, 20))
                painter.drawText(QPointF(8, y + fm.ascent()), row[1])
            else:
                painter.setPen(QColor(130, 130, 130))
                painter.drawText(QPointF(10, y + fm.ascent()), str(row[1]))
                painter.setPen(TEXT)
                painter.drawText(QPointF(32, y + fm.ascent()), row[2])
            y += fm.height()


def item_for(comp, scene) -> ComponentItem:
    if isinstance(comp, lib.NumberSlider):
        return SliderItem(comp, scene)
    if isinstance(comp, lib.Panel):
        return PanelItem(comp, scene)
    return ComponentItem(comp, scene)


# --------------------------------------------------------------------------
# Scene: owns the graph-to-item mapping and schedules solves
# --------------------------------------------------------------------------
class KatydidScene(QtWidgets.QGraphicsScene):
    solved = QtCore.Signal(object)
    edited = QtCore.Signal()  # anything that changes the saved definition

    def __init__(self, graph, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.font = QtGui.QFont()
        self.font.setPointSizeF(8.0)
        self.items_by_comp: dict = {}
        self.wire_items: list[WireItem] = []
        self._pending = False
        # A timer object owned by the scene, not QTimer.singleShot(0, callable):
        # a static single-shot scheduled while FreeCAD was opening a document
        # was measured never to fire (tests/persist_smoke.py, 2026-10-13).
        self._solve_timer = QtCore.QTimer(self)
        self._solve_timer.setSingleShot(True)
        self._solve_timer.setInterval(0)
        self._solve_timer.timeout.connect(self.solve_now)
        self.setSceneRect(-20000, -20000, 40000, 40000)
        self.setItemIndexMethod(QtWidgets.QGraphicsScene.ItemIndexMethod.NoIndex)
        graph.listeners.append(self._on_solved)
        self.selectionChanged.connect(self._repaint_wires)

    def add_component(self, comp, pos: QPointF, centre=False) -> ComponentItem:
        self.graph.add(comp)
        item = self._add_item(comp, pos, centre)
        self.request_solve()
        return item

    def _add_item(self, comp, pos: QPointF, centre=False) -> ComponentItem:
        item = item_for(comp, self)
        if centre:
            pos = pos - QPointF(item.w / 2, item.h / 2)
        item.setPos(pos)
        self.addItem(item)
        self.items_by_comp[comp] = item
        return item

    # persistence --------------------------------------------------------------
    def to_json(self) -> str:
        positions = {c: (i.pos().x(), i.pos().y()) for c, i in self.items_by_comp.items()}
        return document.dumps(self.graph, positions)

    def load_json(self, text: str) -> list[str]:
        """Replace the canvas with a saved definition; returns load warnings."""
        self.clear_all()
        positions, warnings = document.build(self.graph, text)
        for comp in self.graph.components:
            self._add_item(comp, QPointF(*positions[comp]))
        self.rebuild_wires()
        self.edited.emit()
        self.solve_now()  # a load is one discrete event: solve it now, deterministically
        return warnings

    def remove_components(self, comps):
        for comp in comps:
            self.graph.remove(comp)
            self.removeItem(self.items_by_comp.pop(comp))
        self.rebuild_wires()
        self.request_solve()

    def clear_all(self):
        self.remove_components(list(self.items_by_comp))

    def grip(self, param) -> GripItem:
        return self.items_by_comp[param.owner].grips[param]

    def rebuild_wires(self):
        for w in self.wire_items:
            self.removeItem(w)
        self.wire_items = []
        for src, dst in self.graph.wires():
            w = WireItem(self.grip(src), self.grip(dst))
            self.addItem(w)
            self.wire_items.append(w)

    def update_wires(self, item=None):
        for w in self.wire_items:
            if item is None or item in (w.src.parentItem(), w.dst.parentItem()):
                w.update_path()

    def set_modifier(self, param, modifier):
        param.set_modifier(modifier)
        self.items_by_comp[param.owner].update()
        self.request_solve()

    def set_reverse(self, param, on):
        param.set_reverse(on)
        self.items_by_comp[param.owner].update()
        self.request_solve()

    def set_default(self, param, value):
        """The value an input uses when nothing is wired into it."""
        param.default = value
        param.owner.expire()
        self.items_by_comp[param.owner].update()
        self.request_solve()

    def edit_slider(self, comp, name, minimum, maximum, decimals, value):
        if not maximum > minimum:
            raise ValueError("Maximum must be greater than minimum")
        comp.nickname = name.strip() or comp.nickname
        comp.minimum, comp.maximum, comp.decimals = float(minimum), float(maximum), int(decimals)
        comp._set = None
        comp.set_value(value)
        item = self.items_by_comp[comp]
        item.prepareGeometryChange()
        item.layout()
        item.update()
        self.update_wires(item)
        self.request_solve()

    def set_preview(self, comp, on):
        comp.preview = bool(on)
        self.items_by_comp[comp].update()
        self.solved.emit([])   # refresh the 3D preview without a solve
        self.edited.emit()

    def connect_params(self, a, b, add=False) -> bool:
        out, inp = (a, b) if not a.is_input else (b, a)
        if not self.graph.can_connect(out, inp):
            return False
        if not add:
            for src in list(inp.sources):
                self.graph.disconnect(src, inp)
        self.graph.connect(out, inp)
        self.rebuild_wires()
        self.request_solve()
        return True

    def request_solve(self):
        """Coalesce edits into one solve on the next event-loop turn."""
        self.edited.emit()
        if not self._pending:
            self._pending = True
            self._solve_timer.start()

    def solve_now(self):
        self._pending = False
        self._solve_timer.stop()
        self.graph.solve()

    def _on_solved(self, solved):
        # Repaint only what the solve touched; everything else stays cached.
        touched = set(solved)
        for comp in solved:
            item = self.items_by_comp.get(comp)
            if item is not None:
                item.update()
        for w in self.wire_items:
            if w.src.param.owner in touched:
                w.update()
        self.solved.emit(solved)

    def _repaint_wires(self):
        for w in self.wire_items:
            w.update()


# --------------------------------------------------------------------------
# View: navigation, wiring gestures, search, drops
# --------------------------------------------------------------------------
class KatydidView(QtWidgets.QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QtGui.QPainter.RenderHint.Antialiasing
                            | QtGui.QPainter.RenderHint.TextAntialiasing)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)
        self.setCacheMode(QtWidgets.QGraphicsView.CacheModeFlag.CacheBackground)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._pan = None
        self._right_press = QPointF()
        self._drag = None   # (anchor grip, temp path item)
        self._search = None
        self.menu = None    # the last grip/component menu (kept for tests)
        self.dialog = None  # the last slider or value dialog (kept for tests)
        self.last_error = None

    # background ---------------------------------------------------------------
    def drawBackground(self, painter, rect):
        # Cached by the view (CacheBackground); redrawn only on pan and zoom.
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, False)
        painter.fillRect(rect, CANVAS_BG)
        zoom = self.transform().m11()
        for step, colour in ((20, GRID_MINOR), (100, GRID_MAJOR)):
            if step * zoom < 6:
                continue
            lines = []
            x = int(rect.left() // step) * step
            while x < rect.right():
                lines.append(QtCore.QLineF(x, rect.top(), x, rect.bottom()))
                x += step
            y = int(rect.top() // step) * step
            while y < rect.bottom():
                lines.append(QtCore.QLineF(rect.left(), y, rect.right(), y))
                y += step
            painter.setPen(QtGui.QPen(colour, 0))
            painter.drawLines(lines)

    # navigation ---------------------------------------------------------------
    def wheelEvent(self, event):
        factor = 1.0015 ** event.angleDelta().y()
        zoom = self.transform().m11() * factor
        if 0.1 <= zoom <= 5.0:
            self.scale(factor, factor)

    def fit_all(self):
        rect = self.scene().itemsBoundingRect()
        if rect.isNull():
            return
        self.fitInView(rect.adjusted(-40, -40, 40, 40), Qt.AspectRatioMode.KeepAspectRatio)
        zoom = min(max(self.transform().m11(), 0.7), 1.4)  # stay legible; pan for the rest
        self.resetTransform()
        self.scale(zoom, zoom)
        self.centerOn(rect.center())

    def place_at_centre(self, cls):
        centre = self.mapToScene(self.viewport().rect().center())
        self.scene().add_component(cls(), centre, centre=True)

    # mouse ----------------------------------------------------------------------
    def _grip_at(self, pos) -> GripItem | None:
        for item in self.items(pos):
            if isinstance(item, GripItem):
                return item
        return None

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.RightButton:
            self._pan = event.position()
            self._right_press = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            grip = self._grip_at(pos)
            if grip is not None:
                self._start_wire(grip, self.mapToScene(pos))
                event.accept()
                return
        super().mousePressEvent(event)

    def _start_wire(self, grip, scene_pos):
        scene = self.scene()
        anchor = grip
        p = grip.param
        if p.is_input and p.sources:  # pick the wire up off the input
            src = p.sources[-1]
            scene.graph.disconnect(src, p)
            scene.rebuild_wires()
            scene.request_solve()
            anchor = scene.grip(src)
        temp = QtWidgets.QGraphicsPathItem()
        temp.setPen(QtGui.QPen(WIRE, 1.6, Qt.PenStyle.DashLine))
        temp.setZValue(10)
        scene.addItem(temp)
        self._drag = (anchor, temp)
        self._update_drag(scene_pos)

    def _update_drag(self, scene_pos):
        anchor, temp = self._drag
        a = anchor.scenePos()
        temp.setPath(wire_path(scene_pos, a) if anchor.param.is_input else wire_path(a, scene_pos))

    def mouseMoveEvent(self, event):
        if self._pan is not None:
            delta = event.position() - self._pan
            self._pan = event.position()
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            return
        if self._drag is not None:
            self._update_drag(self.mapToScene(event.position().toPoint()))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton and self._pan is not None:
            self._pan = None
            self.viewport().unsetCursor()
            moved = (event.position() - self._right_press).manhattanLength()
            if moved < 4:  # a click, not a pan: the grip or component menu
                self.open_menu(event.position().toPoint())
            return
        if self._drag is not None:
            anchor, temp = self._drag
            self._drag = None
            self.scene().removeItem(temp)
            target = self._grip_at(event.position().toPoint())
            if target is not None and target.param.is_input != anchor.param.is_input:
                add = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.scene().connect_params(anchor.param, target.param, add=add)
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        pos = event.position().toPoint()
        if not [i for i in self.items(pos) if isinstance(i, (ComponentItem, GripItem))]:
            self.open_search(pos)
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        event.accept()  # right-drag pans; a right-click is handled on release

    # menus ----------------------------------------------------------------------
    def open_menu(self, view_pos) -> QtWidgets.QMenu | None:
        """Grip menu (data mapping) or component menu, like Grasshopper's."""
        scene = self.scene()
        grip = self._grip_at(view_pos)
        items = [i for i in self.items(view_pos) if isinstance(i, ComponentItem)]
        menu = QtWidgets.QMenu(self)
        if grip is not None:
            p = grip.param
            title = menu.addAction(f"{p.name} ({'input' if p.is_input else 'output'})")
            title.setEnabled(False)
            menu.addSeparator()
            for label, mod in (("Flatten", "flatten"), ("Graft", "graft"), ("Simplify", "simplify")):
                act = menu.addAction(label)
                act.setCheckable(True)
                act.setChecked(p.modifier == mod)
                act.triggered.connect(
                    lambda on, m=mod: scene.set_modifier(p, m if on else None))
            act = menu.addAction("Reverse")
            act.setCheckable(True)
            act.setChecked(p.reverse)
            act.triggered.connect(lambda on: scene.set_reverse(p, on))
            if p.is_input and param_kind(p) is not None:
                menu.addSeparator()
                menu.addAction("Set value…", lambda: self.edit_default(p))
        elif items:
            comp = items[0].comp
            title = menu.addAction(comp.name)
            title.setEnabled(False)
            menu.addSeparator()
            act = menu.addAction("Preview")
            act.setCheckable(True)
            act.setChecked(comp.preview)
            act.triggered.connect(lambda on: scene.set_preview(comp, on))
            menu.addAction("Delete", lambda: scene.remove_components([comp]))
        else:
            return None
        menu.popup(self.viewport().mapToGlobal(view_pos))
        self.menu = menu
        return menu

    # keyboard -------------------------------------------------------------------
    OWN_KEYS = {Qt.Key.Key_Delete, Qt.Key.Key_Backspace, Qt.Key.Key_Q}

    def event(self, event):
        # FreeCAD binds Delete (delete document objects) and Ctrl+Q (quit) on the
        # main window; claim them while the canvas has focus.
        if event.type() == QtCore.QEvent.Type.ShortcutOverride and event.key() in self.OWN_KEYS:
            event.accept()
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        scene = self.scene()
        selected = [i.comp for i in scene.selectedItems() if isinstance(i, ComponentItem)]
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace) and selected:
            scene.remove_components(selected)
            return
        if event.key() == Qt.Key.Key_Q and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            for comp in selected:
                comp.preview = not comp.preview
            scene.solved.emit([])
            scene.edited.emit()
            for item in scene.selectedItems():
                item.update()
            return
        super().keyPressEvent(event)

    # dialogs --------------------------------------------------------------------
    def edit_slider(self, comp) -> "SliderDialog":
        """Double-click a slider: name, range, decimals and value."""
        self.dialog = SliderDialog(self, comp)
        self.dialog.open()
        return self.dialog

    def edit_default(self, param) -> QtWidgets.QInputDialog:
        """Right-click an input > Set value…: the value used when nothing is wired."""
        kind = param_kind(param)
        dlg = QtWidgets.QInputDialog(self)
        dlg.setWindowTitle(f"{param.owner.nickname}: {param.name}")
        dlg.setLabelText({"number": "Number", "text": "Text", "bool": "Value",
                          "point": "Point or vector (x, y, z)"}[kind])
        if kind == "bool":
            dlg.setComboBoxItems(["True", "False"])
        dlg.setTextValue(format_value(kind, param.default))

        def accept(text):
            if not text.strip() and param.optional:
                self.scene().set_default(param, None)  # an empty optional input: no value
                return
            try:
                value = parse_value(kind, text)
            except ValueError as exc:
                QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), f"Not changed: {exc}", self)
                self.last_error = str(exc)
                return
            self.scene().set_default(param, value)

        dlg.textValueSelected.connect(accept)
        dlg.open()
        self.dialog = dlg
        return dlg

    # search ---------------------------------------------------------------------
    def open_search(self, view_pos):
        if self._search is not None:
            self._search.close()
        self._search = SearchPopup(self, view_pos)
        self._search.show()
        self._search.edit.setFocus()

    # drops ----------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(MIME):
            return super().dropEvent(event)
        name = bytes(event.mimeData().data(MIME)).decode()
        pos = self.mapToScene(event.position().toPoint())
        self.scene().add_component(lib.by_name(name)(), pos, centre=True)
        event.acceptProposedAction()


class SliderDialog(QtWidgets.QDialog):
    """Edit a Number Slider: name, minimum, maximum, decimals and value."""

    def __init__(self, view, comp):
        super().__init__(view)
        self.view, self.comp = view, comp
        self.setWindowTitle("Number Slider")
        form = QtWidgets.QFormLayout(self)
        self.name = QtWidgets.QLineEdit(comp.nickname)

        def number(v):
            edit = QtWidgets.QLineEdit(f"{v:g}")
            edit.setValidator(QtGui.QDoubleValidator(-1e12, 1e12, 9, edit))
            return edit

        self.minimum, self.maximum, self.value = number(comp.minimum), number(comp.maximum), number(comp.value)
        self.decimals = QtWidgets.QSpinBox()
        self.decimals.setRange(0, 6)
        self.decimals.setValue(int(comp.decimals))
        for label, widget in (("Name", self.name), ("Minimum", self.minimum), ("Maximum", self.maximum),
                              ("Decimals", self.decimals), ("Value", self.value)):
            form.addRow(label, widget)
        self.buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok
                                                  | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        for edit in (self.minimum, self.maximum, self.value):
            edit.textChanged.connect(self._validate)
        self.accepted.connect(self._apply)

    def _numbers(self):
        try:
            return float(self.minimum.text()), float(self.maximum.text()), float(self.value.text())
        except ValueError:
            return None

    def _validate(self):
        n = self._numbers()
        ok = n is not None and n[1] > n[0]
        self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setEnabled(ok)

    def _apply(self):
        n = self._numbers()
        if n is not None and n[1] > n[0]:
            self.view.scene().edit_slider(self.comp, self.name.text(), n[0], n[1],
                                          self.decimals.value(), n[2])


class SearchPopup(QtWidgets.QFrame):
    """Double-click search box, placed under the cursor."""

    def __init__(self, view, view_pos):
        super().__init__(view.viewport())
        self.view = view
        self.scene_pos = view.mapToScene(view_pos)
        self.setFrameShape(QtWidgets.QFrame.Shape.Box)
        self.setStyleSheet("SearchPopup { background: #f4f4f4; border: 1px solid #262626;"
                           " border-radius: 4px; }")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)
        self.edit = QtWidgets.QLineEdit()
        self.edit.setPlaceholderText("Search components…")
        self.list = QtWidgets.QListWidget()
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setIconSize(QtCore.QSize(20, 20))
        self.list.setFixedHeight(150)
        lay.addWidget(self.edit)
        lay.addWidget(self.list)
        self.setFixedWidth(240)
        self.move(view_pos - QtCore.QPoint(20, 14))
        self.edit.textChanged.connect(self.filter)
        self.edit.returnPressed.connect(self.accept_current)
        self.list.itemClicked.connect(lambda _: self.accept_current())
        self.edit.installEventFilter(self)
        self.filter("")

    def filter(self, text):
        self.list.clear()
        text = text.lower().strip()
        for cls in lib.REGISTRY:
            haystack = f"{cls.name} {cls.nickname} {cls.category} {cls.description}".lower()
            if text in haystack:
                item = QtWidgets.QListWidgetItem(make_icon(cls), f"{cls.name}   ·  {cls.category}")
                item.setData(Qt.ItemDataRole.UserRole, cls.__name__)
                self.list.addItem(item)
        self.list.setCurrentRow(0)

    def accept_current(self):
        item = self.list.currentItem()
        if item is not None:
            cls = lib.by_name(item.data(Qt.ItemDataRole.UserRole))
            self.view.scene().add_component(cls(), self.scene_pos, centre=True)
        self.close()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.close()
                return True
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                step = 1 if key == Qt.Key.Key_Down else -1
                row = min(max(self.list.currentRow() + step, 0), self.list.count() - 1)
                self.list.setCurrentRow(row)
                return True
        if event.type() == QtCore.QEvent.Type.FocusOut:
            QtCore.QTimer.singleShot(0, self.close)
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        if self.view._search is self:
            self.view._search = None
        self.view.setFocus()
        super().closeEvent(event)


# --------------------------------------------------------------------------
# Ribbon: component tabs by category
# --------------------------------------------------------------------------
class PaletteButton(QtWidgets.QToolButton):
    def __init__(self, cls, view):
        super().__init__()
        self.cls, self.view = cls, view
        self.setIcon(make_icon(cls, 64))
        self.setIconSize(QtCore.QSize(32, 32))
        self.setFixedSize(40, 40)
        self.setAutoRaise(True)
        self.setToolTip(f"{cls.name}\n{cls.description}\n\nClick to place, or drag onto the canvas")
        self._press = None
        self.clicked.connect(lambda: view.place_at_centre(cls))

    def mousePressEvent(self, event):
        self._press = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press is not None and (event.position().toPoint() - self._press).manhattanLength() \
                >= QtWidgets.QApplication.startDragDistance():
            self._press = None
            self.setDown(False)
            mime = QtCore.QMimeData()
            mime.setData(MIME, QtCore.QByteArray(self.cls.__name__.encode()))
            drag = QtGui.QDrag(self)
            drag.setMimeData(mime)
            drag.setPixmap(self.icon().pixmap(30, 30))
            drag.exec(Qt.DropAction.CopyAction)
            return
        super().mouseMoveEvent(event)


class Ribbon(QtWidgets.QTabWidget):
    def __init__(self, view, parent=None):
        super().__init__(parent)
        self.setObjectName("KatydidRibbon")
        self.setDocumentMode(True)
        # The selected tab pairs Highlight with HighlightedText, so its label is
        # always readable; the other tabs keep the theme's look. Left to the
        # application stylesheet, one theme drew it as a black box with no text.
        self.tabBar().setStyleSheet(
            "QTabBar::tab:selected { background: palette(highlight); color: palette(highlighted-text); }")
        for cat in lib.CATEGORIES:
            page = QtWidgets.QWidget()
            row = QtWidgets.QHBoxLayout(page)
            row.setContentsMargins(4, 2, 4, 2)
            row.setSpacing(2)
            for cls in lib.REGISTRY:
                if cls.category == cat:
                    row.addWidget(PaletteButton(cls, view))
            row.addStretch(1)
            self.addTab(page, cat)
        self.setFixedHeight(self.tabBar().sizeHint().height() + 48)
