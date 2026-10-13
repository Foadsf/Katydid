# SPDX-License-Identifier: LGPL-2.1-or-later
"""Generate docs/components.adoc and the component icons from the registry.

    python tools/gen_docs.py            write the files
    python tools/gen_docs.py --check    exit 1 if the committed files are stale

Needs PySide6 (icons are drawn by the same code the ribbon uses). Opens no
window; on Linux it runs with QT_QPA_PLATFORM=offscreen.
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
if sys.platform != "win32":
    # Offscreen on Windows has no font database: every icon came out as an empty
    # square. The native Windows backend draws them without opening a window.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DOCS = os.path.join(ROOT, "docs")
ICONS = os.path.join(DOCS, "images", "icons")
ACCESS = {"item": "item", "list": "list", "tree": "tree"}


def fmt_default(p) -> str:
    if p.default is None:
        if p.optional:
            return "optional"
        return f"_type a {p.kind} or wire it_" if getattr(p, "kind", None) else "_wire it_"
    if isinstance(p.default, bool):
        return f"`{p.default}`"
    if isinstance(p.default, float):
        return f"`{p.default:g}`"
    if isinstance(p.default, (tuple, list)):
        return "`(" + ", ".join(f"{v:g}" for v in p.default) + ")`"
    if isinstance(p.default, str):
        return f"`\"{p.default}\"`" if p.default else "`\"\"`"
    return f"`{p.default}`"


def cell(text: str) -> str:
    return (text or "").replace("|", "\\|")


def render(lib) -> str:
    out = [
        "= Component reference",
        ":page-id: components",
        "include::_attributes.adoc[]",
        "",
        "[.lead]",
        f"All {len(lib.REGISTRY)} components, tab by tab. This page is generated from the code "
        "(`tools/gen_docs.py`), so it always matches the version you are reading.",
        "",
        "How to read the tables: *Access* says how an input takes its data "
        "(see xref:data-trees.adoc#access[access modes]). An input with a *Default* works "
        "without a wire, and menu:Set value…[] on the input's right-click menu changes that value. "
        "_Type a number or wire it_ means it needs a value before the component can run; "
        "_wire it_ means it needs data from another component (geometry, for example).",
        "",
    ]
    for cat in lib.CATEGORIES:
        classes = [c for c in lib.REGISTRY if c.category == cat]
        out += [f"== {cat}", ""]
        for cls in classes:
            comp = cls()
            out += [f"[[cmp-{cls.__name__}]]",
                    f"=== image:icons/{cls.__name__}.png[{cls.name},28,28,role=icon] {cls.name}",
                    "",
                    f"*Nickname* `{cls.nickname}` · {cell(cls.description)}.",
                    ""]
            if comp.inputs:
                out += ['[cols="3,1,1,2,5",options="header",role="params"]', "|===",
                        "|Input |Nick |Access |Default |Description"]
                for p in comp.inputs:
                    out.append(f"|{cell(p.name)} |`{cell(p.nickname) or '·'}` |{ACCESS[p.access]} "
                               f"|{fmt_default(p)} |{cell(p.description)}")
                out += ["|===", ""]
            if comp.outputs:
                out += ['[cols="3,1,1,7",options="header",role="params"]', "|===",
                        "|Output |Nick |Access |Description"]
                for p in comp.outputs:
                    out.append(f"|{cell(p.name)} |`{cell(p.nickname)}` |{ACCESS[p.access]} "
                               f"|{cell(p.description)}")
                out += ["|===", ""]
    return "\n".join(out) + "\n"


def icons(lib) -> dict[str, bytes]:
    from PySide6 import QtCore, QtWidgets
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from katydid.canvas import make_icon
    files = {}
    for cls in lib.REGISTRY:
        pm = make_icon(cls, 56).pixmap(56, 56)
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        pm.save(buf, "PNG")
        files[f"{cls.__name__}.png"] = bytes(buf.data())
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if docs/components.adoc is stale")
    args = ap.parse_args(argv)
    from katydid import components as lib
    text = render(lib)
    path = os.path.join(DOCS, "components.adoc")
    if args.check:
        current = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        missing = [c.__name__ for c in lib.REGISTRY
                   if not os.path.exists(os.path.join(ICONS, f"{c.__name__}.png"))]
        if current != text or missing:
            print("docs/components.adoc or icons are stale: run python tools/gen_docs.py", file=sys.stderr)
            return 1
        print("component reference is up to date")
        return 0
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.makedirs(ICONS, exist_ok=True)
    for name, data in icons(lib).items():
        with open(os.path.join(ICONS, name), "wb") as fh:
            fh.write(data)
    print(f"wrote {path} and {len(lib.REGISTRY)} icons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
