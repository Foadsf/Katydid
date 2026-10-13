# SPDX-License-Identifier: LGPL-2.1-or-later
"""The component library. Geometry components import FreeCAD's Part module
lazily, so the registry itself loads without FreeCAD."""

from __future__ import annotations

from .engine import LIST, TREE, Component
from .tree import Tree, format_path


def _part():
    import FreeCAD
    import Part
    return FreeCAD, Part


def _point(p):
    """A Part.Vertex, or anything with x/y/z, as a FreeCAD.Vector."""
    FreeCAD, _ = _part()
    if hasattr(p, "Point"):
        return p.Point
    return FreeCAD.Vector(p.x, p.y, p.z)


# --------------------------------------------------------------------------
# Params
# --------------------------------------------------------------------------
class NumberSlider(Component):
    name = "Number Slider"
    nickname = "Slider"
    glyph = "◆"
    category = "Params"
    description = "Numeric slider for single values"

    def __init__(self, value=10.0, minimum=0.0, maximum=50.0, decimals=1):
        self.minimum, self.maximum, self.decimals = minimum, maximum, decimals
        self.value = value
        super().__init__()
        self.set_value(value, expire=False)

    def setup(self):
        self.add_output("Number", "N", "Slider value")

    def set_value(self, value, expire=True):
        value = round(min(max(value, self.minimum), self.maximum), self.decimals)
        if value == getattr(self, "_set", None):
            return False
        self.value = self._set = value
        if expire:
            self.expire()
        return True

    def compute(self):
        self.outputs[0].data = Tree.from_list([self.value])

    def write_state(self):
        return {"value": self.value, "minimum": self.minimum,
                "maximum": self.maximum, "decimals": self.decimals}

    def read_state(self, state):
        self.minimum = state.get("minimum", self.minimum)
        self.maximum = state.get("maximum", self.maximum)
        self.decimals = state.get("decimals", self.decimals)
        self._set = None
        self.set_value(state.get("value", self.value), expire=False)


class Panel(Component):
    name = "Panel"
    nickname = "Panel"
    glyph = "≡"
    category = "Params"
    description = "Shows the data flowing into it, branch by branch"

    def setup(self):
        self.add_input("Input", "", "Data to display", optional=True, access=TREE)
        self.rows: list[tuple] = []
        self.text_lines: list[str] = []

    def compute(self):
        tree = self.collect(self.inputs[0])
        self.rows, self.text_lines = [], []
        for path, items in tree.branches():
            self.rows.append(("path", format_path(path)))
            for i, item in enumerate(items):
                text = _format(item)
                self.rows.append(("item", i, text))
                self.text_lines.append(text)


def _num(v: float) -> str:
    """Display a number without floating-point dust: -6.4e-15 shows as 0."""
    return f"{0.0 if abs(v) < 1e-9 else v:.6g}"


def _format(item):
    if isinstance(item, float):
        return _num(item)
    shape_type = getattr(item, "ShapeType", None)
    if shape_type == "Vertex":
        p = item.Point
        return f"{{{_num(p.x)}, {_num(p.y)}, {_num(p.z)}}}"
    if shape_type == "Solid":
        return f"Solid (volume {item.Volume:.4g})"
    if shape_type:
        return shape_type
    return str(item)


# --------------------------------------------------------------------------
# Maths and sets
# --------------------------------------------------------------------------
class Addition(Component):
    name = "Addition"
    nickname = "A+B"
    glyph = "+"
    category = "Maths"
    description = "Add two numbers"

    def setup(self):
        self.add_input("A", "A", "First operand", default=0.0)
        self.add_input("B", "B", "Second operand", default=0.0)
        self.add_output("Result", "R", "A + B")

    def solve_instance(self, a, b):
        return a + b


class Multiplication(Component):
    name = "Multiplication"
    nickname = "A×B"
    glyph = "×"
    category = "Maths"
    description = "Multiply two numbers"

    def setup(self):
        self.add_input("A", "A", "First operand", default=1.0)
        self.add_input("B", "B", "Second operand", default=1.0)
        self.add_output("Result", "R", "A × B")

    def solve_instance(self, a, b):
        return a * b


class Series(Component):
    name = "Series"
    nickname = "Series"
    glyph = "1…n"
    category = "Sets"
    description = "Arithmetic sequence of numbers"

    def setup(self):
        self.add_input("Start", "S", "First number", default=0.0)
        self.add_input("Step", "N", "Step size", default=1.0)
        self.add_input("Count", "C", "Number of values", default=10.0)
        self.add_output("Series", "S", "The sequence", access=LIST)

    def solve_instance(self, start, step, count):
        return [start + i * step for i in range(max(int(count), 0))]


# --------------------------------------------------------------------------
# Curves
# --------------------------------------------------------------------------
class Circle(Component):
    name = "Circle"
    nickname = "Cir"
    glyph = "○"
    category = "Curve"
    description = "Circle in a horizontal plane"

    def setup(self):
        self.add_input("Radius", "R", "Circle radius", default=10.0)
        self.add_input("Height", "Z", "Height of the circle's plane", default=0.0)
        self.add_output("Circle", "C", "Resulting circle")

    def solve_instance(self, r, z):
        if r <= 0:
            raise ValueError("Radius must be positive")
        FreeCAD, Part = _part()
        return Part.makeCircle(r, FreeCAD.Vector(0, 0, z))


class DivideCurve(Component):
    name = "Divide Curve"
    nickname = "Divide"
    glyph = "÷"
    category = "Curve"
    description = "Points dividing a curve into equal-length segments"

    def setup(self):
        self.add_input("Curve", "C", "Curve to divide")
        self.add_input("Count", "N", "Number of segments", default=10.0)
        self.add_output("Points", "P", "Division points", access=LIST)

    def solve_instance(self, curve, count):
        n = int(count)
        if n < 1:
            raise ValueError("Count must be at least 1")
        _, Part = _part()
        points = curve.discretize(Number=n + 1)
        if curve.isClosed():
            points = points[:-1]  # the end point repeats the start
        return [Part.Vertex(p) for p in points]


class Polyline(Component):
    name = "Polyline"
    nickname = "PLine"
    glyph = "PL"
    category = "Curve"
    description = "Polyline through a list of points"

    def setup(self):
        self.add_input("Vertices", "V", "Points, in order", access=LIST)
        self.add_input("Closed", "C", "Close the polyline", default=False)
        self.add_output("Polyline", "Pl", "Resulting polyline")

    def solve_instance(self, vertices, closed):
        if len(vertices) < 2:
            raise ValueError("A polyline needs at least two points")
        _, Part = _part()
        points = [_point(v) for v in vertices]
        if closed:
            points.append(points[0])
        return Part.makePolygon(points)


# --------------------------------------------------------------------------
# Surfaces and solids
# --------------------------------------------------------------------------
class Box(Component):
    name = "Center Box"
    nickname = "Box"
    glyph = "Box"
    category = "Surface"
    description = "Box centred on the XY origin"

    def setup(self):
        self.add_input("X size", "X", "Size in X", default=10.0)
        self.add_input("Y size", "Y", "Size in Y", default=10.0)
        self.add_input("Z size", "Z", "Size in Z", default=10.0)
        self.add_output("Box", "B", "Resulting solid")

    def solve_instance(self, x, y, z):
        if min(x, y, z) <= 0:
            raise ValueError("Box dimensions must be positive")
        FreeCAD, Part = _part()
        return Part.makeBox(x, y, z, FreeCAD.Vector(-x / 2, -y / 2, 0))


class Sphere(Component):
    name = "Sphere"
    nickname = "Sph"
    glyph = "●"
    category = "Surface"
    description = "Sphere at the origin"

    def setup(self):
        self.add_input("Radius", "R", "Sphere radius", default=5.0)
        self.add_output("Sphere", "S", "Resulting solid")

    def solve_instance(self, r):
        if r <= 0:
            raise ValueError("Radius must be positive")
        _, Part = _part()
        return Part.makeSphere(r)


class Cylinder(Component):
    name = "Cylinder"
    nickname = "Cyl"
    glyph = "Cyl"
    category = "Surface"
    description = "Cylinder standing on the origin"

    def setup(self):
        self.add_input("Radius", "R", "Cylinder radius", default=5.0)
        self.add_input("Length", "L", "Cylinder height", default=10.0)
        self.add_output("Cylinder", "C", "Resulting solid")

    def solve_instance(self, r, h):
        if r <= 0 or h <= 0:
            raise ValueError("Radius and length must be positive")
        _, Part = _part()
        return Part.makeCylinder(r, h)


class Loft(Component):
    name = "Loft"
    nickname = "Loft"
    glyph = "Lft"
    category = "Surface"
    description = "Surface through a list of section curves"

    def setup(self):
        self.add_input("Curves", "C", "Section curves, in order", access=LIST)
        self.add_output("Loft", "L", "Resulting surface")

    def solve_instance(self, curves):
        if len(curves) < 2:
            raise ValueError("A loft needs at least two section curves")
        _, Part = _part()
        wires = [c if c.ShapeType == "Wire" else Part.Wire(c.Edges) for c in curves]
        return Part.makeLoft(wires, False, False)


# --------------------------------------------------------------------------
# Transform and intersect
# --------------------------------------------------------------------------
class Move(Component):
    name = "Move"
    nickname = "Move"
    glyph = "→"
    category = "Transform"
    description = "Translate geometry"

    def setup(self):
        self.add_input("Geometry", "G", "Geometry to move")
        self.add_input("X", "X", "Offset in X", default=0.0)
        self.add_input("Y", "Y", "Offset in Y", default=0.0)
        self.add_input("Z", "Z", "Offset in Z", default=0.0)
        self.add_output("Geometry", "G", "Moved geometry")

    def solve_instance(self, g, x, y, z):
        FreeCAD, _ = _part()
        return g.translated(FreeCAD.Vector(x, y, z))


class Union(Component):
    name = "Solid Union"
    nickname = "SUnion"
    glyph = "∪"
    category = "Intersect"
    description = "Boolean union of the solids in each branch"

    def setup(self):
        self.add_input("Breps", "B", "Solids to combine", access=LIST)
        self.add_output("Result", "R", "Union")

    def solve_instance(self, shapes):
        result = shapes[0].fuse(shapes[1:]) if len(shapes) > 1 else shapes[0]
        return result.removeSplitter()


REGISTRY = [NumberSlider, Panel, Addition, Multiplication, Series,
            Circle, DivideCurve, Polyline, Box, Sphere, Cylinder, Loft, Move, Union]
CATEGORIES = ["Params", "Maths", "Sets", "Curve", "Surface", "Transform", "Intersect"]


def by_name(name: str):
    for cls in REGISTRY:
        if cls.__name__ == name or cls.name == name:
            return cls
    raise KeyError(name)
