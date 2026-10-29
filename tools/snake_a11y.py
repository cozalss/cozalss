"""Make Platane/snk output honour prefers-reduced-motion (standard library only).

    python tools/snake_a11y.py dist/github-snake.svg dist/github-snake-dark.svg

snk animates with CSS, so one injected rule freezes it on the full contribution
grid for viewers who ask their OS for less motion. Idempotent; never writes a
file that is not well-formed SVG.
"""
from __future__ import annotations

import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree

log = logging.getLogger("snake_a11y")
RULE = "<style>@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>"
ROOT_TAG = re.compile(r"""<svg\b(?:[^>"']|"[^"]*"|'[^']*')*>""")  # a quoted ">" does not end the tag


def patch(svg: str) -> str:
    if "prefers-reduced-motion" in svg:
        return svg
    root_tag = ROOT_TAG.search(svg)
    if root_tag is None:
        raise ValueError("not an SVG document")
    patched = svg[: root_tag.end()] + RULE + svg[root_tag.end() :]
    ElementTree.fromstring(patched)
    return patched


def patch_file(path: Path) -> None:
    patched = patch(path.read_text(encoding="utf-8"))
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(patched)
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    paths = [Path(p) for p in (sys.argv[1:] if argv is None else argv)]
    failed = False
    for path in paths:
        try:
            patch_file(path)
            log.info("patched %s", path)
        except (OSError, ValueError, ElementTree.ParseError) as exc:
            log.error("left %s untouched: %s", path, exc)
            failed = True
    return 1 if failed or not paths else 0


if __name__ == "__main__":
    raise SystemExit(main())
