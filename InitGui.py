# SPDX-License-Identifier: LGPL-2.1-or-later
import FreeCADGui


class KatydidWorkbench(FreeCADGui.Workbench):
    MenuText = "Katydid"
    ToolTip = "Grasshopper-style visual programming canvas"

    def __init__(self):
        import katydid
        self.__class__.Icon = katydid.resource("katydid.svg")

    def Initialize(self):
        from katydid import commands
        commands.register()
        self.appendToolbar("Katydid", commands.COMMANDS)
        self.appendMenu("Katydid", commands.COMMANDS)

    def Activated(self):
        from katydid import gui
        gui.show_canvas()

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(KatydidWorkbench())

# Register Katydid_Canvas and Katydid_Bake now, not on first activation, so
# other workbenches can put them on their toolbars. This imports no Qt code.
from katydid import commands as _commands  # noqa: E402

_commands.register()
