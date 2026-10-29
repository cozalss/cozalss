"""Text wrapping, chip flow and the shared "copy must fit" guard, measured with the real font metrics."""
from __future__ import annotations

from dataclasses import dataclass

from .fonts import Face, measure


def require_fit(what: str, needed: float, available: float) -> float:
    """The one guard behind every "copy must fit" rule: returns the spare px, or raises instead of clipping."""
    if not needed <= available:  # written this way so a NaN width fails too
        raise ValueError(f"{what} needs {needed:.1f}px, layout allows {available:.1f}px")
    return available - needed


def wrap(face: Face, value: str, size: float, max_width: float, max_lines: int) -> tuple[str, ...]:
    """Greedy word wrap. Raises if the copy does not fit (too many lines, or a word wider than the line),
    so layouts never clip silently."""
    lines: list[str] = []
    current = ""
    for word in value.split():
        candidate = f"{current} {word}".strip()
        if current and measure(face, candidate, size) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        require_fit(f"word {word[:40]!r}", measure(face, word, size), max_width)  # a word has no break point
        current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        raise ValueError(f"{value[:40]!r}… needs {len(lines)} lines, layout allows {max_lines}")
    return tuple(lines)


@dataclass(frozen=True)
class Slot:
    x: float
    y: float
    width: float


def flow(widths: list[float], *, left: float, right: float, top: float, gap: float,
         row_pitch: float) -> tuple[Slot, ...]:
    """Place boxes left to right, wrapping rows within [left, right]."""
    slots: list[Slot] = []
    x, y = left, top
    for w in widths:
        if x > left and x + w > right:
            x, y = left, y + row_pitch
        slots.append(Slot(x, y, w))
        x += w + gap
    return tuple(slots)


def _pack(widths: list[float], capacity: float, gap: float) -> list[list[int]]:
    """Order-preserving first fit: each row takes the earliest remaining boxes that fit."""
    remaining = list(range(len(widths)))
    rows: list[list[int]] = []
    while remaining:
        row, used = [], 0.0
        for index in list(remaining):
            need = widths[index] + (gap if row else 0)
            if used + need <= capacity or not row:
                row.append(index)
                used += need
                remaining.remove(index)
        rows.append(row)
    return rows


def packed(widths: list[float], *, left: float, right: float, top: float, gap: float,
           row_pitch: float) -> tuple[Slot, ...]:
    """Tightly packed rows; every row but the last is stretched to the full width.

    Returns slots in the original order of `widths`.
    """
    capacity = right - left
    rows = _pack(widths, capacity, gap)
    slots: dict[int, Slot] = {}
    for r, row in enumerate(rows):
        natural = sum(widths[i] for i in row) + gap * (len(row) - 1)
        stretch = (capacity - natural) / len(row) if r < len(rows) - 1 else 0.0
        x = left
        for index in row:
            w = widths[index] + stretch
            slots[index] = Slot(x, top + r * row_pitch, w)
            x += w + gap
    return tuple(slots[i] for i in range(len(widths)))
