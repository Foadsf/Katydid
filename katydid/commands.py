# SPDX-License-Identifier: LGPL-2.1-or-later
"""Katydid's FreeCAD commands, registered when FreeCAD starts.

This module imports nothing heavy: the canvas (Qt, the component library) is
only loaded when a command runs. So other workbenches and toolbars can use
Katydid_Canvas and Katydid_Bake without activating the Katydid workbench.
"""

from . import resource

COMMANDS = ["Katydid_Canvas", "Katydid_Bake"]


class _CanvasCommand:
    def GetResources(self):
        return {"Pixmap": resource("katydid.svg"), "MenuText": "Canvas",
                "ToolTip": "Show the Katydid visual programming canvas"}

    def Activated(self):
        from .gui import show_canvas
        show_canvas()

    def IsActive(self):
        return True


class _BakeCommand:
    def GetResources(self):
        return {"Pixmap": resource("bake.svg"), "MenuText": "Bake",
                "ToolTip": "Bake the selected canvas components into the document"}

    def Activated(self):
        from .gui import show_canvas
        show_canvas().bake()

    def IsActive(self):
        return True


def register():
    """Add the commands once; calling again is harmless."""
    import FreeCADGui
    known = set(FreeCADGui.listCommands())
    for name, cmd in (("Katydid_Canvas", _CanvasCommand), ("Katydid_Bake", _BakeCommand)):
        if name not in known:
            FreeCADGui.addCommand(name, cmd())
