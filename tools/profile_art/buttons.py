"""Contact buttons, drawn in-house so the page needs no badge service."""
from __future__ import annotations

from .content import Contact
from .fonts import Face, measure, text
from .icons import symbols, use
from .svg import document, el, join, num
from .theme import Theme

H = 40
MONO = Face("mono", 500, code="m")


def width(contact: Contact) -> float:
    return 16 + 18 + 10 + measure(MONO, contact.label, 13.5) + 18


def render(t: Theme, contact: Contact) -> str:
    acc = t.accent(contact.accent)
    w = round(width(contact))
    body = join([
        el("rect", x="0.75", y="0.75", width=num(w - 1.5), height=num(H - 1.5), rx=num(H / 2 - 1),
           fill=t.surface, stroke=t.border_strong, stroke_width="1.5"),
        use(contact.icon, x=16, y=11, size=18, fill=acc.text),
        text(MONO, contact.label, x=44, y=25, size=13.5, fill=t.text),
    ])
    return document(w, H, body, title=contact.label, desc=contact.alt, defs=symbols({contact.icon}))
