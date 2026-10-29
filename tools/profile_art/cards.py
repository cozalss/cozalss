"""Project cards: 400 px wide so two sit side by side on desktop and each
wraps to a full-width card on phones (fixed-width inline images reflow)."""
from __future__ import annotations

from .content import Card
from .fonts import Face, measure, text
from .iso import Box, Iso
from .layout import flow, require_fit, wrap
from .svg import Fragment, document, el, group, join, num, points
from .theme import Theme

W, H = 400, 300
PAD = 24
INNER = W - 2 * PAD
TITLE_X = PAD + 30  # after the cube
TITLE_TAG_GAP = 12  # least clearance between the title and the tag pill

TITLE = Face("sans", 700, 100, code="t")
BODY = Face("sans", 500, 100, code="p")
VALUE = Face("sans", 760, 108, code="v")
MONO = Face("mono", 500, code="m")
MONO_B = Face("mono", 800, code="k")


def _frame(t: Theme, card: Card) -> Fragment:
    acc = t.accent(card.accent)
    defs = el("defs", join([
        el("radialGradient", join([el("stop", offset="0", stop_color=acc.solid, stop_opacity=num(t.glow_opacity * 0.9)),
                                   el("stop", offset="1", stop_color=acc.solid, stop_opacity="0")]),
           id="c-glow", cx="1", cy="0", r="0.9"),
        el("linearGradient", join([el("stop", offset="0", stop_color=acc.solid),
                                   el("stop", offset="1", stop_color=acc.solid, stop_opacity="0")]),
           id="c-bar", x1="0", y1="0", x2="1", y2="0"),
        el("clipPath", el("rect", x="0.75", y="0.75", width=num(W - 1.5), height=num(H - 1.5), rx="18"), id="c-clip"),
    ]))
    return defs + group([
        el("rect", width=str(W), height=str(H), fill=t.surface),
        el("rect", width=str(W), height=str(H), fill="url(#c-glow)"),
        el("rect", width=str(W), height="3", fill="url(#c-bar)"),
    ], clip_path="url(#c-clip)") + el("rect", x="0.75", y="0.75", width=num(W - 1.5), height=num(H - 1.5),
                                       rx="18", stroke=t.border, stroke_width="1.5")


def _cube(t: Theme, accent: str, x: float, y: float) -> Fragment:
    acc = t.accent(accent)
    iso, box = Iso(ox=x, oy=y, a=10), Box(0, 0, 1, 1, 0, 11)
    style = dict(stroke=acc.line, stroke_width="1", stroke_linejoin="round")
    return join([
        el("polygon", points=points(iso.left(box)), fill=t.iso_left, **style),
        el("polygon", points=points(iso.right(box)), fill=t.iso_right, **style),
        el("polygon", points=points(iso.top(box)), fill=acc.solid, **style),
    ])


def _header(t: Theme, card: Card) -> Fragment:
    tag_w = measure(MONO, card.tag, 10.5) + 18
    require_fit(f"{card.slug}: title", measure(TITLE, card.title, 21), W - PAD - tag_w - TITLE_TAG_GAP - TITLE_X)
    return join([
        _cube(t, card.accent, PAD + 10, 37),
        text(TITLE, card.title, x=TITLE_X, y=44, size=21, fill=t.text),
        el("rect", x=num(W - PAD - tag_w), y="27", width=num(tag_w), height="22", rx="11",
           stroke=t.border_strong, fill=t.surface_alt),
        text(MONO, card.tag, x=W - PAD - tag_w / 2, y=42, size=10.5, fill=t.text_muted, anchor="middle"),
    ])


def _context(t: Theme, card: Card) -> Fragment:
    acc = t.accent(card.accent)
    lead = 30 if card.medal else 12
    w = lead + measure(MONO, card.context, 11.5) + 12
    require_fit(f"{card.slug}: context chip", w, INNER)
    parts = [el("rect", x=str(PAD), y="62", width=num(w), height="26", rx="13", fill=acc.tint, stroke=acc.line)]
    if card.medal:
        parts += [
            el("circle", cx=str(PAD + 15), cy="75", r="8.5", fill=acc.solid),
            el("circle", cx=str(PAD + 15), cy="75", r="6", stroke=t.surface, stroke_width="1", opacity="0.55"),
            text(MONO_B, card.medal, x=PAD + 15, y=79, size=11, fill=t.surface, anchor="middle"),
        ]
    parts.append(text(MONO, card.context, x=PAD + lead, y=79.5, size=11.5, fill=acc.text))
    return join(parts)


def _pitch(t: Theme, card: Card) -> Fragment:
    lines = wrap(BODY, card.pitch, 14.5, INNER, max_lines=3)
    return join(text(BODY, line, x=PAD, y=116 + 21 * n, size=14.5, fill=t.text_soft) for n, line in enumerate(lines))


def _metrics(t: Theme, card: Card) -> Fragment:
    col = INNER / 3
    parts = [el("path", d=f"M{PAD} 180 H{W - PAD}", stroke=t.border)]
    for n, metric in enumerate(card.metrics):
        x = PAD + n * col + (14 if n else 0)
        for value, size in ((metric.label, 10.5), (metric.note, 10)):
            if value:
                require_fit(f"{card.slug}: metric {value!r}", measure(MONO, value, size), col - 16)
        if n:
            parts.append(el("path", d=f"M{num(PAD + n * col)} 196 V246", stroke=t.border))
        parts += [
            text(VALUE, metric.value, x=x, y=214, size=24, fill=t.text, tracking=-10),
            text(MONO, metric.label, x=x, y=231, size=10.5, fill=t.text_soft),
        ]
        if metric.note:
            parts.append(text(MONO, metric.note, x=x, y=245, size=10, fill=t.text_muted))
    return join(parts)


def _stack(t: Theme, card: Card) -> Fragment:
    widths = [measure(MONO, s, 10.5) + 18 for s in card.stack]
    slots = flow(widths, left=PAD, right=W - PAD - 30, top=258, gap=6, row_pitch=28)
    if slots[-1].y != 258:
        raise ValueError(f"{card.slug}: stack chips must fit on one row")
    parts = []
    for label, slot in zip(card.stack, slots):
        parts += [
            el("rect", x=num(slot.x), y="258", width=num(slot.width), height="22", rx="6",
               fill=t.surface_alt, stroke=t.border),
            text(MONO, label, x=slot.x + 9, y=273, size=10.5, fill=t.text_soft),
        ]
    ax, ay = W - PAD - 12, 275  # "opens the repo" arrow
    parts.append(el("path", d=f"M{ax} {ay} l11 -11 M{ax + 3} {ay - 11} h8 v8", stroke=t.text_muted,
                    stroke_width="1.6", stroke_linecap="round", stroke_linejoin="round"))
    return join(parts)


def render(t: Theme, card: Card) -> str:
    body = join([_frame(t, card), _header(t, card), _context(t, card), _pitch(t, card), _metrics(t, card),
                 _stack(t, card)])
    return document(W, H, body, title=card.title, desc=card.alt)
