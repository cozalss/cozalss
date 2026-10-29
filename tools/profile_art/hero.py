"""The header: identity on the left, an isometric cluster running the projects
as pods on the right, a typed motto and the brand gradient bar.

Motion is a one-shot "boot" (git push -> control plane -> pods) that settles in
under five seconds. Below 600 px rendered width the small print is swapped for
a large two-line role so the header stays legible on phones.
"""
from __future__ import annotations

from .anim import STYLE, Once, type_once
from .content import Hero
from .fonts import Face, measure, text
from .iso import Box, Iso
from .layout import require_fit
from .svg import Fragment, document, el, group, join, num, points
from .theme import Theme

W, H = 1000, 340
LEFT = 56
NAME_SIZE = 78
CHIP_GAP = 10

NAME = Face("sans", 800, 112, code="n")
ROLE = Face("sans", 500, 100, code="r")
ROLE_BIG = Face("sans", 640, 104, code="q")
MONO = Face("mono", 500, code="m")
MONO_B = Face("mono", 700, code="b")

ISO = Iso(ox=772, oy=96, a=27)
PLATFORM = Box(0, 0, 6, 6, -12, 0)
CONTROL = Box(1, 1, 3, 3, 0, 58)
PODS = (Box(4.2, 0.8, 5.2, 1.8, 0, 30), Box(4.2, 3.6, 5.2, 4.6, 0, 30), Box(1.0, 4.3, 2.0, 5.3, 0, 30))
GIT = Box(-2.4, 1.4, -1.6, 2.2, 0, 16)
TRACES = (  # control plane -> pod, on the platform surface
    [(3, 1.3, 0), (4.2, 1.3, 0)],
    [(2.6, 3, 0), (2.6, 4.1, 0), (4.2, 4.1, 0)],
    [(1.5, 3, 0), (1.5, 4.3, 0)],
)
GIT_TRACE = [(-1.6, 1.8, 0), (1, 1.8, 0)]

# the boot sequence, in seconds
GIT_PACKET = Once(0.2, 0.7)
CONTROL_FLASH = Once(0.85, 0.45)
POD_PACKETS = (Once(1.1, 0.8), Once(1.35, 0.8), Once(1.6, 0.8))
POD_FLASH_DUR = 0.55
TYPE_BEGIN = 0.5
BAR = Once(0, 4.2)


def _poly(pts: list[tuple[float, float]], **kw: object) -> Fragment:
    return el("polygon", points=points(pts), **kw)


def _animate(attr: str, values: str, once: Once, **kw: object) -> Fragment:
    return el("animate", attributeName=attr, values=values, **once.attrs(), **kw)


def _background(t: Theme) -> Fragment:
    defs = el("defs", join([
        el("linearGradient", join([el("stop", offset="0", stop_color=t.bg_top),
                                   el("stop", offset="1", stop_color=t.bg_bottom)]),
           id="h-bg", x1="0", y1="0", x2=str(W), y2=str(H), gradientUnits="userSpaceOnUse"),
        el("radialGradient", join([el("stop", offset="0", stop_color=t.teal.solid, stop_opacity=num(t.glow_opacity)),
                                   el("stop", offset="1", stop_color=t.teal.solid, stop_opacity="0")]), id="h-glow"),
        el("radialGradient", join([el("stop", offset="0", stop_color=t.plum.solid,
                                      stop_opacity=num(t.glow_opacity * 0.8)),
                                   el("stop", offset="1", stop_color=t.plum.solid, stop_opacity="0")]), id="h-glow2"),
        el("pattern", el("circle", cx="1.2", cy="1.2", r="1.1", fill=t.grid),
           id="h-dots", width="22", height="22", patternUnits="userSpaceOnUse"),
        el("linearGradient", join([el("stop", offset="0", stop_color="#fff", stop_opacity="0"),
                                   el("stop", offset="0.55", stop_color="#fff", stop_opacity="0.55"),
                                   el("stop", offset="1", stop_color="#fff", stop_opacity="0.15")]),
           id="h-fade", x1="0", y1="0", x2="1", y2="0"),
        el("mask", el("rect", width=str(W), height=str(H), fill="url(#h-fade)"), id="h-dotmask"),
        el("clipPath", el("rect", x="0.75", y="0.75", width=str(W - 1.5), height=str(H - 1.5), rx="20"), id="h-card"),
    ]))
    return defs + group([
        el("rect", width=str(W), height=str(H), fill="url(#h-bg)"),
        el("rect", width=str(W), height=str(H), fill="url(#h-dots)", mask="url(#h-dotmask)", opacity="0.5"),
        el("circle", cx="790", cy="160", r="250", fill="url(#h-glow)"),
        el("circle", cx="960", cy="330", r="170", fill="url(#h-glow2)"),
    ], clip_path="url(#h-card)")


def _name(t: Theme, value: str, y: float) -> Fragment:
    """Name filled with a soft vertical gradient (via a mask of its outlines)."""
    width = measure(NAME, value, NAME_SIZE, tracking=-6) + 8
    defs = el("defs", join([
        el("linearGradient", join([el("stop", offset="0", stop_color=t.text),
                                   el("stop", offset="1", stop_color=t.text_soft)]),
           id="h-name", x1="0", y1=num(y - 60), x2="0", y2=num(y + 6), gradientUnits="userSpaceOnUse"),
        el("mask", text(NAME, value, x=LEFT, y=y, size=NAME_SIZE, fill="#fff", tracking=-6), id="h-namemask"),
    ]))
    return defs + el("rect", x=str(LEFT - 4), y=num(y - 78), width=num(width), height="98",
                     fill="url(#h-name)", mask="url(#h-namemask)")


def _platform_left() -> float:
    """Leftmost x of the isometric platform, read off the projection: the chip row must end before it."""
    return min(x for face in (ISO.left, ISO.top, ISO.right) for x, _ in face(PLATFORM))


def _chips(t: Theme, hero: Hero, y: float) -> Fragment:
    parts, x = [], float(LEFT)
    for chip in hero.chips:
        acc = t.accent(chip.accent)
        w = measure(MONO, chip.label, 13) + 40
        parts += [
            el("rect", x=num(x), y=num(y), width=num(w), height="32", rx="16", fill=acc.tint, stroke=acc.line),
            el("circle", cx=num(x + 16), cy=num(y + 16), r="3.5", fill=acc.solid),
            text(MONO, chip.label, x=x + 27, y=y + 20.5, size=13, fill=acc.text),
        ]
        x += w + CHIP_GAP
    require_fit("hero chip row", x - CHIP_GAP - LEFT, _platform_left() - LEFT)
    return join(parts)


def _motto(t: Theme, hero: Hero, y: float) -> Fragment:
    size, x0 = 16.5, LEFT + 20.0
    char_w = measure(MONO, "0", size)
    motto = hero.motto
    plan = type_once(len(motto), char_w, x0, begin=TYPE_BEGIN)
    discrete = dict(calcMode="discrete", keyTimes=plan.key_times, **plan.timing.attrs())
    caret_box = dict(y=num(y - size * 0.82), width=num(char_w * 0.56), height=num(size * 1.02), rx="1",
                     fill=t.teal.text)
    blink = Once(plan.timing.begin + plan.timing.dur, 0.9)
    prompt = el("path", d=f"M{LEFT + 1} {num(y - 11)} l7 6 -7 6", stroke=t.coral.solid,
                stroke_width="2.2", stroke_linecap="round", stroke_linejoin="round")
    clip = el("clipPath", el("rect", el("animate", attributeName="width", values=plan.widths, **discrete),
                             x=num(x0 - 1), y=num(y - size), width="0", height=num(size * 1.4)), id="h-type")
    typed = group([
        # clip on an untransformed wrapper: on the glyph group it would be read in font units
        group([text(MONO, motto, x=x0, y=y, size=size, fill=t.text)], clip_path="url(#h-type)"),
        el("rect", join([
            el("animate", attributeName="x", values=plan.caret_x, **discrete),
            el("animate", attributeName="opacity", values="1;0;1", keyTimes="0;0.5;1", calcMode="discrete",
               repeatCount="2", begin=f"{blink.begin:g}s", dur=f"{blink.dur / 2:g}s", fill="freeze"),
        ]), x=num(x0), **caret_box),
    ], class_="anim")
    still = group([
        text(MONO, motto, x=x0, y=y, size=size, fill=t.text),
        el("rect", x=num(x0 + len(motto) * char_w + 1), **caret_box),
    ], class_="static")
    return el("defs", clip) + prompt + typed + still


def _box(t: Theme, b: Box, *, top: str | None = None, edge: str | None = None) -> Fragment:
    common = dict(stroke=edge or t.border_strong, stroke_width="1", stroke_linejoin="round")
    return join([
        _poly(ISO.left(b), fill=t.iso_left, **common),
        _poly(ISO.right(b), fill=t.iso_right, **common),
        _poly(ISO.top(b), fill=top or t.iso_top, **common),
    ])


def _platform(t: Theme) -> Fragment:
    grid = []
    for n in range(1, 6):
        grid.append(el("path", d=ISO.path([(n, 0, 0), (n, 6, 0)])))
        grid.append(el("path", d=ISO.path([(0, n, 0), (6, n, 0)])))
    return join([
        _box(t, PLATFORM, top=t.surface_alt),
        group(grid, stroke=t.border, stroke_width="1", opacity="0.9"),
        _poly(ISO.top(PLATFORM), fill="none", stroke=t.teal.line, stroke_width="1.2"),
    ])


def _traces(t: Theme) -> Fragment:
    return group([el("path", d=ISO.path(GIT_TRACE), stroke_dasharray="3 5")]
                 + [el("path", d=ISO.path(tr)) for tr in TRACES],
                 stroke=t.border_strong, stroke_width="2", stroke_linecap="round", fill="none")


def _packet(t: Theme, accent: str, path: str, once: Once) -> Fragment:
    acc = t.accent(accent)
    return group([
        el("circle", r="7", fill=acc.solid, opacity="0.28"),
        el("circle", r="3.2", fill=acc.text),
        el("animateMotion", path=path, calcMode="linear", **once.attrs()),
        _animate("opacity", "0;1;1;0", once, keyTimes="0;0.15;0.85;1"),
    ], class_="anim", opacity="0")


def _flash(pts: list[tuple[float, float]], color: str, once: Once, peak: float) -> Fragment:
    return el("polygon", _animate("opacity", f"0;{peak};0", once), points=points(pts), fill=color, opacity="0",
              class_="anim")


def _control_plane(t: Theme) -> Fragment:
    b = CONTROL
    ci, cj = (b.i0 + b.i1) / 2, (b.j0 + b.j1) / 2
    wheel = ISO.polygon_on_top(ci, cj, b.k1, 0.62, 7)  # the Kubernetes helm, flat on the roof
    hub = ISO.polygon_on_top(ci, cj, b.k1, 0.2, 7)
    spokes = [el("path", d=f"M{num(hx)} {num(hy)} L{num(wx)} {num(wy)}") for (hx, hy), (wx, wy) in zip(hub, wheel)]
    leds = [ISO.right_patch(b.i1, b.j0 + 0.25 + 0.42 * n, b.j0 + 0.55 + 0.42 * n, 38, 44) for n in range(4)]
    vents = [el("path", d=ISO.path([(b.i0 + 0.25, b.j1, k), (b.i1 - 0.25, b.j1, k)])) for k in (14, 22, 30)]
    blinks = [el("polygon", el("animate", attributeName="opacity", values="0;0.7;0", begin=f"{0.3 + 0.2 * n:g}s",
                               dur="1.1s", repeatCount="3", fill="freeze"),
                 points=points(p), fill=t.surface, opacity="0", class_="anim") for n, p in enumerate(leds)]
    return join([
        _box(t, b),
        group(vents, stroke=t.border_strong, stroke_width="1.4", stroke_linecap="round"),
        _poly(wheel, fill=t.teal.tint, stroke=t.teal.solid, stroke_width="1.6", stroke_linejoin="round"),
        group(spokes, stroke=t.teal.solid, stroke_width="1.3"),
        _poly(hub, fill=t.teal.solid),
        _flash(wheel, t.teal.text, CONTROL_FLASH, 0.55),
        group([_poly(p, fill=t.teal.text, opacity="0.85") for p in leds]),
        join(blinks),
    ])


def _pod(t: Theme, b: Box, accent: str, packet: Once) -> Fragment:
    acc = t.accent(accent)
    led = ISO.right_patch(b.i1, b.j0 + 0.3, b.j1 - 0.3, 17, 21)
    inner = ISO.top(Box(b.i0 + 0.22, b.j0 + 0.22, b.i1 - 0.22, b.j1 - 0.22, b.k0, b.k1))
    arrival = Once(packet.begin + packet.dur, POD_FLASH_DUR)
    return join([
        _box(t, b, top=acc.tint, edge=acc.line),
        _poly(ISO.top(b), fill="none", stroke=acc.solid, stroke_width="1.4", stroke_linejoin="round"),
        _poly(inner, fill=acc.solid, opacity="0.9"),
        _flash(inner, acc.text, arrival, 0.9),
        _poly(led, fill=acc.text),
    ])


def _labels(t: Theme, hero: Hero) -> Fragment:
    anchors = (  # (pod face point, label origin) chosen to sit off the platform
        (ISO.p(5.2, 1.3, 22), (884.0, 116.0)),
        (ISO.p(5.2, 4.1, 14), (856.0, 236.0)),
        (ISO.p(1.5, 5.3, 12), (636.0, 252.0)),
    )
    parts = []
    for pod, ((px, py), (lx, ly)) in zip(hero.pods, anchors):
        acc = t.accent(pod.accent)
        parts += [
            el("path", d=f"M{num(px)} {num(py)} L{num(lx - 6)} {num(ly - 4)}", stroke=t.border_strong,
               stroke_width="1", stroke_dasharray="2 3"),
            el("circle", cx=num(lx), cy=num(ly - 4.5), r="3.2", fill=acc.solid),
            text(MONO, pod.name, x=lx + 8, y=ly, size=13, fill=t.text_soft),
        ]
    gx, gy = ISO.p(-2.0, 1.4, 16)
    parts.append(text(MONO, "git push", x=gx, y=gy - 14, size=12.5, fill=t.text_muted, anchor="middle"))
    status_w = measure(MONO, hero.status, 12.5)
    parts += [
        el("circle", cx=num(ISO.ox - status_w / 2 - 8), cy=num(304 - 4.5), r="3.2", fill=t.teal.solid),
        text(MONO, hero.status, x=ISO.ox + 4, y=304, size=12.5, fill=t.text_muted, anchor="middle"),
    ]
    return join(parts)


def _bar_gradient(t: Theme, gid: str, *, sweep: bool) -> Fragment:
    """The brand gradient. The sweeping copy moves its two inner stops once and settles back on the layout
    the still copy shows, so reduced-motion viewers get the very frame the animation freezes on."""
    def stop(offset: str, color: str, values: str = "") -> Fragment:
        return el("stop", _animate("offset", values, BAR) if sweep and values else None,
                  offset=offset, stop_color=color)

    return el("linearGradient", join([
        stop("0", t.teal.solid, "0;0.25;0"),
        stop("0.5", t.plum.solid, "0.5;0.75;0.5"),
        stop("1", t.coral.solid),
    ]), id=gid, x1="0", y1="0", x2=str(W), y2="0", gradientUnits="userSpaceOnUse")


def _bar(t: Theme) -> Fragment:
    """CSS cannot stop SMIL, so the sweeping bar and its still twin are separate shapes: reduced motion hides
    the .anim one, and the animated gradient in <defs> goes unpainted with it."""
    def strip(gid: str, class_: str) -> Fragment:
        return el("rect", x="0", y=str(H - 7), width=str(W), height="7", fill=f"url(#{gid})",
                  clip_path="url(#h-card)", class_=class_)

    defs = el("defs", join([_bar_gradient(t, "h-bar", sweep=True), _bar_gradient(t, "h-bar-static", sweep=False)]))
    return defs + strip("h-bar", "anim") + strip("h-bar-static", "static")


def _cluster(t: Theme, hero: Hero) -> Fragment:
    gx, gy = ISO.p(-2, 1.8)
    pods = sorted(zip(PODS, hero.pods, POD_PACKETS), key=lambda item: item[0].depth)
    return join([
        _platform(t),
        _traces(t),
        el("ellipse", cx=num(gx), cy=num(gy + 10), rx="22", ry="7", fill=t.grid, opacity="0.25"),
        _box(t, GIT, top=t.teal.tint, edge=t.teal.line),
        _packet(t, "teal", ISO.path(GIT_TRACE), GIT_PACKET),  # drawn before the control plane: it hides it
        _control_plane(t),
        join(_packet(t, pod.accent, ISO.path(tr), once) for pod, tr, once in zip(hero.pods, TRACES, POD_PACKETS)),
        join(_pod(t, b, pod.accent, once) for b, pod, once in pods),
    ])


PHONE_TEXT_MAX_W = 520  # must stay clear of the cluster, which starts near x=600


def _phone_role(t: Theme, hero: Hero) -> Fragment:
    first, second = hero.role_short
    for line in hero.role_short:
        require_fit(f"phone role line {line!r}", measure(ROLE_BIG, line, 40), PHONE_TEXT_MAX_W)
    return join([
        text(ROLE_BIG, first, x=LEFT, y=218, size=40, fill=t.text_soft),
        text(ROLE_BIG, second, x=LEFT, y=270, size=40, fill=t.teal.text),
    ])


def render(t: Theme, hero: Hero) -> str:
    wide = group([
        text(MONO_B, "$", x=LEFT, y=78, size=15, fill=t.teal.text),
        text(MONO, hero.kicker, x=LEFT + 17, y=78, size=15, fill=t.text_muted),
        text(ROLE, hero.role, x=LEFT, y=193, size=21, fill=t.text_soft),
        _motto(t, hero, 238),
        _chips(t, hero, 266),
        _labels(t, hero),
    ], class_="wide")
    body = join([
        _background(t),
        el("rect", x="0.75", y="0.75", width=str(W - 1.5), height=str(H - 1.5), rx="20", stroke=t.border,
           stroke_width="1.5"),
        _name(t, hero.name, 154),
        _cluster(t, hero),
        wide,
        group([_phone_role(t, hero)], class_="narrow"),
        _bar(t),
    ])
    return document(W, H, body, title=hero.name, desc=hero.alt, style=STYLE)
