"""Design tokens. Every asset is rendered once per theme from these values.

Dark is "ink", light is "paper"; the three accents (teal, plum, coral) are the
profile's identity and map to the three things it is about: cloud-native,
AI agents, and product engineering.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Accent:
    solid: str  # strokes, dots, fills
    text: str  # same hue, tuned for legible text on this theme
    tint: str  # chip / tile background
    line: str  # chip / tile border


@dataclass(frozen=True)
class Theme:
    name: str
    bg_top: str
    bg_bottom: str
    surface: str
    surface_alt: str
    border: str
    border_strong: str
    grid: str
    text: str
    text_soft: str
    text_muted: str
    teal: Accent
    plum: Accent
    coral: Accent
    # isometric shading: top / left / right faces of neutral blocks
    iso_top: str
    iso_left: str
    iso_right: str
    glow_opacity: float

    def accent(self, key: str) -> Accent:
        return {"teal": self.teal, "plum": self.plum, "coral": self.coral}[key]


DARK = Theme(
    name="dark",
    bg_top="#0b0f14",
    bg_bottom="#101720",
    surface="#0f161e",
    surface_alt="#131c26",
    border="#1f2a36",
    border_strong="#2b3a49",
    grid="#334455",
    text="#e8edf2",
    text_soft="#a9bccb",
    text_muted="#7d93a6",
    teal=Accent(solid="#2f8fa6", text="#5fb7cc", tint="#12202b", line="#204052"),
    plum=Accent(solid="#a24b78", text="#d387ae", tint="#1d1420", line="#43263a"),
    coral=Accent(solid="#e0563c", text="#f0906c", tint="#20140f", line="#4a2a1e"),
    iso_top="#1a2531",
    iso_left="#111a23",
    iso_right="#151f2a",
    glow_opacity=0.16,
)

LIGHT = Theme(
    name="light",
    bg_top="#f7f3ee",
    bg_bottom="#efe6da",
    surface="#fffcf7",
    surface_alt="#f6efe5",
    border="#e0d3c1",
    border_strong="#cdb99f",
    grid="#b9a88f",
    text="#161616",
    text_soft="#3a3229",
    text_muted="#6b5d4f",
    teal=Accent(solid="#2f8fa6", text="#1c6676", tint="#e2eff1", line="#a7cfd8"),
    plum=Accent(solid="#8e3d66", text="#7a2f56", tint="#f4e6ec", line="#dcb3c6"),
    coral=Accent(solid="#e0563c", text="#ad3f28", tint="#fbe8e1", line="#efbaa9"),
    iso_top="#fbf7f1",
    iso_left="#e6dccd",
    iso_right="#f0e8dc",
    glow_opacity=0.10,
)

THEMES = (DARK, LIGHT)


def _channel(c: int) -> float:
    s = c / 255
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast(fg: str, bg: str) -> float:
    """WCAG 2.x contrast ratio between two #rrggbb colours."""
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
