# SPDX-License-Identifier: LGPL-2.1-or-later
"""Run every FreeCAD-hosted test without touching the user's screen.

    python tests/run_gui_tests.py [--out DIR] [--visible] [--only smoke,tree,...]

With the optional `surfacekit` helper (a directory named by KATYDID_SURFACEKIT,
or importable from sys.path), each FreeCAD runs on a private Win32 desktop: no
window, no taskbar button, no focus change on the desktop you are working on.
Per run it records the two controls that prove it: whether FreeCAD ever owned
the foreground window, and whether it had any window on your desktop. Without
surfacekit, or with --visible, FreeCAD is started minimised and unactivated
instead (it may still flash). Results and screenshots go to ../_runs/.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

TESTS = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.dirname(TESTS)
BIN = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "FreeCAD 1.1", "bin")
RUNS = [("smoke", "freecad.exe", "gui_smoke.py"),
        ("tree", "freecad.exe", "tree_smoke.py"),
        ("attractor", "freecad.exe", "attractor_smoke.py"),
        ("tolerance", "freecad.exe", "tolerance_smoke.py"),
        ("showcase", "freecad.exe", "showcase_smoke.py"),
        ("save", "freecad.exe", "persist_smoke.py"),
        ("load", "freecad.exe", "persist_smoke.py"),
        ("headless", "freecadcmd.exe", "persist_headless.py"),
        ("geometry", "freecadcmd.exe", "test_geometry.py"),
        ("docshots", "freecad.exe", "doc_shots.py")]  # regenerates docs/images
TIMEOUTS = {"docshots": 1200}   # seconds; 7-16 s per showcase for canvas, preview and render images


def surfacekit():
    extra = os.environ.get("KATYDID_SURFACEKIT")
    if extra:
        sys.path.insert(0, extra)
    try:
        import surfacekit as sk  # noqa: PLC0415
        return sk
    except ImportError:
        return None


def launch(sk, exe, script, env, visible, timeout=240):
    """Run one FreeCAD to completion; returns (exit code, controls)."""
    if sk is not None and not visible and exe == "freecad.exe":
        app = sk.LaunchedApp(os.path.join(BIN, exe), [script], hidden=True, env=env,
                             timeout=60, max_memory_gb=8)
        # focus_taken only says the foreground window changed, which also happens
        # when YOU switch windows meanwhile; who owns the foreground tells them apart.
        owners = {sk.window_pid(sk.foreground())}
        controls = {"desktop": "hidden", "focus_changed": app.focus_taken,
                    "window_on_your_desktop": app.on_default_desktop}
        try:
            end = time.monotonic() + timeout
            code = None
            while time.monotonic() < end:
                code = app.proc.poll()
                if code is not None:
                    break
                owners.add(sk.window_pid(sk.foreground()))
                time.sleep(0.5)
            else:
                app.proc.kill()
        finally:
            sk.LaunchedApp.registry.discard(app.pid)
            app.desktop.close()
        controls["focus_taken"] = app.pid in owners
        return code, controls
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    flags = 0x08000000 if exe == "freecadcmd.exe" else 0  # CREATE_NO_WINDOW for the console one
    p = subprocess.Popen([os.path.join(BIN, exe), script], env=env, startupinfo=si,
                         creationflags=flags, stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        return p.wait(timeout), {"desktop": "console, no window" if flags else "minimised"}
    except subprocess.TimeoutExpired:
        p.kill()
        return None, {"desktop": "minimised"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(os.path.dirname(ADDON), "_runs",
                                                  time.strftime("gui_%Y%m%d_%H%M%S")))
    ap.add_argument("--visible", action="store_true", help="do not use a hidden desktop")
    ap.add_argument("--only", help="comma list of: " + ",".join(r[0] for r in RUNS))
    args = ap.parse_args(argv)
    sk = surfacekit()
    if sk is None and not args.visible:
        # Never fall back to the user's desktop silently: that is the one thing
        # this runner exists to avoid.
        print("surfacekit not found: set KATYDID_SURFACEKIT to its directory, "
              "or pass --visible to run FreeCAD on your desktop (minimised).", file=sys.stderr)
        return 2
    os.makedirs(args.out, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None
    failed, summary = 0, {}
    for name, exe, script in RUNS:
        if only and name not in only:
            continue
        if not only and name == "docshots":  # rewrites docs/images: only on request
            continue
        env = dict(os.environ, KATYDID_OUT=args.out, KATYDID_PHASE=name)
        env.pop("KATYDID_EXPERIMENTS", None)
        env.pop("KATYDID_HIDDEN", None)
        if sk is not None and not args.visible:
            env["KATYDID_HIDDEN"] = "1"
        t0 = time.perf_counter()
        code, controls = launch(sk, exe, os.path.join(TESTS, script), env, args.visible,
                                TIMEOUTS.get(name, 240))
        result = os.path.join(args.out, f"results_{name}.json")
        if not os.path.exists(result):
            print(f"{name:9s}: NO RESULTS (exit {code}) {controls}")
            failed += 1
            continue
        with open(result, encoding="utf-8") as fh:
            r = json.load(fh)
        bad = [k for k, v in r["checks"].items() if not v["ok"]] + (["exception"] if r.get("exception") else [])
        intruded = controls.get("focus_taken") or controls.get("window_on_your_desktop")
        if intruded:
            bad.append("touched-your-desktop")
        failed += len(bad)
        summary[name] = {"passed": r["passed"], "total": r["total"], "failed": bad,
                         "seconds": round(time.perf_counter() - t0, 1), **controls}
        print(f"{name:9s}: {r['passed']}/{r['total']} passed  {', '.join(bad)}  "
              f"[{controls.get('desktop')}, FreeCAD took focus: {controls.get('focus_taken', 'n/a')}, "
              f"window on your desktop: {controls.get('window_on_your_desktop', 'n/a')}]")
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
    print(f"Output: {args.out}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
