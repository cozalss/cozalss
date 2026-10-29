# Profile toolchain

Everything the profile README shows is built here, and nothing is fetched from a
third-party service when someone views the page.

| Piece | What it does | Runs |
|---|---|---|
| `build.py` + `profile_art/` | Compiles the hero, project cards, toolbox panels and contact buttons (dark + light) into `../assets`, writes `../README.md` and `glyph-atlas.json` | locally, when copy or design changes |
| `telemetry.py` | Renders the Activity and Languages panels from the GitHub GraphQL API (standard library only) | nightly in [`profile.yml`](../.github/workflows/profile.yml) |
| `snake_a11y.py` | Makes the Platane/snk snake honour *prefers-reduced-motion* | nightly, after the snake is drawn |
| `validate_dist.py` | Lets only the six expected, self-contained, script-free SVGs reach the `output` branch | nightly, in render and again in publish |

## Edit and rebuild

All words and numbers inside the artwork live in [`profile_art/content.py`](profile_art/content.py),
and the README's own prose lives in [`profile_art/readme.py`](profile_art/readme.py).
Colours live in [`profile_art/theme.py`](profile_art/theme.py). Never edit `../README.md` by hand.

```sh
cd tools
python -m pip install -r requirements-dev.txt
python build.py           # writes ../assets/*.svg, ../README.md and glyph-atlas.json
python -m pytest          # unit tests; fails below 90% coverage (see pyproject.toml)
```

CI runs `python tools/build.py --check` and fails when a committed file no
longer matches its sources, so always commit the rebuilt files.

## Dependencies

Python packages are locked with hashes, and CI installs wheels only
(`--require-hashes --only-binary :all:`). To change one, edit `requirements.in` or
`requirements-dev.in`, then regenerate both locks from this folder with pip-tools 7.5.3:

```sh
uvx --python 3.12 --from pip-tools==7.5.3 --with "pip<26" --with "click<8.2" \
    pip-compile --generate-hashes --strip-extras requirements.in   # then the same for requirements-dev.in
```

Dependabot proposes these updates monthly, after a seven-day cooldown, and the test job checks them.

## Design rules the build enforces

- **No font dependency.** Text is shaped with HarfBuzz and outlined from Mona Sans and JetBrains Mono (OFL). The fonts come from npm and are verified against the hashes in `fonts.lock.json`. Font files are never committed or served.
- **Copy must fit.** The build stops if a pitch needs too many lines, a word or metric is wider than its column, or a chip row, title, context line or subtitle would run into its neighbour. It never silently clips.
- **One source of truth.** The README is generated from the same content as the artwork, so alt text, links and image widths can't drift.
- **Accessible.** Text and accent colours pass WCAG AA in both themes. Motion plays once, settles within five seconds and is skipped under reduced motion.
- **Phone layout.** Below 600 px rendered width the hero swaps its small print for a large two-line role.
- **Self-contained SVGs.** Every SVG carries a title and description and references nothing outside itself.

Icon sources and licences are listed in [`icons/SOURCES.md`](icons/SOURCES.md).
