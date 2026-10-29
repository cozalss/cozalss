"""Pinned OFL fonts turned into SVG outlines at build time.

No font file is committed or ever requested by a browser. Every string in the
artwork is shaped with HarfBuzz and emitted as <path> geometry, so it renders
identically on every OS, in the GitHub mobile app and behind GitHub's image
proxy. Font packages come from the npm registry and are verified against the
integrity hashes in tools/fonts.lock.json before use. The extracted fonts are cached in a folder named after
the exact pin, and each file is swapped in whole, so a stale or interrupted run is never reused.
"""
from __future__ import annotations

import base64
import hashlib
import http.client
import io
import json
import logging
import os
import re
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

from .svg import Fragment, el, glyph_transform, num

log = logging.getLogger(__name__)

TOOLS_DIR = Path(__file__).resolve().parent.parent
LOCK_FILE = TOOLS_DIR / "fonts.lock.json"
CACHE_DIR = TOOLS_DIR / ".cache" / "fonts"
REGISTRY = "https://registry.npmjs.org"
DOWNLOAD_TIMEOUT_S = 60
DOWNLOAD_ATTEMPTS = 3
RETRY_BACKOFF_S = 1.0  # pause before the second attempt; doubles for each one after


class FontError(RuntimeError):
    pass


@dataclass(frozen=True)
class Face:
    """A family pinned to one point of its variable design space."""

    family: str  # key in fonts.lock.json
    weight: float
    width: float = 100.0  # `wdth` axis; ignored by families without it
    code: str = "f"  # short prefix for glyph ids, unique per Face


@dataclass(frozen=True)
class Shaped:
    face: Face
    glyph_ids: tuple[str, ...]
    offsets: tuple[float, ...]  # pen x per glyph, font units
    advance: float  # font units, tracking included
    upem: int

    def width(self, size: float) -> float:
        return self.advance * size / self.upem


def _lock() -> dict:
    return json.loads(LOCK_FILE.read_text(encoding="utf-8"))


def _verify(data: bytes, integrity: str) -> None:
    algo, _, expected = integrity.partition("-")
    actual = base64.b64encode(hashlib.new(algo, data).digest()).decode()
    if actual != expected:
        raise FontError(f"integrity mismatch: expected {integrity}, got {algo}-{actual}")


def _retryable(exc: Exception) -> bool:
    """Dropped connections, timeouts and 5xx answers may pass; any other HTTP status will not."""
    return not isinstance(exc, urllib.error.HTTPError) or exc.code >= 500


def _fetch(url: str) -> bytes:
    """GET `url`, retrying transient failures a bounded number of times with doubling pauses."""
    attempt = 0
    while True:
        attempt += 1
        log.info("fetching %s", url)
        try:
            with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as response:  # noqa: S310 - fixed https host
                return response.read()
        except (OSError, http.client.HTTPException) as exc:  # HTTPError is an OSError
            if attempt >= DOWNLOAD_ATTEMPTS or not _retryable(exc):
                raise
            pause = RETRY_BACKOFF_S * 2 ** (attempt - 1)
            log.warning("fetch failed (%s); retrying in %gs (attempt %d of %d)", exc, pause, attempt + 1,
                        DOWNLOAD_ATTEMPTS)
            time.sleep(pause)


def _download(package: str, version: str, integrity: str) -> bytes:
    name = package.rsplit("/", 1)[-1]
    data = _fetch(f"{REGISTRY}/{package}/-/{name}-{version}.tgz")
    _verify(data, integrity)  # a complete but wrong body is final: fetching it again would not change it
    return data


def _to_sfnt(woff2: bytes) -> bytes:
    """HarfBuzz reads raw sfnt only, so unwrap WOFF2 once at fetch time."""
    font = TTFont(io.BytesIO(woff2))
    font.flavor = None
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def _cache_folder(spec: dict) -> Path:
    """Named after the exact pin (package, version, first hex digits of its hash), so a bumped version or a
    re-pinned archive never meets files that came from an older one."""
    try:
        digest = base64.b64decode(spec["integrity"].partition("-")[2], validate=True).hex()
        if not digest:
            raise ValueError("empty digest")
    except ValueError as exc:
        raise FontError(f"malformed integrity {spec['integrity']!r} for {spec['package']}") from exc
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{spec['package']}-{spec['version']}").strip("-")
    return CACHE_DIR / f"{slug}-{digest[:12]}"


def _write_atomic(path: Path, data: bytes) -> None:
    """Write beside the target and swap it in, so an interrupted run never leaves a truncated font at `path`."""
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)  # only does anything when the swap did not happen


def _read_member(tar: tarfile.TarFile, spec: dict, name: str) -> bytes:
    """Read one named file of the package; nothing else in the archive is ever extracted."""
    try:
        member = tar.extractfile(f"package/files/{name}")
    except KeyError:  # raised for an unknown name; None means the name is not a regular file
        member = None
    if member is None:
        raise FontError(f"{name} missing from {spec['package']}@{spec['version']}")
    with member:
        return member.read()


def _ensure_files(spec: dict) -> tuple[Path, ...]:
    folder = _cache_folder(spec)  # also rejects a malformed integrity before anything is fetched
    paths = tuple(folder / Path(name).with_suffix(".ttf").name for name in spec["files"])
    if all(p.is_file() for p in paths):  # files reach these paths whole, from an archive that matched the pin
        return paths
    archive = _download(spec["package"], spec["version"], spec["integrity"])  # verified before it is opened
    folder.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        for name, path in zip(spec["files"], paths):
            _write_atomic(path, _to_sfnt(_read_member(tar, spec, name)))  # our own path: no traversal
    return paths


@lru_cache(maxsize=None)
def font_files(family: str) -> tuple[Path, ...]:
    """Return local .ttf paths of a family's files, fetching and verifying once."""
    return _ensure_files(_lock()[family])


@lru_cache(maxsize=None)
def _ttfont(path: Path) -> TTFont:
    return TTFont(path)


@lru_cache(maxsize=None)
def _cmap(path: Path) -> frozenset[int]:
    return frozenset(_ttfont(path).getBestCmap())


def _location(path: Path, face: Face) -> dict[str, float]:
    axes = {a.axisTag for a in _ttfont(path)["fvar"].axes}
    wanted = {"wght": face.weight, "wdth": face.width}
    return {tag: value for tag, value in wanted.items() if tag in axes}


@lru_cache(maxsize=None)
def _hb_font(path: Path, face: Face) -> hb.Font:
    font = hb.Font(hb.Face(hb.Blob(path.read_bytes())))
    upem = _ttfont(path)["head"].unitsPerEm
    font.scale = (upem, upem)
    font.set_variations(_location(path, face))
    return font


@lru_cache(maxsize=None)
def _glyph_set(path: Path, face: Face):  # noqa: ANN202 - fontTools glyph set type
    return _ttfont(path).getGlyphSet(location=_location(path, face))


@lru_cache(maxsize=None)
def _outline(path: Path, face: Face, gid: int) -> str:
    glyph_set = _glyph_set(path, face)
    pen = SVGPathPen(glyph_set, ntos=lambda v: num(round(v, 1)))
    glyph_set[_ttfont(path).getGlyphOrder()[gid]].draw(pen)
    return pen.getCommands()


def _runs(text: str, files: tuple[Path, ...]) -> list[tuple[int, str]]:
    """Split text into runs, each covered by the first file that has its chars."""
    runs: list[tuple[int, str]] = []
    for ch in text:
        index = next((i for i, p in enumerate(files) if ord(ch) in _cmap(p)), None)
        if index is None:
            raise FontError(f"no glyph for {ch!r} (U+{ord(ch):04X}); draw it as a shape")
        if runs and runs[-1][0] == index:
            runs[-1] = (index, runs[-1][1] + ch)
        else:
            runs.append((index, ch))
    return runs


def units_per_em(face: Face) -> int:
    return _ttfont(font_files(face.family)[0])["head"].unitsPerEm


@lru_cache(maxsize=4096)
def shape(face: Face, text: str, tracking: float = 0.0) -> Shaped:
    """Shape `text`; `tracking` is extra space per glyph in 1/1000 em."""
    files = font_files(face.family)
    upem = units_per_em(face)
    extra = tracking * upem / 1000
    ids: list[str] = []
    offsets: list[float] = []
    pen_x = 0.0
    for index, run in _runs(text, files):
        buf = hb.Buffer()
        buf.add_str(run)
        buf.guess_segment_properties()
        hb.shape(_hb_font(files[index], face), buf, {"kern": True, "liga": False, "calt": False})
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            ids.append(f"{face.code}{index}-{info.codepoint}")
            offsets.append(pen_x + pos.x_offset)
            pen_x += pos.x_advance + extra
    advance = pen_x - extra if ids else 0.0
    return Shaped(face, tuple(ids), tuple(offsets), advance, upem)


def measure(face: Face, text: str, size: float, tracking: float = 0.0) -> float:
    return shape(face, text, tracking).width(size)


def glyph(face: Face, char: str) -> tuple[float, str]:
    """(advance in font units, outline path) of a single character."""
    shaped = shape(face, char)
    (_, path), *rest = _glyph_paths(shaped)
    if rest:
        raise FontError(f"{char!r} shapes to more than one glyph")
    return shaped.advance, path


def _glyph_paths(shaped: Shaped) -> frozenset[tuple[str, str]]:
    files = font_files(shaped.face.family)
    out = set()
    for gid_ref in shaped.glyph_ids:
        index, gid = gid_ref[len(shaped.face.code):].split("-")
        out.add((gid_ref, _outline(files[int(index)], shaped.face, int(gid))))
    return frozenset(out)


def text(
    face: Face,
    value: str,
    *,
    x: float,
    y: float,
    size: float,
    fill: str | None = None,
    tracking: float = 0.0,
    anchor: str = "start",
    **extra: object,
) -> Fragment:
    """Outlined text whose baseline starts at (x, y); anchor: start|middle|end."""
    shaped = shape(face, value, tracking)
    shift = {"start": 0.0, "middle": 0.5, "end": 1.0}[anchor] * shaped.width(size)
    scale = size / shaped.upem
    uses = "".join(
        f'<use href="#{gid}" x="{num(off)}"/>' if off else f'<use href="#{gid}"/>'
        for gid, off in zip(shaped.glyph_ids, shaped.offsets)
    )
    body = el("g", uses, transform=glyph_transform(x - shift, y, scale), fill=fill, **extra)
    return Fragment(body.markup, _glyph_paths(shaped))
