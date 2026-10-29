"""Render the live Activity and Languages panels (standard library only).

    GITHUB_TOKEN=... python tools/telemetry.py --user cozalss --out dist
    python tools/telemetry.py --fixture payload.json --out preview   # offline

On any failure it exits 1 and leaves the existing SVGs as they were (the one
exception is documented on `write_atomically`), so the workflow keeps publishing
the last good SVGs instead of a broken one.
"""
from __future__ import annotations

import argparse
import http.client
import json
import logging
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

from profile_art.telemetry import (  # noqa: E402
    QUERY,
    PayloadError,
    Snapshot,
    parse,
    render_activity,
    render_languages,
)
from profile_art.theme import THEMES  # noqa: E402

log = logging.getLogger("telemetry")
API = "https://api.github.com/graphql"
ATTEMPTS = 3
TIMEOUT_S = 30


def _is_permanent(exc: BaseException) -> bool:
    """A 4xx other than 429 (bad token, unknown user) will not fix itself, so retrying only delays the failure."""
    return (isinstance(exc, urllib.error.HTTPError) and 400 <= exc.code < 500
            and exc.code != http.HTTPStatus.TOO_MANY_REQUESTS)


def fetch(login: str, token: str) -> dict[str, Any]:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": f"{login}-profile-telemetry",
    })
    for attempt in range(1, ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:  # noqa: S310 - fixed https URL
                return json.loads(response.read())
        # urllib wraps only connect-time errors; resets and truncated bodies escape raw, from urlopen or read()
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
            if attempt == ATTEMPTS or _is_permanent(exc):
                raise
            log.warning("attempt %d failed (%s); retrying", attempt, exc)
            time.sleep(2 ** attempt)
    raise AssertionError("unreachable")


def render_all(snap: Snapshot) -> dict[str, str]:
    files = {}
    for theme in THEMES:
        files[f"telemetry-activity-{theme.name}.svg"] = render_activity(theme, snap)
        files[f"telemetry-languages-{theme.name}.svg"] = render_languages(theme, snap)
    for name, svg in files.items():
        ElementTree.fromstring(svg)  # never publish malformed XML
    return files


def write_atomically(out: Path, files: dict[str, str]) -> None:
    """Stage every file as a temporary sibling, then rename them all into place.

    Guaranteed: if staging fails (disk full, bad path) no file in `out` is touched, and no temporary file is left
    behind on any failure. Each rename is atomic, so a reader sees a whole old or a whole new file.
    Not guaranteed: the set of files is not replaced atomically; if a rename fails part-way, the files renamed
    before it stay replaced.
    """
    out.mkdir(parents=True, exist_ok=True)
    staged: list[tuple[Path, Path]] = []
    try:
        for name, svg in files.items():
            fd, tmp = tempfile.mkstemp(dir=out, suffix=".tmp")
            staged.append((Path(tmp), out / name))
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(svg)
        for tmp, final in staged:
            os.replace(tmp, final)
    finally:
        for tmp, _ in staged:  # never leave partial files behind in the publish dir
            tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "cozalss"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, help="read a saved GraphQL response instead of calling the API")
    parser.add_argument("--today", type=date.fromisoformat, default=datetime.now(timezone.utc).date())
    args = parser.parse_args(argv)

    try:
        if args.fixture:
            payload = json.loads(args.fixture.read_text(encoding="utf-8"))
        else:
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                raise PayloadError("GITHUB_TOKEN is not set")
            payload = fetch(args.user, token)
        files = render_all(parse(payload, args.today))
        write_atomically(args.out, files)
    # URLError/HTTPError are OSErrors; http.client's own errors (IncompleteRead, BadStatusLine) are not
    except (OSError, ValueError, ElementTree.ParseError, http.client.HTTPException) as exc:
        log.error("telemetry not updated, keeping the last good panels: %s", exc)
        return 1
    log.info("wrote %s", ", ".join(sorted(files)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
