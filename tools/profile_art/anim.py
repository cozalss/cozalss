"""SMIL timing helpers and the motion/layout stylesheet shared by animated art.

All motion is SMIL so it plays inside an <img> (no scripts). It runs once and
settles in under five seconds (WCAG 2.2.2), freezing on the same frame the
static version shows. Moving parts are tagged class="anim"; viewers who ask the
OS for reduced motion get the class="static" stand-ins instead.
"""
from __future__ import annotations

from dataclasses import dataclass

SETTLE_S = 5.0  # every animation must have finished by then
NARROW_PX = 600  # rendered width below which the art switches to its phone layout

STYLE = (
    ".static,.narrow{display:none}"
    "@media (prefers-reduced-motion:reduce){.anim{display:none}.static{display:inline}}"
    f"@media (max-width:{NARROW_PX}px){{.wide{{display:none}}.narrow{{display:inline}}}}"
)


def key_times(times: list[float]) -> str:
    return ";".join(f"{t:.4f}".rstrip("0").rstrip(".") or "0" for t in times)


@dataclass(frozen=True)
class Once:
    """A single run: `begin` and `dur` in seconds, frozen on its last value."""

    begin: float
    dur: float

    def __post_init__(self) -> None:
        if self.begin + self.dur > SETTLE_S:
            raise ValueError(f"animation ends at {self.begin + self.dur:.2f}s, after the {SETTLE_S}s budget")

    def attrs(self) -> dict[str, str]:
        return {"begin": f"{self.begin:g}s", "dur": f"{self.dur:g}s", "fill": "freeze"}


@dataclass(frozen=True)
class Typed:
    timing: Once
    key_times: str
    widths: str  # clip width per step
    caret_x: str  # caret position per step


def type_once(chars: int, char_w: float, x0: float, *, begin: float, step: float = 0.055) -> Typed:
    """Reveal `chars` monospaced characters one by one, then hold."""
    if chars <= 0:
        raise ValueError("nothing to type")
    times = key_times([c / chars for c in range(chars + 1)])
    widths = ";".join(f"{c * char_w:.1f}" for c in range(chars + 1))
    caret = ";".join(f"{x0 + c * char_w + 1:.1f}" for c in range(chars + 1))
    return Typed(Once(begin, chars * step), times, widths, caret)
