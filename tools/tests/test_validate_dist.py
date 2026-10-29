from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import validate_dist as vd  # noqa: E402

GOOD = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1">'
        '<style>@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>'
        '<desc>Generated with https://github.com/Platane/snk</desc>'
        '<defs><path id="g" d="M0 0Z"/></defs><use href="#g" fill="url(#grad)"/></svg>')
SVG = '<svg xmlns="http://www.w3.org/2000/svg">'
STILL = "<style>@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>"


def make_dist(tmp_path: Path, overrides: dict[str, str] | None = None) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    for name in vd.EXPECTED:
        (dist / name).write_text(GOOD, encoding="utf-8")
    for name, content in (overrides or {}).items():
        (dist / name).write_text(content, encoding="utf-8")
    return dist


def test_exact_expected_set_passes(tmp_path: Path) -> None:
    assert vd.validate(make_dist(tmp_path)) == []
    assert vd.main([str(tmp_path / "dist")]) == 0


def test_missing_and_unexpected_files_fail(tmp_path: Path) -> None:
    dist = make_dist(tmp_path, {".gitattributes": "* -text"})
    (dist / "github-snake.svg").unlink()
    errors = vd.validate(dist)
    assert "missing github-snake.svg" in errors
    assert "unexpected .gitattributes" in errors


@pytest.mark.parametrize("svg, issue", [
    ('<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>', "forbidden <script>"),
    ('<svg xmlns="http://www.w3.org/2000/svg" onload="x()"/>', "event handler onload="),
    ('<svg xmlns="http://www.w3.org/2000/svg"><foreignObject/></svg>', "forbidden <foreignObject>"),
    ('<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.example/t.png"/></svg>', "external reference"),
    ('<svg xmlns="http://www.w3.org/2000/svg"><rect style="fill:url(https://x.example)"/></svg>', "url() pointing"),
    ("<svg><unclosed></svg>", "malformed XML"),
    ('<html xmlns="http://www.w3.org/1999/xhtml"/>', "root element is not <svg>"),
    (rf'{SVG}{STILL}<style>.a{{fill:u\72l(#x)}}</style></svg>', "CSS escape in <style>"),  # \72 spells "r"
    (rf'{SVG}{STILL}<rect style="fill:u\72l(x)"/></svg>', "CSS escape in style="),
    (f'{SVG}{STILL}<style>@import "https://x.example/a.css";</style></svg>', "CSS @import"),
    (f'{SVG}{STILL}<style>.a{{background:image-set("https://x.example/a.png")}}</style></svg>', "URL in <style>"),
    (f'{SVG}{STILL}<a href="#a"><set attributeName="href" to="https://x.example"/></a></svg>', "URL in to="),
    (f'{SVG}{STILL}<a href="#a"><set attributeName="xlink:href" to="#b"/></a></svg>', "<set> animates href"),
    (f'<!DOCTYPE svg [<!ENTITY e "x">]>{SVG}{STILL}<desc>&e;</desc></svg>', "DTD or entity declaration"),
    (f'<?xml-stylesheet href="https://x.example/a.css"?>{SVG}{STILL}</svg>', "processing instruction"),
    (f"{SVG}<style>.c{{animation:x 1s infinite}}</style></svg>", "does not honour prefers-reduced-motion"),
])
def test_dangerous_or_broken_svgs_fail(tmp_path: Path, svg: str, issue: str) -> None:
    dist = make_dist(tmp_path, {"github-snake.svg": svg})
    assert any(issue in error for error in vd.validate(dist)), vd.validate(dist)


def test_empty_and_oversized_files_fail(tmp_path: Path) -> None:
    dist = make_dist(tmp_path, {"github-snake.svg": "", "github-snake-dark.svg": "x" * (vd.MAX_BYTES + 1)})
    errors = vd.validate(dist)
    assert any("github-snake.svg: size 0" in e for e in errors)
    assert any("github-snake-dark.svg: size" in e for e in errors)


def test_symlinks_are_rejected(tmp_path: Path) -> None:
    dist = make_dist(tmp_path)
    target = dist / "telemetry-activity-dark.svg"
    target.unlink()
    try:
        target.symlink_to(tmp_path / "elsewhere.svg")
    except OSError:
        pytest.skip("symlinks need extra privileges on this platform")
    assert any("not a regular file" in e for e in vd.validate(dist))


def test_cli_usage_and_missing_dir(tmp_path: Path) -> None:
    assert vd.main([]) == 2
    assert vd.main([str(tmp_path / "nope")]) == 1


def test_reduced_motion_rule_is_required_only_for_the_animated_snake(tmp_path: Path) -> None:
    plain = f"{SVG}<rect/></svg>"
    dist = make_dist(tmp_path, {name: plain for name in vd.EXPECTED - vd.ANIMATED})
    assert vd.validate(dist) == []


def test_expected_flag_lists_the_required_names(capsys: pytest.CaptureFixture[str]) -> None:
    assert vd.main(["--expected"]) == 0
    assert capsys.readouterr().out.split() == sorted(vd.EXPECTED)
