# SPDX-License-Identifier: LGPL-2.1-or-later
"""Showcase definitions: a Voronoi screen, a twisted tower, a waffle dome and
a wave surface with contour lines. Each builder places and wires real
components on a scene (the canvas, or a stand-in in the tests) and returns
them by name, exactly as the tutorials describe them.
"""

from __future__ import annotations

from . import components as lib
from .canvas import QPointF


def _slider(label, value, lo, hi, decimals=1):
    s = lib.NumberSlider(value, lo, hi, decimals)
    s.nickname = label
    return s


def _place(scene, c, layout):
    for key, (x, y) in layout.items():
        scene.add_component(c[key], QPointF(x, y))


def _wire(scene, c, wires):
    for a, ai, b, bi in wires:
        if not scene.graph.connect(c[a].outputs[ai], c[b].inputs[bi]):
            raise RuntimeError(f"could not wire {a}[{ai}] -> {b}[{bi}]")
    scene.rebuild_wires()
    scene.request_solve()


def _set(comp, **defaults):
    by_nick = {p.nickname: p for p in comp.inputs}
    for nick, value in defaults.items():
        by_nick[nick].default = value


def build_voronoi(scene) -> dict:
    """A perforated screen: relaxed Voronoi cells, shrunk about their centroids
    by distance to an attractor, cut through a plate, stood upright."""
    W, H = 120.0, 70.0
    c = {
        "cells": _slider("Cells", 70, 10, 200, 0),
        "seed": _slider("Seed", 3, 1, 50, 0),
        "relax": _slider("Relax", 3, 0, 8, 0),
        "ax": _slider("Attractor X", 35, -60, 60),
        "ay": _slider("Attractor Y", 10, -35, 35),
        "small": _slider("Smallest hole", 0.3, 0.05, 0.9, 2),
        "large": _slider("Largest hole", 0.85, 0.1, 0.95, 2),
        "thick": _slider("Thickness", 3, 1, 10),
        "pop": lib.Populate2D(), "voronoi": lib.Voronoi(), "area": lib.Area(),
        "attractor": lib.ConstructPoint(), "dist": lib.Distance(), "bounds": lib.Bounds(),
        "remap": lib.Remap(), "scale": lib.Scale(), "surface": lib.PlanarSurface(),
        "drop": lib.Move(), "depth": lib.Addition(), "vec": lib.VectorXYZ(), "holes": lib.Extrude(),
        "plate": lib.Box(), "screen": lib.Difference(), "stand": lib.Rotate(),
    }
    _set(c["pop"], W=W, H=H)
    _set(c["voronoi"], W=W, H=H)
    _set(c["plate"], X=W + 6, Y=H + 6)
    _set(c["drop"], Z=-1.0)
    _set(c["depth"], B=2.0)
    _set(c["stand"], A=90.0, X=(1.0, 0.0, 0.0))
    c["attractor"].nickname = "Attractor"
    c["bounds"].inputs[0].modifier = "flatten"
    for key in ("pop", "voronoi", "attractor", "area", "scale", "surface", "drop", "holes", "plate", "screen"):
        c[key].preview = False
    _place(scene, c, {
        "cells": (-760, -160), "seed": (-760, -105), "relax": (-760, -50), "ax": (-760, 60),
        "ay": (-760, 115), "small": (-760, 220), "large": (-760, 275), "thick": (-760, 380),
        "pop": (-460, -150), "voronoi": (-280, -120), "area": (-110, -40), "attractor": (-460, 70),
        "dist": (60, 40), "bounds": (220, 110), "remap": (390, 60), "scale": (560, -80),
        "surface": (720, -80), "drop": (870, -100), "depth": (560, 340), "vec": (720, 330),
        "holes": (1040, -30), "plate": (870, 200), "screen": (1200, 60), "stand": (1360, 60)})
    _wire(scene, c, [
        ("cells", 0, "pop", 2), ("seed", 0, "pop", 3), ("relax", 0, "pop", 4),
        ("pop", 0, "voronoi", 0), ("voronoi", 0, "area", 0),
        ("ax", 0, "attractor", 0), ("ay", 0, "attractor", 1),
        ("area", 1, "dist", 0), ("attractor", 0, "dist", 1), ("dist", 0, "bounds", 0),
        ("dist", 0, "remap", 0), ("bounds", 0, "remap", 1), ("bounds", 1, "remap", 2),
        ("small", 0, "remap", 3), ("large", 0, "remap", 4),
        ("voronoi", 0, "scale", 0), ("remap", 0, "scale", 1), ("area", 1, "scale", 2),
        ("scale", 0, "surface", 0), ("surface", 0, "drop", 0),
        ("thick", 0, "depth", 0), ("depth", 0, "vec", 2),
        ("drop", 0, "holes", 0), ("vec", 0, "holes", 1),
        ("thick", 0, "plate", 2), ("plate", 0, "screen", 0), ("holes", 0, "screen", 1),
        ("screen", 0, "stand", 0)])
    return c


def build_tower(scene) -> dict:
    """A twisted tower: one polygon per floor, rotated a little more on every
    floor and swelling in the middle, lofted into a facade, with floor slabs."""
    c = {
        "floors": _slider("Floors", 36, 6, 60, 0),
        "fh": _slider("Floor height", 4, 2, 8),
        "radius": _slider("Radius", 14, 6, 30),
        "sides": _slider("Sides", 4, 3, 12, 0),
        "twist": _slider("Twist per floor", 3.5, 0, 10),
        "bulge": _slider("Bulge", 0.25, 0, 0.8, 2),
        "heights": lib.Series(), "index": lib.Series(), "angle": lib.Multiplication(),
        "swell": lib.Expression(), "rad": lib.Multiplication(), "poly": lib.RegularPolygon(),
        "facade": lib.Loft(), "floor": lib.PlanarSurface(), "slab_t": lib.VectorXYZ(), "slabs": lib.Extrude(),
    }
    c["heights"].nickname = "Heights"
    c["index"].nickname = "Floor no."
    _set(c["swell"], F="1 + z*sin(pi*x/y)")
    _set(c["slab_t"], Z=0.5)
    c["facade"].inputs[0].modifier = "flatten"
    for key in ("poly", "floor"):
        c[key].preview = False
    _place(scene, c, {
        "floors": (-700, -120), "fh": (-700, -60), "radius": (-700, 40), "sides": (-700, 100),
        "twist": (-700, 160), "bulge": (-700, 220),
        "heights": (-400, -150), "index": (-400, -30), "angle": (-200, 120), "swell": (-200, -20),
        "rad": (-10, 0), "poly": (180, -60), "facade": (380, -140), "floor": (380, 20),
        "slab_t": (380, 140), "slabs": (560, 40)})
    _wire(scene, c, [
        ("fh", 0, "heights", 1), ("floors", 0, "heights", 2), ("floors", 0, "index", 2),
        ("index", 0, "angle", 0), ("twist", 0, "angle", 1),
        ("index", 0, "swell", 1), ("floors", 0, "swell", 2), ("bulge", 0, "swell", 3),
        ("swell", 0, "rad", 0), ("radius", 0, "rad", 1),
        ("rad", 0, "poly", 0), ("sides", 0, "poly", 1), ("angle", 0, "poly", 2), ("heights", 0, "poly", 3),
        ("poly", 0, "facade", 0), ("poly", 0, "floor", 0),
        ("floor", 0, "slabs", 0), ("slab_t", 0, "slabs", 1)])
    return c


def build_waffle(scene) -> dict:
    """A waffle dome: a lofted, capped dome cut by two families of planes into
    thin interlocking ribs, like a plywood pavilion model."""
    c = {
        "rings": _slider("Rings", 10, 4, 16, 0),
        "spacing": _slider("Ring spacing", 3.2, 1, 8),
        "radius": _slider("Radius", 34, 10, 50),
        "ribs": _slider("Ribs", 9, 3, 21, 0),
        "pitch": _slider("Rib pitch", 7, 3, 15),
        "thick": _slider("Thickness", 1.4, 0.4, 3, 2),
        "index": lib.Series(), "heights": lib.Series(), "profile": lib.Expression(),
        "circle": lib.Circle(), "loft": lib.Loft(), "dome": lib.CapHoles(),
        "start": lib.Expression(), "offsets": lib.Series(),
        "x_cut": lib.Section(), "y_cut": lib.Section(),
        "half": lib.Multiplication(), "x_back": lib.Move(), "y_back": lib.Move(),
        "x_dir": lib.VectorXYZ(), "y_dir": lib.VectorXYZ(), "x_ribs": lib.Extrude(), "y_ribs": lib.Extrude(),
    }
    c["index"].nickname = "Ring no."
    c["heights"].nickname = "Heights"
    c["offsets"].nickname = "Rib offsets"
    c["profile"].nickname = "Profile"
    c["start"].nickname = "First rib"
    _set(c["profile"], F="z*sqrt(1 - (x/(y - 0.6))**2)")   # a dome: widest at the ground
    _set(c["start"], F="-(x - 1)*y/2")
    _set(c["x_cut"], N=(1.0, 0.0, 0.0))
    _set(c["y_cut"], N=(0.0, 1.0, 0.0))
    _set(c["half"], B=-0.5)
    c["loft"].inputs[0].modifier = "flatten"
    for key in ("circle", "loft", "dome", "x_cut", "y_cut", "x_back", "y_back"):
        c[key].preview = False
    _place(scene, c, {
        "rings": (-720, -170), "spacing": (-720, -110), "radius": (-720, -50), "ribs": (-720, 80),
        "pitch": (-720, 140), "thick": (-720, 260),
        "index": (-420, -200), "heights": (-420, -80), "profile": (-240, -190), "circle": (-60, -150),
        "loft": (90, -150), "dome": (230, -150), "start": (-420, 60), "offsets": (-240, 60),
        "x_cut": (400, -60), "y_cut": (400, 90), "half": (-240, 250), "x_back": (560, -80),
        "y_back": (560, 90), "x_dir": (-60, 230), "y_dir": (-60, 330), "x_ribs": (740, -60),
        "y_ribs": (740, 110)})
    _wire(scene, c, [
        ("rings", 0, "index", 2), ("rings", 0, "heights", 2), ("spacing", 0, "heights", 1),
        ("index", 0, "profile", 1), ("rings", 0, "profile", 2), ("radius", 0, "profile", 3),
        ("profile", 0, "circle", 0), ("heights", 0, "circle", 1),
        ("circle", 0, "loft", 0), ("loft", 0, "dome", 0),
        ("ribs", 0, "start", 1), ("pitch", 0, "start", 2),
        ("start", 0, "offsets", 0), ("pitch", 0, "offsets", 1), ("ribs", 0, "offsets", 2),
        ("dome", 0, "x_cut", 0), ("offsets", 0, "x_cut", 2),
        ("dome", 0, "y_cut", 0), ("offsets", 0, "y_cut", 2),
        ("thick", 0, "half", 0), ("thick", 0, "x_dir", 0), ("thick", 0, "y_dir", 1),
        ("x_cut", 0, "x_back", 0), ("half", 0, "x_back", 1),
        ("y_cut", 0, "y_back", 0), ("half", 0, "y_back", 2),
        ("x_back", 0, "x_ribs", 0), ("x_dir", 0, "x_ribs", 1),
        ("y_back", 0, "y_ribs", 0), ("y_dir", 0, "y_ribs", 1)])
    return c


def build_wave(scene) -> dict:
    """A wave surface from a formula over a grafted grid, with contour lines
    every few millimetres of height, like a topographic map."""
    c = {
        "size": _slider("Size", 90, 40, 150),
        "count": _slider("Grid", 24, 8, 40, 0),
        "amp": _slider("Amplitude", 7, 0, 15),
        "freq": _slider("Frequency", 0.09, 0.02, 0.3, 3),
        "levels": _slider("Contours", 12, 2, 30, 0),
        "lo": lib.Multiplication(), "hi": lib.Multiplication(), "xs": lib.Range(), "ys": lib.Range(),
        "wave": lib.Expression(), "z": lib.Multiplication(), "pts": lib.ConstructPoint(),
        "surface": lib.SurfaceFromPoints(),
        "zlo": lib.Multiplication(), "heights": lib.Range(), "contours": lib.Contour(),
    }
    c["xs"].nickname = "X values"
    c["ys"].nickname = "Y values"
    c["wave"].nickname = "Wave"
    c["heights"].nickname = "Levels"
    _set(c["lo"], B=-0.5)
    _set(c["hi"], B=0.5)
    _set(c["wave"], F="sin(z*x)*cos(z*y) + 0.4*sin(1.7*z*(x + y))")
    _set(c["zlo"], B=-1.4)
    c["wave"].inputs[2].modifier = "graft"
    c["pts"].inputs[1].modifier = "graft"
    c["surface"].inputs[0].modifier = "flatten"   # all rows, in order, as one list
    c["pts"].preview = False
    c["hl"] = lib.Multiplication()
    _set(c["hl"], B=1.4)
    c["per_row"] = lib.Addition()      # Range gives steps + 1 values per row
    _set(c["per_row"], B=1.0)
    _place(scene, c, {
        "size": (-720, -120), "count": (-720, -60), "amp": (-720, 120), "freq": (-720, 40),
        "levels": (-720, 260), "lo": (-430, -170), "hi": (-430, -70), "xs": (-260, -180),
        "ys": (-260, -60), "wave": (-60, -10), "z": (120, 40), "pts": (290, -100),
        "surface": (470, -100), "zlo": (-260, 170), "hl": (-260, 270),
        "heights": (-60, 200), "contours": (650, 60), "per_row": (290, 80)})
    _wire(scene, c, [
        ("size", 0, "lo", 0), ("size", 0, "hi", 0),
        ("lo", 0, "xs", 0), ("hi", 0, "xs", 1), ("count", 0, "xs", 2),
        ("lo", 0, "ys", 0), ("hi", 0, "ys", 1), ("count", 0, "ys", 2),
        ("xs", 0, "wave", 1), ("ys", 0, "wave", 2), ("freq", 0, "wave", 3),
        ("wave", 0, "z", 0), ("amp", 0, "z", 1),
        ("xs", 0, "pts", 0), ("ys", 0, "pts", 1), ("z", 0, "pts", 2),
        ("pts", 0, "surface", 0), ("count", 0, "per_row", 0), ("per_row", 0, "surface", 1),
        ("amp", 0, "zlo", 0), ("amp", 0, "hl", 0),
        ("zlo", 0, "heights", 0), ("hl", 0, "heights", 1), ("levels", 0, "heights", 2),
        ("surface", 0, "contours", 0), ("heights", 0, "contours", 2)])
    return c


SHOWCASE = {"voronoi": build_voronoi, "tower": build_tower, "waffle": build_waffle, "wave": build_wave}
