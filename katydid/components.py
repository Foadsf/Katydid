# SPDX-License-Identifier: LGPL-2.1-or-later
"""The component library. Geometry components import FreeCAD's Part module
lazily, so the registry itself loads without FreeCAD."""

from __future__ import annotations

from .engine import Component


def _part():
    import FreeCAD
    import Part
    return FreeCAD, Part


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
        self.state, self.messages = "ok", []
        self.outputs[0].data = [self.value]

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
    description = "Shows the data flowing into it"

    def setup(self):
        self.add_input("Input", "", "Data to display", optional=True)

    def solve_instance(self, item):
        return None

    def compute(self):
        self.state, self.messages = "ok", []
        self.text_lines = [_format(item) for item in self.collect(self.inputs[0])]


def _format(item):
    if isinstance(item, float):
        return f"{item:g}"
    shape_type = getattr(item, "ShapeType", None)
    if shape_type:
        return f"{shape_type} (volume {item.Volume:.4g})" if shape_type == "Solid" else shape_type
    return str(item)


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
    description = "Boolean union of all input solids"

    def setup(self):
        self.add_input("Breps", "B", "Solids to combine")
        self.add_output("Result", "R", "Union")

    def compute(self):
        # Works on the whole list at once (list access), not item by item.
        self.state, self.messages = "ok", []
        self.outputs[0].data = []
        shapes = self.collect(self.inputs[0])
        if not shapes:
            self.state = "warning"
            self.messages.append("Input parameter B failed to collect data")
            return
        try:
            result = shapes[0].fuse(shapes[1:]) if len(shapes) > 1 else shapes[0]
            self.outputs[0].data = [result.removeSplitter()]
        except Exception as exc:
            self.state = "error"
            self.messages.append(str(exc))


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
        self.add_output("Series", "S", "The sequence")

    def compute(self):
        self.state, self.messages = "ok", []
        self.outputs[0].data = []
        lists = [self.collect(p) for p in self.inputs]
        missing = [p.nickname for p, items in zip(self.inputs, lists) if not items]
        if missing:
            self.state = "warning"
            self.messages = [f"Input parameter {m} failed to collect data" for m in missing]
            return
        start, step, count = (items[0] for items in lists)
        self.outputs[0].data = [start + i * step for i in range(max(int(count), 0))]


REGISTRY = [NumberSlider, Panel, Addition, Multiplication, Series,
            Box, Sphere, Cylinder, Move, Union]
CATEGORIES = ["Params", "Maths", "Sets", "Surface", "Transform", "Intersect"]


def by_name(name: str):
    for cls in REGISTRY:
        if cls.__name__ == name or cls.name == name:
            return cls
    raise KeyError(name)
