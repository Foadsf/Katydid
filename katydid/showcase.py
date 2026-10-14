# SPDX-License-Identifier: LGPL-2.1-or-later
"""Showcase definitions for the gallery (see SHOWCASE at the end). Each builder
places and wires real components on a scene (the canvas, or a stand-in in the
tests) and returns them by name, exactly as the tutorials describe them.
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


def build_knot(scene) -> dict:
    """A torus knot: a closed curve that winds p times round the axis while
    looping q times through the hole, interpolated and piped."""
    c = {
        "p": _slider("Windings", 2, 1, 9, 0),
        "q": _slider("Loops", 3, 1, 9, 0),
        "R": _slider("Ring radius", 30, 10, 60),
        "r": _slider("Tube offset", 12, 3, 30),
        "count": _slider("Points", 240, 60, 600, 0),
        "thick": _slider("Thickness", 3.2, 0.5, 8, 2),
        "n": lib.Series(), "phi": lib.Expression(), "pphi": lib.Multiplication(), "qphi": lib.Multiplication(),
        "rho": lib.Expression(), "x": lib.Expression(), "y": lib.Expression(), "z": lib.Expression(),
        "pts": lib.ConstructPoint(), "curve": lib.Interpolate(), "tube": lib.Pipe(),
    }
    c["n"].nickname = "Point no."
    for key, nick, f in (("phi", "Angle", "2*pi*x/y"), ("rho", "Radius", "y + z*cos(x)"),
                         ("x", "X", "x*cos(y)"), ("y", "Y", "x*sin(y)"), ("z", "Z", "y*sin(x)")):
        c[key].nickname = nick
        _set(c[key], F=f)
    _set(c["curve"], P=True)
    for key in ("pts", "curve"):
        c[key].preview = False
    _place(scene, c, {
        "p": (-720, -200), "q": (-720, -140), "R": (-720, -40), "r": (-720, 20), "count": (-720, 120),
        "thick": (-720, 240), "n": (-440, 110), "phi": (-280, 110), "pphi": (-110, -170), "qphi": (-110, 20),
        "rho": (60, -20), "x": (240, -170), "y": (240, -60), "z": (240, 80), "pts": (420, -80),
        "curve": (580, -80), "tube": (740, -60)})
    _wire(scene, c, [
        ("count", 0, "n", 2), ("n", 0, "phi", 1), ("count", 0, "phi", 2),
        ("phi", 0, "pphi", 0), ("p", 0, "pphi", 1), ("phi", 0, "qphi", 0), ("q", 0, "qphi", 1),
        ("qphi", 0, "rho", 1), ("R", 0, "rho", 2), ("r", 0, "rho", 3),
        ("rho", 0, "x", 1), ("pphi", 0, "x", 2), ("rho", 0, "y", 1), ("pphi", 0, "y", 2),
        ("qphi", 0, "z", 1), ("r", 0, "z", 2),
        ("x", 0, "pts", 0), ("y", 0, "pts", 1), ("z", 0, "pts", 2),
        ("pts", 0, "curve", 0), ("curve", 0, "tube", 0), ("thick", 0, "tube", 1)])
    return c


def build_ring(scene) -> dict:
    """A twisted lobed ring: a lobed profile swept round a circle while its
    lobes turn, built as closed sections and a closed loft."""
    c = {
        "sections": _slider("Sections", 24, 12, 72, 0),
        "R": _slider("Ring radius", 40, 20, 60),
        "a": _slider("Profile size", 14, 5, 25),
        "lobes": _slider("Lobes", 3, 2, 6, 0),
        "depth": _slider("Lobe depth", 0.45, 0, 0.7, 2),
        "twist": _slider("Twist", 1, 0, 4, 0),
        "k": lib.Series(), "m": lib.Series(), "theta": lib.Expression(), "phi": lib.Expression(),
        "shift": lib.Expression(), "ltheta": lib.Multiplication(), "arg": lib.Addition(),
        "rho": lib.Expression(), "c": lib.Expression(), "x": lib.Expression(), "y": lib.Expression(),
        "z": lib.Expression(), "pts": lib.ConstructPoint(), "section": lib.Interpolate(), "ring": lib.Loft(),
    }
    c["k"].nickname = "Section no."
    c["m"].nickname = "Profile no."
    _set(c["m"], C=32.0)   # 20 x 32 solves in ~1 s; 36 x 48 took 4 s for an area 0.06 % different
    for key, nick, f in (("theta", "θ", "2*pi*x/y"), ("phi", "φ", "2*pi*x/y"), ("shift", "Lobe turn", "2*pi*x*y/z"),
                         ("rho", "Profile", "y*(1 + z*cos(x))"), ("c", "Reach", "z + x*cos(y)"),
                         ("x", "X", "x*cos(y)"), ("y", "Y", "x*sin(y)"), ("z", "Z", "x*sin(y)")):
        c[key].nickname = nick
        _set(c[key], F=f)
    _set(c["theta"], y=32.0)
    _set(c["section"], P=True)
    _set(c["ring"], Cl=True)
    c["arg"].inputs[1].modifier = "graft"     # one branch per section
    c["x"].inputs[2].modifier = "graft"
    c["y"].inputs[2].modifier = "graft"
    c["ring"].inputs[0].modifier = "flatten"
    for key in ("pts", "section"):
        c[key].preview = False
    _place(scene, c, {
        "sections": (-780, -220), "R": (-780, -120), "a": (-780, -60), "lobes": (-780, 40),
        "depth": (-780, 100), "twist": (-780, 200),
        "k": (-500, -220), "m": (-500, 300), "theta": (-330, 300), "phi": (-330, -230), "shift": (-330, -110),
        "ltheta": (-160, 220), "arg": (0, 120), "rho": (160, 120), "c": (320, 40), "x": (480, -120),
        "y": (480, -10), "z": (480, 160), "pts": (640, 0), "section": (800, 0), "ring": (960, 0)})
    _wire(scene, c, [
        ("sections", 0, "k", 2), ("m", 0, "theta", 1),
        ("k", 0, "phi", 1), ("sections", 0, "phi", 2),
        ("k", 0, "shift", 1), ("twist", 0, "shift", 2), ("sections", 0, "shift", 3),
        ("theta", 0, "ltheta", 0), ("lobes", 0, "ltheta", 1),
        ("ltheta", 0, "arg", 0), ("shift", 0, "arg", 1),
        ("arg", 0, "rho", 1), ("a", 0, "rho", 2), ("depth", 0, "rho", 3),
        ("rho", 0, "c", 1), ("theta", 0, "c", 2), ("R", 0, "c", 3),
        ("c", 0, "x", 1), ("phi", 0, "x", 2), ("c", 0, "y", 1), ("phi", 0, "y", 2),
        ("rho", 0, "z", 1), ("theta", 0, "z", 2),
        ("x", 0, "pts", 0), ("y", 0, "pts", 1), ("z", 0, "pts", 2),
        ("pts", 0, "section", 0), ("section", 0, "ring", 0)])
    return c


def build_frames(scene) -> dict:
    """A frame tunnel: one rectangular frame, copied along a line, each copy
    turned a little more and swelling towards the middle."""
    c = {
        "frames": _slider("Frames", 40, 5, 80, 0),
        "spacing": _slider("Spacing", 5, 2, 12),
        "width": _slider("Width", 40, 10, 80),
        "height": _slider("Height", 30, 10, 60),
        "bar": _slider("Frame bar", 2.5, 0.5, 6, 2),
        "turn": _slider("Turn per frame", 4.5, 0, 15),
        "swell": _slider("Swell", 0.3, 0, 0.8, 2),
        "outer": lib.Box(), "in_x": lib.Expression(), "in_z": lib.Expression(), "in_y": lib.Multiplication(),
        "inner": lib.Box(), "lift": lib.Move(), "frame": lib.Difference(),
        "mid": lib.Multiplication(), "centre": lib.ConstructPoint(),
        "n": lib.Series(), "angle": lib.Multiplication(), "size": lib.Expression(), "y": lib.Multiplication(),
        "grown": lib.Scale(), "turned": lib.Rotate(), "tunnel": lib.Move(),
    }
    c["outer"].nickname = "Outer"
    c["inner"].nickname = "Opening"
    c["centre"].nickname = "Centre"
    c["n"].nickname = "Frame no."
    c["size"].nickname = "Size"
    _set(c["in_x"], F="x - 2*y")
    _set(c["in_z"], F="x - 2*y")
    _set(c["in_y"], B=3.0)
    _set(c["mid"], B=0.5)
    _set(c["size"], F="1 + z*sin(pi*x/y)")
    _set(c["turned"], X=(0.0, 1.0, 0.0))
    for key in ("outer", "inner", "lift", "frame", "centre", "grown", "turned"):
        c[key].preview = False
    _place(scene, c, {
        "frames": (-780, -220), "spacing": (-780, -160), "width": (-780, -60), "height": (-780, 0),
        "bar": (-780, 60), "turn": (-780, 160), "swell": (-780, 220),
        "outer": (-480, -260), "in_x": (-480, -150), "in_z": (-480, -50), "in_y": (-480, 50),
        "inner": (-300, -100), "lift": (-140, -100), "frame": (20, -180), "mid": (-300, 60),
        "centre": (-140, 60), "n": (-480, 200), "angle": (-300, 200), "size": (-300, 300),
        "y": (-140, 300), "grown": (200, -60), "turned": (360, -40), "tunnel": (520, -20)})
    _wire(scene, c, [
        ("width", 0, "outer", 0), ("bar", 0, "outer", 1), ("height", 0, "outer", 2),
        ("width", 0, "in_x", 1), ("bar", 0, "in_x", 2), ("height", 0, "in_z", 1), ("bar", 0, "in_z", 2),
        ("bar", 0, "in_y", 0),
        ("in_x", 0, "inner", 0), ("in_y", 0, "inner", 1), ("in_z", 0, "inner", 2),
        ("inner", 0, "lift", 0), ("bar", 0, "lift", 3),
        ("outer", 0, "frame", 0), ("lift", 0, "frame", 1),
        ("height", 0, "mid", 0), ("mid", 0, "centre", 2),
        ("frames", 0, "n", 2), ("n", 0, "angle", 0), ("turn", 0, "angle", 1),
        ("n", 0, "size", 1), ("frames", 0, "size", 2), ("swell", 0, "size", 3),
        ("n", 0, "y", 0), ("spacing", 0, "y", 1),
        ("frame", 0, "grown", 0), ("size", 0, "grown", 1), ("centre", 0, "grown", 2),
        ("grown", 0, "turned", 0), ("angle", 0, "turned", 1), ("centre", 0, "turned", 2),
        ("turned", 0, "tunnel", 0), ("y", 0, "tunnel", 2)])
    return c


def build_hypar(scene) -> dict:
    """A hypar umbrella: four hyperbolic paraboloids, each a grid of straight
    members between opposite edges, round a central column."""
    c = {
        "size": _slider("Size", 40, 10, 80),
        "centre_h": _slider("Centre height", 22, 5, 40),
        "edge_h": _slider("Edge height", 32, 10, 60),
        "members": _slider("Members", 18, 4, 40, 0),
        "radius": _slider("Member radius", 0.4, 0.1, 1.5, 2),
        "c0": lib.ConstructPoint(), "c1": lib.ConstructPoint(), "c2": lib.ConstructPoint(), "c3": lib.ConstructPoint(),
        "e01": lib.Line(), "e32": lib.Line(), "e03": lib.Line(), "e12": lib.Line(),
        "d01": lib.DivideCurve(), "d32": lib.DivideCurve(), "d03": lib.DivideCurve(), "d12": lib.DivideCurve(),
        "fam1": lib.Line(), "fam2": lib.Line(), "pipe1": lib.Pipe(), "pipe2": lib.Pipe(),
        "membrane": lib.RuledSurface(), "quadrants": lib.Series(),
        "rot1": lib.Rotate(), "rot2": lib.Rotate(), "roof": lib.Rotate(), "column": lib.Cylinder(),
    }
    for key, nick in (("c0", "Centre"), ("c1", "High 1"), ("c2", "Foot"), ("c3", "High 2"),
                      ("quadrants", "Quadrants"), ("roof", "Membrane")):
        c[key].nickname = nick
    _set(c["quadrants"], N=90.0, C=4.0)
    _set(c["column"], R=1.6)
    for key in ("rot1", "rot2", "roof"):
        c[key].inputs[1].modifier = "graft"   # one branch per quadrant: every member turned by each angle
    for key in ("c0", "c1", "c2", "c3", "e01", "e32", "e03", "e12", "d01", "d32", "d03", "d12",
                "fam1", "fam2", "pipe1", "pipe2", "membrane"):
        c[key].preview = False
    _place(scene, c, {
        "size": (-820, -200), "centre_h": (-820, -100), "edge_h": (-820, -40), "members": (-820, 80),
        "radius": (-820, 180),
        "c0": (-520, -260), "c1": (-520, -160), "c2": (-520, -60), "c3": (-520, 40),
        "e01": (-350, -260), "e32": (-350, -160), "e03": (-350, -60), "e12": (-350, 40),
        "d01": (-190, -260), "d32": (-190, -160), "d03": (-190, -60), "d12": (-190, 40),
        "fam1": (-20, -210), "fam2": (-20, -10), "pipe1": (140, -210), "pipe2": (140, -10),
        "membrane": (-20, 160), "quadrants": (140, 260), "rot1": (320, -200), "rot2": (320, -40),
        "roof": (320, 140), "column": (320, 300)})
    _wire(scene, c, [
        ("centre_h", 0, "c0", 2),
        ("size", 0, "c1", 0), ("edge_h", 0, "c1", 2),
        ("size", 0, "c2", 0), ("size", 0, "c2", 1),
        ("size", 0, "c3", 1), ("edge_h", 0, "c3", 2),
        ("c0", 0, "e01", 0), ("c1", 0, "e01", 1), ("c3", 0, "e32", 0), ("c2", 0, "e32", 1),
        ("c0", 0, "e03", 0), ("c3", 0, "e03", 1), ("c1", 0, "e12", 0), ("c2", 0, "e12", 1),
        ("e01", 0, "d01", 0), ("e32", 0, "d32", 0), ("e03", 0, "d03", 0), ("e12", 0, "d12", 0),
        ("members", 0, "d01", 1), ("members", 0, "d32", 1), ("members", 0, "d03", 1), ("members", 0, "d12", 1),
        ("d01", 0, "fam1", 0), ("d32", 0, "fam1", 1), ("d03", 0, "fam2", 0), ("d12", 0, "fam2", 1),
        ("fam1", 0, "pipe1", 0), ("radius", 0, "pipe1", 1), ("fam2", 0, "pipe2", 0), ("radius", 0, "pipe2", 1),
        ("e01", 0, "membrane", 0), ("e32", 0, "membrane", 1),
        ("pipe1", 0, "rot1", 0), ("quadrants", 0, "rot1", 1),
        ("pipe2", 0, "rot2", 0), ("quadrants", 0, "rot2", 1),
        ("membrane", 0, "roof", 0), ("quadrants", 0, "roof", 1),
        ("centre_h", 0, "column", 1)])
    return c


def build_slats(scene) -> dict:
    """A slatted wave ceiling: thin timber slats whose top and bottom edges
    follow a drifting wave, each a ruled surface between two curves."""
    c = {
        "slats": _slider("Slats", 30, 8, 60, 0),
        "spacing": _slider("Spacing", 4, 2, 10),
        "length": _slider("Length", 120, 40, 200),
        "depth": _slider("Depth", 10, 3, 30),
        "amp": _slider("Amplitude", 8, 0, 20),
        "waves": _slider("Waves", 1.5, 0.5, 4, 2),
        "drift": _slider("Drift", 0.18, 0, 0.6, 2),
        "thick": _slider("Thickness", 1.2, 0.3, 3, 2),
        "i": lib.Series(), "xi": lib.Multiplication(), "phase": lib.Multiplication(), "yj": lib.Range(),
        "u": lib.Expression(), "top": lib.Expression(), "bottom": lib.Expression(),
        "tp": lib.ConstructPoint(), "bp": lib.ConstructPoint(), "tc": lib.Interpolate(), "bc": lib.Interpolate(),
        "face": lib.RuledSurface(), "dir": lib.VectorXYZ(), "slat": lib.Extrude(),
    }
    for key, nick in (("i", "Slat no."), ("xi", "Slat X"), ("phase", "Phase"), ("yj", "Y values"),
                      ("u", "Wave position"), ("top", "Top"), ("bottom", "Bottom"),
                      ("tp", "Top points"), ("bp", "Bottom points")):
        c[key].nickname = nick
    _set(c["yj"], N=40.0)
    _set(c["u"], F="x*y/z")
    _set(c["top"], F="z*sin(2*pi*x + y)")
    _set(c["bottom"], F="x - y*(0.6 + 0.4*cos(2*pi*z))")
    c["top"].inputs[2].modifier = "graft"   # y = phase: one branch per slat
    c["tp"].inputs[0].modifier = "graft"
    c["bp"].inputs[0].modifier = "graft"
    for key in ("tp", "bp", "tc", "bc", "face"):
        c[key].preview = False
    _place(scene, c, {
        "slats": (-800, -220), "spacing": (-800, -160), "length": (-800, -60), "depth": (-800, 0),
        "amp": (-800, 100), "waves": (-800, 160), "drift": (-800, 260), "thick": (-800, 360),
        "i": (-500, -230), "xi": (-330, -270), "phase": (-330, -170), "yj": (-500, -60), "u": (-330, -40),
        "top": (-150, -60), "bottom": (20, 60), "tp": (200, -160), "bp": (200, 40),
        "tc": (360, -160), "bc": (360, 40), "face": (520, -60), "dir": (520, 120), "slat": (680, -40)})
    _wire(scene, c, [
        ("slats", 0, "i", 2), ("i", 0, "xi", 0), ("spacing", 0, "xi", 1),
        ("i", 0, "phase", 0), ("drift", 0, "phase", 1),
        ("length", 0, "yj", 1),
        ("yj", 0, "u", 1), ("waves", 0, "u", 2), ("length", 0, "u", 3),
        ("u", 0, "top", 1), ("phase", 0, "top", 2), ("amp", 0, "top", 3),
        ("top", 0, "bottom", 1), ("depth", 0, "bottom", 2), ("u", 0, "bottom", 3),
        ("xi", 0, "tp", 0), ("yj", 0, "tp", 1), ("top", 0, "tp", 2),
        ("xi", 0, "bp", 0), ("yj", 0, "bp", 1), ("bottom", 0, "bp", 2),
        ("tp", 0, "tc", 0), ("bp", 0, "bc", 0), ("tc", 0, "face", 0), ("bc", 0, "face", 1),
        ("thick", 0, "dir", 0), ("face", 0, "slat", 0), ("dir", 0, "slat", 1)])
    return c


def build_monolith(scene) -> dict:
    """A carved monolith: a block hollowed by spherical voids that grow towards
    one corner, all subtracted in one Solid Difference."""
    c = {
        "w": _slider("Width", 60, 30, 120),
        "d": _slider("Depth", 40, 20, 80),
        "h": _slider("Height", 30, 15, 60),
        "voids": _slider("Voids", 60, 10, 150, 0),
        "seed": _slider("Seed", 4, 1, 50, 0),
        "small": _slider("Smallest void", 3, 1, 8, 2),
        "large": _slider("Largest void", 9, 3, 15, 2),
        "ax": _slider("Attractor X", -30, -60, 60),
        "ay": _slider("Attractor Y", -20, -40, 40),
        "az": _slider("Attractor Z", 30, 0, 60),
        "block": lib.Box(), "pop": lib.Populate2D(), "xy": lib.Deconstruct(), "z": lib.Expression(),
        "centres": lib.ConstructPoint(), "attractor": lib.ConstructPoint(), "dist": lib.Distance(),
        "bounds": lib.Bounds(), "remap": lib.Remap(), "sphere": lib.Sphere(), "voids_at": lib.Move(),
        "carved": lib.Difference(),
    }
    for key, nick in (("z", "Heights"), ("centres", "Void centres"), ("attractor", "Attractor"),
                      ("voids_at", "Voids")):
        c[key].nickname = nick
    _set(c["pop"], R=1.0)
    _set(c["z"], F="z*(0.1 + 0.8*abs(sin(x*1.7 + y*2.3)))")   # repeatable "random" heights
    c["bounds"].inputs[0].modifier = "flatten"
    for key in ("block", "pop", "centres", "attractor", "sphere", "voids_at"):
        c[key].preview = False
    _place(scene, c, {
        "w": (-800, -240), "d": (-800, -180), "h": (-800, -120), "voids": (-800, -20), "seed": (-800, 40),
        "small": (-800, 140), "large": (-800, 200), "ax": (-800, 300), "ay": (-800, 360), "az": (-800, 420),
        "block": (-480, -250), "pop": (-480, -60), "xy": (-320, -60), "z": (-160, 0), "centres": (0, -60),
        "attractor": (-480, 340), "dist": (160, 120), "bounds": (320, 200), "remap": (480, 140),
        "sphere": (640, 140), "voids_at": (800, 0), "carved": (960, -120)})
    _wire(scene, c, [
        ("w", 0, "block", 0), ("d", 0, "block", 1), ("h", 0, "block", 2),
        ("w", 0, "pop", 0), ("d", 0, "pop", 1), ("voids", 0, "pop", 2), ("seed", 0, "pop", 3),
        ("pop", 0, "xy", 0), ("xy", 0, "z", 1), ("xy", 1, "z", 2), ("h", 0, "z", 3),
        ("xy", 0, "centres", 0), ("xy", 1, "centres", 1), ("z", 0, "centres", 2),
        ("ax", 0, "attractor", 0), ("ay", 0, "attractor", 1), ("az", 0, "attractor", 2),
        ("centres", 0, "dist", 0), ("attractor", 0, "dist", 1), ("dist", 0, "bounds", 0),
        ("dist", 0, "remap", 0), ("bounds", 0, "remap", 1), ("bounds", 1, "remap", 2),
        ("large", 0, "remap", 3), ("small", 0, "remap", 4),
        ("remap", 0, "sphere", 0),
        ("sphere", 0, "voids_at", 0), ("xy", 0, "voids_at", 1), ("xy", 1, "voids_at", 2), ("z", 0, "voids_at", 3),
        ("block", 0, "carved", 0), ("voids_at", 0, "carved", 1)])
    return c


def build_flange(scene) -> dict:
    """A bolted flange with its GD&T made visible: each hole's position
    tolerance zone (bonus included, exaggerated) and a gauge pin at the
    holes' virtual condition. Drag the actual hole size and the zones grow."""
    MMC, LMC = 9.0, 9.3   # hole size limits, mm
    c = {
        "R": _slider("Flange radius", 40, 25, 60),
        "t": _slider("Thickness", 8, 4, 16),
        "bc": _slider("Bolt circle", 28, 15, 50),
        "bolts": _slider("Bolts", 6, 3, 12, 0),
        "actual": _slider("Actual hole Ø", 9.15, MMC, LMC, 3),
        "pos": _slider("Position Ø", 0.2, 0.05, 0.5, 3),
        "scale": _slider("Zone scale", 15, 1, 40, 0),
        # the part
        "disc": lib.Cylinder(), "hub": lib.Cylinder(), "bore": lib.Cylinder(), "bore_dn": lib.Move(),
        "circle": lib.Circle(), "div": lib.DivideCurve(), "xy": lib.Deconstruct(),
        "hole_r": lib.Expression(), "hole_l": lib.Addition(), "hole": lib.Cylinder(), "holes": lib.Move(),
        "drilled": lib.Difference(), "flange": lib.Difference(), "hub_bored": lib.Difference(),
        # the tolerance
        "bonus": lib.BonusTolerance(), "bounds": lib.SizeBoundaries(), "panel": lib.Panel(),
        "zone_r": lib.Expression(), "zone": lib.Cylinder(), "zones": lib.Move(),
        "pin_r": lib.Multiplication(), "pin": lib.Cylinder(), "pins": lib.Move(),
    }
    for key, nick in (("disc", "Disc"), ("hub", "Hub"), ("bore", "Bore"), ("hole", "Hole"), ("holes", "Holes"),
                      ("zone", "Zone"), ("zones", "Zones"), ("pin", "Gauge pin"), ("pins", "Gauge pins"),
                      ("zone_r", "Zone radius"), ("hole_r", "Hole radius")):
        c[key].nickname = nick
    _set(c["hub"], R=15.0, L=22.0)
    _set(c["bore"], R=8.0, L=30.0)
    _set(c["bore_dn"], Z=-2.0)
    _set(c["hole_r"], F="x/2")
    _set(c["hole_l"], B=2.0)
    _set(c["holes"], Z=-1.0)
    _set(c["bonus"], MMC=MMC, LMC=LMC)
    _set(c["bounds"], MMC=MMC, LMC=LMC)
    _set(c["zone_r"], F="x*y/2")
    _set(c["zone"], L=14.0)
    _set(c["zones"], Z=-3.0)
    _set(c["pin_r"], B=0.5)
    _set(c["pin"], L=20.0)
    _set(c["pins"], Z=-6.0)
    c["panel"].size = (170, 70)
    for key in ("disc", "hub", "bore", "bore_dn", "circle", "div", "hole", "holes", "drilled", "zone", "pin"):
        c[key].preview = False
    _place(scene, c, {
        "R": (-880, -380), "t": (-880, -320), "bc": (-880, -200), "bolts": (-880, -140), "actual": (-880, 0),
        "pos": (-880, 60), "scale": (-880, 200),
        "disc": (-580, -400), "hub": (-580, -290), "bore": (-580, -180), "circle": (-580, -60),
        "hole_r": (-580, 60), "hole_l": (-580, 190), "bonus": (-580, 320), "bounds": (-580, 490),
        "bore_dn": (-400, -180), "div": (-400, -60), "hole": (-400, 140), "panel": (-400, 330),
        "xy": (-220, -60), "zone_r": (-220, 280), "pin_r": (-220, 490),
        "holes": (-40, -20), "zone": (-40, 280), "pin": (-40, 490),
        "zones": (140, 240), "pins": (140, 440),
        "drilled": (320, -330), "hub_bored": (320, -180), "flange": (500, -330)})
    _wire(scene, c, [
        ("R", 0, "disc", 0), ("t", 0, "disc", 1),
        ("bore", 0, "bore_dn", 0),
        ("bc", 0, "circle", 0), ("circle", 0, "div", 0), ("bolts", 0, "div", 1), ("div", 0, "xy", 0),
        ("actual", 0, "hole_r", 1), ("t", 0, "hole_l", 0),
        ("hole_r", 0, "hole", 0), ("hole_l", 0, "hole", 1),
        ("hole", 0, "holes", 0), ("xy", 0, "holes", 1), ("xy", 1, "holes", 2),
        ("disc", 0, "drilled", 0), ("holes", 0, "drilled", 1),
        ("drilled", 0, "flange", 0), ("bore_dn", 0, "flange", 1),
        ("hub", 0, "hub_bored", 0), ("bore_dn", 0, "hub_bored", 1),
        ("actual", 0, "bonus", 0), ("pos", 0, "bonus", 3), ("pos", 0, "bounds", 2),
        ("bonus", 1, "panel", 0),
        ("bonus", 1, "zone_r", 1), ("scale", 0, "zone_r", 2), ("zone_r", 0, "zone", 0),
        ("zone", 0, "zones", 0), ("xy", 0, "zones", 1), ("xy", 1, "zones", 2),
        ("bounds", 0, "pin_r", 0), ("pin_r", 0, "pin", 0),
        ("pin", 0, "pins", 0), ("xy", 0, "pins", 1), ("xy", 1, "pins", 2)])
    return c


def build_bridge(scene) -> dict:
    """A network-arch bridge: twin arches leaning towards each other over a
    cambered deck, each hung from it by two crossing families of hangers."""
    c = {
        "span": _slider("Span", 120, 60, 200),
        "rise": _slider("Rise", 40, 15, 70),
        "lean": _slider("Lean", 6, 0, 15),
        "width": _slider("Deck width", 16, 8, 30),
        "camber": _slider("Camber", 3, 0.5, 10),
        "hangers": _slider("Hangers", 24, 6, 48, 0),
        "drift": _slider("Hanger slope", 0.08, 0, 0.12, 3),   # t ± slope stays within 0..1
        "arch_r": _slider("Arch radius", 1.4, 0.4, 3, 2),
        # arch
        "sx": lib.Expression(), "nsx": lib.Multiplication(), "ey": lib.Expression(), "ay": lib.Expression(),
        "s0": lib.ConstructPoint(), "apex": lib.ConstructPoint(), "s1": lib.ConstructPoint(), "arch": lib.Arc3Pt(),
        # deck
        "half": lib.Expression(), "nhalf": lib.Multiplication(), "d0": lib.ConstructPoint(),
        "dm": lib.ConstructPoint(), "d1": lib.ConstructPoint(), "deck_c": lib.Arc3Pt(), "wy": lib.Multiplication(),
        "left": lib.Move(), "right": lib.Move(), "face": lib.RuledSurface(), "down": lib.VectorXYZ(),
        "deck": lib.Extrude(),
        # hangers
        "t": lib.Range(), "tp": lib.Addition(), "tm": lib.Expression(), "ap": lib.EvaluateCurve(),
        "dp": lib.EvaluateCurve(), "dmn": lib.EvaluateCurve(), "h1": lib.Line(), "h2": lib.Line(),
        "arch_p": lib.Pipe(), "hp1": lib.Pipe(), "hp2": lib.Pipe(),
        "arch_m": lib.Mirror(), "hm1": lib.Mirror(), "hm2": lib.Mirror(),
    }
    for key, nick in (("sx", "Spring X"), ("ey", "Edge Y"), ("ay", "Apex Y"), ("s0", "Spring 1"),
                      ("apex", "Apex"), ("s1", "Spring 2"), ("half", "Half span"), ("deck_c", "Deck line"),
                      ("left", "Deck edge"), ("t", "Hanger t"), ("ap", "On arch"), ("dp", "On deck +"),
                      ("dmn", "On deck −"), ("h1", "Hangers 1"), ("h2", "Hangers 2")):
        c[key].nickname = nick
    _set(c["sx"], F="x/2 + 6")      # the arch springs from abutments beyond the deck ends...
    _set(c["nsx"], B=-1.0)
    _set(c["ey"], F="-x/2")
    _set(c["ay"], F="z - x/2")      # ...and leans in by Lean at the crown
    _set(c["s0"], Z=-5.0)
    _set(c["s1"], Z=-5.0)
    _set(c["half"], F="x/2")
    _set(c["nhalf"], B=-1.0)
    _set(c["wy"], B=-1.0)
    _set(c["down"], Z=-1.5)
    _set(c["t"], S=0.12, E=0.88)
    _set(c["tm"], F="x - y")
    _set(c["hp1"], R=0.22)
    _set(c["hp2"], R=0.22)
    for key in ("arch_m", "hm1", "hm2"):
        _set(c[key], N=(0.0, 1.0, 0.0))   # mirror in the deck's centre plane
    for key in ("s0", "apex", "s1", "arch", "d0", "dm", "d1", "deck_c", "left", "right", "face",
                "ap", "dp", "dmn", "h1", "h2"):
        c[key].preview = False
    _place(scene, c, {
        "span": (-900, -320), "rise": (-900, -260), "lean": (-900, -200), "width": (-900, -100),
        "camber": (-900, -40), "hangers": (-900, 80), "drift": (-900, 140), "arch_r": (-900, 260),
        "sx": (-600, -360), "nsx": (-440, -400), "ey": (-600, -240), "ay": (-600, -130),
        "s0": (-280, -420), "apex": (-280, -300), "s1": (-280, -180), "arch": (-110, -300),
        "half": (-600, 0), "nhalf": (-440, 0), "d0": (-280, -40), "dm": (-280, 60), "d1": (-280, 160),
        "deck_c": (-110, 60), "wy": (-440, 120), "left": (60, 0), "right": (60, 120), "face": (230, 60),
        "down": (230, 180), "deck": (400, 100),
        "t": (-440, 300), "tp": (-280, 300), "tm": (-280, 400), "ap": (230, -300), "dp": (230, 300),
        "dmn": (230, 400), "h1": (400, -200), "h2": (400, -60), "arch_p": (560, -360),
        "hp1": (560, -220), "hp2": (560, -80), "arch_m": (720, -360), "hm1": (720, -220), "hm2": (720, -80)})
    _wire(scene, c, [
        ("span", 0, "sx", 1), ("sx", 0, "nsx", 0), ("width", 0, "ey", 1),
        ("width", 0, "ay", 1), ("lean", 0, "ay", 3),
        ("nsx", 0, "s0", 0), ("ey", 0, "s0", 1), ("ay", 0, "apex", 1), ("rise", 0, "apex", 2),
        ("sx", 0, "s1", 0), ("ey", 0, "s1", 1),
        ("s0", 0, "arch", 0), ("apex", 0, "arch", 1), ("s1", 0, "arch", 2),
        ("span", 0, "half", 1), ("half", 0, "nhalf", 0),
        ("nhalf", 0, "d0", 0), ("camber", 0, "dm", 2), ("half", 0, "d1", 0),
        ("d0", 0, "deck_c", 0), ("dm", 0, "deck_c", 1), ("d1", 0, "deck_c", 2),
        ("ey", 0, "wy", 0),
        ("deck_c", 0, "left", 0), ("ey", 0, "left", 2), ("deck_c", 0, "right", 0), ("wy", 0, "right", 2),
        ("left", 0, "face", 0), ("right", 0, "face", 1), ("face", 0, "deck", 0), ("down", 0, "deck", 1),
        ("hangers", 0, "t", 2), ("t", 0, "tp", 0), ("drift", 0, "tp", 1), ("t", 0, "tm", 1), ("drift", 0, "tm", 2),
        ("arch", 0, "ap", 0), ("t", 0, "ap", 1),
        ("left", 0, "dp", 0), ("tp", 0, "dp", 1), ("left", 0, "dmn", 0), ("tm", 0, "dmn", 1),
        ("ap", 0, "h1", 0), ("dp", 0, "h1", 1), ("ap", 0, "h2", 0), ("dmn", 0, "h2", 1),
        ("arch", 0, "arch_p", 0), ("arch_r", 0, "arch_p", 1), ("h1", 0, "hp1", 0), ("h2", 0, "hp2", 0),
        ("arch_p", 0, "arch_m", 0), ("hp1", 0, "hm1", 0), ("hp2", 0, "hm2", 0)])
    return c


def build_shell(scene) -> dict:
    """A spiral shell: circles that grow exponentially along a logarithmic
    spiral which also drops in proportion to its radius, so the shell is
    self-similar, lofted into a horn with a thin growth line on every ring."""
    c = {
        "turns": _slider("Turns", 3, 1, 5, 2),
        "steps": _slider("Rings", 60, 20, 120, 0),
        "a": _slider("Start radius", 1, 0.5, 5, 2),
        "b": _slider("Growth", 0.14, 0.05, 0.25, 3),
        "spire": _slider("Spire", 1.6, 0, 3, 2),
        "open": _slider("Opening", 0.7, 0.2, 0.9, 2),
        "end": lib.Expression(), "phi": lib.Range(), "r": lib.Expression(),
        "cx": lib.Expression(), "cy": lib.Expression(), "cz": lib.Expression(),
        "tx": lib.Expression(), "ty": lib.Expression(), "tz": lib.Expression(),
        "centre": lib.ConstructPoint(), "normal": lib.VectorXYZ(),
        "size": lib.Multiplication(), "ring": lib.CircleCNR(), "shell": lib.Loft(),
        "line_r": lib.Multiplication(), "lines": lib.Pipe(),
    }
    for key, nick, f in (("end", "End angle", "2*pi*x"), ("r", "Spiral radius", "y*exp(z*x)"),
                         ("cx", "X", "x*cos(y)"), ("cy", "Y", "x*sin(y)"), ("cz", "Z", "-x*y"),
                         ("tx", "Tangent X", "x*(z*cos(y) - sin(y))"), ("ty", "Tangent Y", "x*(z*sin(y) + cos(y))"),
                         ("tz", "Tangent Z", "-x*y*z")):
        c[key].nickname = nick
        _set(c[key], F=f)
    c["phi"].nickname = "φ"
    c["lines"].nickname = "Growth lines"
    _set(c["line_r"], B=0.05)
    c["shell"].inputs[0].modifier = "flatten"
    for key in ("centre", "ring"):
        c[key].preview = False
    _place(scene, c, {
        "turns": (-820, -240), "steps": (-820, -180), "a": (-820, -80), "b": (-820, -20), "spire": (-820, 80),
        "open": (-820, 180),
        "end": (-520, -240), "phi": (-360, -200), "r": (-200, -140), "cx": (-40, -300), "cy": (-40, -190),
        "cz": (-40, -80), "tx": (-40, 30), "ty": (-40, 140), "tz": (-40, 250), "centre": (140, -190),
        "normal": (140, 60), "size": (140, 200), "ring": (320, -40), "shell": (500, -120),
        "line_r": (320, 160), "lines": (500, 80)})
    _wire(scene, c, [
        ("turns", 0, "end", 1), ("end", 0, "phi", 1), ("steps", 0, "phi", 2),
        ("phi", 0, "r", 1), ("a", 0, "r", 2), ("b", 0, "r", 3),
        ("r", 0, "cx", 1), ("phi", 0, "cx", 2), ("r", 0, "cy", 1), ("phi", 0, "cy", 2),
        ("r", 0, "cz", 1), ("spire", 0, "cz", 2),
        ("r", 0, "tx", 1), ("phi", 0, "tx", 2), ("b", 0, "tx", 3),
        ("r", 0, "ty", 1), ("phi", 0, "ty", 2), ("b", 0, "ty", 3),
        ("r", 0, "tz", 1), ("spire", 0, "tz", 2), ("b", 0, "tz", 3),
        ("cx", 0, "centre", 0), ("cy", 0, "centre", 1), ("cz", 0, "centre", 2),
        ("tx", 0, "normal", 0), ("ty", 0, "normal", 1), ("tz", 0, "normal", 2),
        ("r", 0, "size", 0), ("open", 0, "size", 1),
        ("centre", 0, "ring", 0), ("normal", 0, "ring", 1), ("size", 0, "ring", 2),
        ("ring", 0, "shell", 0),
        ("size", 0, "line_r", 0), ("ring", 0, "lines", 0), ("line_r", 0, "lines", 1)])
    return c


def build_origami(scene) -> dict:
    """A Miura-ori fold: rows of zigzags, each shifted alternately left and
    right, lofted with straight faces, so every facet is a flat parallelogram."""
    c = {
        "pleats": _slider("Pleats", 16, 4, 40, 0),
        "rows": _slider("Rows", 12, 2, 30, 0),
        "width": _slider("Pleat width", 6, 2, 12),
        "depth": _slider("Pleat depth", 6, 0, 10),
        "height": _slider("Row height", 6, 2, 12),
        "shear": _slider("Shear", 2.5, 0, 6),
        "np": lib.Addition(), "nr": lib.Addition(), "i": lib.Series(), "k": lib.Series(),
        "ix": lib.Multiplication(), "shift": lib.Expression(), "x": lib.Addition(), "y": lib.Expression(),
        "z": lib.Multiplication(), "pts": lib.ConstructPoint(), "row": lib.Polyline(), "sheet": lib.Loft(),
    }
    for key, nick in (("i", "Point no."), ("k", "Row no."), ("shift", "Row shift"), ("y", "Zigzag"),
                      ("x", "X"), ("z", "Z"), ("row", "Rows")):
        c[key].nickname = nick
    _set(c["np"], B=1.0)
    _set(c["nr"], B=1.0)
    _set(c["shift"], F="y*(x % 2)")
    _set(c["y"], F="y*(x % 2)")
    _set(c["sheet"], St=True)
    c["shift"].inputs[1].modifier = "graft"   # x = row number: one branch per row
    c["z"].inputs[0].modifier = "graft"
    c["sheet"].inputs[0].modifier = "flatten"
    for key in ("pts", "row"):
        c[key].preview = False
    _place(scene, c, {
        "pleats": (-760, -200), "rows": (-760, -140), "width": (-760, -40), "depth": (-760, 20),
        "height": (-760, 120), "shear": (-760, 180),
        "np": (-480, -230), "nr": (-480, -120), "i": (-320, -230), "k": (-320, -120), "ix": (-160, -260),
        "shift": (-160, -150), "x": (0, -220), "y": (0, -90), "z": (0, 30), "pts": (160, -120),
        "row": (320, -120), "sheet": (480, -120)})
    _wire(scene, c, [
        ("pleats", 0, "np", 0), ("rows", 0, "nr", 0), ("np", 0, "i", 2), ("nr", 0, "k", 2),
        ("i", 0, "ix", 0), ("width", 0, "ix", 1),
        ("k", 0, "shift", 1), ("shear", 0, "shift", 2),
        ("ix", 0, "x", 0), ("shift", 0, "x", 1),
        ("i", 0, "y", 1), ("depth", 0, "y", 2),
        ("k", 0, "z", 0), ("height", 0, "z", 1),
        ("x", 0, "pts", 0), ("y", 0, "pts", 1), ("z", 0, "pts", 2),
        ("pts", 0, "row", 0), ("row", 0, "sheet", 0)])
    return c


def build_rose(scene) -> dict:
    """A guilloché rose: arcs from every point of an inner ring, through a
    middle ring and out to an outer ring, turned k places one way and k the
    other, piped into interlacing filigree."""
    c = {
        "r1": _slider("Inner radius", 8, 3, 20),
        "r2": _slider("Middle radius", 20, 8, 35),
        "r3": _slider("Outer radius", 32, 15, 50),
        "n": _slider("Points", 48, 12, 96, 0),
        "k": _slider("Outer turn", 8, 1, 24, 0),
        "m": _slider("Middle turn", 5, 0, 24, 0),
        "wire": _slider("Wire radius", 0.3, 0.1, 1, 2),
        "c1": lib.Circle(), "c2": lib.Circle(), "c3": lib.Circle(),
        "d1": lib.DivideCurve(), "d2": lib.DivideCurve(), "d3": lib.DivideCurve(),
        "nk": lib.Multiplication(), "nm": lib.Multiplication(),
        "s2p": lib.ShiftList(), "s3p": lib.ShiftList(), "s2n": lib.ShiftList(), "s3n": lib.ShiftList(),
        "ap": lib.Arc3Pt(), "an": lib.Arc3Pt(), "pp": lib.Pipe(), "pn": lib.Pipe(),
        "ring_r": lib.Multiplication(), "inner": lib.Pipe(), "outer": lib.Pipe(),
    }
    for key, nick in (("c1", "Inner"), ("c2", "Middle"), ("c3", "Outer"), ("ap", "Arcs +"), ("an", "Arcs −"),
                      ("inner", "Inner ring"), ("outer", "Outer ring")):
        c[key].nickname = nick
    _set(c["nk"], B=-1.0)
    _set(c["nm"], B=-1.0)
    _set(c["ring_r"], B=2.5)
    for key in ("c1", "c2", "c3", "d1", "d2", "d3", "s2p", "s3p", "s2n", "s3n", "ap", "an"):
        c[key].preview = False
    _place(scene, c, {
        "r1": (-820, -260), "r2": (-820, -200), "r3": (-820, -140), "n": (-820, -40), "k": (-820, 60),
        "m": (-820, 120), "wire": (-820, 240),
        "c1": (-520, -280), "c2": (-520, -180), "c3": (-520, -80), "d1": (-360, -280), "d2": (-360, -180),
        "d3": (-360, -80), "nk": (-520, 60), "nm": (-520, 160), "s2p": (-180, -200), "s3p": (-180, -100),
        "s2n": (-180, 20), "s3n": (-180, 120), "ap": (0, -180), "an": (0, 40), "pp": (180, -180),
        "pn": (180, 40), "ring_r": (0, 220), "inner": (180, 200), "outer": (180, 300)})
    _wire(scene, c, [
        ("r1", 0, "c1", 0), ("r2", 0, "c2", 0), ("r3", 0, "c3", 0),
        ("c1", 0, "d1", 0), ("c2", 0, "d2", 0), ("c3", 0, "d3", 0),
        ("n", 0, "d1", 1), ("n", 0, "d2", 1), ("n", 0, "d3", 1),
        ("k", 0, "nk", 0), ("m", 0, "nm", 0),
        ("d2", 0, "s2p", 0), ("m", 0, "s2p", 1), ("d3", 0, "s3p", 0), ("k", 0, "s3p", 1),
        ("d2", 0, "s2n", 0), ("nm", 0, "s2n", 1), ("d3", 0, "s3n", 0), ("nk", 0, "s3n", 1),
        ("d1", 0, "ap", 0), ("s2p", 0, "ap", 1), ("s3p", 0, "ap", 2),
        ("d1", 0, "an", 0), ("s2n", 0, "an", 1), ("s3n", 0, "an", 2),
        ("ap", 0, "pp", 0), ("wire", 0, "pp", 1), ("an", 0, "pn", 0), ("wire", 0, "pn", 1),
        ("wire", 0, "ring_r", 0), ("c1", 0, "inner", 0), ("ring_r", 0, "inner", 1),
        ("c3", 0, "outer", 0), ("ring_r", 0, "outer", 1)])
    return c


def build_mashrabiya(scene) -> dict:
    """A responsive mashrabiya: a hexagonal grid of cells, each a ruled frustum
    from its outline to a smaller copy pushed forward. Cells facing the sun
    close up and stand out; the rest open flat."""
    c = {
        "cols": _slider("Columns", 12, 4, 30, 0),
        "rows": _slider("Rows", 9, 4, 24, 0),
        "cell": _slider("Cell radius", 6, 3, 12),
        "sides": _slider("Sides", 6, 3, 8, 0),
        "sx": _slider("Sun X", 30, -40, 160),
        "sy": _slider("Sun Y", 45, -40, 120),
        "sz": _slider("Sun distance", 40, 5, 120),
        "closed": _slider("Most closed", 0.15, 0.05, 0.9, 2),
        "opened": _slider("Most open", 0.85, 0.1, 0.95, 2),
        "deep": _slider("Most depth", 4, 0.5, 10),
        "i": lib.Series(), "j": lib.Series(), "x": lib.Expression(), "y": lib.Expression(),
        "centres": lib.ConstructPoint(), "outline": lib.RegularPolygon(), "cells": lib.Move(),
        "sun": lib.ConstructPoint(), "dist": lib.Distance(), "bounds": lib.Bounds(),
        "open": lib.Remap(), "depth": lib.Remap(), "shrunk": lib.Scale(), "inner": lib.Move(),
        "louvres": lib.RuledSurface(), "facade": lib.Rotate(),
    }
    for key, nick in (("i", "Column no."), ("j", "Row no."), ("centres", "Cell centres"), ("sun", "Sun"),
                      ("open", "Opening"), ("depth", "Depth"), ("inner", "Inner"), ("louvres", "Louvres")):
        c[key].nickname = nick
    # pointy-top hexagons: sqrt(3) R apart in a row, rows 1.5 R apart, odd rows shifted half a cell
    _set(c["x"], F="(x + 0.5*(y % 2))*1.7320508*z")
    _set(c["y"], F="1.5*x*y")
    _set(c["outline"], A=30.0)
    _set(c["facade"], A=90.0, X=(1.0, 0.0, 0.0))
    c["x"].inputs[2].modifier = "graft"   # y = row number: one branch per row
    c["y"].inputs[1].modifier = "graft"
    c["bounds"].inputs[0].modifier = "flatten"
    for key in ("centres", "outline", "cells", "sun", "shrunk", "inner", "louvres"):
        c[key].preview = False
    _place(scene, c, {
        "cols": (-860, -300), "rows": (-860, -240), "cell": (-860, -140), "sides": (-860, -80),
        "sx": (-860, 40), "sy": (-860, 100), "sz": (-860, 160), "closed": (-860, 260), "opened": (-860, 320),
        "deep": (-860, 420),
        "i": (-560, -320), "j": (-560, -210), "x": (-400, -320), "y": (-400, -190), "centres": (-220, -260),
        "outline": (-400, -60), "cells": (-40, -160), "sun": (-560, 120), "dist": (-40, 40),
        "bounds": (120, 120), "open": (280, 20), "depth": (280, 220), "shrunk": (440, -120),
        "inner": (600, -60), "louvres": (760, -140), "facade": (920, -140)})
    _wire(scene, c, [
        ("cols", 0, "i", 2), ("rows", 0, "j", 2),
        ("i", 0, "x", 1), ("j", 0, "x", 2), ("cell", 0, "x", 3),
        ("j", 0, "y", 1), ("cell", 0, "y", 2),
        ("x", 0, "centres", 0), ("y", 0, "centres", 1),
        ("cell", 0, "outline", 0), ("sides", 0, "outline", 1),
        ("outline", 0, "cells", 0), ("x", 0, "cells", 1), ("y", 0, "cells", 2),
        ("sx", 0, "sun", 0), ("sy", 0, "sun", 1), ("sz", 0, "sun", 2),
        ("centres", 0, "dist", 0), ("sun", 0, "dist", 1), ("dist", 0, "bounds", 0),
        ("dist", 0, "open", 0), ("bounds", 0, "open", 1), ("bounds", 1, "open", 2),
        ("closed", 0, "open", 3), ("opened", 0, "open", 4),
        ("dist", 0, "depth", 0), ("bounds", 0, "depth", 1), ("bounds", 1, "depth", 2), ("deep", 0, "depth", 3),
        ("cells", 0, "shrunk", 0), ("open", 0, "shrunk", 1), ("centres", 0, "shrunk", 2),
        ("shrunk", 0, "inner", 0), ("depth", 0, "inner", 3),
        ("cells", 0, "louvres", 0), ("inner", 0, "louvres", 1), ("louvres", 0, "facade", 0)])
    return c


def build_columns(scene) -> dict:
    """Mushroom columns: a slender stem flaring into a fluted, scalloped
    canopy, lofted through three sections and arrayed into a forest."""
    c = {
        "stem": _slider("Stem radius", 1.2, 0.4, 4, 2),
        "neck": _slider("Neck radius", 2.2, 0.5, 6, 2),
        "crown": _slider("Canopy radius", 12, 5, 25),
        "height": _slider("Height", 20, 8, 40),
        "flutes": _slider("Flutes", 12, 3, 24, 0),
        "scallop": _slider("Scallop", 1.6, 0, 5, 2),
        "cols": _slider("Columns", 4, 1, 8, 0),
        "rows": _slider("Rows", 3, 1, 8, 0),
        "base": lib.Circle(), "neck_z": lib.Multiplication(), "mid": lib.Circle(),
        "k": lib.Series(), "theta": lib.Expression(), "nt": lib.Multiplication(),
        "x": lib.Expression(), "y": lib.Expression(), "z": lib.Expression(), "pts": lib.ConstructPoint(),
        "rim": lib.Interpolate(), "column": lib.Loft(),
        "pitch": lib.Multiplication(), "dx": lib.VectorXYZ(), "dy": lib.VectorXYZ(),
        "row": lib.LinearArray(), "forest": lib.LinearArray(),
    }
    for key, nick in (("base", "Base ring"), ("mid", "Neck ring"), ("rim", "Scalloped rim"), ("column", "Column"),
                      ("k", "Point no."), ("theta", "θ"), ("pitch", "Pitch"), ("row", "Row"), ("forest", "Forest")):
        c[key].nickname = nick
    _set(c["neck_z"], B=0.7)
    _set(c["k"], C=48.0)   # 48 rim points: 96 made each canopy surface heavier to draw for no visible gain
    _set(c["theta"], F="2*pi*x/48")
    _set(c["x"], F="y*cos(x)")
    _set(c["y"], F="y*sin(x)")
    _set(c["z"], F="y + z*cos(x)")
    _set(c["rim"], P=True)
    _set(c["pitch"], B=2.0)
    c["column"].inputs[0].modifier = "flatten"
    for key in ("base", "mid", "pts", "rim", "column", "row"):
        c[key].preview = False
    _place(scene, c, {
        "stem": (-820, -260), "neck": (-820, -200), "crown": (-820, -140), "height": (-820, -40),
        "flutes": (-820, 60), "scallop": (-820, 120), "cols": (-820, 240), "rows": (-820, 300),
        "base": (-520, -280), "neck_z": (-520, -170), "mid": (-360, -200), "k": (-520, -40),
        "theta": (-360, -40), "nt": (-200, 60), "x": (-200, -120), "y": (-40, -60), "z": (-40, 60),
        "pts": (120, -40), "rim": (280, -40), "column": (440, -180), "pitch": (280, 180),
        "dx": (440, 120), "dy": (440, 240), "row": (600, -120), "forest": (760, -60)})
    wires = [
        ("stem", 0, "base", 0),
        ("height", 0, "neck_z", 0), ("neck", 0, "mid", 0), ("neck_z", 0, "mid", 1),
        ("k", 0, "theta", 1), ("theta", 0, "nt", 0), ("flutes", 0, "nt", 1),
        ("theta", 0, "x", 1), ("crown", 0, "x", 2), ("theta", 0, "y", 1), ("crown", 0, "y", 2),
        ("nt", 0, "z", 1), ("height", 0, "z", 2), ("scallop", 0, "z", 3),
        ("x", 0, "pts", 0), ("y", 0, "pts", 1), ("z", 0, "pts", 2), ("pts", 0, "rim", 0),
        # three wires into one input: their curves merge, in this order, into the loft's sections
        ("base", 0, "column", 0), ("mid", 0, "column", 0), ("rim", 0, "column", 0),
        ("crown", 0, "pitch", 0), ("pitch", 0, "dx", 0), ("pitch", 0, "dy", 1),
        ("column", 0, "row", 0), ("dx", 0, "row", 1), ("cols", 0, "row", 2),
        ("row", 0, "forest", 0), ("dy", 0, "forest", 1), ("rows", 0, "forest", 2)]
    _wire(scene, c, wires)
    return c


def build_pendants(scene) -> dict:
    """A pendant cloud: a grid of orbs hanging from a ceiling, their drops
    following a damped ripple, like a frozen wave of light."""
    c = {
        "size": _slider("Size", 70, 20, 140),
        "grid": _slider("Grid", 12, 4, 24, 0),
        "ceiling": _slider("Ceiling", 40, 20, 80),
        "drop": _slider("Drop", 16, 4, 40),
        "amp": _slider("Amplitude", 8, 0, 20),
        "freq": _slider("Frequency", 0.25, 0.05, 0.8, 3),
        "orb": _slider("Orb radius", 1.3, 0.3, 3, 2),
        "lo": lib.Multiplication(), "hi": lib.Multiplication(), "xs": lib.Range(), "ys": lib.Range(),
        "d": lib.Expression(), "ripple": lib.Expression(), "zo": lib.Expression(),
        "top": lib.ConstructPoint(), "bottom": lib.ConstructPoint(), "cable": lib.Line(), "cables": lib.Pipe(),
        "sphere": lib.Sphere(), "orbs": lib.Move(), "plate_w": lib.Addition(), "plate": lib.Box(),
        "ceiling_at": lib.Move(),
    }
    for key, nick in (("xs", "X values"), ("ys", "Y values"), ("d", "Distance"), ("ripple", "Ripple"),
                      ("zo", "Orb height"), ("top", "Anchors"), ("bottom", "Orb centres"), ("cables", "Cables"),
                      ("orbs", "Orbs"), ("ceiling_at", "Ceiling")):
        c[key].nickname = nick
    _set(c["lo"], B=-0.5)
    _set(c["hi"], B=0.5)
    _set(c["d"], F="sqrt(x**2 + y**2)")
    _set(c["ripple"], F="z*sin(y*x)/(1 + 0.08*x)")   # Gemini's damped ripple, A sin(k d) / (1 + c d)
    _set(c["zo"], F="x - y + z")
    _set(c["cables"], R=0.08)
    _set(c["plate_w"], B=10.0)
    _set(c["plate"], Z=1.5)
    c["d"].inputs[2].modifier = "graft"
    c["top"].inputs[1].modifier = "graft"
    c["bottom"].inputs[1].modifier = "graft"
    c["orbs"].inputs[2].modifier = "graft"
    for key in ("top", "bottom", "cable", "sphere", "plate"):
        c[key].preview = False
    _place(scene, c, {
        "size": (-820, -260), "grid": (-820, -200), "ceiling": (-820, -100), "drop": (-820, -40),
        "amp": (-820, 60), "freq": (-820, 120), "orb": (-820, 220),
        "lo": (-520, -300), "hi": (-520, -200), "xs": (-360, -300), "ys": (-360, -190), "d": (-180, -200),
        "ripple": (-20, -120), "zo": (140, -60), "top": (140, -240), "bottom": (300, -100),
        "cable": (460, -200), "cables": (620, -200), "sphere": (300, 80), "orbs": (460, 20),
        "plate_w": (-360, 120), "plate": (-180, 160), "ceiling_at": (0, 160)})
    _wire(scene, c, [
        ("size", 0, "lo", 0), ("size", 0, "hi", 0),
        ("lo", 0, "xs", 0), ("hi", 0, "xs", 1), ("grid", 0, "xs", 2),
        ("lo", 0, "ys", 0), ("hi", 0, "ys", 1), ("grid", 0, "ys", 2),
        ("xs", 0, "d", 1), ("ys", 0, "d", 2),
        ("d", 0, "ripple", 1), ("freq", 0, "ripple", 2), ("amp", 0, "ripple", 3),
        ("ceiling", 0, "zo", 1), ("drop", 0, "zo", 2), ("ripple", 0, "zo", 3),
        ("xs", 0, "top", 0), ("ys", 0, "top", 1), ("ceiling", 0, "top", 2),
        ("xs", 0, "bottom", 0), ("ys", 0, "bottom", 1), ("zo", 0, "bottom", 2),
        ("top", 0, "cable", 0), ("bottom", 0, "cable", 1), ("cable", 0, "cables", 0),
        ("orb", 0, "sphere", 0),
        ("sphere", 0, "orbs", 0), ("xs", 0, "orbs", 1), ("ys", 0, "orbs", 2), ("zo", 0, "orbs", 3),
        ("size", 0, "plate_w", 0), ("plate_w", 0, "plate", 0), ("plate_w", 0, "plate", 1),
        ("plate", 0, "ceiling_at", 0), ("ceiling", 0, "ceiling_at", 3)])
    return c


def build_enneper(scene) -> dict:
    """Enneper's minimal surface from its parametric formula on a (u, v) grid,
    with contour lines at even heights."""
    c = {
        "r": _slider("Parameter range", 1.2, 0.5, 2, 2),
        "grid": _slider("Grid", 30, 10, 50, 0),
        "size": _slider("Size", 20, 5, 40),
        "levels": _slider("Contours", 12, 2, 40, 0),
        "nr": lib.Multiplication(), "u": lib.Range(), "v": lib.Range(),
        "x": lib.Expression(), "y": lib.Expression(), "z": lib.Expression(), "pts": lib.ConstructPoint(),
        "n": lib.Addition(), "surface": lib.SurfaceFromPoints(),
        "zmax": lib.Expression(), "zmin": lib.Multiplication(), "heights": lib.Range(), "contours": lib.Contour(),
    }
    for key, nick in (("u", "u"), ("v", "v"), ("heights", "Levels")):
        c[key].nickname = nick
    _set(c["nr"], B=-1.0)
    _set(c["x"], F="z*(x - x**3/3 + x*y**2)")
    _set(c["y"], F="z*(y - y**3/3 + y*x**2)")
    _set(c["z"], F="z*(x**2 - y**2)")
    _set(c["n"], B=1.0)
    _set(c["zmax"], F="0.95*z*x**2")   # just inside the highest point, so the top level is not a single point
    # (the surface crosses itself beyond |(u, v)| = sqrt(3); the grid's corners are sqrt(2) x range out)
    _set(c["zmin"], B=-1.0)
    for key in ("x", "y", "z"):
        c[key].inputs[2].modifier = "graft"   # y = v: one branch per row
    c["surface"].inputs[0].modifier = "flatten"
    c["pts"].preview = False
    _place(scene, c, {
        "r": (-760, -200), "grid": (-760, -140), "size": (-760, -40), "levels": (-760, 60),
        "nr": (-480, -220), "u": (-320, -240), "v": (-320, -130), "x": (-140, -260), "y": (-140, -150),
        "z": (-140, -40), "pts": (40, -160), "n": (40, 0), "surface": (200, -120),
        "zmax": (-320, 80), "zmin": (-140, 120), "heights": (40, 120), "contours": (360, 0)})
    _wire(scene, c, [
        ("r", 0, "nr", 0),
        ("nr", 0, "u", 0), ("r", 0, "u", 1), ("grid", 0, "u", 2),
        ("nr", 0, "v", 0), ("r", 0, "v", 1), ("grid", 0, "v", 2),
        ("u", 0, "x", 1), ("v", 0, "x", 2), ("size", 0, "x", 3),
        ("u", 0, "y", 1), ("v", 0, "y", 2), ("size", 0, "y", 3),
        ("u", 0, "z", 1), ("v", 0, "z", 2), ("size", 0, "z", 3),
        ("x", 0, "pts", 0), ("y", 0, "pts", 1), ("z", 0, "pts", 2),
        ("grid", 0, "n", 0), ("pts", 0, "surface", 0), ("n", 0, "surface", 1),
        ("r", 0, "zmax", 1), ("size", 0, "zmax", 3), ("zmax", 0, "zmin", 0),
        ("zmin", 0, "heights", 0), ("zmax", 0, "heights", 1), ("levels", 0, "heights", 2),
        ("surface", 0, "contours", 0), ("heights", 0, "contours", 2)])
    return c


def build_stadium(scene) -> dict:
    """A woven-bowl stadium roof: arcs from a ground ring over a raised rim to
    an inner oculus, each turned a few places one way and one family the
    other, under a translucent roof between rim and oculus."""
    c = {
        "R": _slider("Radius", 50, 25, 90),
        "rim_s": _slider("Rim scale", 0.7, 0.4, 0.95, 2),
        "rim_h": _slider("Rim height", 18, 5, 40),
        "ocu_s": _slider("Oculus scale", 0.35, 0.1, 0.6, 2),
        "ocu_h": _slider("Oculus height", 14, 2, 40),
        "n": _slider("Arches", 36, 12, 72, 0),
        "a": _slider("Rim turn", 4, 0, 12, 0),
        "b": _slider("Oculus turn", 8, 0, 24, 0),
        "member": _slider("Member radius", 0.5, 0.1, 1.5, 2),
        "r1": lib.Multiplication(), "r2": lib.Multiplication(),
        "base": lib.Circle(), "rim": lib.Circle(), "ocu": lib.Circle(),
        "d0": lib.DivideCurve(), "d1": lib.DivideCurve(), "d2": lib.DivideCurve(),
        "na": lib.Multiplication(), "nb": lib.Multiplication(),
        "s1p": lib.ShiftList(), "s2p": lib.ShiftList(), "s1n": lib.ShiftList(), "s2n": lib.ShiftList(),
        "ap": lib.Arc3Pt(), "an": lib.Arc3Pt(), "pp": lib.Pipe(), "pn": lib.Pipe(),
        "ring_r": lib.Multiplication(), "rim_p": lib.Pipe(), "ocu_p": lib.Pipe(), "base_p": lib.Pipe(),
        "roof": lib.Loft(),
    }
    for key, nick in (("base", "Ground ring"), ("rim", "Rim"), ("ocu", "Oculus"), ("ap", "Arches +"),
                      ("an", "Arches −"), ("roof", "Roof")):
        c[key].nickname = nick
    _set(c["na"], B=-1.0)
    _set(c["nb"], B=-1.0)
    _set(c["ring_r"], B=2.0)
    for key in ("base", "rim", "ocu", "d0", "d1", "d2", "s1p", "s2p", "s1n", "s2n", "ap", "an"):
        c[key].preview = False
    _place(scene, c, {
        "R": (-860, -300), "rim_s": (-860, -240), "rim_h": (-860, -180), "ocu_s": (-860, -80),
        "ocu_h": (-860, -20), "n": (-860, 80), "a": (-860, 180), "b": (-860, 240), "member": (-860, 340),
        "r1": (-560, -260), "r2": (-560, -120), "base": (-400, -340), "rim": (-400, -230), "ocu": (-400, -100),
        "d0": (-240, -340), "d1": (-240, -230), "d2": (-240, -100), "na": (-560, 160), "nb": (-560, 260),
        "s1p": (-60, -260), "s2p": (-60, -160), "s1n": (-60, -40), "s2n": (-60, 60),
        "ap": (120, -230), "an": (120, -40), "pp": (300, -230), "pn": (300, -40), "ring_r": (120, 180),
        "rim_p": (300, 120), "ocu_p": (300, 220), "base_p": (300, 320), "roof": (120, 320)})
    _wire(scene, c, [
        ("R", 0, "r1", 0), ("rim_s", 0, "r1", 1), ("R", 0, "r2", 0), ("ocu_s", 0, "r2", 1),
        ("R", 0, "base", 0), ("r1", 0, "rim", 0), ("rim_h", 0, "rim", 1), ("r2", 0, "ocu", 0), ("ocu_h", 0, "ocu", 1),
        ("base", 0, "d0", 0), ("rim", 0, "d1", 0), ("ocu", 0, "d2", 0),
        ("n", 0, "d0", 1), ("n", 0, "d1", 1), ("n", 0, "d2", 1),
        ("a", 0, "na", 0), ("b", 0, "nb", 0),
        ("d1", 0, "s1p", 0), ("a", 0, "s1p", 1), ("d2", 0, "s2p", 0), ("b", 0, "s2p", 1),
        ("d1", 0, "s1n", 0), ("na", 0, "s1n", 1), ("d2", 0, "s2n", 0), ("nb", 0, "s2n", 1),
        ("d0", 0, "ap", 0), ("s1p", 0, "ap", 1), ("s2p", 0, "ap", 2),
        ("d0", 0, "an", 0), ("s1n", 0, "an", 1), ("s2n", 0, "an", 2),
        ("ap", 0, "pp", 0), ("member", 0, "pp", 1), ("an", 0, "pn", 0), ("member", 0, "pn", 1),
        ("member", 0, "ring_r", 0), ("rim", 0, "rim_p", 0), ("ring_r", 0, "rim_p", 1),
        ("ocu", 0, "ocu_p", 0), ("ring_r", 0, "ocu_p", 1), ("base", 0, "base_p", 0), ("ring_r", 0, "base_p", 1),
        ("rim", 0, "roof", 0), ("ocu", 0, "roof", 0)])
    return c


def build_whirlpool(scene) -> dict:
    """A whirlpool ziggurat: each tier is the polygon whose corners lie a
    fraction t along the edges of the one below (the 'mice problem'), so it
    turns and shrinks by a fixed amount, stacked as slabs with spiral ribs
    through the corners."""
    c = {
        "n": _slider("Sides", 6, 3, 12, 0),
        "tiers": _slider("Tiers", 24, 4, 60, 0),
        "R": _slider("Radius", 30, 10, 60),
        "t": _slider("Pursuit", 0.12, 0.02, 0.5, 3),
        "step": _slider("Step", 0.8, 0.2, 3, 2),
        "alpha": lib.Expression(), "s": lib.Expression(), "k": lib.Series(),
        "Rk": lib.Expression(), "Ak": lib.Multiplication(), "Zk": lib.Multiplication(),
        "poly": lib.RegularPolygon(), "face": lib.PlanarSurface(), "up": lib.VectorXYZ(), "tiers_s": lib.Extrude(),
        "j": lib.Series(), "jang": lib.Expression(), "ang": lib.Addition(), "top": lib.Addition(),
        "cx": lib.Expression(), "cy": lib.Expression(), "corners": lib.ConstructPoint(),
        "spiral": lib.Interpolate(), "ribs": lib.Pipe(),
    }
    for key, nick, f in (("alpha", "Turn per tier", "degrees(atan2(x*sin(2*pi/y), 1 - x + x*cos(2*pi/y)))"),
                         ("s", "Shrink per tier", "sqrt((1 - x)**2 + x**2 + 2*x*(1 - x)*cos(2*pi/y))"),
                         ("Rk", "Tier radius", "z*y**x"), ("jang", "Corner angle", "360*x/y"),
                         ("cx", "X", "x*cos(radians(y))"), ("cy", "Y", "x*sin(radians(y))")):
        c[key].nickname = nick
        _set(c[key], F=f)
    c["k"].nickname = "Tier no."
    c["j"].nickname = "Corner no."
    c["tiers_s"].nickname = "Tiers"
    _set(c["ribs"], R=0.35)
    c["ang"].inputs[1].modifier = "graft"   # one branch per corner, the tiers in order along it
    for key in ("poly", "face", "corners", "spiral"):
        c[key].preview = False
    _place(scene, c, {
        "n": (-820, -220), "tiers": (-820, -160), "R": (-820, -60), "t": (-820, 0), "step": (-820, 100),
        "alpha": (-520, -260), "s": (-520, -140), "k": (-520, -20), "Rk": (-340, -120), "Ak": (-340, -20),
        "Zk": (-340, 80), "poly": (-160, -120), "face": (20, -160), "up": (20, -40), "tiers_s": (200, -120),
        "j": (-520, 220), "jang": (-340, 220), "ang": (-160, 120), "top": (-160, 240), "cx": (20, 100),
        "cy": (20, 200), "corners": (200, 160), "spiral": (360, 160), "ribs": (520, 160)})
    _wire(scene, c, [
        ("t", 0, "alpha", 1), ("n", 0, "alpha", 2), ("t", 0, "s", 1), ("n", 0, "s", 2),
        ("tiers", 0, "k", 2),
        ("k", 0, "Rk", 1), ("s", 0, "Rk", 2), ("R", 0, "Rk", 3),
        ("k", 0, "Ak", 0), ("alpha", 0, "Ak", 1), ("k", 0, "Zk", 0), ("step", 0, "Zk", 1),
        ("Rk", 0, "poly", 0), ("n", 0, "poly", 1), ("Ak", 0, "poly", 2), ("Zk", 0, "poly", 3),
        ("poly", 0, "face", 0), ("step", 0, "up", 2), ("face", 0, "tiers_s", 0), ("up", 0, "tiers_s", 1),
        ("n", 0, "j", 2), ("j", 0, "jang", 1), ("n", 0, "jang", 2),
        ("Ak", 0, "ang", 0), ("jang", 0, "ang", 1), ("Zk", 0, "top", 0), ("step", 0, "top", 1),
        ("Rk", 0, "cx", 1), ("ang", 0, "cx", 2), ("Rk", 0, "cy", 1), ("ang", 0, "cy", 2),
        ("cx", 0, "corners", 0), ("cy", 0, "corners", 1), ("top", 0, "corners", 2),
        ("corners", 0, "spiral", 0), ("spiral", 0, "ribs", 0)])
    return c


def build_impeller(scene) -> dict:
    """A turbine impeller in a cut-away shroud: twisted blades lofted through
    three turned radial lines and arrayed round a hub, with the tip clearance
    as a live tolerance stack-up (shroud bore, blade tip, hub runout)."""
    c = {
        "blades": _slider("Blades", 12, 3, 24, 0),
        "hub_r": _slider("Hub radius", 8, 4, 15),
        "tip_r": _slider("Tip radius", 30, 15, 50),
        "h": _slider("Height", 16, 6, 30),
        "twist": _slider("Twist", 40, 0, 90),
        "gap": _slider("Nominal clearance", 0.6, 0.1, 2, 2),
        # one blade
        "root": lib.ConstructPoint(), "tip": lib.ConstructPoint(), "line": lib.Line(),
        "lz": lib.Range(), "la": lib.Range(), "lifted": lib.Move(), "turned": lib.Rotate(), "blade": lib.Loft(),
        "step": lib.Expression(), "angles": lib.Series(), "rotor": lib.Rotate(),
        # hub and shroud
        "hub": lib.Cylinder(), "nose": lib.Sphere(), "nose_at": lib.Move(),
        "bore": lib.Addition(), "outer_r": lib.Addition(), "outer": lib.Cylinder(), "inner": lib.Cylinder(),
        "inner_dn": lib.Move(), "ring": lib.Difference(), "cut": lib.Box(), "cut_at": lib.Move(), "cut_turn": lib.Rotate(),
        "shroud": lib.Difference(),
        # tip clearance stack-up
        "d_bore": lib.Dimension(), "d_tip": lib.Dimension(), "d_run": lib.Dimension(), "stack": lib.StackUp(),
        "mc": lib.MonteCarlo(), "report": lib.Panel(),
    }
    for key, nick in (("line", "Blade line"), ("lz", "Section heights"), ("la", "Section turns"), ("blade", "Blade"),
                      ("rotor", "Rotor"), ("hub", "Hub"), ("ring", "Shroud ring"), ("shroud", "Shroud"),
                      ("stack", "Tip clearance"), ("mc", "Monte Carlo")):
        c[key].nickname = nick
    _set(c["lz"], S=0.0, N=2.0)
    _set(c["la"], S=0.0, N=2.0)
    _set(c["step"], F="360/x")
    _set(c["angles"], S=0.0)
    _set(c["outer_r"], B=2.0)
    _set(c["inner"], L=40.0)
    _set(c["inner_dn"], Z=-10.0)
    _set(c["cut"], X=80.0, Y=80.0, Z=60.0)
    _set(c["cut_at"], X=40.0, Y=40.0, Z=-10.0)
    _set(c["cut_turn"], A=30.0)   # off the cylinders' seams on +X: a cut through a seam is fragile
    _set(c["d_bore"], U=0.1, L=-0.1, D=1.0, Nm="Shroud bore radius")
    _set(c["d_tip"], U=0.05, L=-0.05, D=-1.0, Nm="Blade tip radius")
    _set(c["d_run"], N=0.0, U=0.05, L=-0.05, D=-1.0, Nm="Hub runout")
    _set(c["mc"], LSL=0.3)
    c["rotor"].inputs[1].modifier = "graft"   # every blade turned by every angle: the array
    c["report"].size = (300, 150)
    for key in ("root", "tip", "line", "lifted", "turned", "blade", "outer", "inner", "inner_dn", "ring", "cut",
                "cut_at", "cut_turn", "nose"):
        c[key].preview = False
    _place(scene, c, {
        "blades": (-900, -320), "hub_r": (-900, -260), "tip_r": (-900, -200), "h": (-900, -140),
        "twist": (-900, -80), "gap": (-900, 40),
        "root": (-600, -360), "tip": (-600, -260), "line": (-440, -320), "lz": (-600, -150), "la": (-600, -40),
        "lifted": (-280, -300), "turned": (-120, -280), "blade": (40, -280), "step": (-440, 60),
        "angles": (-280, 60), "rotor": (200, -220),
        "hub": (-440, 160), "nose": (-600, 260), "nose_at": (-440, 260),
        "bore": (-600, 380), "outer_r": (-440, 380), "outer": (-280, 340), "inner": (-280, 440),
        "inner_dn": (-120, 440), "ring": (40, 380), "cut": (-120, 560), "cut_at": (40, 560),
        "cut_turn": (200, 560), "shroud": (360, 420),
        "d_bore": (200, 40), "d_tip": (200, 160), "d_run": (200, 280), "stack": (420, 120), "mc": (420, 280),
        "report": (620, 80)})
    wires = [
        ("hub_r", 0, "root", 0), ("tip_r", 0, "tip", 0), ("root", 0, "line", 0), ("tip", 0, "line", 1),
        ("h", 0, "lz", 1), ("twist", 0, "la", 1),
        ("line", 0, "lifted", 0), ("lz", 0, "lifted", 3), ("lifted", 0, "turned", 0), ("la", 0, "turned", 1),
        ("turned", 0, "blade", 0),
        ("blades", 0, "step", 1), ("step", 0, "angles", 1), ("blades", 0, "angles", 2),
        ("blade", 0, "rotor", 0), ("angles", 0, "rotor", 1),
        ("hub_r", 0, "hub", 0), ("h", 0, "hub", 1), ("hub_r", 0, "nose", 0), ("nose", 0, "nose_at", 0),
        ("h", 0, "nose_at", 3),
        ("tip_r", 0, "bore", 0), ("gap", 0, "bore", 1), ("bore", 0, "outer_r", 0),
        ("outer_r", 0, "outer", 0), ("h", 0, "outer", 1), ("bore", 0, "inner", 0), ("inner", 0, "inner_dn", 0),
        ("outer", 0, "ring", 0), ("inner_dn", 0, "ring", 1),
        ("cut", 0, "cut_at", 0), ("cut_at", 0, "cut_turn", 0), ("ring", 0, "shroud", 0), ("cut_turn", 0, "shroud", 1),
        ("bore", 0, "d_bore", 0), ("tip_r", 0, "d_tip", 0),
        # three dimensions into one input: the chain, in order
        ("d_bore", 0, "stack", 0), ("d_tip", 0, "stack", 0), ("d_run", 0, "stack", 0),
        ("d_bore", 0, "mc", 0), ("d_tip", 0, "mc", 0), ("d_run", 0, "mc", 0),
        ("stack", 8, "report", 0)]
    _wire(scene, c, wires)
    return c


def build_morph(scene) -> dict:
    """The helicoid-catenoid morph: one family of minimal surfaces, bent
    isometrically from a helicoid (0°) into a catenoid (90°) by one slider."""
    c = {
        "alpha": _slider("Morph", 45, 0, 90),
        "grid": _slider("Grid", 40, 10, 60, 0),
        "vr": _slider("Height range", 1.5, 0.5, 2.2, 2),
        "size": _slider("Size", 12, 4, 30),
        "u": lib.Range(), "nv": lib.Multiplication(), "v": lib.Range(),
        "x": lib.Expression(), "y": lib.Expression(), "z": lib.Expression(), "pts": lib.ConstructPoint(),
        "n": lib.Addition(), "surface": lib.SurfaceFromPoints(), "scaled": lib.Scale(),
    }
    c["u"].nickname = "u"
    c["v"].nickname = "v"
    _set(c["u"], S=-3.14159265, E=3.14159265)
    _set(c["nv"], B=-1.0)
    _set(c["x"], F="cos(radians(z))*sinh(y)*sin(x) + sin(radians(z))*cosh(y)*cos(x)")
    _set(c["y"], F="-cos(radians(z))*sinh(y)*cos(x) + sin(radians(z))*cosh(y)*sin(x)")
    _set(c["z"], F="x*cos(radians(z)) + y*sin(radians(z))")
    _set(c["n"], B=1.0)
    for key in ("x", "y", "z"):
        c[key].inputs[2].modifier = "graft"   # y = v: one branch per row
    c["surface"].inputs[0].modifier = "flatten"
    for key in ("pts", "surface"):
        c[key].preview = False
    _place(scene, c, {
        "alpha": (-760, -200), "grid": (-760, -100), "vr": (-760, -40), "size": (-760, 60),
        "u": (-460, -260), "nv": (-460, -140), "v": (-300, -140), "x": (-120, -260), "y": (-120, -140),
        "z": (-120, -20), "pts": (60, -140), "n": (60, 20), "surface": (220, -100), "scaled": (380, -80)})
    _wire(scene, c, [
        ("grid", 0, "u", 2), ("vr", 0, "nv", 0), ("nv", 0, "v", 0), ("vr", 0, "v", 1), ("grid", 0, "v", 2),
        ("u", 0, "x", 1), ("v", 0, "x", 2), ("alpha", 0, "x", 3),
        ("u", 0, "y", 1), ("v", 0, "y", 2), ("alpha", 0, "y", 3),
        ("u", 0, "z", 1), ("v", 0, "z", 2), ("alpha", 0, "z", 3),
        ("x", 0, "pts", 0), ("y", 0, "pts", 1), ("z", 0, "pts", 2),
        ("grid", 0, "n", 0), ("pts", 0, "surface", 0), ("n", 0, "surface", 1),
        ("surface", 0, "scaled", 0), ("size", 0, "scaled", 1)])
    return c


def build_tensegrity(scene) -> dict:
    """A tensegrity tower: stacked prisms, each top polygon turned 90° + 180°/n
    from its bottom (the twist at which a regular prism balances), struts in
    compression and a net of cables in tension, sharing rings module to module."""
    c = {
        "n": _slider("Sides", 3, 3, 6, 0),
        "m": _slider("Modules", 5, 1, 12, 0),
        "R": _slider("Radius", 12, 4, 20),
        "taper": _slider("Taper", 0.9, 0.7, 1, 2),
        "h": _slider("Module height", 10, 3, 20),
        "strut_r": _slider("Strut radius", 0.5, 0.1, 1.5, 2),
        "cable_r": _slider("Cable radius", 0.12, 0.03, 0.5, 2),
        "twist": lib.Expression(), "j": lib.Series(),
        "Rb": lib.Expression(), "Rt": lib.Expression(), "Ab": lib.Multiplication(), "At": lib.Addition(),
        "Zb": lib.Multiplication(), "Zt": lib.Addition(),
        "bottom": lib.RegularPolygon(), "top": lib.RegularPolygon(), "db": lib.DivideCurve(), "dt": lib.DivideCurve(),
        "prev": lib.ShiftList(), "struts": lib.Line(), "verticals": lib.Line(),
        "strut_p": lib.Pipe(), "vert_p": lib.Pipe(), "last": lib.ListItem(), "ring_p": lib.Pipe(),
        "nodes": lib.DivideCurve(), "xyz": lib.Deconstruct(), "joint_r": lib.Multiplication(),
        "ball": lib.Sphere(), "joints": lib.Move(),
    }
    for key, nick in (("twist", "Twist"), ("j", "Module no."), ("Rb", "Bottom radius"), ("Rt", "Top radius"),
                      ("bottom", "Bottom ring"), ("top", "Top ring"), ("prev", "Previous corner"),
                      ("struts", "Struts"), ("verticals", "Vertical cables"), ("strut_p", "Strut tubes"),
                      ("vert_p", "Cable tubes"), ("ring_p", "Ring cables"), ("joints", "Joints")):
        c[key].nickname = nick
    _set(c["twist"], F="90 + 180/x")
    _set(c["Rb"], F="z*y**x")
    _set(c["Rt"], F="z*y**(x + 1)")
    _set(c["prev"], S=-1.0)
    _set(c["last"], i=-1.0)
    _set(c["joint_r"], B=1.6)
    for key in ("bottom", "top", "db", "dt", "prev", "struts", "verticals", "last", "nodes", "ball"):
        c[key].preview = False
    _place(scene, c, {
        "n": (-880, -260), "m": (-880, -200), "R": (-880, -100), "taper": (-880, -40), "h": (-880, 60),
        "strut_r": (-880, 180), "cable_r": (-880, 240),
        "twist": (-600, -300), "j": (-600, -200), "Rb": (-440, -260), "Rt": (-440, -160), "Ab": (-440, -60),
        "At": (-280, -60), "Zb": (-440, 40), "Zt": (-280, 40), "bottom": (-120, -240), "top": (-120, -100),
        "db": (40, -240), "dt": (40, -100), "prev": (200, -60), "struts": (360, -200), "verticals": (360, -60),
        "strut_p": (520, -200), "vert_p": (520, -60), "last": (40, 60), "ring_p": (520, 80),
        "nodes": (200, 160), "xyz": (360, 160), "joint_r": (360, 280), "ball": (520, 280), "joints": (680, 200)})
    _wire(scene, c, [
        ("n", 0, "twist", 1), ("m", 0, "j", 2),
        ("j", 0, "Rb", 1), ("taper", 0, "Rb", 2), ("R", 0, "Rb", 3),
        ("j", 0, "Rt", 1), ("taper", 0, "Rt", 2), ("R", 0, "Rt", 3),
        ("j", 0, "Ab", 0), ("twist", 0, "Ab", 1), ("Ab", 0, "At", 0), ("twist", 0, "At", 1),
        ("j", 0, "Zb", 0), ("h", 0, "Zb", 1), ("Zb", 0, "Zt", 0), ("h", 0, "Zt", 1),
        ("Rb", 0, "bottom", 0), ("n", 0, "bottom", 1), ("Ab", 0, "bottom", 2), ("Zb", 0, "bottom", 3),
        ("Rt", 0, "top", 0), ("n", 0, "top", 1), ("At", 0, "top", 2), ("Zt", 0, "top", 3),
        ("bottom", 0, "db", 0), ("n", 0, "db", 1), ("top", 0, "dt", 0), ("n", 0, "dt", 1),
        ("dt", 0, "prev", 0),
        ("db", 0, "struts", 0), ("dt", 0, "struts", 1), ("db", 0, "verticals", 0), ("prev", 0, "verticals", 1),
        ("struts", 0, "strut_p", 0), ("strut_r", 0, "strut_p", 1),
        ("verticals", 0, "vert_p", 0), ("cable_r", 0, "vert_p", 1),
        ("top", 0, "last", 0),
        # every bottom ring and the very top ring: each ring once
        ("bottom", 0, "ring_p", 0), ("last", 0, "ring_p", 0), ("cable_r", 0, "ring_p", 1),
        ("bottom", 0, "nodes", 0), ("last", 0, "nodes", 0), ("n", 0, "nodes", 1),
        ("nodes", 0, "xyz", 0), ("strut_r", 0, "joint_r", 0), ("joint_r", 0, "ball", 0),
        ("ball", 0, "joints", 0), ("xyz", 0, "joints", 1), ("xyz", 1, "joints", 2), ("xyz", 2, "joints", 3)])
    return c


def build_lotus(scene) -> dict:
    """A blooming lotus: one cupped petal lofted through arcs, copied round
    several staggered tiers; one Bloom slider tilts every tier open, the outer
    ones furthest."""
    c = {
        "P": _slider("Petals", 10, 5, 16, 0),
        "M": _slider("Tiers", 4, 1, 6, 0),
        "L": _slider("Length", 14, 6, 25),
        "W": _slider("Width", 7, 2, 12),
        "cup": _slider("Cup", 0.35, 0, 0.8, 2),
        "curl": _slider("Curl", 0.15, -0.3, 0.5, 2),
        "bloom": _slider("Bloom", 55, 0, 85),
        "taper": _slider("Taper", 0.75, 0.5, 1, 2),
        # one petal
        "u": lib.Range(), "w": lib.Expression(), "d": lib.Multiplication(), "z": lib.Multiplication(),
        "xo": lib.Expression(), "xe": lib.Expression(), "hw": lib.Multiplication(), "nhw": lib.Multiplication(),
        "pl": lib.ConstructPoint(), "pm": lib.ConstructPoint(), "pr": lib.ConstructPoint(),
        "arcs": lib.Arc3Pt(), "petal": lib.Loft(),
        # tiers
        "k": lib.Series(), "s": lib.Expression(), "tilt": lib.Expression(), "r": lib.Expression(),
        "lift": lib.Expression(), "stagger": lib.Expression(),
        "scaled": lib.Scale(), "tilted": lib.Rotate(), "out": lib.Move(), "staggered": lib.Rotate(),
        "step": lib.Expression(), "angles": lib.Series(), "flower": lib.Rotate(),
        "pod_r": lib.Expression(), "pod": lib.Sphere(),
    }
    for key, nick, f in (("w", "Width profile", "y*(0.35*(1 - x) + 2.2*x*(1 - x))"),
                         ("xo", "Spine", "y*z*x**2"), ("xe", "Edges", "x - y"),
                         ("s", "Tier scale", "y**x"), ("tilt", "Tier tilt", "y*(1 - x/z)"),
                         ("r", "Tier radius", "0.06*x*y*z"), ("lift", "Tier lift", "0.08*x*y"),
                         ("stagger", "Tier stagger", "180*x/y"), ("step", "Petal step", "360/x"),
                         ("pod_r", "Pod radius", "0.048*x*y")):
        c[key].nickname = nick
        _set(c[key], F=f)
    for key, nick in (("u", "Along the petal"), ("arcs", "Sections"), ("petal", "Petal"), ("k", "Tier no."),
                      ("flower", "Flower"), ("pod", "Seed pod")):
        c[key].nickname = nick
    _set(c["u"], S=0.0, E=0.95, N=7.0)
    _set(c["hw"], B=0.5)
    _set(c["nhw"], B=-0.5)
    _set(c["tilted"], X=(0.0, 1.0, 0.0))
    _set(c["angles"], S=0.0)
    c["flower"].inputs[1].modifier = "graft"   # every tier copied to every angle
    for key in ("pl", "pm", "pr", "arcs", "petal", "scaled", "tilted", "out", "staggered"):
        c[key].preview = False
    _place(scene, c, {
        "P": (-940, -300), "M": (-940, -240), "L": (-940, -140), "W": (-940, -80), "cup": (-940, -20),
        "curl": (-940, 40), "bloom": (-940, 160), "taper": (-940, 220),
        "u": (-660, -360), "w": (-500, -300), "d": (-340, -300), "z": (-500, -400), "xo": (-500, -200),
        "xe": (-340, -200), "hw": (-340, -100), "nhw": (-340, -10),
        "pl": (-160, -300), "pm": (-160, -200), "pr": (-160, -100), "arcs": (0, -200), "petal": (160, -200),
        "k": (-660, 120), "s": (-500, 60), "tilt": (-500, 160), "r": (-500, 260), "lift": (-500, 360),
        "stagger": (-500, 460), "scaled": (320, -120), "tilted": (320, -10), "out": (480, -10),
        "staggered": (640, -10), "step": (480, 160), "angles": (640, 160), "flower": (800, 40),
        "pod_r": (480, 300), "pod": (640, 300)})
    _wire(scene, c, [
        ("u", 0, "w", 1), ("W", 0, "w", 2), ("w", 0, "d", 0), ("cup", 0, "d", 1), ("u", 0, "z", 0), ("L", 0, "z", 1),
        ("u", 0, "xo", 1), ("curl", 0, "xo", 2), ("L", 0, "xo", 3), ("xo", 0, "xe", 1), ("d", 0, "xe", 2),
        ("w", 0, "hw", 0), ("w", 0, "nhw", 0),
        ("xe", 0, "pl", 0), ("nhw", 0, "pl", 1), ("z", 0, "pl", 2),
        ("xo", 0, "pm", 0), ("z", 0, "pm", 2),
        ("xe", 0, "pr", 0), ("hw", 0, "pr", 1), ("z", 0, "pr", 2),
        ("pl", 0, "arcs", 0), ("pm", 0, "arcs", 1), ("pr", 0, "arcs", 2), ("arcs", 0, "petal", 0),
        ("M", 0, "k", 2),
        ("k", 0, "s", 1), ("taper", 0, "s", 2),
        ("k", 0, "tilt", 1), ("bloom", 0, "tilt", 2), ("M", 0, "tilt", 3),
        ("s", 0, "r", 1), ("P", 0, "r", 2), ("W", 0, "r", 3),
        ("k", 0, "lift", 1), ("L", 0, "lift", 2), ("k", 0, "stagger", 1), ("P", 0, "stagger", 2),
        ("petal", 0, "scaled", 0), ("s", 0, "scaled", 1),
        ("scaled", 0, "tilted", 0), ("tilt", 0, "tilted", 1),
        ("tilted", 0, "out", 0), ("r", 0, "out", 1), ("lift", 0, "out", 3),
        ("out", 0, "staggered", 0), ("stagger", 0, "staggered", 1),
        ("P", 0, "step", 1), ("step", 0, "angles", 1), ("P", 0, "angles", 2),
        ("staggered", 0, "flower", 0), ("angles", 0, "flower", 1),
        ("P", 0, "pod_r", 1), ("W", 0, "pod_r", 2), ("pod_r", 0, "pod", 0)])
    return c


def build_auxetic(scene) -> dict:
    """A re-entrant (auxetic) honeycomb: bow-tie cells offset to wall
    thickness, arrayed in two interlocking rows and cut from a block, with the
    Poisson's ratio of the bending model in a Panel."""
    c = {
        "l": _slider("Wall length", 6, 3, 12),
        "h": _slider("Rib length", 12, 4, 24),
        "theta": _slider("Wall angle", -30, -40, 40, 0),
        "t": _slider("Wall thickness", 0.8, 0.3, 2, 2),
        "nx": _slider("Columns", 7, 2, 14, 0),
        "ny": _slider("Rows", 4, 1, 10, 0),
        "depth": _slider("Depth", 8, 2, 30),
        # one cell
        "lc": lib.Expression(), "ls": lib.Expression(), "half": lib.Multiplication(), "apex": lib.Addition(),
        "nlc": lib.Multiplication(), "nhalf": lib.Multiplication(), "napex": lib.Multiplication(),
        "p0": lib.ConstructPoint(), "p1": lib.ConstructPoint(), "p2": lib.ConstructPoint(),
        "p3": lib.ConstructPoint(), "p4": lib.ConstructPoint(), "p5": lib.ConstructPoint(),
        "cell": lib.Polyline(), "inset": lib.Multiplication(), "hole": lib.OffsetCurve(),
        "face": lib.PlanarSurface(), "drop": lib.Move(), "deep": lib.Addition(), "up": lib.VectorXYZ(),
        "cutter": lib.Extrude(),
        # the lattice
        "pitch_y": lib.Addition(), "row2": lib.Move(), "dx": lib.Multiplication(), "vx": lib.VectorXYZ(),
        "cols": lib.LinearArray(), "dy": lib.Multiplication(), "vy": lib.VectorXYZ(), "rows": lib.LinearArray(),
        "W": lib.Expression(), "H": lib.Expression(), "xc": lib.Expression(), "yc": lib.Multiplication(),
        "block": lib.Box(), "placed": lib.Move(), "lattice": lib.Difference(),
        "nu": lib.Expression(), "report": lib.Panel(),
    }
    for key, nick, f in (("lc", "Wall X", "x*cos(radians(y))"), ("ls", "Wall Y", "x*sin(radians(y))"),
                         ("W", "Block width", "2*(x - 1)*y"), ("H", "Block height", "(2*x - 1)*y"),
                         ("xc", "Block X", "(x - 0.5)*y"),
                         ("nu", "Poisson's ratio",
                          "cos(radians(z))**2/((x/y + sin(radians(z)))*sin(radians(z)))")):
        c[key].nickname = nick
        _set(c[key], F=f)
    for key, nick in (("cell", "Cell"), ("hole", "Hole"), ("cutter", "Cutter"), ("row2", "Second row"),
                      ("cols", "Columns"), ("rows", "Rows"), ("block", "Block"), ("lattice", "Lattice")):
        c[key].nickname = nick
    _set(c["half"], B=0.5)
    for key in ("nlc", "nhalf", "napex"):
        _set(c[key], B=-1.0)
    _set(c["cell"], C=True)
    _set(c["inset"], B=-0.5)
    _set(c["drop"], Z=-1.0)
    _set(c["deep"], B=2.0)
    _set(c["dx"], B=2.0)
    _set(c["dy"], B=2.0)
    _set(c["yc"], B=0.5)
    c["lattice"].inputs[1].modifier = "flatten"   # every cutter in one list: one cut
    c["report"].size = (220, 80)
    for key in ("p0", "p1", "p2", "p3", "p4", "p5", "hole", "face", "drop", "cutter", "row2", "cols", "rows",
                "block", "placed"):
        c[key].preview = False
    _place(scene, c, {
        "l": (-960, -300), "h": (-960, -240), "theta": (-960, -180), "t": (-960, -60), "nx": (-960, 60),
        "ny": (-960, 120), "depth": (-960, 220),
        "lc": (-680, -330), "ls": (-680, -230), "half": (-680, -130), "apex": (-520, -180),
        "nlc": (-520, -330), "nhalf": (-520, -80), "napex": (-360, -180),
        "p0": (-200, -420), "p1": (-200, -340), "p2": (-200, -260), "p3": (-200, -180), "p4": (-200, -100),
        "p5": (-200, -20), "cell": (-40, -220), "inset": (-200, 80), "hole": (120, -220), "face": (280, -220),
        "drop": (440, -240), "deep": (280, -100), "up": (440, -120), "cutter": (600, -200),
        "pitch_y": (-360, 60), "row2": (760, -240), "dx": (-360, 160), "vx": (600, -40), "cols": (920, -200),
        "dy": (-360, 260), "vy": (760, -40), "rows": (1080, -200),
        "W": (-680, 360), "H": (-520, 360), "xc": (-680, 460), "yc": (-360, 380), "block": (760, 160),
        "placed": (920, 160), "lattice": (1240, -60), "nu": (-680, 560), "report": (-480, 560)})
    _wire(scene, c, [
        ("l", 0, "lc", 1), ("theta", 0, "lc", 2), ("l", 0, "ls", 1), ("theta", 0, "ls", 2),
        ("h", 0, "half", 0), ("half", 0, "apex", 0), ("ls", 0, "apex", 1),
        ("lc", 0, "nlc", 0), ("half", 0, "nhalf", 0), ("apex", 0, "napex", 0),
        ("lc", 0, "p0", 0), ("nhalf", 0, "p0", 1), ("lc", 0, "p1", 0), ("half", 0, "p1", 1),
        ("apex", 0, "p2", 1), ("nlc", 0, "p3", 0), ("half", 0, "p3", 1),
        ("nlc", 0, "p4", 0), ("nhalf", 0, "p4", 1), ("napex", 0, "p5", 1),
        # six corners into one input: the polygon, in order
        ("p0", 0, "cell", 0), ("p1", 0, "cell", 0), ("p2", 0, "cell", 0),
        ("p3", 0, "cell", 0), ("p4", 0, "cell", 0), ("p5", 0, "cell", 0),
        ("t", 0, "inset", 0), ("cell", 0, "hole", 0), ("inset", 0, "hole", 1),
        ("hole", 0, "face", 0), ("face", 0, "drop", 0), ("depth", 0, "deep", 0), ("deep", 0, "up", 2),
        ("drop", 0, "cutter", 0), ("up", 0, "cutter", 1),
        ("h", 0, "pitch_y", 0), ("ls", 0, "pitch_y", 1),
        ("cutter", 0, "row2", 0), ("lc", 0, "row2", 1), ("pitch_y", 0, "row2", 2),
        ("lc", 0, "dx", 0), ("dx", 0, "vx", 0), ("pitch_y", 0, "dy", 0), ("dy", 0, "vy", 1),
        ("cutter", 0, "cols", 0), ("row2", 0, "cols", 0), ("vx", 0, "cols", 1), ("nx", 0, "cols", 2),
        ("cols", 0, "rows", 0), ("vy", 0, "rows", 1), ("ny", 0, "rows", 2),
        ("nx", 0, "W", 1), ("lc", 0, "W", 2), ("ny", 0, "H", 1), ("pitch_y", 0, "H", 2),
        ("nx", 0, "xc", 1), ("lc", 0, "xc", 2), ("H", 0, "yc", 0),
        ("W", 0, "block", 0), ("H", 0, "block", 1), ("depth", 0, "block", 2),
        ("block", 0, "placed", 0), ("xc", 0, "placed", 1), ("yc", 0, "placed", 2),
        ("placed", 0, "lattice", 0), ("rows", 0, "lattice", 1),
        ("h", 0, "nu", 1), ("l", 0, "nu", 2), ("theta", 0, "nu", 3), ("nu", 0, "report", 0)])
    return c


def build_amphitheatre(scene) -> dict:
    """A stepped amphitheatre: tiers as ruled strips between concentric arcs,
    extruded to rising heights, round an orchestra, with a band shell of
    telescoping arches lofted behind the stage."""
    c = {
        "K": _slider("Tiers", 12, 4, 24, 0),
        "r0": _slider("Inner radius", 14, 6, 30),
        "tread": _slider("Tread", 2.2, 1, 4, 2),
        "riser": _slider("Riser", 0.9, 0.3, 2, 2),
        "sweep": _slider("Sweep", 210, 90, 270, 0),
        "bands": _slider("Shell bands", 8, 2, 16, 0),
        "span": _slider("Shell span", 24, 10, 40),
        "rise": _slider("Shell height", 12, 5, 25),
        "deep": _slider("Shell depth", 10, 4, 20),
        # seating
        "sx": lib.Expression(), "cy": lib.Expression(), "nsx": lib.Multiplication(),
        "pa": lib.ConstructPoint(), "pb": lib.ConstructPoint(), "pc": lib.ConstructPoint(), "unit": lib.Arc3Pt(),
        "radii": lib.Series(), "outer": lib.Addition(), "inner_a": lib.Scale(), "outer_a": lib.Scale(),
        "treads": lib.RuledSurface(), "heights": lib.Series(), "up": lib.VectorXYZ(), "tiers": lib.Extrude(),
        "stage_r": lib.Multiplication(), "stage": lib.Cylinder(),
        # band shell
        "u": lib.Range(), "hw": lib.Expression(), "nhw": lib.Multiplication(), "top": lib.Expression(),
        "y": lib.Expression(), "ql": lib.ConstructPoint(), "qt": lib.ConstructPoint(), "qr": lib.ConstructPoint(),
        "arches": lib.Arc3Pt(), "shell": lib.Loft(), "ribs": lib.Pipe(),
    }
    for key, nick, f in (("sx", "Half-sweep X", "sin(radians(x/2))"), ("cy", "Half-sweep Y", "-cos(radians(x/2))"),
                         ("hw", "Arch half-span", "y*(1 + x)/4"), ("top", "Arch height", "y*(0.45 + 0.55*x)"),
                         ("y", "Arch position", "y*(1 - x)")):
        c[key].nickname = nick
        _set(c[key], F=f)
    for key, nick in (("unit", "Unit arc"), ("radii", "Tier radii"), ("inner_a", "Inner edges"),
                      ("outer_a", "Outer edges"), ("treads", "Treads"), ("heights", "Tier heights"),
                      ("tiers", "Tiers"), ("stage", "Orchestra"), ("arches", "Arches"), ("shell", "Band shell"),
                      ("ribs", "Ribs")):
        c[key].nickname = nick
    _set(c["nsx"], B=-1.0)
    _set(c["pb"], Y=-1.0)
    _set(c["stage_r"], B=0.8)
    _set(c["u"], S=0.0, E=1.0)
    _set(c["nhw"], B=-1.0)
    _set(c["ribs"], R=0.3)
    for key in ("pa", "pb", "pc", "unit", "inner_a", "outer_a", "treads", "ql", "qt", "qr", "arches"):
        c[key].preview = False
    _place(scene, c, {
        "K": (-900, -320), "r0": (-900, -260), "tread": (-900, -200), "riser": (-900, -140), "sweep": (-900, -40),
        "bands": (-900, 100), "span": (-900, 160), "rise": (-900, 220), "deep": (-900, 280),
        "sx": (-620, -420), "cy": (-620, -320), "nsx": (-460, -420), "pa": (-300, -440), "pb": (-300, -350),
        "pc": (-300, -260), "unit": (-140, -350), "radii": (-620, -200), "outer": (-460, -160),
        "inner_a": (20, -360), "outer_a": (20, -240), "treads": (180, -300), "heights": (-460, -60),
        "up": (20, -100), "tiers": (340, -240), "stage_r": (-460, 20), "stage": (20, 20),
        "u": (-620, 160), "hw": (-460, 120), "nhw": (-300, 100), "top": (-460, 220), "y": (-460, 320),
        "ql": (-140, 140), "qt": (-140, 240), "qr": (-140, 340), "arches": (20, 220), "shell": (180, 160),
        "ribs": (180, 280)})
    _wire(scene, c, [
        ("sweep", 0, "sx", 1), ("sweep", 0, "cy", 1), ("sx", 0, "nsx", 0),
        ("nsx", 0, "pa", 0), ("cy", 0, "pa", 1), ("sx", 0, "pc", 0), ("cy", 0, "pc", 1),
        ("pa", 0, "unit", 0), ("pb", 0, "unit", 1), ("pc", 0, "unit", 2),
        ("r0", 0, "radii", 0), ("tread", 0, "radii", 1), ("K", 0, "radii", 2),
        ("radii", 0, "outer", 0), ("tread", 0, "outer", 1),
        ("unit", 0, "inner_a", 0), ("radii", 0, "inner_a", 1), ("unit", 0, "outer_a", 0), ("outer", 0, "outer_a", 1),
        ("inner_a", 0, "treads", 0), ("outer_a", 0, "treads", 1),
        ("riser", 0, "heights", 0), ("riser", 0, "heights", 1), ("K", 0, "heights", 2), ("heights", 0, "up", 2),
        ("treads", 0, "tiers", 0), ("up", 0, "tiers", 1),
        ("r0", 0, "stage_r", 0), ("stage_r", 0, "stage", 0), ("riser", 0, "stage", 1),
        ("bands", 0, "u", 2), ("u", 0, "hw", 1), ("span", 0, "hw", 2), ("hw", 0, "nhw", 0),
        ("u", 0, "top", 1), ("rise", 0, "top", 2), ("u", 0, "y", 1), ("deep", 0, "y", 2),
        ("nhw", 0, "ql", 0), ("y", 0, "ql", 1), ("y", 0, "qt", 1), ("top", 0, "qt", 2),
        ("hw", 0, "qr", 0), ("y", 0, "qr", 1),
        ("ql", 0, "arches", 0), ("qt", 0, "arches", 1), ("qr", 0, "arches", 2),
        ("arches", 0, "shell", 0), ("arches", 0, "ribs", 0)])
    return c


SHOWCASE = {"voronoi": build_voronoi, "tower": build_tower, "waffle": build_waffle, "wave": build_wave,
            "phyllotaxis": build_phyllotaxis, "hyperboloid": build_hyperboloid,
            "staircase": build_staircase, "city": build_city, "weave": build_weave,
            "knot": build_knot, "ring": build_ring, "frames": build_frames, "hypar": build_hypar,
            "slats": build_slats, "monolith": build_monolith, "flange": build_flange,
            "bridge": build_bridge, "shell": build_shell, "origami": build_origami, "rose": build_rose,
            "mashrabiya": build_mashrabiya, "columns": build_columns, "pendants": build_pendants,
            "enneper": build_enneper, "stadium": build_stadium, "whirlpool": build_whirlpool,
            "impeller": build_impeller, "morph": build_morph, "tensegrity": build_tensegrity,
            "lotus": build_lotus, "auxetic": build_auxetic, "amphitheatre": build_amphitheatre}
