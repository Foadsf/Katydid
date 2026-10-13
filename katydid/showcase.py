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


def build_phyllotaxis(scene) -> dict:
    """A sunflower head: seeds placed one golden angle (137.5°) apart at a
    radius growing with the square root of their number, on a shallow dome."""
    c = {
        "seeds": _slider("Seeds", 400, 50, 1000, 0),
        "spacing": _slider("Spacing", 2.2, 0.5, 5, 2),
        "angle": _slider("Angle", 137.508, 130, 145, 3),
        "height": _slider("Dome height", 18, 0, 60),
        "size": _slider("Seed size", 2.0, 0.3, 4, 2),
        "n": lib.Series(), "x": lib.Expression(), "y": lib.Expression(), "z": lib.Expression(),
        "r": lib.Expression(), "sphere": lib.Sphere(), "seed": lib.Move(),
    }
    c["n"].nickname = "Seed no."
    for key, nick, f in (("x", "X", "y*sqrt(x)*cos(radians(x*z))"), ("y", "Y", "y*sqrt(x)*sin(radians(x*z))"),
                         ("z", "Z", "z*(1 - x/y)"), ("r", "Size", "z*(0.6 + 0.4*sqrt(x/y))")):
        c[key].nickname = nick
        _set(c[key], F=f)
    c["sphere"].preview = False
    _place(scene, c, {
        "seeds": (-640, -150), "spacing": (-640, -90), "angle": (-640, -30), "height": (-640, 70),
        "size": (-640, 170), "n": (-340, -150), "x": (-120, -200), "y": (-120, -90), "z": (-120, 20),
        "r": (-120, 140), "sphere": (90, 150), "seed": (280, -40)})
    _wire(scene, c, [
        ("seeds", 0, "n", 2),
        ("n", 0, "x", 1), ("spacing", 0, "x", 2), ("angle", 0, "x", 3),
        ("n", 0, "y", 1), ("spacing", 0, "y", 2), ("angle", 0, "y", 3),
        ("n", 0, "z", 1), ("seeds", 0, "z", 2), ("height", 0, "z", 3),
        ("n", 0, "r", 1), ("seeds", 0, "r", 2), ("size", 0, "r", 3),
        ("r", 0, "sphere", 0),
        ("sphere", 0, "seed", 0), ("x", 0, "seed", 1), ("y", 0, "seed", 2), ("z", 0, "seed", 3)])
    return c


def build_hyperboloid(scene) -> dict:
    """A Shukhov tower: straight struts between two rings, shifted round by a
    few points, form a hyperboloid; a second family twists the other way, and
    horizontal rings are traced by evaluating every strut at the same height."""
    c = {
        "struts": _slider("Struts", 24, 8, 72, 0),
        "height": _slider("Height", 120, 40, 200),
        "base": _slider("Base radius", 30, 10, 60),
        "top": _slider("Top radius", 16, 5, 50),
        "twist": _slider("Twist", 5, 1, 20, 0),
        "rings": _slider("Rings", 7, 0, 15, 0),
        "thick": _slider("Strut radius", 0.7, 0.2, 2, 2),
        "bottom": lib.Circle(), "top_c": lib.Circle(), "div_b": lib.DivideCurve(), "div_t": lib.DivideCurve(),
        "left": lib.ShiftList(), "neg": lib.Multiplication(), "right": lib.ShiftList(),
        "struts_l": lib.Line(), "struts_r": lib.Line(),
        "steps": lib.Addition(), "t": lib.Range(), "eval": lib.EvaluateCurve(), "ring": lib.Interpolate(),
        "ring_r": lib.Multiplication(), "pipes_l": lib.Pipe(), "pipes_r": lib.Pipe(), "ring_pipes": lib.Pipe(),
    }
    c["top_c"].nickname = "Top ring"
    c["bottom"].nickname = "Base ring"
    c["t"].nickname = "Ring heights"
    _set(c["neg"], B=-1.0)
    _set(c["steps"], B=1.0)
    _set(c["ring"], P=True)
    _set(c["ring_r"], B=1.4)
    c["eval"].inputs[1].modifier = "graft"   # one branch per ring height
    for key in ("bottom", "top_c", "div_b", "div_t", "left", "right", "struts_l", "struts_r", "eval", "ring"):
        c[key].preview = False
    _place(scene, c, {
        "struts": (-760, -200), "height": (-760, -140), "base": (-760, -80), "top": (-760, -20),
        "twist": (-760, 80), "rings": (-760, 200), "thick": (-760, 300),
        "bottom": (-470, -200), "top_c": (-470, -90), "div_b": (-300, -200), "div_t": (-300, -90),
        "neg": (-300, 40), "left": (-120, -110), "right": (-120, 10), "struts_l": (60, -190),
        "struts_r": (60, -60), "steps": (-470, 200), "t": (-300, 180), "eval": (240, 120),
        "ring": (420, 120), "ring_r": (240, 280), "pipes_l": (420, -200), "pipes_r": (420, -60),
        "ring_pipes": (600, 160)})
    _wire(scene, c, [
        ("base", 0, "bottom", 0), ("top", 0, "top_c", 0), ("height", 0, "top_c", 1),
        ("bottom", 0, "div_b", 0), ("struts", 0, "div_b", 1),
        ("top_c", 0, "div_t", 0), ("struts", 0, "div_t", 1),
        ("div_t", 0, "left", 0), ("twist", 0, "left", 1),
        ("twist", 0, "neg", 0), ("div_t", 0, "right", 0), ("neg", 0, "right", 1),
        ("div_b", 0, "struts_l", 0), ("left", 0, "struts_l", 1),
        ("div_b", 0, "struts_r", 0), ("right", 0, "struts_r", 1),
        ("rings", 0, "steps", 0), ("steps", 0, "t", 2),
        ("struts_l", 0, "eval", 0), ("t", 0, "eval", 1), ("eval", 0, "ring", 0),
        ("thick", 0, "ring_r", 0),
        ("struts_l", 0, "pipes_l", 0), ("thick", 0, "pipes_l", 1),
        ("struts_r", 0, "pipes_r", 0), ("thick", 0, "pipes_r", 1),
        ("ring", 0, "ring_pipes", 0), ("ring_r", 0, "ring_pipes", 1)])
    return c


def build_staircase(scene) -> dict:
    """A spiral staircase: one tread per step, lifted and turned a little
    more each time round a central column, with balusters and a handrail
    interpolated through their tops."""
    c = {
        "steps": _slider("Steps", 22, 6, 40, 0),
        "rise": _slider("Rise", 3.2, 2, 5),
        "turn": _slider("Turn per step", 16, 5, 30),
        "col": _slider("Column radius", 3, 1, 8),
        "width": _slider("Step width", 18, 8, 30),
        "rail_h": _slider("Rail height", 15, 8, 25),
        "n": lib.Series(), "z": lib.Multiplication(), "angle": lib.Multiplication(),
        "tread": lib.Box(), "reach": lib.Expression(), "out": lib.Move(), "stair": lib.Rotate(),
        "length": lib.Expression(), "column": lib.Cylinder(),
        "rail_r": lib.Expression(), "px": lib.Expression(), "py": lib.Expression(), "pz": lib.Addition(),
        "foot": lib.ConstructPoint(), "head": lib.ConstructPoint(), "post": lib.Line(),
        "balusters": lib.Pipe(), "rail": lib.Interpolate(), "handrail": lib.Pipe(),
    }
    c["n"].nickname = "Step no."
    c["z"].nickname = "Heights"
    c["angle"].nickname = "Angles"
    c["foot"].nickname = "Foot"
    c["head"].nickname = "Head"
    _set(c["tread"], Y=8.0, Z=1.2)
    _set(c["reach"], F="x + y/2")
    _set(c["length"], F="(x - 1)*y + z")   # up to the top of the last baluster
    _set(c["rail_r"], F="x + y - 1.2")
    _set(c["px"], F="z*cos(radians(x*y))")
    _set(c["py"], F="z*sin(radians(x*y))")
    _set(c["balusters"], R=0.3)
    _set(c["handrail"], R=0.6)
    for key in ("tread", "out", "foot", "head", "post", "rail"):
        c[key].preview = False
    _place(scene, c, {
        "steps": (-760, -220), "rise": (-760, -160), "turn": (-760, -100), "col": (-760, 0),
        "width": (-760, 60), "rail_h": (-760, 160),
        "n": (-470, -230), "z": (-300, -230), "angle": (-300, -130), "tread": (-300, -20),
        "reach": (-470, 20), "out": (-120, -60), "stair": (60, -120), "length": (-300, 330),
        "column": (-120, 330), "rail_r": (-470, 150), "px": (-300, 100), "py": (-300, 200),
        "pz": (-120, 220), "foot": (60, 60), "head": (60, 200), "post": (240, 120),
        "balusters": (420, 100), "rail": (240, 250), "handrail": (420, 250)})
    _wire(scene, c, [
        ("steps", 0, "n", 2), ("n", 0, "z", 0), ("rise", 0, "z", 1),
        ("n", 0, "angle", 0), ("turn", 0, "angle", 1),
        ("width", 0, "tread", 0), ("col", 0, "reach", 1), ("width", 0, "reach", 2),
        ("tread", 0, "out", 0), ("reach", 0, "out", 1), ("z", 0, "out", 3),
        ("out", 0, "stair", 0), ("angle", 0, "stair", 1),
        ("steps", 0, "length", 1), ("rise", 0, "length", 2), ("rail_h", 0, "length", 3),
        ("col", 0, "column", 0), ("length", 0, "column", 1),
        ("col", 0, "rail_r", 1), ("width", 0, "rail_r", 2),
        ("n", 0, "px", 1), ("turn", 0, "px", 2), ("rail_r", 0, "px", 3),
        ("n", 0, "py", 1), ("turn", 0, "py", 2), ("rail_r", 0, "py", 3),
        ("z", 0, "pz", 0), ("rail_h", 0, "pz", 1),
        ("px", 0, "foot", 0), ("py", 0, "foot", 1), ("z", 0, "foot", 2),
        ("px", 0, "head", 0), ("py", 0, "head", 1), ("pz", 0, "head", 2),
        ("foot", 0, "post", 0), ("head", 0, "post", 1), ("post", 0, "balusters", 0),
        ("head", 0, "rail", 0), ("rail", 0, "handrail", 0)])
    return c


def build_city(scene) -> dict:
    """A Voronoi city: relaxed cells become plots with streets between them,
    extruded into blocks that rise towards a centre, with some variety."""
    S = 160.0
    c = {
        "plots": _slider("Plots", 160, 30, 400, 0),
        "seed": _slider("Seed", 7, 1, 50, 0),
        "gap": _slider("Street gap", 0.82, 0.5, 0.98, 2),
        "peak": _slider("Peak height", 60, 5, 120),
        "spread": _slider("Spread", 45, 10, 120),
        "cx": _slider("Centre X", 10, -80, 80),
        "cy": _slider("Centre Y", -5, -80, 80),
        "pop": lib.Populate2D(), "voronoi": lib.Voronoi(), "area": lib.Area(), "plot": lib.Scale(),
        "floor": lib.PlanarSurface(), "centre": lib.ConstructPoint(), "dist": lib.Distance(),
        "height": lib.Expression(), "xy": lib.Deconstruct(), "variety": lib.Expression(),
        "h": lib.Multiplication(), "up": lib.VectorXYZ(), "blocks": lib.Extrude(),
        "base": lib.Box(), "ground": lib.Move(),
    }
    c["centre"].nickname = "Centre"
    c["height"].nickname = "Height"
    c["variety"].nickname = "Variety"
    _set(c["pop"], W=S, H=S, R=2.0)
    _set(c["voronoi"], W=S, H=S)
    _set(c["height"], F="3 + z*exp(-(x/y)**2)")
    _set(c["variety"], F="0.55 + 0.45*abs(sin(x*12.9898 + y*78.233))")
    _set(c["base"], X=S + 6, Y=S + 6, Z=2.0)
    _set(c["ground"], Z=-2.0)   # the Box stands on z = 0: drop it so its top is the street level
    for key in ("pop", "voronoi", "area", "plot", "floor", "centre", "base"):
        c[key].preview = False
    _place(scene, c, {
        "plots": (-760, -200), "seed": (-760, -140), "gap": (-760, -40), "peak": (-760, 60),
        "spread": (-760, 120), "cx": (-760, 220), "cy": (-760, 280),
        "pop": (-470, -190), "voronoi": (-300, -170), "area": (-130, -90), "plot": (60, -190),
        "floor": (230, -190), "centre": (-470, 230), "dist": (60, 40), "height": (230, 60),
        "xy": (60, 160), "variety": (230, 190), "h": (400, 100), "up": (560, 100),
        "blocks": (720, -60), "base": (560, 280), "ground": (720, 280)})
    _wire(scene, c, [
        ("plots", 0, "pop", 2), ("seed", 0, "pop", 3),
        ("pop", 0, "voronoi", 0), ("voronoi", 0, "area", 0),
        ("voronoi", 0, "plot", 0), ("gap", 0, "plot", 1), ("area", 1, "plot", 2),
        ("plot", 0, "floor", 0),
        ("cx", 0, "centre", 0), ("cy", 0, "centre", 1),
        ("area", 1, "dist", 0), ("centre", 0, "dist", 1),
        ("dist", 0, "height", 1), ("spread", 0, "height", 2), ("peak", 0, "height", 3),
        ("area", 1, "xy", 0), ("xy", 0, "variety", 1), ("xy", 1, "variety", 2),
        ("height", 0, "h", 0), ("variety", 0, "h", 1), ("h", 0, "up", 2),
        ("floor", 0, "blocks", 0), ("up", 0, "blocks", 1),
        ("base", 0, "ground", 0)])
    return c


def build_weave(scene) -> dict:
    """A woven mat: two families of threads that pass over and under each
    other, from one formula on a grafted grid, interpolated and piped."""
    c = {
        "threads": _slider("Threads", 14, 4, 30, 0),
        "spacing": _slider("Spacing", 6, 3, 12),
        "amp": _slider("Amplitude", 1.3, 0.2, 3, 2),
        "radius": _slider("Thread radius", 1, 0.2, 2.5, 2),
        "i": lib.Series(), "pos": lib.Multiplication(),
        "n2": lib.Addition(), "j": lib.Series(), "along": lib.Multiplication(),
        "wave": lib.Expression(), "neg": lib.Multiplication(),
        "warp_pts": lib.ConstructPoint(), "weft_pts": lib.ConstructPoint(),
        "warp_c": lib.Interpolate(), "weft_c": lib.Interpolate(), "warp": lib.Pipe(), "weft": lib.Pipe(),
    }
    c["i"].nickname = "Thread no."
    c["pos"].nickname = "Thread positions"
    c["j"].nickname = "Point no."
    c["along"].nickname = "Along"
    c["wave"].nickname = "Over-under"
    c["warp_pts"].nickname = "Warp points"
    c["weft_pts"].nickname = "Weft points"
    # Each thread runs one spacing past the outermost crossing (points -1 .. n):
    # an interpolated curve dives at its free ends, and edge threads cut into each other.
    _set(c["n2"], B=2.0)
    _set(c["j"], S=-1.0)
    _set(c["wave"], F="z*cos(pi*(x + y))")
    _set(c["neg"], B=-1.0)
    c["wave"].inputs[2].modifier = "graft"       # y: one branch per thread
    c["warp_pts"].inputs[1].modifier = "graft"   # warp threads run along X, one per Y
    c["weft_pts"].inputs[0].modifier = "graft"   # weft threads run along Y, one per X
    for key in ("warp_pts", "weft_pts", "warp_c", "weft_c"):
        c[key].preview = False
    _place(scene, c, {
        "threads": (-700, -140), "spacing": (-700, -80), "amp": (-700, 20), "radius": (-700, 140),
        "i": (-420, -220), "pos": (-240, -220), "n2": (-420, -100), "j": (-420, 10), "along": (-240, -100),
        "wave": (-240, 40), "neg": (-60, 100),
        "warp_pts": (120, -170), "weft_pts": (120, 30), "warp_c": (300, -170), "weft_c": (300, 30),
        "warp": (480, -160), "weft": (480, 40)})
    _wire(scene, c, [
        ("threads", 0, "i", 2), ("i", 0, "pos", 0), ("spacing", 0, "pos", 1),
        ("threads", 0, "n2", 0), ("n2", 0, "j", 2), ("j", 0, "along", 0), ("spacing", 0, "along", 1),
        ("j", 0, "wave", 1), ("i", 0, "wave", 2), ("amp", 0, "wave", 3), ("wave", 0, "neg", 0),
        ("along", 0, "warp_pts", 0), ("pos", 0, "warp_pts", 1), ("wave", 0, "warp_pts", 2),
        ("pos", 0, "weft_pts", 0), ("along", 0, "weft_pts", 1), ("neg", 0, "weft_pts", 2),
        ("warp_pts", 0, "warp_c", 0), ("weft_pts", 0, "weft_c", 0),
        ("warp_c", 0, "warp", 0), ("radius", 0, "warp", 1),
        ("weft_c", 0, "weft", 0), ("radius", 0, "weft", 1)])
    return c


SHOWCASE = {"voronoi": build_voronoi, "tower": build_tower, "waffle": build_waffle, "wave": build_wave,
            "phyllotaxis": build_phyllotaxis, "hyperboloid": build_hyperboloid,
            "staircase": build_staircase, "city": build_city, "weave": build_weave}
