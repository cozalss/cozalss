"""Tiny, dependency-free SVG building blocks.

Markup is assembled from immutable `Fragment`s. A fragment carries the glyph
outlines it references, so a finished document can emit every glyph exactly
once in <defs> without any shared mutable registry.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from xml.sax.saxutils import escape, quoteattr


@dataclass(frozen=True)
class Fragment:
    markup: str = ""
    # Mapping-like tuple of (glyph_id, path_data) pairs, kept as a frozenset so
    # that composing fragments is a pure union.
    glyphs: frozenset[tuple[str, str]] = frozenset()

    def __add__(self, other: "Fragment") -> "Fragment":
        return Fragment(self.markup + other.markup, self.glyphs | other.glyphs)


EMPTY = Fragment()


def join(parts: Iterable[Fragment]) -> Fragment:
    markup: list[str] = []
    glyphs: set[tuple[str, str]] = set()
    for part in parts:
        markup.append(part.markup)
        glyphs |= part.glyphs
    return Fragment("".join(markup), frozenset(glyphs))


def num(value: float) -> str:
    """Compact coordinate formatting: at most two decimals, no trailing zeros."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def glyph_transform(x: float, y: float, scale: float) -> str:
    """Place font-unit outlines at (x, y). The scale keeps 6 significant digits:
    rounding it like a coordinate would snap every font size to a multiple of 10."""
    return f"translate({num(x)} {num(y)}) scale({scale:.6g} {-scale:.6g})"


def attrs(**values: object) -> str:
    out = []
    for key, value in values.items():
        if value is None or value is False:
            continue
        name = key.rstrip("_").replace("_", "-")
        if isinstance(value, float):
            value = num(value)
        out.append(f" {name}={quoteattr(str(value))}")
    return "".join(out)


def el(tag: str, children: Fragment | str | None = None, **values: object) -> Fragment:
    """Build one element. `children` may be raw markup or a Fragment."""
    if children is None:
        return Fragment(f"<{tag}{attrs(**values)}/>")
    if isinstance(children, str):
        children = Fragment(children)
    return Fragment(f"<{tag}{attrs(**values)}>", children.glyphs) + children + Fragment(f"</{tag}>")


def group(children: Iterable[Fragment], **values: object) -> Fragment:
    return el("g", join(children), **values)


def points(pts: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{num(x)},{num(y)}" for x, y in pts)


def document(
    width: int,
    height: int,
    body: Fragment,
    *,
    title: str,
    desc: str,
    style: str = "",
    defs: Fragment = EMPTY,
) -> str:
    glyphs = sorted(body.glyphs | defs.glyphs)
    if len({gid for gid, _ in glyphs}) != len(glyphs):
        raise ValueError("glyph id collision: two Faces share a `code`")
    glyph_defs = "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in glyphs)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" fill="none" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>'
        + (f"<style>{style}</style>" if style else "")
        + f"<defs>{glyph_defs}{defs.markup}</defs>"
        + body.markup
        + "</svg>\n"
    )
