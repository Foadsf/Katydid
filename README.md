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
| Flatten / Graft / Simplify / Reverse | Right-click a grip (a right-drag still pans); a yellow F/G/S/R badge marks it |
| Component menu | Right-click a component: Preview, Delete |
| Bake | **Bake**: selected components, or everything previewed if none selected |

Component colours: grey OK, orange warning (missing input), red error (hover for the message), green selected. Wires: solid = one item, double = list, dashed = a tree of several branches, thin dashed orange = empty.

## Data trees

Data flows as trees: branches of items addressed by paths like `{0;1}`. Each input is item, list or tree access. Components match inputs branch by branch (a tree with fewer branches repeats its last one; outputs take the paths of the first input with the most branches) and, within a branch, item by item (longest list). A list output gets a branch per iteration, so dividing three circles in `{0}` gives `{0;0}`, `{0;1}`, `{0;2}`. The Panel lists data under its branch paths. These rules are our reading of Grasshopper's, written down in `katydid/engine.py`; they have not been checked against Grasshopper itself.

**Tree Demo** shows it: stacked circles → Divide Curve (a branch of points per circle) → a closed Polyline per branch → Loft with **Flatten** on its input, so one surface runs through every ring. Turn Flatten off and Loft goes red, because each branch then holds only one curve.

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
$py = "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin\python.exe"
& $py -I tests\mutate.py          # engine, tree and save-format tests, plus 5 deliberate breaks that must be caught
python tests\run_gui_tests.py     # everything in real FreeCAD, on a hidden desktop
```

`run_gui_tests.py` starts each FreeCAD on a private Win32 desktop through `surfacekit` (from `C:\dev\scripts`), so nothing appears on your screen and focus never moves; every run reports both controls. It runs `gui_smoke.py` (canvas driven with real mouse and key events, bake), `tree_smoke.py` (the tree demo, the grip menu by real right-clicks, Flatten/Simplify, save, reopen, bake), `persist_smoke.py` in a save phase and then a reopen phase in a fresh FreeCAD, and `persist_headless.py` in console FreeCAD. Drag speed is only judged with `--visible`: on the hidden desktop FreeCAD's 3D repaint is several times slower than on the real display. Screenshots and results go to `../_runs/`; nothing is saved to your settings. `paint_profile.py` and `preview_profile.py` measure where frame time goes.

## Not yet

Undo on the canvas, radial menu, a Param Viewer, Path Mapper and other tree components, clusters, script component, `.ghx` import.
