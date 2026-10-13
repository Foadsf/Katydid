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


def build_attractor(scene) -> dict:
    """The classic attractor grid: a 10 x 10 point grid made with Graft, circles
    sized by distance to an attractor point, extruded by their radius."""
    def slider(label, value, lo, hi, decimals=1):
        s = lib.NumberSlider(value, lo, hi, decimals)
        s.nickname = label
        return s

    c = {
        "count": slider("Count", 10, 2, 20, 0),
        "spacing": slider("Spacing", 10, 2, 30),
        "ax": slider("Attractor X", 25, -20, 120),
        "ay": slider("Attractor Y", 65, -20, 120),
        "rmin": slider("Min radius", 0.5, 0.1, 5),
        "rmax": slider("Max radius", 4.5, 0.5, 10),
        "height": slider("Height", 3, 0, 10),
        "xs": lib.Series(),
        "ys": lib.Series(),
        "grid": lib.ConstructPoint(),
        "attractor": lib.ConstructPoint(),
        "dist": lib.Distance(),
        "bounds": lib.Bounds(),
        "remap": lib.Remap(),
        "circle": lib.CircleCNR(),
        "mult": lib.Multiplication(),
        "vec": lib.VectorXYZ(),
        "extrude": lib.Extrude(),
        "panel": lib.Panel(),
    }
    c["grid"].nickname = "Grid"
    c["attractor"].nickname = "Attractor"
    c["grid"].inputs[1].modifier = "graft"      # Y grafted: every X meets every Y
    c["bounds"].inputs[0].modifier = "flatten"  # one min/max over the whole grid
    c["grid"].preview = False
    c["circle"].preview = False
    layout = {"count": (-700, 40), "spacing": (-700, -20), "ax": (-700, 140), "ay": (-700, 200),
              "rmin": (-700, 290), "rmax": (-700, 350), "height": (-700, 420),
              "xs": (-400, -80), "ys": (-400, 20), "attractor": (-400, 150),
              "grid": (-200, -40), "dist": (-30, 40), "bounds": (130, 120), "remap": (300, 40),
              "circle": (500, -40), "mult": (500, 160), "vec": (660, 150), "extrude": (840, 40),
              "panel": (660, 270)}
    for key, (x, y) in layout.items():
        scene.add_component(c[key], QPointF(x, y))

    g = scene.graph
    wires = [("spacing", 0, "xs", 1), ("count", 0, "xs", 2), ("spacing", 0, "ys", 1),
             ("count", 0, "ys", 2), ("xs", 0, "grid", 0), ("ys", 0, "grid", 1),
             ("ax", 0, "attractor", 0), ("ay", 0, "attractor", 1),
             ("grid", 0, "dist", 0), ("attractor", 0, "dist", 1), ("dist", 0, "bounds", 0),
             ("dist", 0, "remap", 0), ("bounds", 0, "remap", 1), ("bounds", 1, "remap", 2),
             ("rmin", 0, "remap", 3), ("rmax", 0, "remap", 4),
             ("grid", 0, "circle", 0), ("remap", 0, "circle", 2),
             ("remap", 0, "mult", 0), ("height", 0, "mult", 1), ("mult", 0, "vec", 2),
             ("circle", 0, "extrude", 0), ("vec", 0, "extrude", 1), ("bounds", 0, "panel", 0)]
    for a, ai, b, bi in wires:
        g.connect(c[a].outputs[ai], c[b].inputs[bi])
    scene.rebuild_wires()
    scene.request_solve()
    return c


FISCHER_8_9 = [  # (name, nominal, tol, direction): Fischer 2011, Figures 8.9-8.14
    ("A to B (overall)", 56.5, 1.5, 1), ("Part 1", 11.0, 1.0, -1),
    ("Part 2", 17.5, 0.5, -1), ("Part 3", 16.5, 0.5, -1)]


def build_stackup(scene) -> dict:
    """Fischer's statistical stack-up example as a live definition: drag the
    tolerance of the 56.5 dimension or the RSS factor and watch the limits and
    the Monte Carlo out-of-spec share move."""
    def slider(label, value, lo, hi, decimals=2):
        s = lib.NumberSlider(value, lo, hi, decimals)
        s.nickname = label
        return s

    c = {"tol": slider("±tol 56.5", 1.5, 0, 3), "factor": slider("RSS factor", 1.5, 1, 2),
         "neg": lib.Multiplication(), "stack": lib.StackUp(), "mc": lib.MonteCarlo(),
         "report": lib.Panel(), "hist": lib.Panel(), "stats": lib.Panel()}
    c["neg"].inputs[1].default = -1.0
    c["mc"].inputs[4].default = 10.0    # spec limits for the gap: about 2 % fall outside
    c["mc"].inputs[5].default = 13.0
    c["report"].size = (470, 150)
    c["hist"].size = (330, 290)
    c["stats"].size = (190, 80)
    dims = []
    for i, (name, nominal, tol, direction) in enumerate(FISCHER_8_9):
        d = lib.Dimension()
        d.nickname = f"Dim {i + 1}"
        for p, v in zip(d.inputs, (nominal, tol, -tol, float(direction), "normal", name)):
            p.default = v
        c[f"dim{i + 1}"] = d
        dims.append(d)
    # Four 126-px Dimension components only just fit a 460-px canvas at zoom 0.7.
    layout = {"tol": (-620, -60), "factor": (-620, 280), "neg": (-330, 0),
              "dim1": (-160, -150), "dim2": (-160, -18), "dim3": (-160, 114), "dim4": (-160, 246),
              "stack": (60, -40), "mc": (60, 230), "report": (260, -150), "hist": (260, 60),
              "stats": (620, 260)}
    for key, (x, y) in layout.items():
        scene.add_component(c[key], QPointF(x, y))

    g = scene.graph
    g.connect(c["tol"].outputs[0], c["dim1"].inputs[1])
    g.connect(c["tol"].outputs[0], c["neg"].inputs[0])
    g.connect(c["neg"].outputs[0], c["dim1"].inputs[2])
    for d in dims:  # several wires into one input merge into one list, in wire order
        g.connect(d.outputs[0], c["stack"].inputs[0])
        g.connect(d.outputs[0], c["mc"].inputs[0])
    g.connect(c["factor"].outputs[0], c["stack"].inputs[1])
    g.connect(c["stack"].outputs[8], c["report"].inputs[0])
    g.connect(c["mc"].outputs[3], c["hist"].inputs[0])
    for i in range(3):
        g.connect(c["mc"].outputs[i], c["stats"].inputs[0])
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
