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
