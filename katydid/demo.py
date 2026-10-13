# SPDX-License-Identifier: LGPL-2.1-or-later
"""Demo definition: a row of boxes driven by four sliders."""

from __future__ import annotations

from . import components as lib
from .canvas import QPointF


def build(scene) -> dict:
    def slider(label, value, lo, hi, decimals=1):
        s = lib.NumberSlider(value, lo, hi, decimals)
        s.nickname = label
        return s

    c = {
        "width": slider("Width", 20, 5, 40),
        "height": slider("Height", 30, 0, 80),
        "spacing": slider("Spacing", 32, 10, 60),
        "count": slider("Count", 4, 1, 8, 0),
        "box": lib.Box(),
        "series": lib.Series(),
        "move": lib.Move(),
        "panel": lib.Panel(),
    }
    c["box"].preview = False  # only the moved copies are shown, as a user would set it
    layout = {"width": (-440, -150), "height": (-440, -90), "spacing": (-440, 10),
              "count": (-440, 70), "box": (-110, -150), "series": (-110, 10),
              "move": (140, -80), "panel": (140, 50)}
    for key, (x, y) in layout.items():
        scene.add_component(c[key], QPointF(x, y))

    g = scene.graph
    box, series, move = c["box"], c["series"], c["move"]
    g.connect(c["width"].outputs[0], box.inputs[0])
    g.connect(c["width"].outputs[0], box.inputs[1])
    g.connect(c["height"].outputs[0], box.inputs[2])
    g.connect(c["spacing"].outputs[0], series.inputs[1])
    g.connect(c["count"].outputs[0], series.inputs[2])
    g.connect(box.outputs[0], move.inputs[0])
    g.connect(series.outputs[0], move.inputs[1])
    g.connect(series.outputs[0], c["panel"].inputs[0])
    scene.rebuild_wires()
    scene.request_solve()
    return c


def build_tree(scene) -> dict:
    """Data trees: rings -> a branch of points per ring -> a polyline per branch
    -> one loft, which needs Flatten on its input to see all the polylines."""
    def slider(label, value, lo, hi, decimals=1):
        s = lib.NumberSlider(value, lo, hi, decimals)
        s.nickname = label
        return s

    c = {
        "rings": slider("Rings", 4, 2, 8, 0),
        "radius": slider("Radius", 20, 5, 40),
        "taper": slider("Taper", -3, -8, 8),
        "spacing": slider("Spacing", 12, 4, 30),
        "points": slider("Points", 6, 3, 16, 0),
        "radii": lib.Series(),
        "heights": lib.Series(),
        "circle": lib.Circle(),
        "divide": lib.DivideCurve(),
        "polyline": lib.Polyline(),
        "loft": lib.Loft(),
        "panel": lib.Panel(),
    }
    c["circle"].preview = False
    c["polyline"].inputs[1].default = True     # closed rings
    c["loft"].inputs[0].modifier = "flatten"   # one loft through every branch
    layout = {"rings": (-560, -40), "radius": (-560, -150), "taper": (-560, -95),
              "spacing": (-560, 15), "points": (-560, 110), "radii": (-250, -140),
              "heights": (-250, 0), "circle": (-60, -70), "divide": (110, -10),
              "polyline": (290, -90), "loft": (450, -90), "panel": (290, 40)}
    for key, (x, y) in layout.items():
        scene.add_component(c[key], QPointF(x, y))

    g = scene.graph
    g.connect(c["radius"].outputs[0], c["radii"].inputs[0])
    g.connect(c["taper"].outputs[0], c["radii"].inputs[1])
    g.connect(c["rings"].outputs[0], c["radii"].inputs[2])
    g.connect(c["spacing"].outputs[0], c["heights"].inputs[1])
    g.connect(c["rings"].outputs[0], c["heights"].inputs[2])
    g.connect(c["radii"].outputs[0], c["circle"].inputs[0])
    g.connect(c["heights"].outputs[0], c["circle"].inputs[1])
    g.connect(c["circle"].outputs[0], c["divide"].inputs[0])
    g.connect(c["points"].outputs[0], c["divide"].inputs[1])
    g.connect(c["divide"].outputs[0], c["polyline"].inputs[0])
    g.connect(c["divide"].outputs[0], c["panel"].inputs[0])
    g.connect(c["polyline"].outputs[0], c["loft"].inputs[0])
    scene.rebuild_wires()
    scene.request_solve()
    return c
