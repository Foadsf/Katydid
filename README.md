# Katydid

A Grasshopper-style visual programming canvas for FreeCAD 1.1 (working name). This is the first spike: slider → components → live red preview in the 3D view → bake to the document.

## Install (this machine)

The source folder is linked into FreeCAD's user Mod folder:

```powershell
New-Item -ItemType Junction -Path "$env:APPDATA\FreeCAD\v1-1\Mod\Katydid" -Target "<path to this folder>"
```

Restart FreeCAD, pick **Katydid** in the workbench list. The canvas opens as a floating window; press **Demo**.

## Using the canvas

| Action | How |
|---|---|
| Add a component | Double-click empty canvas and type, or click/drag an icon from the tabs |
| Wire | Drag from an output grip to an input grip (Shift adds instead of replacing) |
| Remove a wire | Drag it off its input grip and drop on empty canvas |
| Pan / zoom | Right-drag / mouse wheel (zooms about the cursor) |
| Change a slider | Drag along its rail |
| Toggle preview | Select, Ctrl+Q (preview-off components turn darker grey) |
| Delete components | Select, Delete (only canvas components; document objects are safe) |
| Bake | **Bake**: selected components, or everything previewed if none selected |

Component colours: grey OK, orange warning (missing input), red error (hover for the message), green selected. Wires: solid = one item, double = list, dashed orange = empty.

## Layout

- `katydid/engine.py`: parameters, components, expire-then-solve, longest-list matching. No FreeCAD or Qt imports.
- `katydid/components.py`: the component library (10 components).
- `katydid/canvas.py`: the Qt canvas, grips, wires, search, tabs.
- `katydid/preview.py`, `bake.py`: Coin3D preview and bake.
- `katydid/gui.py`, `InitGui.py`: panel, commands, workbench.

## Tests

```powershell
& "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin\python.exe" -I tests\test_engine.py       # engine, headless
& "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin\python.exe" -I tests\paint_profile.py     # canvas paint cost
& "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin\freecad.exe" tests\gui_smoke.py            # real GUI, 20 checks
```

`gui_smoke.py` drives the canvas with real mouse and key events, bakes, writes screenshots and `results.json` to `../_runs/`, and exits without saving anything.

## Not yet

Data trees (only flat lists so far), saving the graph in the `.FCStd`, undo on the canvas, radial menu, clusters, script component, `.ghx` import.
