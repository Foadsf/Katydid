# SPDX-License-Identifier: LGPL-2.1-or-later
"""Where does preview time go? Run: freecadcmd.exe tests/preview_profile.py"""

import os
import statistics
import time

import FreeCAD
import Part

out = os.environ.get("KATYDID_OUT", os.path.dirname(os.path.abspath(__file__)))


def ms(fn, n=30):
    t = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        t.append((time.perf_counter() - t0) * 1000)
    return round(statistics.median(t), 3)


def fresh_shapes():
    box = Part.makeBox(20, 20, 30, FreeCAD.Vector(-10, -10, 0))
    return [box.translated(FreeCAD.Vector(32 * i, 0, 0)) for i in range(4)]


def tessellate():
    for s in fresh_shapes():
        s.tessellate(max(s.BoundBox.DiagonalLength * 0.002, 0.01))


def discretize():
    for s in fresh_shapes():
        tol = max(s.BoundBox.DiagonalLength * 0.002, 0.01)
        for e in s.Edges:
            e.discretize(Deflection=tol)


def tessellate_compound():
    c = Part.makeCompound(fresh_shapes())
    c.tessellate(max(c.BoundBox.DiagonalLength * 0.002, 0.01))


def tessellate_once_then_place():
    shapes = fresh_shapes()
    base = shapes[0].copy()
    base.Placement = FreeCAD.Placement()
    base.tessellate(0.1)
    for s in shapes:
        s.Placement  # noqa: B018 - transforming cached vertices would cost about this


def edges_line_shortcut():
    for s in fresh_shapes():
        tol = max(s.BoundBox.DiagonalLength * 0.002, 0.01)
        for e in s.Edges:
            if e.Curve.TypeId == "Part::GeomLine":
                _ = (e.Vertexes[0].Point, e.Vertexes[-1].Point)
            else:
                e.discretize(Deflection=tol)


def full():
    from katydid.preview import RED, _mesh_node
    _mesh_node(fresh_shapes(), RED)


lines = [f"make shapes          {ms(fresh_shapes)} ms",
         f"tessellate each      {ms(tessellate)} ms (incl. make)",
         f"tessellate compound  {ms(tessellate_compound)} ms (incl. make)",
         f"tessellate once      {ms(tessellate_once_then_place)} ms (incl. make)",
         f"edges discretize     {ms(discretize)} ms (incl. make)",
         f"edges line shortcut  {ms(edges_line_shortcut)} ms (incl. make)"]
try:
    lines.append(f"full node            {ms(full)} ms (incl. make)")
except Exception as exc:  # pivy unavailable in console mode
    lines.append(f"full node            n/a ({exc!r})")
with open(os.path.join(out, "preview_profile.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
os._exit(0)
