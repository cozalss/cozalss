"""The profile README itself, generated so its alt text, links and image sizes can't drift from the artwork."""
from __future__ import annotations

from html import escape

from . import buttons
from .content import CARDS, CONTACTS, HERO, PANELS, Card, Contact

REPO = "cozalss/cozalss"
RAW = f"https://raw.githubusercontent.com/{REPO}"
GITHUB = f"https://github.com/{REPO}"  # absolute links: relative ones break when the README shows on the profile
CARD_W = 400  # two per row fill GitHub's ~846 px column; phones get one per row

ACTIVITY_ALT = ("Activity over the last 12 months: total contributions, weekly bars, longest and current streak, "
                "share of active days. Refreshed nightly.")
LANGUAGES_ALT = "Language share across public repositories by code size. Refreshed nightly."
SNAKE_ALT = "A snake eating the contribution graph, redrawn every night"


def picture(stem: str, alt: str, width: int | str, *, branch: str = "main", light: str = "-light") -> str:
    """Theme-aware image: GitHub picks the dark or light file from the viewer's colour scheme."""
    dark_src, light_src = f"{RAW}/{branch}/{stem}-dark.svg", f"{RAW}/{branch}/{stem}{light}.svg"
    return ("<picture>"
            f'<source media="(prefers-color-scheme: dark)" srcset="{dark_src}">'
            f'<source media="(prefers-color-scheme: light)" srcset="{light_src}">'
            f'<img alt="{escape(alt)}" src="{dark_src}" width="{width}">'
            "</picture>")


def _card(card: Card) -> str:
    return f'<a href="{card.url}">{picture(f"assets/card-{card.slug}", card.alt, CARD_W)}</a>'


def _contact(contact: Contact) -> str:
    width = round(buttons.width(contact))
    return f'<a href="{contact.url}">{picture(f"assets/contact-{contact.slug}", contact.alt, width)}</a>'


def _pairs(items: list[str]) -> str:
    """Two images per line; the blank line between pairs starts a new row."""
    return "\n\n".join("\n".join(items[i:i + 2]) for i in range(0, len(items), 2))


def render() -> str:
    hero = picture("assets/hero", HERO.alt, "100%")
    cards = _pairs([_card(c) for c in CARDS])
    panels = "\n".join(picture(f"assets/stack-{p.slug}", p.alt, CARD_W) for p in PANELS)
    telemetry = "\n".join((picture("telemetry-activity", ACTIVITY_ALT, CARD_W, branch="output"),
                           picture("telemetry-languages", LANGUAGES_ALT, CARD_W, branch="output")))
    snake = picture("github-snake", SNAKE_ALT, "100%", branch="output", light="")
    contacts = "\n".join(_contact(c) for c in CONTACTS)
    workflow = f"{GITHUB}/actions/workflows/profile.yml"
    return f"""<div align="center">

{hero}

</div>

Hi 👋 I'm **Cem**, a software engineering student who likes owning the whole path: from the agent graph and the React screen to the container they ship in. Most of what I build is **multi-agent AI that has to be right** (law, public-sector paperwork, kids' sports screening) and the **cloud-native plumbing** that keeps it running.

- 🤖 **Building:** multi-agent systems on FastAPI · LangGraph · Qdrant that cite a source or say *unverified*
- ☸️ **Going deep on:** Kubernetes and cloud-native delivery, so `git push` stays the only manual step
- 📐 **Rule I code by:** every external call gets a deterministic fallback, so the demo never dies on stage

<div align="center">

## Selected work

{cards}

Figures come from each project's own README. Try the live demo at **[adalet-agent.vercel.app](https://adalet-agent.vercel.app)**.

## Toolbox

{panels}

## Telemetry

{telemetry}

<details>
<summary><b>🐍 Feed the snake</b>: it eats the contribution graph every night</summary>
<br>

{snake}

</details>

## Reach me

{contacts}

<br>

<details>
<summary>How this page is built</summary>
<br>

This README is a small delivery pipeline, built the way I like to ship things.

**No third-party image services, no web fonts.** Every image is an SVG built and served by this repo; only the status badge comes from GitHub itself.

**Compiled artwork.** [`tools/build.py`]({GITHUB}/tree/main/tools) compiles the art and this page, outlining the text from Mona Sans and JetBrains Mono so it renders the same on every OS.

**Nightly refresh.** [`profile.yml`]({GITHUB}/blob/main/.github/workflows/profile.yml) re-renders the telemetry and the snake each night and publishes them only if they validate. If a step fails, yesterday's panels stay up.

**Locked supply chain.** Actions are pinned to commit SHAs and Python packages to hashes. Only the publish job can write, and it runs no third-party code.

**Accessible motion.** The header animates once and settles within five seconds, and the snake only moves once you open it. Both stand still when your OS asks for reduced motion.

[![profile pipeline]({workflow}/badge.svg)]({workflow})

</details>

</div>
"""
