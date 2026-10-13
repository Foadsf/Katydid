# SPDX-License-Identifier: LGPL-2.1-or-later
"""The document object that carries a canvas definition inside the .FCStd.

Its Definition property holds the JSON from document.py, so the definition is
written into the file's Document.xml and comes back on open. No Qt imports at
module level: FreeCAD imports this module (the stored proxy) when it opens a
file, including in console mode.
"""

from __future__ import annotations

import FreeCAD

from . import resource

PROPERTY = "Definition"


class DefinitionFeature:
    def __init__(self, obj):
        obj.Proxy = self
        self.setup(obj)

    def setup(self, obj):
        if PROPERTY not in obj.PropertiesList:
            obj.addProperty("App::PropertyString", PROPERTY, "Katydid",
                            "Canvas definition as JSON. Edit it on the canvas.")
        obj.setEditorMode(PROPERTY, 1)  # read-only in the property editor
        # Writing the definition must not flag the object for recompute.
        obj.setPropertyStatus(PROPERTY, "Output")

    def onDocumentRestored(self, obj):
        self.setup(obj)

    def execute(self, obj):
        pass

    def dumps(self):
        return None

    def loads(self, state):
        return None


class ViewProviderDefinition:
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        pass

    def getIcon(self):
        return resource("katydid.svg")

    def doubleClicked(self, vobj):
        from .gui import show_canvas
        show_canvas()
        return True

    def dumps(self):
        return None

    def loads(self, state):
        return None


def find(doc):
    for obj in doc.Objects:
        if isinstance(getattr(obj, "Proxy", None), DefinitionFeature):
            return obj
    return None


def create(doc):
    obj = doc.addObject("App::FeaturePython", "Katydid")
    DefinitionFeature(obj)
    if FreeCAD.GuiUp:
        ViewProviderDefinition(obj.ViewObject)
    return obj


def read(doc) -> str | None:
    obj = find(doc)
    return getattr(obj, PROPERTY, None) if obj is not None else None
