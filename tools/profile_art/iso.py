"""2:1 isometric projection helpers.

Grid axis i runs to the lower right, j to the lower left, k is height in
pixels. A viewer sees three faces of a box: top (max k), left (max j) and
right (max i).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

Point = tuple[float, float]


@dataclass(frozen=True)
class Box:
    i0: float
    j0: float
    i1: float
    j1: float
    k0: float
    k1: float

    @property
    def depth(self) -> float:
        """Painter's-algorithm key: draw smaller values first."""
        return (self.i0 + self.i1 + self.j0 + self.j1) / 2


@dataclass(frozen=True)
class Iso:
    ox: float
    oy: float
    a: float  # half the screen width of one grid tile

    def p(self, i: float, j: float, k: float = 0.0) -> Point:
        return (self.ox + (i - j) * self.a, self.oy + (i + j) * self.a / 2 - k)

    def top(self, b: Box) -> list[Point]:
        return [self.p(b.i0, b.j0, b.k1), self.p(b.i1, b.j0, b.k1),
                self.p(b.i1, b.j1, b.k1), self.p(b.i0, b.j1, b.k1)]

    def left(self, b: Box) -> list[Point]:
        return [self.p(b.i0, b.j1, b.k1), self.p(b.i1, b.j1, b.k1),
                self.p(b.i1, b.j1, b.k0), self.p(b.i0, b.j1, b.k0)]

    def right(self, b: Box) -> list[Point]:
        return [self.p(b.i1, b.j0, b.k1), self.p(b.i1, b.j1, b.k1),
                self.p(b.i1, b.j1, b.k0), self.p(b.i1, b.j0, b.k0)]

    def right_patch(self, i: float, j0: float, j1: float, k0: float, k1: float) -> list[Point]:
        """A rectangle lying on a right-facing face (constant i)."""
        return [self.p(i, j0, k1), self.p(i, j1, k1), self.p(i, j1, k0), self.p(i, j0, k0)]

    def left_patch(self, j: float, i0: float, i1: float, k0: float, k1: float) -> list[Point]:
        """A rectangle lying on a left-facing face (constant j)."""
        return [self.p(i0, j, k1), self.p(i1, j, k1), self.p(i1, j, k0), self.p(i0, j, k0)]

    def polygon_on_top(self, ci: float, cj: float, k: float, r: float, sides: int,
                       phase: float = -math.pi / 2) -> list[Point]:
        """A regular polygon drawn flat on a horizontal plane."""
        return [self.p(ci + r * math.cos(phase + 2 * math.pi * n / sides),
                       cj + r * math.sin(phase + 2 * math.pi * n / sides), k)
                for n in range(sides)]

    def path(self, stops: list[tuple[float, float, float]]) -> str:
        pts = [self.p(i, j, k) for i, j, k in stops]
        head, *rest = pts
        return f"M{head[0]:.1f} {head[1]:.1f}" + "".join(f" L{x:.1f} {y:.1f}" for x, y in rest)
