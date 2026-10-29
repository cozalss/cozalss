"""Compile every static profile asset (dark + light), the README and the telemetry glyph atlas.

    python -m pip install -r tools/requirements.txt
    python tools/build.py            # build into assets/, README.md and tools/glyph-atlas.json
    python tools/build.py --check    # rebuild in a temp dir; fail if committed files are stale
"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from pathlib import Path
from typing import Callable
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

from profile_art import atlas, buttons, cards, fonts, hero, readme, stack  # noqa: E402
from profile_art.content import CARDS, CONTACTS, HERO, PANELS  # noqa: E402
from profile_art.theme import THEMES  # noqa: E402

log = logging.getLogger("build")
ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 250_000  # keep every image light enough for GitHub's proxy and mobile

ATLAS_FACES = {  # the card faces, so the stdlib-only telemetry panels match the static cards
    "mono": ("am", cards.MONO),
    "title": ("at", cards.TITLE),
    "value": ("av", cards.VALUE),
}


def targets() -> dict[str, Callable[[], str]]:
    panel_h = max(stack.height(p) for p in PANELS)  # side-by-side panels share a height
    out: dict[str, Callable[[], str]] = {
        "tools/glyph-atlas.json": lambda: atlas.export(ATLAS_FACES, fonts.glyph, fonts.units_per_em),
        "README.md": readme.render,
    }
    for theme in THEMES:
        out[f"assets/hero-{theme.name}.svg"] = lambda t=theme: hero.render(t, HERO)
        for card in CARDS:
            out[f"assets/card-{card.slug}-{theme.name}.svg"] = lambda t=theme, c=card: cards.render(t, c)
        for panel in PANELS:
            out[f"assets/stack-{panel.slug}-{theme.name}.svg"] = lambda t=theme, p=panel: stack.render(t, p, panel_h)
        for contact in CONTACTS:
            out[f"assets/contact-{contact.slug}-{theme.name}.svg"] = lambda t=theme, c=contact: buttons.render(t, c)
    return out


def build(root: Path) -> list[Path]:
    written = []
    for rel, render in targets().items():
        content = render()
        size = len(content.encode())
        if rel.endswith(".svg"):
            ElementTree.fromstring(content)  # fail fast on malformed XML
            if size > MAX_BYTES:
                raise SystemExit(f"{rel} is {size} bytes (> {MAX_BYTES})")
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        written.append(path)
        log.info("%-40s %7d bytes", rel, size)
    return written


def check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp)
        stale = [str(p.relative_to(fresh)) for p in build(fresh)
                 if not (ROOT / p.relative_to(fresh)).exists()
                 or (ROOT / p.relative_to(fresh)).read_bytes() != p.read_bytes()]
    if stale:
        log.error("stale build output, run tools/build.py: %s", ", ".join(stale))
        return 1
    log.info("build output is up to date")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify committed output is up to date")
    args = parser.parse_args()
    if args.check:
        return check()
    build(ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
