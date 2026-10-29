from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snake_a11y  # noqa: E402

SNAKE = '<svg viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg"><style>.c{animation:x 1s infinite}</style></svg>'


def test_rule_goes_right_after_the_root_tag() -> None:
    out = snake_a11y.patch(SNAKE)
    assert out.startswith('<svg viewBox="0 0 10 10" xmlns="http://www.w3.org/2000/svg">' + snake_a11y.RULE)


def test_patch_is_idempotent() -> None:
    once = snake_a11y.patch(SNAKE)
    assert snake_a11y.patch(once) == once


@pytest.mark.parametrize("bad", ["", "not svg at all", "<svg"])
def test_non_svg_input_is_rejected(bad: str) -> None:
    with pytest.raises((ValueError, snake_a11y.ElementTree.ParseError)):
        snake_a11y.patch(bad)


def test_main_patches_files_and_reports_failures(tmp_path: Path) -> None:
    good, bad = tmp_path / "snake.svg", tmp_path / "broken.svg"
    good.write_text(SNAKE, encoding="utf-8")
    bad.write_text("<svg><unclosed></svg>", encoding="utf-8")
    assert snake_a11y.main([str(good)]) == 0
    assert "prefers-reduced-motion" in good.read_text(encoding="utf-8")
    assert snake_a11y.main([str(bad)]) == 1
    assert bad.read_text(encoding="utf-8") == "<svg><unclosed></svg>"  # untouched
    assert snake_a11y.main([str(tmp_path / "missing.svg")]) == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["broken.svg", "snake.svg"]  # no temp files left


def test_a_quoted_angle_bracket_does_not_end_the_root_tag() -> None:
    svg = '<svg xmlns="http://www.w3.org/2000/svg" aria-label="a > b" data-x=\'c>d\'><rect/></svg>'
    root = snake_a11y.ElementTree.fromstring(snake_a11y.patch(svg))
    assert root.get("aria-label") == "a > b" and root.get("data-x") == "c>d"
    assert root[0].tag.endswith("style") and "prefers-reduced-motion" in root[0].text
