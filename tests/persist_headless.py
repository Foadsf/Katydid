# SPDX-License-Identifier: LGPL-2.1-or-later
"""Open the saved definition in console FreeCAD (no GUI) and recompute it.

    set KATYDID_OUT=<dir from persist_smoke>   & freecadcmd.exe tests/persist_headless.py

Proves the definition in the .FCStd is self-contained: the document object
restores without the GUI and the graph solves to the same geometry.
"""

import json
import os
import traceback

import FreeCAD

out = os.environ["KATYDID_OUT"]
res = {"checks": {}}
try:
    from katydid import document, feature
    from katydid.engine import Graph

    res["checks"]["running_without_gui"] = {"ok": not FreeCAD.GuiUp}
    doc = FreeCAD.openDocument(os.path.join(out, "definition.FCStd"))
    obj = feature.find(doc)
    res["checks"]["proxy_restored"] = {"ok": obj is not None}
    graph = Graph()
    _, warnings = document.build(graph, obj.Definition)
    graph.solve()
    shapes = [s for c in graph.components if c.preview for s in c.shapes()]
    with open(os.path.join(out, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    got = sorted(round(s.Volume, 4) for s in shapes)
    res["checks"]["same_geometry_headless"] = {"ok": got == expected["volumes"],
                                               "detail": [got, expected["volumes"]]}
    res["checks"]["no_warnings"] = {"ok": warnings == [], "detail": warnings}
except Exception:
    res["exception"] = traceback.format_exc()
finally:
    res["passed"] = sum(c["ok"] for c in res["checks"].values())
    res["total"] = len(res["checks"])
    with open(os.path.join(out, "results_headless.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    os._exit(0)
