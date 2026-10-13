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
    """A Part.Vertex, a FreeCAD.Vector or an (x, y, z) sequence, as a FreeCAD.Vector."""
    FreeCAD, _ = _part()
    if hasattr(p, "Point"):
        return p.Point
    if isinstance(p, (tuple, list)):
        return FreeCAD.Vector(*p)
    if hasattr(p, "x"):
        return FreeCAD.Vector(p.x, p.y, p.z)
    raise TypeError(f"Expected a point or vector, got {type(p).__name__}")


def _vertex(v):
    _, Part = _part()
    return Part.Vertex(v)


def _edge(curve):
    """A single curve: an Edge, or a Wire made of exactly one edge."""
    if getattr(curve, "ShapeType", None) == "Edge":
        return curve
    edges = getattr(curve, "Edges", [])
    if len(edges) == 1:
        return edges[0]
    raise ValueError("Expected a single curve")


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
        self.size = (190, 150)

    def write_state(self):
        return {"size": list(self.size)} if tuple(self.size) != (190, 150) else {}

    def read_state(self, state):
        if "size" in state:
            self.size = tuple(state["size"])

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
    if hasattr(item, "x") and hasattr(item, "Length"):  # FreeCAD.Vector
        return f"<{_num(item.x)}, {_num(item.y)}, {_num(item.z)}>"
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


# --------------------------------------------------------------------------
# Maths
# --------------------------------------------------------------------------
class Range(Component):
    name = "Range"
    nickname = "Range"
    glyph = "a…b"
    category = "Maths"
    description = "Evenly spaced numbers from start to end"

    def setup(self):
        self.add_input("Start", "S", "First number", default=0.0)
        self.add_input("End", "E", "Last number", default=1.0)
        self.add_input("Steps", "N", "Number of steps (values = steps + 1)", default=10.0)
        self.add_output("Range", "R", "The numbers", access=LIST)

    def solve_instance(self, start, end, steps):
        n = int(steps)
        if n < 1:
            raise ValueError("Steps must be at least 1")
        return [start + (end - start) * i / n for i in range(n + 1)]


class Expression(Component):
    name = "Expression"
    nickname = "Expr"
    glyph = "f(x)"
    category = "Maths"
    description = "Evaluate a formula in x, y and z (safe: arithmetic and math functions only)"

    def setup(self):
        self.add_input("Formula", "F", "For example: x*2 + sin(y)", default="x")
        self.add_input("x", "x", "Variable x", default=0.0)
        self.add_input("y", "y", "Variable y", default=0.0)
        self.add_input("z", "z", "Variable z", default=0.0)
        self.add_output("Result", "R", "Value of the formula")

    def solve_instance(self, formula, x, y, z):
        from .expr import evaluate
        return evaluate(str(formula), x=x, y=y, z=z)


class Remap(Component):
    name = "Remap Numbers"
    nickname = "ReMap"
    glyph = "↦"
    category = "Maths"
    description = "Map a value from a source range to a target range"

    def setup(self):
        self.add_input("Value", "V", "Value to remap")
        self.add_input("Source start", "S0", "Source range start", default=0.0)
        self.add_input("Source end", "S1", "Source range end", default=1.0)
        self.add_input("Target start", "T0", "Target range start", default=0.0)
        self.add_input("Target end", "T1", "Target range end", default=1.0)
        self.add_output("Mapped", "R", "Remapped value")

    def solve_instance(self, v, s0, s1, t0, t1):
        if s1 == s0:
            raise ValueError("Source range has zero length")
        return t0 + (v - s0) * (t1 - t0) / (s1 - s0)


class Bounds(Component):
    name = "Bounds"
    nickname = "Bnd"
    glyph = "⌊⌉"
    category = "Maths"
    description = "Smallest and largest number in each list"

    def setup(self):
        self.add_input("Numbers", "N", "Numbers", access=LIST)
        self.add_output("Minimum", "Min", "Smallest number")
        self.add_output("Maximum", "Max", "Largest number")

    def solve_instance(self, numbers):
        return min(numbers), max(numbers)


# --------------------------------------------------------------------------
# Sets (lists)
# --------------------------------------------------------------------------
class ListItem(Component):
    name = "List Item"
    nickname = "Item"
    glyph = "[i]"
    category = "Sets"
    description = "The item at an index (wraps around by default)"

    def setup(self):
        self.add_input("List", "L", "List to pick from", access=LIST)
        self.add_input("Index", "i", "Item index", default=0.0)
        self.add_input("Wrap", "W", "Wrap indices outside the list", default=True)
        self.add_output("Item", "i", "The item")

    def solve_instance(self, items, index, wrap):
        i = int(index)
        if wrap:
            i %= len(items)
        elif not -len(items) <= i < len(items):
            raise IndexError(f"Index {i} is outside the list of {len(items)}")
        return items[i]


class ListLength(Component):
    name = "List Length"
    nickname = "Lng"
    glyph = "#"
    category = "Sets"
    description = "Number of items in each list"

    def setup(self):
        self.add_input("List", "L", "List to measure", access=LIST, optional=True)
        self.add_output("Length", "L", "Number of items")

    def solve_instance(self, items):
        return float(len(items))


class CullPattern(Component):
    name = "Cull Pattern"
    nickname = "Cull"
    glyph = "✂"
    category = "Sets"
    description = "Keep the items where a repeating True/False pattern is True"

    def setup(self):
        self.add_input("List", "L", "List to cull", access=LIST)
        self.add_input("Pattern", "P", "True keeps, False removes; repeats", access=LIST, default=True)
        self.add_output("List", "L", "Kept items", access=LIST)

    def solve_instance(self, items, pattern):
        return [item for i, item in enumerate(items) if pattern[i % len(pattern)]]


class ShiftList(Component):
    name = "Shift List"
    nickname = "Shift"
    glyph = "⇆"
    category = "Sets"
    description = "Move items along the list"

    def setup(self):
        self.add_input("List", "L", "List to shift", access=LIST)
        self.add_input("Shift", "S", "Positions to shift by", default=1.0)
        self.add_input("Wrap", "W", "Bring items round to the other end", default=True)
        self.add_output("List", "L", "Shifted list", access=LIST)

    def solve_instance(self, items, shift, wrap):
        s = int(shift)
        if wrap:
            s %= len(items)
            return items[s:] + items[:s]
        return items[s:] if s >= 0 else items[:s]


# --------------------------------------------------------------------------
# Vector
# --------------------------------------------------------------------------
class ConstructPoint(Component):
    name = "Construct Point"
    nickname = "Pt"
    glyph = "•"
    category = "Vector"
    description = "Point from X, Y and Z"

    def setup(self):
        self.add_input("X", "X", "X coordinate", default=0.0)
        self.add_input("Y", "Y", "Y coordinate", default=0.0)
        self.add_input("Z", "Z", "Z coordinate", default=0.0)
        self.add_output("Point", "Pt", "The point")

    def solve_instance(self, x, y, z):
        FreeCAD, _ = _part()
        return _vertex(FreeCAD.Vector(x, y, z))


class VectorXYZ(Component):
    name = "Vector XYZ"
    nickname = "Vec"
    glyph = "↗"
    category = "Vector"
    description = "Vector from X, Y and Z"

    def setup(self):
        self.add_input("X", "X", "X component", default=0.0)
        self.add_input("Y", "Y", "Y component", default=0.0)
        self.add_input("Z", "Z", "Z component", default=0.0)
        self.add_output("Vector", "V", "The vector")
        self.add_output("Length", "L", "Its length")

    def solve_instance(self, x, y, z):
        FreeCAD, _ = _part()
        v = FreeCAD.Vector(x, y, z)
        return v, v.Length


class Vector2Pt(Component):
    name = "Vector 2Pt"
    nickname = "Vec2Pt"
    glyph = "A→B"
    category = "Vector"
    description = "Vector from point A to point B"

    def setup(self):
        self.add_input("Point A", "A", "Start point")
        self.add_input("Point B", "B", "End point")
        self.add_output("Vector", "V", "B - A")
        self.add_output("Length", "L", "Distance from A to B")

    def solve_instance(self, a, b):
        v = _point(b) - _point(a)
        return v, v.Length


class Deconstruct(Component):
    name = "Deconstruct"
    nickname = "pDecon"
    glyph = "xyz"
    category = "Vector"
    description = "X, Y and Z of a point or vector"

    def setup(self):
        self.add_input("Point", "P", "Point or vector")
        self.add_output("X", "X", "X coordinate")
        self.add_output("Y", "Y", "Y coordinate")
        self.add_output("Z", "Z", "Z coordinate")

    def solve_instance(self, p):
        v = _point(p)
        return v.x, v.y, v.z


class Distance(Component):
    name = "Distance"
    nickname = "Dist"
    glyph = "|AB|"
    category = "Vector"
    description = "Distance between two points"

    def setup(self):
        self.add_input("Point A", "A", "First point")
        self.add_input("Point B", "B", "Second point")
        self.add_output("Distance", "D", "Distance from A to B")

    def solve_instance(self, a, b):
        return (_point(b) - _point(a)).Length


# --------------------------------------------------------------------------
# Curves
# --------------------------------------------------------------------------
class CircleCNR(Component):
    name = "Circle CNR"
    nickname = "Circle"
    glyph = "◎"
    category = "Curve"
    description = "Circle from centre, normal and radius"

    def setup(self):
        self.add_input("Center", "C", "Centre point", default=(0.0, 0.0, 0.0))
        self.add_input("Normal", "N", "Normal of the circle's plane", default=(0.0, 0.0, 1.0))
        self.add_input("Radius", "R", "Radius", default=1.0)
        self.add_output("Circle", "C", "Resulting circle")

    def solve_instance(self, c, n, r):
        if r <= 0:
            raise ValueError("Radius must be positive")
        _, Part = _part()
        normal = _point(n)
        if normal.Length == 0:
            raise ValueError("Normal must not be zero")
        return Part.makeCircle(r, _point(c), normal)


class Line(Component):
    name = "Line"
    nickname = "Ln"
    glyph = "/"
    category = "Curve"
    description = "Straight line between two points"

    def setup(self):
        self.add_input("Start", "A", "Start point", default=(0.0, 0.0, 0.0))
        self.add_input("End", "B", "End point", default=(10.0, 0.0, 0.0))
        self.add_output("Line", "L", "Resulting line")

    def solve_instance(self, a, b):
        _, Part = _part()
        pa, pb = _point(a), _point(b)
        if (pb - pa).Length == 0:
            raise ValueError("Start and end are the same point")
        return Part.LineSegment(pa, pb).toShape()


class Arc3Pt(Component):
    name = "Arc 3Pt"
    nickname = "Arc"
    glyph = "⌒"
    category = "Curve"
    description = "Arc through three points"

    def setup(self):
        self.add_input("Start", "A", "Start point")
        self.add_input("Through", "B", "Point on the arc")
        self.add_input("End", "C", "End point")
        self.add_output("Arc", "A", "Resulting arc")

    def solve_instance(self, a, b, c):
        _, Part = _part()
        return Part.Arc(_point(a), _point(b), _point(c)).toShape()


class Interpolate(Component):
    name = "Interpolate"
    nickname = "IntCrv"
    glyph = "∿"
    category = "Curve"
    description = "Smooth curve through a list of points"

    def setup(self):
        self.add_input("Vertices", "V", "Points, in order", access=LIST)
        self.add_input("Periodic", "P", "Close the curve smoothly", default=False)
        self.add_output("Curve", "C", "Resulting curve")

    def solve_instance(self, vertices, periodic):
        if len(vertices) < 2:
            raise ValueError("Interpolation needs at least two points")
        _, Part = _part()
        curve = Part.BSplineCurve()
        curve.interpolate([_point(v) for v in vertices], PeriodicFlag=bool(periodic))
        return curve.toShape()


class EvaluateCurve(Component):
    name = "Evaluate Curve"
    nickname = "Eval"
    glyph = "c(t)"
    category = "Curve"
    description = "Point and tangent at a normalised parameter (0 = start, 1 = end)"

    def setup(self):
        self.add_input("Curve", "C", "Curve to evaluate")
        self.add_input("Parameter", "t", "0 to 1 along the curve", default=0.5)
        self.add_output("Point", "P", "Point on the curve")
        self.add_output("Tangent", "T", "Unit tangent there")

    def solve_instance(self, curve, t):
        edge = _edge(curve)
        u = edge.FirstParameter + t * (edge.LastParameter - edge.FirstParameter)
        tangent = edge.tangentAt(u)
        return _vertex(edge.valueAt(u)), tangent


class OffsetCurve(Component):
    name = "Offset Curve"
    nickname = "Offset"
    glyph = "⊂⊃"
    category = "Curve"
    description = "Offset a planar curve in its own plane"

    def setup(self):
        self.add_input("Curve", "C", "Planar curve")
        self.add_input("Distance", "D", "Offset distance (negative goes inward)", default=1.0)
        self.add_output("Curve", "C", "Offset curve")

    def solve_instance(self, curve, d):
        _, Part = _part()
        wire = curve if curve.ShapeType == "Wire" else Part.Wire(curve.Edges)
        return wire.makeOffset2D(d, join=0, fill=False, openResult=not wire.isClosed())


# --------------------------------------------------------------------------
# Surfaces
# --------------------------------------------------------------------------
class Extrude(Component):
    name = "Extrude"
    nickname = "Extr"
    glyph = "⇑"
    category = "Surface"
    description = "Extrude a curve or surface along a vector"

    def setup(self):
        self.add_input("Base", "B", "Curve or surface to extrude")
        self.add_input("Direction", "D", "Extrusion vector", default=(0.0, 0.0, 10.0))
        self.add_output("Extrusion", "E", "Resulting surface or solid")

    def solve_instance(self, base, direction):
        d = _point(direction)
        if d.Length == 0:
            raise ValueError("Direction must not be zero")
        return base.extrude(d)


class Pipe(Component):
    name = "Pipe"
    nickname = "Pipe"
    glyph = "⊙"
    category = "Surface"
    description = "Round solid pipe along a curve"

    def setup(self):
        self.add_input("Curve", "C", "Rail curve")
        self.add_input("Radius", "R", "Pipe radius", default=1.0)
        self.add_output("Pipe", "P", "Resulting solid")

    def solve_instance(self, curve, r):
        if r <= 0:
            raise ValueError("Radius must be positive")
        _, Part = _part()
        rail = curve if curve.ShapeType == "Wire" else Part.Wire(curve.Edges)
        first = rail.Edges[0]
        start, tangent = first.valueAt(first.FirstParameter), first.tangentAt(first.FirstParameter)
        profile = Part.Wire(Part.makeCircle(r, start, tangent))
        return rail.makePipeShell([profile], True, True)


class CapHoles(Component):
    name = "Cap Holes"
    nickname = "Cap"
    glyph = "⊓"
    category = "Surface"
    description = "Close planar openings to make a solid"

    def setup(self):
        self.add_input("Shape", "B", "Open surface")
        self.add_output("Solid", "B", "Closed solid")

    def solve_instance(self, shape):
        _, Part = _part()
        shell = shape.Shells[0] if shape.Shells else Part.Shell(shape.Faces)
        free = shell.getFreeEdges().Edges
        if not free:
            solid = Part.Solid(shell)
        else:
            caps = [Part.Face(Part.Wire(group)) for group in Part.sortEdges(free)]
            closed = Part.Shell(shell.Faces + caps)
            # Without sewing the caps keep their own orientation and the solid is
            # invalid (measured: extruded r=2 circle gave volume 41.9 instead of 125.7).
            closed.sewShape()
            solid = Part.Solid(closed)
        if solid.Volume < 0:
            solid.reverse()
        if not solid.isValid():
            raise ValueError("The capped shape is not a valid solid")
        return solid


# --------------------------------------------------------------------------
# Transform
# --------------------------------------------------------------------------
class Rotate(Component):
    name = "Rotate"
    nickname = "Rot"
    glyph = "↻"
    category = "Transform"
    description = "Rotate geometry about an axis"

    def setup(self):
        self.add_input("Geometry", "G", "Geometry to rotate")
        self.add_input("Angle", "A", "Angle in degrees", default=90.0)
        self.add_input("Center", "C", "Point on the axis", default=(0.0, 0.0, 0.0))
        self.add_input("Axis", "X", "Axis direction", default=(0.0, 0.0, 1.0))
        self.add_output("Geometry", "G", "Rotated geometry")

    def solve_instance(self, g, angle, center, axis):
        return g.rotated(_point(center), _point(axis), angle)


class Scale(Component):
    name = "Scale"
    nickname = "Scale"
    glyph = "⤢"
    category = "Transform"
    description = "Scale geometry uniformly about a point"

    def setup(self):
        self.add_input("Geometry", "G", "Geometry to scale")
        self.add_input("Factor", "F", "Scale factor", default=2.0)
        self.add_input("Center", "C", "Fixed point", default=(0.0, 0.0, 0.0))
        self.add_output("Geometry", "G", "Scaled geometry")

    def solve_instance(self, g, factor, center):
        if factor == 0:
            raise ValueError("Factor must not be zero")
        out = g.copy()
        out.scale(factor, _point(center))
        return out


class Mirror(Component):
    name = "Mirror"
    nickname = "Mirror"
    glyph = "⇋"
    category = "Transform"
    description = "Mirror geometry in a plane"

    def setup(self):
        self.add_input("Geometry", "G", "Geometry to mirror")
        self.add_input("Point", "P", "Point on the mirror plane", default=(0.0, 0.0, 0.0))
        self.add_input("Normal", "N", "Normal of the mirror plane", default=(1.0, 0.0, 0.0))
        self.add_output("Geometry", "G", "Mirrored geometry")

    def solve_instance(self, g, point, normal):
        return g.mirror(_point(point), _point(normal))


class LinearArray(Component):
    name = "Linear Array"
    nickname = "ArrLin"
    glyph = "▭▭"
    category = "Transform"
    description = "Copies of geometry along a vector"

    def setup(self):
        self.add_input("Geometry", "G", "Geometry to copy")
        self.add_input("Direction", "D", "Step between copies", default=(10.0, 0.0, 0.0))
        self.add_input("Count", "N", "Number of copies", default=3.0)
        self.add_output("Geometry", "G", "The copies", access=LIST)

    def solve_instance(self, g, direction, count):
        step = _point(direction)
        return [g.translated(step * i) for i in range(max(int(count), 0))]


# --------------------------------------------------------------------------
# Intersect
# --------------------------------------------------------------------------
class Difference(Component):
    name = "Solid Difference"
    nickname = "SDiff"
    glyph = "∖"
    category = "Intersect"
    description = "Subtract every solid in B from A"

    def setup(self):
        self.add_input("Solid A", "A", "Solid to cut from")
        self.add_input("Solids B", "B", "Solids to subtract", access=LIST)
        self.add_output("Result", "R", "A minus B")

    def solve_instance(self, a, b):
        return a.cut(b).removeSplitter()


class Intersection(Component):
    name = "Solid Intersection"
    nickname = "SInt"
    glyph = "∩"
    category = "Intersect"
    description = "The volume shared by A and B"

    def setup(self):
        self.add_input("Solid A", "A", "First solid")
        self.add_input("Solid B", "B", "Second solid")
        self.add_output("Result", "R", "A and B")

    def solve_instance(self, a, b):
        result = a.common(b).removeSplitter()
        if result.isNull() or not result.Solids:
            raise ValueError("The solids do not overlap")
        return result


# --------------------------------------------------------------------------
# Tolerance (stack-ups and GD&T; the maths lives in tolerance.py)
# --------------------------------------------------------------------------
class Dimension(Component):
    name = "Dimension"
    nickname = "Dim"
    glyph = "±"
    category = "Tolerance"
    description = "A toleranced dimension in a stack-up chain"

    def setup(self):
        self.add_input("Nominal", "N", "Nominal value", default=10.0)
        self.add_input("Upper", "U", "Upper deviation (e.g. 0.1)", default=0.1)
        self.add_input("Lower", "L", "Lower deviation (e.g. -0.1)", default=-0.1)
        self.add_input("Direction", "D", "+1 if it runs from A toward B, -1 if back", default=1.0)
        self.add_input("Distribution", "S", "normal, uniform or triangular", default="normal")
        self.add_input("Name", "Nm", "Label for reports", default="")
        self.add_output("Dimension", "D", "The dimension")
        self.add_output("Mean", "M", "Equal-bilateral nominal")
        self.add_output("Tolerance", "T", "Equal-bilateral ± tolerance")

    def solve_instance(self, nominal, upper, lower, direction, distribution, name):
        from .tolerance import Dim
        d = Dim(nominal, upper, lower, 1 if direction >= 0 else -1, str(distribution).lower(), str(name))
        return d, d.mean, d.tol


class StackUp(Component):
    name = "Stack-up"
    nickname = "Stack"
    glyph = "Σ±"
    category = "Tolerance"
    description = "Worst-case, RSS and adjusted RSS stack-up of a chain of dimensions (Fischer)"

    def setup(self):
        self.add_input("Dimensions", "D", "The chain, from A to B", access=LIST)
        self.add_input("Factor", "F", "Adjustment factor for RSS", default=1.5)
        self.add_output("Nominal", "N", "Nominal distance A-B")
        self.add_output("Worst case", "WC", "Worst-case ± tolerance")
        self.add_output("RSS", "RSS", "Root-sum-square ± tolerance")
        self.add_output("Adjusted RSS", "ARSS", "RSS × factor")
        self.add_output("Worst min", "Wmin", "Worst-case minimum")
        self.add_output("Worst max", "Wmax", "Worst-case maximum")
        self.add_output("Adjusted min", "Amin", "Adjusted RSS minimum")
        self.add_output("Adjusted max", "Amax", "Adjusted RSS maximum")
        self.add_output("Report", "R", "Report lines", access=LIST)

    def solve_instance(self, dims, factor):
        from .tolerance import report, stack
        r = stack(dims, factor)
        wlo, whi = r.limits("worst")
        alo, ahi = r.limits("adjusted")
        return r.nominal, r.worst_case, r.rss, r.adjusted, wlo, whi, alo, ahi, report(dims, r)


class MonteCarlo(Component):
    name = "Monte Carlo Stack-up"
    nickname = "MC"
    glyph = "⚄"
    category = "Tolerance"
    description = "Random builds of the chain: spread, out-of-spec share and histogram"

    def setup(self):
        self.add_input("Dimensions", "D", "The chain, from A to B", access=LIST)
        self.add_input("Samples", "N", "Number of random builds", default=10000.0)
        self.add_input("Seed", "Sd", "Random seed (same seed, same result)", default=1.0)
        self.add_input("Sigmas", "k", "A normal tolerance is this many standard deviations", default=3.0)
        self.add_input("Lower limit", "LSL", "Lower spec limit of A-B", optional=True)
        self.add_input("Upper limit", "USL", "Upper spec limit of A-B", optional=True)
        self.add_output("Mean", "M", "Mean of A-B")
        self.add_output("Std dev", "σ", "Standard deviation of A-B")
        self.add_output("Out of spec", "%", "Percentage of builds outside the limits")
        self.add_output("Histogram", "H", "Text histogram", access=LIST)

    def solve_instance(self, dims, samples, seed, sigmas, low, high):
        from .tolerance import histogram, mean_std, monte_carlo, outside
        values = monte_carlo(dims, int(samples), int(seed), sigmas)
        m, s = mean_std(values)
        return m, s, 100.0 * outside(values, low, high), histogram(values)


class BonusTolerance(Component):
    name = "Bonus Tolerance"
    nickname = "Bonus"
    glyph = "Ⓜ"
    category = "Tolerance"
    description = "Bonus and total geometric tolerance at an actual size (Cogorno)"

    def setup(self):
        self.add_input("Actual size", "A", "Actual mating envelope size")
        self.add_input("MMC", "MMC", "Maximum material size")
        self.add_input("LMC", "LMC", "Least material size")
        self.add_input("Geometric tolerance", "T", "Tolerance in the feature control frame")
        self.add_input("Modifier", "Mod", "MMC, LMC or RFS", default="MMC")
        self.add_output("Bonus", "B", "Bonus tolerance")
        self.add_output("Total", "Tot", "Geometric + bonus")

    def solve_instance(self, actual, mmc, lmc, geometric, modifier):
        from .tolerance import bonus
        return bonus(actual, mmc, lmc, geometric, str(modifier))


class SizeBoundaries(Component):
    name = "Virtual & Resultant Condition"
    nickname = "VC/RC"
    glyph = "◌"
    category = "Tolerance"
    description = "Virtual and resultant condition of a feature of size at MMC (Cogorno)"

    def setup(self):
        self.add_input("MMC", "MMC", "Maximum material size")
        self.add_input("LMC", "LMC", "Least material size")
        self.add_input("Geometric tolerance", "T", "Tolerance at MMC")
        self.add_input("Internal", "Int", "True for a hole, False for a pin", default=True)
        self.add_output("Virtual condition", "VC", "Constant functional boundary")
        self.add_output("Resultant condition", "RC", "Worst-case opposite boundary")
        self.add_output("Inner boundary", "IB", "Worst-case inner boundary")
        self.add_output("Outer boundary", "OB", "Worst-case outer boundary")

    def solve_instance(self, mmc, lmc, geometric, internal):
        from .tolerance import boundaries
        b = boundaries(mmc, lmc, geometric, bool(internal))
        return b["virtual"], b["resultant"], b["inner"], b["outer"]


class PositionToPlusMinus(Component):
    name = "Position to ±"
    nickname = "Pos±"
    glyph = "⌖"
    category = "Tolerance"
    description = "Diametral position tolerance and size bonus as ± values for a stack (Fischer)"

    def setup(self):
        self.add_input("Position", "P", "Diametral position tolerance")
        self.add_input("Size tolerance", "S", "Size tolerance available as bonus", default=0.0)
        self.add_output("± position", "±P", "Half the position tolerance")
        self.add_output("± bonus", "±B", "Half the size tolerance")

    def solve_instance(self, position, size):
        from .tolerance import position_to_plus_minus
        return position_to_plus_minus(position, size)


REGISTRY = [NumberSlider, Panel,
            Addition, Multiplication, Range, Expression, Remap, Bounds,
            Series, ListItem, ListLength, CullPattern, ShiftList,
            ConstructPoint, VectorXYZ, Vector2Pt, Deconstruct, Distance,
            Circle, CircleCNR, Line, Arc3Pt, Polyline, Interpolate, DivideCurve, EvaluateCurve,
            OffsetCurve,
            Box, Sphere, Cylinder, Loft, Extrude, Pipe, CapHoles,
            Move, Rotate, Scale, Mirror, LinearArray,
            Union, Difference, Intersection,
            Dimension, StackUp, MonteCarlo, BonusTolerance, SizeBoundaries, PositionToPlusMinus]
CATEGORIES = ["Params", "Maths", "Sets", "Vector", "Curve", "Surface", "Transform", "Intersect",
              "Tolerance"]


def by_name(name: str):
    for cls in REGISTRY:
        if cls.__name__ == name or cls.name == name:
            return cls
    raise KeyError(name)
