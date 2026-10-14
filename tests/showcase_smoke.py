# SPDX-License-Identifier: LGPL-2.1-or-later
"""The showcase examples in the real FreeCAD GUI, loaded through the Examples
menu: every component OK, preview drawn, timings recorded, one saved and reopened.

    freecad.exe tests/showcase_smoke.py      (KATYDID_OUT chooses the output dir)
"""

import os
import sys
import time

import FreeCAD
import FreeCADGui
import katydid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__))), "tests"))
from guitest import Run, pump  # noqa: E402

SHOWS = [("Voronoi screen", "seed"), ("Twisted tower", "twist"), ("Waffle dome", "pitch"),
         ("Wave surface with contours", "freq"), ("Sunflower (phyllotaxis)", "angle"),
         ("Shukhov tower (hyperboloid)", "twist"), ("Spiral staircase", "turn"),
         ("Voronoi city", "spread"), ("Woven mat", "amp"), ("Torus knot", "r"),
         ("Twisted lobed ring", "depth"), ("Frame tunnel", "turn"), ("Hypar umbrella", "edge_h"),
         ("Slatted wave ceiling", "drift"), ("Carved monolith", "seed"),
         ("Flange with tolerance zones", "actual"), ("Network-arch bridge", "lean"),
         ("Spiral shell", "open"), ("Miura-ori fold", "shear"), ("Guilloché rose", "k"),
         ("Mashrabiya facade", "sx"), ("Mushroom columns", "scallop"), ("Pendant cloud", "freq"),
         ("Enneper surface", "r"), ("Woven-bowl stadium roof", "a"), ("Whirlpool ziggurat", "t"),
         ("Helicoid–catenoid morph", "alpha"), ("Impeller with tip clearance", "twist"),
         ("Tensegrity tower", "taper"), ("Blooming lotus", "bloom"), ("Auxetic lattice", "theta"),
         ("Stepped amphitheatre", "sweep"),
         ("Tri-axial grid-shell", "p"), ("Gaudí double-twist columns", "R"), ("Pangolin-scale tower", "ax"),
         ("Dini's surface", "b"), ("Kumiko asanoha panel", "a"), ("Menger sponge", "S"),
         ("Continuum robot", "theta")]


def body(run):
    from katydid import gui
    check, res = run.check, run.res
    FreeCADGui.getMainWindow().showMaximized()
    FreeCADGui.activateWorkbench("KatydidWorkbench")
    pump(400)
    panel = gui.show_canvas()
    menu = panel.examples.menu()
    res["timings_ms"] = {}
    for label, slider_key in SHOWS:
        act = next((a for a in menu.actions() if a.text() == label), None)
        check(f"menu has {label}", act is not None)
        if act is None:
            continue
        t0 = time.perf_counter()
        act.trigger()
        pump(300)
        while panel.scene._pending:
            pump(50)
        load_s = time.perf_counter() - t0
        bad = {c.nickname: c.messages for c in panel.graph.components if c.state != "ok"}
        check(f"{label}: all ok", not bad, bad)
        shapes = sum(len(c.shapes()) for c in panel.graph.components if c.preview)
        check(f"{label}: previewed", shapes > 0 and panel.preview._doc is not None, shapes)
        # one slider step, timed: solve and preview
        s = panel.demo[slider_key]
        s.set_value(s.value + (s.maximum - s.minimum) * 0.05)
        panel.timings.clear()
        panel.scene.solve_now()
        solve, preview = panel.timings[-1] if panel.timings else (None, None)
        bad = {c.nickname: c.messages for c in panel.graph.components if c.state != "ok"}
        check(f"{label}: slider step ok", not bad, bad)
        res["timings_ms"][label] = {"load_s": round(load_s, 2), "solve_ms": round(solve or 0, 1),
                                    "preview_ms": round(preview or 0, 1)}
        run.grab(panel, f"{label.split()[0].lower()}-canvas.png")

    # Save and reopen the Voronoi screen: modifiers, text and point defaults survive.
    menu_act = next(a for a in menu.actions() if a.text() == "Voronoi screen")
    menu_act.trigger()
    pump(300)
    while panel.scene._pending:
        pump(50)
    volume = list(panel.demo["stand"].outputs[0].data)[0].Volume
    path = os.path.join(run.out, "voronoi.FCStd")
    doc = FreeCAD.ActiveDocument
    doc.saveAs(path)
    FreeCADGui.runCommand("Std_Save", 0)
    pump(300)
    FreeCAD.closeDocument(doc.Name)
    pump(300)
    FreeCAD.openDocument(path)
    pump(1500)
    by = {c.nickname: c for c in panel.graph.components}
    rot, bounds = by.get("Rot"), by.get("Bnd")
    check("reopened: rotate axis kept", rot is not None and rot.inputs[3].default == (1.0, 0.0, 0.0))
    check("reopened: flatten kept", bounds is not None and bounds.inputs[0].modifier == "flatten")
    after = [s for c in panel.graph.components if c.nickname == "Rot" for s in c.outputs[0].data]
    check("reopened: same screen", len(after) == 1 and abs(after[0].Volume - volume) < 1e-6 * volume,
          [volume, after[0].Volume if after else None])


Run("showcase").run_later(body)
