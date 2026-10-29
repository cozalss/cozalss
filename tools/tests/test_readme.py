from __future__ import annotations

import re
import sys
from html import escape
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import build  # noqa: E402
import validate_dist  # noqa: E402
from profile_art import buttons, readme  # noqa: E402
from profile_art.content import CARDS, CONTACTS, HERO, PANELS  # noqa: E402

LINK = re.compile(r'(?:href|src|srcset)="([^"]+)"|\]\(([^)]+)\)')


@pytest.fixture()
def page(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(buttons, "width", lambda contact: 100 + len(contact.label))  # no fonts needed
    return readme.render()


def test_every_image_carries_the_alt_text_of_its_source(page: str) -> None:
    alts = [HERO.alt, readme.ACTIVITY_ALT, readme.LANGUAGES_ALT, readme.SNAKE_ALT]
    alts += [c.alt for c in CARDS] + [p.alt for p in PANELS] + [c.alt for c in CONTACTS]
    for alt in alts:
        assert f'alt="{escape(alt)}"' in page


def test_cards_and_contacts_link_to_their_targets(page: str) -> None:
    for item in (*CARDS, *CONTACTS):
        assert f'<a href="{item.url}"><picture>' in page


def test_contact_buttons_use_their_measured_width(page: str) -> None:
    for contact in CONTACTS:
        assert f'contact-{contact.slug}-dark.svg" width="{100 + len(contact.label)}">' in page


def test_every_link_is_absolute(page: str) -> None:
    links = [a or b for a, b in LINK.findall(page)]
    assert links and all(re.match(r"https://|mailto:", link) for link in links), links


def test_images_point_at_files_that_build_or_publish_produces(page: str) -> None:
    built = set(build.targets())
    for branch, path in re.findall(rf"{re.escape(readme.RAW)}/(main|output)/([^\"]+)", page):
        if branch == "main":
            assert path in built, path
        else:
            assert path in validate_dist.EXPECTED, path


def test_cards_sit_two_per_row(page: str) -> None:
    rows = [block for block in page.split("\n\n") if "assets/card-" in block]
    assert [block.count("<a href=") for block in rows] == [2] * (len(CARDS) // 2) + [1] * (len(CARDS) % 2)
