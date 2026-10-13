# SPDX-License-Identifier: LGPL-2.1-or-later
"""Save/reopen test across two separate FreeCAD processes.

    set KATYDID_OUT=<dir>
    set KATYDID_PHASE=save  & freecad.exe tests/persist_smoke.py   -> <dir>/definition.FCStd, expected.json
    set KATYDID_PHASE=load  & freecad.exe tests/persist_smoke.py   -> reopens it in a fresh process
    freecadcmd.exe tests/persist_headless.py                       -> recomputes it with no GUI at all
"""

import json
import os
import sys
import zipfile

import FreeCAD
import FreeCADGui
import katydid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(katydid.__file__))), "tests"))
from guitest import QtCore, Run, pump  # noqa: E402

PHASE = os.environ.get("KATYDID_PHASE", "save")


def snapshot(panel):
    """What must survive a save and reopen."""
    g = panel.graph
    comps = []
    for c in g.components:
        item = panel.scene.items_by_comp[c]
        comps.append({"type": type(c).__name__, "nickname": c.nickname, "preview": c.preview,
                      "pos": [round(item.pos().x(), 2), round(item.pos().y(), 2)],
                      "defaults": [p.default for p in c.inputs if isinstance(p.default, (int, float))],
                      "value": getattr(c, "value", None)})
    shapes = [s for c in g.components if c.preview for s in c.shapes()]
    return {"components": comps, "wires": len(g.wires()),
            "volumes": sorted(round(s.Volume, 4) for s in shapes),
            "xmin": sorted(round(s.BoundBox.XMin, 4) for s in shapes)}


def definition_in_file(path):
    """The Katydid definition exactly as written in the .FCStd's Document.xml."""
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("Document.xml"))
    for prop in root.iter("Property"):
        if prop.get("name") == "Definition":
            node = prop.find("String")
            return json.loads(node.get("value")) if node is not None else None
    return None


def gui_modified(doc):
    return bool(FreeCADGui.getDocument(doc.Name).Modified)


def save_phase(run):
    from katydid import components as lib
    from katydid import feature, gui
    check = run.check
    FreeCADGui.getMainWindow().showMaximized()
    FreeCADGui.activateWorkbench("KatydidWorkbench")
    pump(400)
    panel = gui.show_canvas()
    doc = FreeCAD.ActiveDocument
    check("no_object_for_empty_canvas", feature.find(doc) is None)
    panel.load_demo()
    pump(300)
    d = panel.demo
    # Edits a user would make: sliders, a moved component, a new wired component,
    # a non-default input value and a preview toggle.
    d["width"].set_value(27.5)
    d["count"].set_value(3)
    d["series"].inputs[0].default = 5.0
    d["box"].preview = True
    panel.scene.items_by_comp[d["panel"]].setPos(QtCore.QPointF(170, 120))
    sph = lib.Sphere()
    panel.scene.add_component(sph, QtCore.QPointF(140, -230))
    panel.scene.connect_params(d["height"].outputs[0], sph.inputs[0])
    panel.scene.request_solve()
    pump(WRITE_WAIT)
    obj = feature.find(doc)
    check("definition_object_created", obj is not None)
    check("edit_marks_document_modified", gui_modified(doc))
    check("definition_needs_no_recompute", obj is not None and "Touched" not in obj.State,
          obj.State if obj is not None else None)
    path = os.path.join(run.out, "definition.FCStd")
    doc.saveAs(path)  # gives the document its file name, as a first Save As would
    pump(200)
    # The last edit right before Ctrl+S must still be saved (flush on save).
    d["height"].set_value(42)
    panel.scene.request_solve()   # starts the write-through timer; we save before it fires
    panel.scene.solve_now()
    FreeCADGui.runCommand("Std_Save", 0)
    pump(300)
    # Judge the FILE, not the in-memory property: the delayed write may have
    # updated memory after the save (a negative control caught exactly that).
    saved = definition_in_file(path)
    check("definition_is_in_document_xml", saved is not None and saved.get("format") == "katydid")
    heights = [c["state"]["value"] for c in (saved or {}).get("components", [])
               if c.get("nickname") == "Height"]
    check("last_edit_flushed_on_save", heights == [42], heights)
    check("saved_clears_modified", not gui_modified(doc))
    expected = snapshot(panel)
    with open(os.path.join(run.out, "expected.json"), "w", encoding="utf-8") as fh:
        json.dump(expected, fh, indent=1)
    run.res["expected"] = {k: expected[k] for k in ("wires", "volumes")}
    run.grab(None, "01_before_save.png")


def load_phase(run):
    from katydid import feature, gui
    check = run.check
    path = os.path.join(run.out, "definition.FCStd")
    with open(os.path.join(run.out, "expected.json"), encoding="utf-8") as fh:
        expected = json.load(fh)
    FreeCADGui.getMainWindow().showMaximized()
    FreeCADGui.activateWorkbench("KatydidWorkbench")
    pump(400)
    panel = gui.show_canvas()          # canvas already open on an empty document
    scratch = FreeCAD.ActiveDocument.Name
    check("starts_empty", not panel.graph.components)
    doc = FreeCAD.openDocument(path)   # the observer must switch the canvas to it
    pump(900)
    check("canvas_follows_opened_file", panel.doc_name == doc.Name, [panel.doc_name, doc.Name])
    run.res["debug_after_open"] = {"pending": panel.scene._pending,
                                   "expired": [c.nickname for c in panel.graph.components if c.expired],
                                   "outputs": {c.nickname: len(c.outputs[0].data)
                                               for c in panel.graph.components if c.outputs}}
    got = snapshot(panel)
    check("same_components", got["components"] == expected["components"],
          {"got": got["components"], "expected": expected["components"]})
    check("same_wires", got["wires"] == expected["wires"], [got["wires"], expected["wires"]])
    check("same_geometry", got["volumes"] == expected["volumes"] and got["xmin"] == expected["xmin"],
          {"got": got["volumes"], "expected": expected["volumes"]})
    check("all_components_ok", all(c.state == "ok" for c in panel.graph.components),
          {c.nickname: c.messages for c in panel.graph.components if c.state != "ok"})
    check("no_load_warnings", panel.load_warnings == [], panel.load_warnings)
    check("opening_does_not_modify", not gui_modified(doc))
    check("preview_on_opened_doc", panel.preview._doc == doc.Name, panel.preview._doc)
    FreeCADGui.ActiveDocument.ActiveView.viewIsometric()
    FreeCADGui.ActiveDocument.ActiveView.fitAll()
    pump(300)
    run.grab(None, "02_reopened.png")

    # Switching documents swaps the canvas; switching back restores it untouched.
    if scratch in FreeCAD.listDocuments():
        _activate_view(scratch)
    else:  # FreeCAD closed the untouched start document when the file opened
        scratch = FreeCAD.newDocument("Scratch").Name
    pump(400)
    check("switch_shows_other_doc", panel.doc_name == scratch and not panel.graph.components,
          [panel.doc_name, len(panel.graph.components)])
    _activate_view(doc.Name)
    pump(400)
    check("switch_back_restores", panel.doc_name == doc.Name and
          snapshot(panel)["components"] == expected["components"])

    # Editing the reopened definition writes through again.
    width = next(c for c in panel.graph.components if c.nickname == "Width")
    width.set_value(12)
    panel.timings.clear()
    panel.scene.request_solve()
    pump(WRITE_WAIT)
    preview_ms = panel.timings[-1][1] if panel.timings else None
    check("preview_fast_with_sphere", preview_ms is not None and preview_ms < 60, preview_ms)
    stored = json.loads(feature.read(doc))
    widths = [c["state"]["value"] for c in stored["components"] if c.get("nickname") == "Width"]
    check("reopened_edit_writes_through", widths == [12] and gui_modified(doc), widths)

    # Closing the document clears the canvas and does not crash.
    name = doc.Name
    FreeCAD.closeDocument(name)
    pump(500)
    check("close_unbinds", panel.doc_name != name, panel.doc_name)
    check("canvas_follows_remaining_doc", panel.doc_name == FreeCAD.ActiveDocument.Name,
          [panel.doc_name, FreeCAD.ActiveDocument.Name if FreeCAD.ActiveDocument else None])


def _activate_view(name):
    """Make name the active document the way a user does: activate its 3D view tab."""
    from PySide import QtWidgets
    mdi = FreeCADGui.getMainWindow().findChild(QtWidgets.QMdiArea)
    label = FreeCAD.getDocument(name).Label
    for sub in mdi.subWindowList():
        if sub.windowTitle().startswith(label + " :") or sub.windowTitle().startswith(label + ":"):
            mdi.setActiveSubWindow(sub)
            return True
    return False


WRITE_WAIT = 900  # > the panel's write-through delay
Run(PHASE).run_later(save_phase if PHASE == "save" else load_phase)
