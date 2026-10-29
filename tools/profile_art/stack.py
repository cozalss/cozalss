"""Toolbox panels: icon chips packed inside 400 px panels (same grid as the cards).

Tools proven in shipped work get solid chips; labs and coursework sit below a
"lab & learning" caption with dashed, muted chips, so the panel stays honest.
"""
from __future__ import annotations

from .content import Panel, Tool
from .fonts import Face, measure, text
from .icons import symbols, use
from .layout import Slot, packed, require_fit
from .svg import Fragment, document, el, join, num
from .theme import Theme

W = 400
PAD = 24
TOP = 66
CHIP_H, ROW_PITCH, GAP = 32, 40, 8
CAPTION = "lab & learning"

TITLE = Face("sans", 700, 100, code="t")
MONO = Face("mono", 500, code="m")


def _slots(tools: tuple[Tool, ...], top: float) -> tuple[Slot, ...]:
    widths = [34 + measure(MONO, tool.label, 12) + 12 for tool in tools]
    return packed(widths, left=PAD, right=W - PAD, top=top, gap=GAP, row_pitch=ROW_PITCH)


def _layout(panel: Panel) -> tuple[tuple[Slot, ...], float, tuple[Slot, ...]]:
    main = _slots(panel.tools, TOP)
    caption_y = max(s.y for s in main) + CHIP_H + 28
    learning = _slots(panel.learning, caption_y + 12) if panel.learning else ()
    return main, caption_y, learning


FOOTNOTE_H = 22


def height(panel: Panel) -> int:
    main, _, learning = _layout(panel)
    return int(max(s.y for s in learning or main) + CHIP_H + PAD + (FOOTNOTE_H if panel.footnote else 0))


def _header(t: Theme, panel: Panel) -> Fragment:
    acc = t.accent(panel.accent)
    title_w = measure(TITLE, panel.title, 19)
    subtitle_x = PAD + 30 + title_w
    require_fit(f"panel {panel.slug}: subtitle", measure(MONO, panel.subtitle, 11.5), W - PAD - subtitle_x)
    return join([
        el("circle", cx=str(PAD + 5), cy="35", r="5", fill=acc.solid),
        text(TITLE, panel.title, x=PAD + 18, y=42, size=19, fill=t.text),
        text(MONO, panel.subtitle, x=subtitle_x, y=41, size=11.5, fill=t.text_muted),
    ])


def _chips(t: Theme, tools: tuple[Tool, ...], slots: tuple[Slot, ...], *, icon: str, label: str,
           fill: str, stroke: str, dashed: bool) -> Fragment:
    parts = []
    for tool, slot in zip(tools, slots):
        parts += [
            el("rect", x=num(slot.x), y=num(slot.y), width=num(slot.width), height=str(CHIP_H), rx="10",
               fill=fill, stroke=stroke, stroke_dasharray="4 3" if dashed else None),
            use(tool.icon, x=slot.x + 11, y=slot.y + 8, size=16, fill=icon),
            text(MONO, tool.label, x=slot.x + 34, y=slot.y + 20.5, size=12, fill=label),
        ]
    return join(parts)


def _caption(t: Theme, y: float) -> Fragment:
    width = measure(MONO, CAPTION, 10.5)
    return join([
        text(MONO, CAPTION, x=PAD, y=y, size=10.5, fill=t.text_muted),
        el("path", d=f"M{num(PAD + width + 10)} {num(y - 3.5)} H{W - PAD}", stroke=t.border, stroke_dasharray="4 3"),
    ])


def render(t: Theme, panel: Panel, h: int) -> str:
    acc = t.accent(panel.accent)
    main, caption_y, learning = _layout(panel)
    parts = [
        el("rect", x="0.75", y="0.75", width=num(W - 1.5), height=num(h - 1.5), rx="18", fill=t.surface,
           stroke=t.border, stroke_width="1.5"),
        _header(t, panel),
        _chips(t, panel.tools, main, icon=acc.text, label=t.text_soft, fill=t.surface_alt, stroke=t.border,
               dashed=False),
    ]
    if panel.learning:
        parts += [
            _caption(t, caption_y),
            _chips(t, panel.learning, learning, icon=t.text_muted, label=t.text_muted, fill=t.surface,
                   stroke=t.border_strong, dashed=True),
        ]
    if panel.footnote:  # sits on the panel floor, under however many rows there are
        parts.append(text(MONO, panel.footnote, x=PAD, y=h - PAD + 4, size=10.5, fill=t.text_muted))
    icons = {tool.icon for tool in panel.tools + panel.learning}
    return document(W, h, join(parts), title=f"{panel.title} — {panel.subtitle}", desc=panel.alt,
                    defs=symbols(icons))
