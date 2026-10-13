# SPDX-License-Identifier: LGPL-2.1-or-later
"""Canvas paint cost outside FreeCAD (no geometry kernel needed).

    <FreeCAD>/bin/python.exe -I tests/paint_profile.py [--profile]
"""

import cProfile
import os
import pstats
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6 import QtWidgets  # noqa: E402

app = QtWidgets.QApplication(sys.argv[:1])
from katydid.gui import KatydidPanel  # noqa: E402

panel = KatydidPanel(with_preview=False)
panel.resize(1150, 420)
panel.show()
panel.load_demo()
for _ in range(20):
    app.processEvents()
    time.sleep(0.01)
vp = panel.view.viewport()
slider = panel.demo["spacing"]
full, update = [], []
for i in range(30):
    t0 = time.perf_counter()
    vp.repaint()
    full.append((time.perf_counter() - t0) * 1000)
    # a slider step: value change, solve, then whatever Qt repaints
    slider.set_value(10 + (i % 10) * 5)
    t0 = time.perf_counter()
    panel.scene.solve_now()
    app.processEvents()
    update.append((time.perf_counter() - t0) * 1000)
print(f"full repaint median {statistics.median(full):.2f} ms; "
      f"slider step (solve + incremental paint) median {statistics.median(update):.2f} ms; "
      f"zoom {panel.view.transform().m11():.2f}")
if "--profile" in sys.argv:
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(20):
        vp.repaint()
    pr.disable()
    pstats.Stats(pr).sort_stats("cumulative").print_stats(12)
