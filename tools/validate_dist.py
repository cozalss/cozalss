"""Gatekeeper for the `output` branch (standard library only).

    python3 tools/validate_dist.py dist          # check a folder before it is published
    python3 tools/validate_dist.py --expected    # print the file names a folder must hold

Passes only if `dist` holds exactly the expected files, each a regular, small,
well-formed SVG with no scripts, event handlers, foreign content, DTDs, CSS
escapes or external references, and the animated snake honours reduced motion.
Render and publish both run it, so nothing a generator (or anything else in the
render job) did can reach the branch unchecked.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree

EXPECTED = frozenset({
    "github-snake.svg",
    "github-snake-dark.svg",
    "telemetry-activity-light.svg",
    "telemetry-activity-dark.svg",
    "telemetry-languages-light.svg",
    "telemetry-languages-dark.svg",
})
ANIMATED = frozenset({"github-snake.svg", "github-snake-dark.svg"})  # must carry the reduced-motion rule
REDUCED_MOTION = "prefers-reduced-motion"
MAX_BYTES = 1_000_000
FORBIDDEN_TAGS = frozenset({"script", "foreignObject", "iframe", "object", "embed"})
ANIMATION_TAGS = frozenset({"animate", "set"})
EXTERNAL = re.compile(r"""^\s*(?!#)\S""")  # any href that is not a same-document fragment
URL_FN = re.compile(r"url\(\s*['\"]?(?!#)", re.IGNORECASE)
RAW_RULES = (  # the parser drops these silently, so they are checked on the raw text
    (re.compile(r"<!DOCTYPE|<!ENTITY", re.IGNORECASE), "DTD or entity declaration"),
    (re.compile(r"<\?(?!xml\s)", re.IGNORECASE), "processing instruction"),
    (re.compile(r"@import", re.IGNORECASE), "CSS @import"),
    (URL_FN, "url() pointing outside the document"),
)


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _css_problems(css: str, where: str) -> list[str]:
    found = []
    if "\\" in css:
        found.append(f"CSS escape in {where}")  # escapes could spell url( or @import past the checks
    if "://" in css:
        found.append(f"URL in {where}")
    return found


def _element_problems(node: ElementTree.Element) -> list[str]:
    tag = _local(node.tag)
    found = [f"forbidden <{tag}>"] if tag in FORBIDDEN_TAGS else []
    if tag == "style":
        found += _css_problems(node.text or "", "<style>")
    for name, value in node.attrib.items():
        attr = _local(name)
        if attr.lower().startswith("on"):
            found.append(f"event handler {attr}=")
        elif attr == "href" and EXTERNAL.match(value):
            found.append(f"external reference {value[:60]!r}")
        elif attr == "style":
            found += _css_problems(value, "style=")
        elif "://" in value:
            found.append(f"URL in {attr}=")
        if tag in ANIMATION_TAGS and attr == "attributeName" and value.rsplit(":", 1)[-1] == "href":
            found.append(f"<{tag}> animates href")
    return found


def problems(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file():
        return ["not a regular file"]
    size = path.stat().st_size
    if not 0 < size <= MAX_BYTES:
        return [f"size {size} outside 1..{MAX_BYTES}"]
    text = path.read_text(encoding="utf-8")
    found = [issue for pattern, issue in RAW_RULES if pattern.search(text)]
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        return found + [f"malformed XML: {exc}"]
    if _local(root.tag) != "svg":
        found.append("root element is not <svg>")
    for node in root.iter():
        found += _element_problems(node)
    styles = "".join(node.text or "" for node in root.iter() if _local(node.tag) == "style")
    if path.name in ANIMATED and REDUCED_MOTION not in styles:
        found.append(f"does not honour {REDUCED_MOTION}")
    return found


def validate(dist: Path) -> list[str]:
    if not dist.is_dir():
        return [f"{dist} is not a directory"]
    names = {p.name for p in dist.iterdir()}
    errors = [f"missing {n}" for n in sorted(EXPECTED - names)]
    errors += [f"unexpected {n}" for n in sorted(names - EXPECTED)]
    for name in sorted(EXPECTED & names):
        errors += [f"{name}: {issue}" for issue in problems(dist / name)]
    return errors


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["--expected"]:
        print("\n".join(sorted(EXPECTED)))
        return 0
    if len(args) != 1 or args[0].startswith("-"):
        print("usage: validate_dist.py DIST | --expected", file=sys.stderr)  # CLI usage text, not logging
        return 2
    errors = validate(Path(args[0]))
    for error in errors:
        print(f"::error::{error}")  # GitHub Actions annotation format
    if not errors:
        print(f"ok: {len(EXPECTED)} files")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
