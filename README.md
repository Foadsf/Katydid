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

## Saving

The canvas follows the active FreeCAD document. Its definition is stored on a **Katydid** object in that document (a JSON string property), so it is written into the `.FCStd`'s `Document.xml` when you save and the canvas comes back when you open the file. Edits are written to the document about 0.4 s after they stop, and again at the start of every save, so Ctrl+S right after a slider move still saves it. Switching documents switches the canvas; closing one clears it. Double-click the Katydid object in the tree to open the canvas. A component type this version does not know is kept as a red placeholder and saved back unchanged.

## Layout

- `katydid/engine.py`: parameters, components, expire-then-solve, longest-list matching. No FreeCAD or Qt imports.
- `katydid/components.py`: the component library (10 components).
- `katydid/canvas.py`: the Qt canvas, grips, wires, search, tabs.
- `katydid/preview.py`, `bake.py`: Coin3D preview and bake.
- `katydid/gui.py`, `InitGui.py`: panel, commands, workbench.

## Tests

```powershell
& "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin\python.exe" -I tests\test_engine.py       # engine, headless
& "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin\python.exe" -I tests\test_document.py     # save format, headless
pwsh tests\run_gui_tests.ps1                                                             # everything in real FreeCAD
```

`run_gui_tests.ps1` runs four FreeCAD processes: `gui_smoke.py` (canvas driven with real mouse and key events, speed, bake; 20 checks), `persist_smoke.py` in a save phase and then a reopen phase in a fresh FreeCAD (7 + 15 checks, judged on the saved file), and `persist_headless.py` in console FreeCAD (4 checks: the definition recomputes with no GUI). Screenshots and results go to `../_runs/`; nothing is saved to your settings. `paint_profile.py` and `preview_profile.py` measure where frame time goes.

## Not yet

Data trees (only flat lists so far), undo on the canvas, radial menu, clusters, script component, `.ghx` import.
