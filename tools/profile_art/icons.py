"""Vendored brand icons (see tools/icons/SOURCES.md) as recolourable <symbol>s."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from .svg import Fragment, el, join

ICON_DIR = Path(__file__).resolve().parent.parent / "icons"
SVG_NS = "{http://www.w3.org/2000/svg}"


@lru_cache(maxsize=None)
def _load(name: str) -> tuple[str, tuple[str, ...]]:
    root = ElementTree.parse(ICON_DIR / f"{name}.svg").getroot()
    paths = tuple(p.attrib["d"] for p in root.iter(f"{SVG_NS}path"))
    if not paths:
        raise ValueError(f"icon {name!r} has no <path>")
    return root.attrib.get("viewBox", "0 0 24 24"), paths


def symbol_id(name: str) -> str:
    return f"i-{name}"


def symbols(names: set[str]) -> Fragment:
    """One <symbol> per icon; original fills are dropped so <use fill> recolours it."""
    out = []
    for name in sorted(names):
        view_box, paths = _load(name)
        out.append(el("symbol", join(el("path", d=d) for d in paths), id=symbol_id(name), viewBox=view_box))
    return join(out)


def use(name: str, *, x: float, y: float, size: float, fill: str) -> Fragment:
    return el("use", href=f"#{symbol_id(name)}", x=f"{x:.1f}", y=f"{y:.1f}", width=f"{size:g}",
              height=f"{size:g}", fill=fill)
