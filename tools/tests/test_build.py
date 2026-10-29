"""End-to-end build with the pinned fonts (skipped when they cannot be fetched)."""
from __future__ import annotations

import re
import sys
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree
from xml.etree.ElementTree import Element

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build  # noqa: E402
from profile_art import cards, fonts, hero, stack  # noqa: E402
from profile_art.content import CARDS, CONTACTS, HERO, PANELS, Chip  # noqa: E402
from profile_art.layout import wrap  # noqa: E402
from profile_art.theme import DARK  # noqa: E402

SVG = "{http://www.w3.org/2000/svg}"
EXTERNAL = re.compile(r"""(?:href|src)=["'](?!#)|url\((?!#)""")


@pytest.fixture(scope="module")
def pinned_fonts() -> None:
    try:
        fonts.font_files("sans")
        fonts.font_files("mono")
    except (OSError, fonts.FontError) as exc:  # offline: nothing to verify against
        pytest.skip(f"pinned fonts unavailable: {exc}")


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory, pinned_fonts: None) -> list[Path]:
    return build.build(tmp_path_factory.mktemp("root"))


def test_every_target_is_written(built: list[Path]) -> None:
    per_theme = 1 + len(CARDS) + len(PANELS) + len(CONTACTS)
    assert len(built) == 2 + 2 * per_theme  # + glyph atlas + README


def test_svgs_are_self_contained_and_described(built: list[Path]) -> None:
    for path in (p for p in built if p.suffix == ".svg"):
        svg = path.read_text(encoding="utf-8")
        root = ElementTree.fromstring(svg)
        assert root.find(f"{SVG}title").text, path.name
        assert root.find(f"{SVG}desc").text, path.name
        assert not EXTERNAL.search(svg), f"{path.name} references an external resource"
        assert "<text" not in svg, f"{path.name} relies on installed fonts"
        assert len(svg.encode()) <= build.MAX_BYTES


def test_hero_honours_reduced_motion_and_phones(built: list[Path]) -> None:
    hero = next(p for p in built if p.name == "hero-dark.svg").read_text(encoding="utf-8")
    assert "prefers-reduced-motion" in hero and "max-width" in hero
    for cls in ("static", "anim", "wide", "narrow"):
        assert f'class="{cls}"' in hero


SMIL = frozenset({"animate", "animateTransform", "animateMotion", "set"})
URL_REF = re.compile(r"url\(\s*#([^)\s]+)\s*\)")


def _tag(node: Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


def _motion_outside_anim(root: Element) -> list[str]:
    """Describe every SMIL element that would keep running under prefers-reduced-motion.

    CSS can hide elements but cannot pause SMIL, so an animation is only safe when it sits inside a `.anim`
    element, or inside <defs> below an element whose id is used solely by `.anim` elements (a gradient or
    clip path that only a hidden shape paints with).
    """
    parent = {child: node for node in root.iter() for child in node}

    def lineage(node: Element):  # the node itself, then each ancestor up to the root
        while node is not None:
            yield node
            node = parent.get(node)

    def hidden(node: Element) -> bool:
        return any("anim" in (n.get("class") or "").split() for n in lineage(node))

    users: dict[str, list[Element]] = {}  # id -> elements that paint with it or point at it
    for node in root.iter():
        for key, value in node.attrib.items():
            ids = URL_REF.findall(value)
            if key.rsplit("}", 1)[-1] == "href" and value.startswith("#"):
                ids.append(value[1:])
            for ref in ids:
                users.setdefault(ref, []).append(node)

    def only_hidden_users(node: Element) -> bool:
        return any(all(hidden(u) for u in users[n.get("id")]) for n in lineage(node) if n.get("id") in users)

    leaks = []
    for node in root.iter():
        if _tag(node) in SMIL and not hidden(node):
            if not (any(_tag(n) == "defs" for n in lineage(node)) and only_hidden_users(node)):
                path = " > ".join(_tag(n) + (f"#{n.get('id')}" if n.get("id") else "") for n in reversed(list(lineage(node))))
                leaks.append(f"{path}[{node.get('attributeName') or ''}]")
    return leaks


SMIL_BARE = '<rect><animate attributeName="x" values="0;1"/></rect>'
SMIL_GRADIENT = '<defs><linearGradient id="g"><stop><animate attributeName="offset" values="0;1"/></stop></linearGradient></defs>'
SMIL_SYMBOL = '<defs><g id="s"><rect><animate attributeName="x" values="0;1"/></rect></g></defs>'


@pytest.mark.parametrize("markup, leaks", [
    pytest.param(SMIL_BARE, 1, id="bare animation"),
    pytest.param(f'<g class="anim">{SMIL_BARE}</g>', 0, id="inside .anim"),
    pytest.param(f'<g class="wide anim">{SMIL_BARE}</g>', 0, id="one of several classes"),
    pytest.param(f'<g class="static">{SMIL_BARE}</g>', 1, id="inside .static, which stays visible"),
    pytest.param(SMIL_GRADIENT, 1, id="defs nobody paints with are not provably hidden"),
    pytest.param(f'{SMIL_GRADIENT}<rect fill="url(#g)"/>', 1, id="gradient painting a visible rect"),
    pytest.param(f'{SMIL_GRADIENT}<rect class="anim" fill="url(#g)"/>', 0, id="gradient used by .anim rect"),
    pytest.param(f'{SMIL_GRADIENT}<g class="anim"><rect fill="url(#g)"/></g>', 0, id="gradient used below .anim"),
    pytest.param(f'{SMIL_GRADIENT}<rect class="anim" fill="url(#g)"/><rect fill="url(#g)"/>', 1,
                 id="gradient shared with a visible rect"),
    pytest.param(f'{SMIL_GRADIENT}<rect class="anim" style="fill:url(#g)"/>', 0, id="reference through style"),
    pytest.param(f'{SMIL_SYMBOL}<use class="anim" href="#s"/>', 0, id="href to a symbol used by .anim"),
    pytest.param(f'{SMIL_SYMBOL}<use href="#s"/>', 1, id="href to a symbol used by a visible use"),
])
def test_reduced_motion_checker_flags_only_unhidden_motion(markup: str, leaks: int) -> None:
    root = ElementTree.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{markup}</svg>')
    assert len(_motion_outside_anim(root)) == leaks


def test_no_motion_survives_reduced_motion(built: list[Path]) -> None:
    """CSS can hide elements under prefers-reduced-motion but cannot pause SMIL, so every animation must be
    hidden with the `.anim` element it lives in, or with all of the `.anim` elements that use it."""
    for path in (p for p in built if p.suffix == ".svg"):
        leaks = _motion_outside_anim(ElementTree.fromstring(path.read_text(encoding="utf-8")))
        assert not leaks, f"{path.name}: still animates under prefers-reduced-motion: {leaks}"


@pytest.mark.parametrize("theme", ["dark", "light"])
def test_hero_bar_has_a_still_twin_on_the_final_frame(built: list[Path], theme: str) -> None:
    root = ElementTree.fromstring(next(p for p in built if p.name == f"hero-{theme}.svg").read_text(encoding="utf-8"))
    gradients = {g.get("id"): g for g in root.iter(f"{SVG}linearGradient")}
    sweeping, still = gradients["h-bar"], gradients["h-bar-static"]

    def final_frame(gradient: Element) -> list[tuple[float, str | None]]:
        frame = []
        for stop in gradient.iter(f"{SVG}stop"):
            sweep = stop.find(f"{SVG}animate")
            offset = sweep.get("values").split(";")[-1] if sweep is not None else stop.get("offset")  # fill=freeze
            frame.append((float(offset), stop.get("stop-color")))
        return frame

    assert not [n for n in still.iter() if _tag(n) in SMIL], "the still gradient must not move"
    assert final_frame(still) == final_frame(sweeping)
    rects = {r.get("fill"): r for r in root.iter(f"{SVG}rect") if (r.get("fill") or "").startswith("url(#h-bar")}
    assert rects["url(#h-bar)"].get("class") == "anim"
    assert rects["url(#h-bar-static)"].get("class") == "static"
    box = ("x", "y", "width", "height", "clip-path")
    assert [rects["url(#h-bar)"].get(k) for k in box] == [rects["url(#h-bar-static)"].get(k) for k in box]


def _seconds(value: str) -> float:
    return float(value.removesuffix("s"))


def test_all_motion_settles_within_five_seconds(built: list[Path]) -> None:
    """WCAG 2.2.2: nothing may keep moving or blinking for more than five seconds."""
    for path in (p for p in built if p.suffix == ".svg"):
        root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
        for node in root.iter():
            if node.tag.rsplit("}", 1)[-1] not in {"animate", "animateMotion", "animateTransform", "set"}:
                continue
            repeat = node.get("repeatCount", "1")
            assert repeat != "indefinite", f"{path.name}: endless animation"
            end = _seconds(node.get("begin", "0s")) + _seconds(node.get("dur", "0s")) * float(repeat)
            assert end <= 5.0, f"{path.name}: animation ends at {end:.2f}s"
            assert node.get("fill") == "freeze", f"{path.name}: animation does not hold its final frame"


@pytest.mark.usefixtures("pinned_fonts")
def test_wrap_refuses_copy_that_overflows() -> None:
    face = fonts.Face("sans", 500, code="p")
    assert len(wrap(face, "short line", 14, 300, max_lines=1)) == 1
    with pytest.raises(ValueError, match="needs"):
        wrap(face, "word " * 80, 14, 300, max_lines=3)


@pytest.mark.usefixtures("pinned_fonts")
def test_missing_glyphs_fail_loudly() -> None:
    with pytest.raises(fonts.FontError, match="no glyph"):
        fonts.shape(fonts.Face("mono", 500, code="m"), "✓")


CARD = CARDS[1]  # Adalet Agent: no medal, so every card limit can be pushed from the same copy
CROWDED = replace(HERO, chips=HERO.chips + (Chip("one chip too many", "teal"),))  # its row ends near x=761


@pytest.mark.usefixtures("pinned_fonts")
class TestCopyMustFit:
    """Every place where copy meets a limit raises instead of clipping or overlapping silently."""

    def test_wrap_refuses_a_word_wider_than_the_line(self) -> None:
        face = fonts.Face("sans", 500, code="p")
        with pytest.raises(ValueError, match=r"word 'x{40}' needs"):
            wrap(face, "ok " + "x" * 80, 14, 300, max_lines=3)

    def test_wrap_keeps_a_long_word_that_fits_a_line_of_its_own(self) -> None:
        face = fonts.Face("sans", 500, code="p")
        longest = next("x" * n for n in range(1, 200) if fonts.measure(face, "x" * (n + 1), 14) > 300)
        assert wrap(face, f"ok {longest}", 14, 300, max_lines=2) == ("ok", longest)

    def test_a_context_chip_wider_than_the_card_is_refused(self) -> None:
        with pytest.raises(ValueError, match="adalet: context chip needs"):
            cards.render(DARK, replace(CARD, context="x" * 80))

    def test_a_title_that_would_run_into_the_tag_pill_is_refused(self) -> None:
        with pytest.raises(ValueError, match="adalet: title needs"):
            cards.render(DARK, replace(CARD, title="A title far too long to sit beside its tag"))

    def test_a_metric_wider_than_its_column_is_refused(self) -> None:
        wide = replace(CARD.metrics[0], label="a label far wider than a third of the card")
        with pytest.raises(ValueError, match="adalet: metric"):
            cards.render(DARK, replace(CARD, metrics=(wide, *CARD.metrics[1:])))

    def test_a_chip_row_that_would_reach_the_platform_is_refused(self) -> None:
        with pytest.raises(ValueError, match="hero chip row needs"):
            hero.render(DARK, CROWDED)

    @pytest.mark.parametrize("copy, shift, fits", [
        pytest.param(HERO, -60, False, id="platform pulled left under today's chips"),
        pytest.param(CROWDED, 200, True, id="platform pushed right of a longer row"),
    ])
    def test_the_chip_row_limit_follows_the_platform_geometry(self, monkeypatch: pytest.MonkeyPatch, copy, shift: int,
                                                              fits: bool) -> None:
        monkeypatch.setattr(hero, "ISO", replace(hero.ISO, ox=hero.ISO.ox + shift))
        if fits:
            hero.render(DARK, copy)
        else:
            with pytest.raises(ValueError, match="hero chip row needs"):
                hero.render(DARK, copy)

    def test_a_phone_role_line_that_reaches_the_cluster_is_refused(self) -> None:
        with pytest.raises(ValueError, match="phone role line"):
            hero.render(DARK, replace(HERO, role_short=("Software engineer", "x" * 60)))

    def test_a_subtitle_that_overflows_the_panel_is_refused(self) -> None:
        panel = replace(PANELS[0], subtitle="a subtitle that runs well past the right edge of the panel")
        with pytest.raises(ValueError, match="panel build: subtitle needs"):
            stack.render(DARK, panel, stack.height(panel))
