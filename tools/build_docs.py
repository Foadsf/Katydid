# SPDX-License-Identifier: LGPL-2.1-or-later
"""Build the documentation site from docs/*.adoc into site/.

    python tools/build_docs.py [--out site] [--strict]

Needs Asciidoctor (Ruby gem); Rouge enables syntax highlighting and is used
when installed. --strict fails on any Asciidoctor warning (broken xref,
missing include, missing image), which is how CI runs it.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")


def asciidoctor() -> list[str]:
    exe = shutil.which("asciidoctor")
    if not exe:
        sys.exit("asciidoctor not found: gem install asciidoctor rouge")
    return [exe]


def has_rouge() -> bool:
    ruby = shutil.which("ruby")
    if not ruby:
        return False
    return subprocess.run([ruby, "-e", "require 'rouge'"], capture_output=True).returncode == 0


def missing_images(pages) -> list[str]:
    missing = []
    for page in pages:
        text = open(page, encoding="utf-8").read()
        for target in re.findall(r"image::?([^\[\s]+)\[", text):
            if not target.startswith("http") and not os.path.exists(os.path.join(DOCS, "images", target)):
                missing.append(f"{os.path.basename(page)}: {target}")
    return missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "site"))
    ap.add_argument("--strict", action="store_true", help="fail on any Asciidoctor warning")
    args = ap.parse_args(argv)

    pages = sorted(p for p in glob.glob(os.path.join(DOCS, "*.adoc"))
                   if not os.path.basename(p).startswith("_"))
    missing = missing_images(pages)
    if missing:
        print("missing images:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1
    if os.path.isdir(args.out):
        shutil.rmtree(args.out)
    os.makedirs(args.out)

    cmd = asciidoctor() + ["-D", args.out, "-a", f"docinfodir={os.path.join(DOCS, 'theme')}"]
    if not has_rouge():
        print("rouge not installed: building without syntax highlighting", file=sys.stderr)
        cmd += ["-a", "source-highlighter!"]
    if args.strict:
        cmd += ["--failure-level", "WARN"]
    run = subprocess.run(cmd + pages, capture_output=True, text=True)
    if run.stdout:
        print(run.stdout)
    if run.stderr:
        print(run.stderr, file=sys.stderr)
    if run.returncode:
        return run.returncode

    shutil.copytree(os.path.join(DOCS, "images"), os.path.join(args.out, "images"))
    shutil.copytree(os.path.join(DOCS, "theme"), os.path.join(args.out, "theme"),
                    ignore=shutil.ignore_patterns("*.html"))
    shutil.copy(os.path.join(ROOT, "katydid", "resources", "katydid.svg"),
                os.path.join(args.out, "images", "katydid.svg"))
    open(os.path.join(args.out, ".nojekyll"), "w").close()
    print(f"built {len(pages)} pages into {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
