"""Pre-outlined glyphs, so the nightly telemetry job needs no font tooling.

`tools/build.py` writes tools/glyph-atlas.json from the pinned fonts; the
stdlib-only telemetry script reads it to typeset live numbers and names.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping

from .svg import Fragment, el, glyph_transform, num

ATLAS_FILE = Path(__file__).resolve().parent.parent / "glyph-atlas.json"
CHARS = "".join(chr(c) for c in range(32, 127)) + "·–—…"


@dataclass(frozen=True)
class AtlasFace:
    code: str
    upem: int
    advances: Mapping[str, float]
    paths: Mapping[str, str]


def load(path: Path = ATLAS_FILE) -> dict[str, AtlasFace]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        key: AtlasFace(f["code"], f["upem"], MappingProxyType(f["advances"]), MappingProxyType(f["paths"]))
        for key, f in raw["faces"].items()
    }


def _check(face: AtlasFace, value: str) -> None:
    missing = sorted({ch for ch in value if ch not in face.advances})
    if missing:
        raise ValueError(f"glyph atlas lacks {missing!r}")


def measure(face: AtlasFace, value: str, size: float, tracking: float = 0.0) -> float:
    _check(face, value)
    units = sum(face.advances[ch] for ch in value) + tracking * face.upem / 1000 * max(len(value) - 1, 0)
    return units * size / face.upem


def text(face: AtlasFace, value: str, *, x: float, y: float, size: float, fill: str | None = None,
         tracking: float = 0.0, anchor: str = "start", **extra: object) -> Fragment:
    """Same output contract as fonts.text, but typeset from the atlas."""
    _check(face, value)
    shift = {"start": 0.0, "middle": 0.5, "end": 1.0}[anchor] * measure(face, value, size, tracking)
    scale = size / face.upem
    extra_units = tracking * face.upem / 1000
    uses, glyphs, pen = [], set(), 0.0
    for ch in value:
        path = face.paths[ch]
        if path:
            gid = f"{face.code}-{ord(ch):x}"
            uses.append(f'<use href="#{gid}" x="{num(pen)}"/>' if pen else f'<use href="#{gid}"/>')
            glyphs.add((gid, path))
        pen += face.advances[ch] + extra_units
    body = el("g", "".join(uses), transform=glyph_transform(x - shift, y, scale), fill=fill, **extra)
    return Fragment(body.markup, frozenset(glyphs))


GlyphFn = Callable[[object, str], tuple[float, str]]
UpemFn = Callable[[object], int]


def export(faces: Mapping[str, tuple[str, object]], glyph_fn: GlyphFn, upem_fn: UpemFn, chars: str = CHARS) -> str:
    """Serialise {key: (code, Face)} using `glyph_fn(face, ch) -> (advance, path)` in the face's own units."""
    def one(code: str, face: object) -> dict:
        pairs = {ch: glyph_fn(face, ch) for ch in chars}
        return {"code": code, "upem": upem_fn(face),
                "advances": {ch: round(adv, 1) for ch, (adv, _) in pairs.items()},
                "paths": {ch: path for ch, (_, path) in pairs.items()}}

    out = {"version": 2, "faces": {key: one(code, face) for key, (code, face) in faces.items()}}
    return json.dumps(out, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
