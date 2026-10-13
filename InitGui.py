# SPDX-License-Identifier: LGPL-2.1-or-later
import FreeCADGui


class KatydidWorkbench(FreeCADGui.Workbench):
    MenuText = "Katydid"
    ToolTip = "Grasshopper-style visual programming canvas"

    def __init__(self):
        import katydid
        self.__class__.Icon = katydid.resource("katydid.svg")

    def Initialize(self):
        from katydid import gui
        gui.register_commands()
        self.appendToolbar("Katydid", gui.COMMANDS)
        self.appendMenu("Katydid", gui.COMMANDS)

    def Activated(self):
        from katydid import gui
        gui.show_canvas()

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


FreeCADGui.addWorkbench(KatydidWorkbench())
