from __future__ import annotations

import errno
import http.client
import json
import logging
import re
import sys
import urllib.error
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable, NamedTuple
from xml.etree import ElementTree

import pytest

TOOLS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(TOOLS))

import telemetry as cli  # noqa: E402
from profile_art import atlas, telemetry  # noqa: E402
from profile_art.theme import DARK, LIGHT  # noqa: E402

TODAY = date(2026, 10, 29)
SVG = "{http://www.w3.org/2000/svg}"
MONO = atlas.load()["mono"]


def payload(counts: list[int], languages: dict[str, int] | None = None, total: int | None = None, *,
            end: date = TODAY, repos: int = 1, repo_total: int | None = None) -> dict:
    start = end - timedelta(days=len(counts) - 1)
    days = [{"date": (start + timedelta(days=n)).isoformat(), "contributionCount": c} for n, c in enumerate(counts)]
    weeks = [{"contributionDays": days[i:i + 7]} for i in range(0, len(days), 7)]
    langs = languages if languages is not None else {"Python": 600, "TypeScript": 300, "CSS": 5000}
    nodes = [{"name": f"r{n}", "languages": {"edges": [{"size": s, "node": {"name": name}} for name, s in langs.items()]}}
             for n in range(repos)]
    return {"data": {"user": {
        "contributionsCollection": {"contributionCalendar": {
            "totalContributions": sum(counts) if total is None else total, "weeks": weeks}},
        "repositories": {"totalCount": repos if repo_total is None else repo_total, "nodes": nodes},
    }}}


class Run(NamedTuple):
    text: str
    left: float
    right: float
    baseline: float


def mono_runs(svg: str) -> list[Run]:
    """Mono-face text of a panel, decoded back from its glyph markup (spaces have no outline: rebuild them)."""
    runs = []
    for group in ElementTree.fromstring(svg).iter(f"{SVG}g"):
        uses = [(u.get("href", ""), float(u.get("x", "0"))) for u in group.iter(f"{SVG}use")]
        if not uses or not uses[0][0].startswith(f"#{MONO.code}-"):
            continue
        placed = re.match(r"translate\(([-\d.]+) ([-\d.]+)\) scale\(([-\d.e]+) ", group.get("transform", ""))
        left, baseline, scale = (float(v) for v in placed.groups())
        cells = {round(px / MONO.advances[" "]): chr(int(href.rsplit("-", 1)[1], 16)) for href, px in uses}
        text = "".join(cells.get(i, " ") for i in range(max(cells) + 1))
        runs.append(Run(text, left, left + atlas.measure(MONO, text, scale * MONO.upem), baseline))
    return runs


def footer(svg: str) -> Run:
    return max(mono_runs(svg), key=lambda run: run.baseline)


def bar_left(svg: str) -> float:
    return min(float(r.get("x")) for r in ElementTree.fromstring(svg).iter(f"{SVG}rect") if r.get("height") == "4")


class TestStreaks:
    def test_longest_and_current(self) -> None:
        snap = telemetry.parse(payload([1, 1, 0, 1, 1, 1, 0, 2, 3]), TODAY)
        assert snap.activity.longest_streak == 3
        assert snap.activity.current_streak == 2

    def test_today_without_contributions_does_not_break_the_streak(self) -> None:
        snap = telemetry.parse(payload([0, 4, 4, 0]), TODAY)
        assert snap.activity.current_streak == 2

    def test_two_idle_days_end_the_streak(self) -> None:
        snap = telemetry.parse(payload([5, 5, 0, 0]), TODAY)
        assert snap.activity.current_streak == 0
        assert snap.activity.longest_streak == 2

    def test_active_days_and_weekly_totals(self) -> None:
        snap = telemetry.parse(payload([1] * 7 + [0] * 6 + [3]), TODAY)
        assert snap.activity.active_days == 8
        assert snap.activity.days == 14
        assert snap.activity.weekly == (7, 3)

    def test_a_calendar_that_ends_on_an_idle_yesterday_has_no_current_streak(self) -> None:
        stale = payload([1, 1, 1, 0], end=TODAY - timedelta(days=1))  # today is missing, yesterday is idle
        snap = telemetry.parse(stale, TODAY)
        assert snap.activity.current_streak == 0
        assert snap.activity.longest_streak == 3

    def test_a_missing_today_still_counts_a_streak_that_ends_yesterday(self) -> None:
        snap = telemetry.parse(payload([1, 1, 1], end=TODAY - timedelta(days=1)), TODAY)
        assert snap.activity.current_streak == 3

    def test_an_idle_day_after_today_is_ignored(self) -> None:
        snap = telemetry.parse(payload([1, 1, 1, 0], end=TODAY + timedelta(days=1)), TODAY)
        assert snap.activity.current_streak == 3

    def test_contributions_after_today_extend_neither_streak(self) -> None:
        skewed = payload([2, 2, 0, 7, 7, 7], end=TODAY + timedelta(days=3))  # a clock-skewed calendar
        snap = telemetry.parse(skewed, TODAY)
        assert snap.activity.longest_streak == 2
        assert snap.activity.current_streak == 2

    def test_a_date_missing_from_the_calendar_counts_as_idle(self) -> None:
        gappy = payload([1] * 7)
        del gappy["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"][0]["contributionDays"][3]
        snap = telemetry.parse(gappy, TODAY)
        assert snap.activity.longest_streak == 3
        assert snap.activity.current_streak == 3

    def test_a_calendar_entirely_after_today_has_no_streaks(self) -> None:
        snap = telemetry.parse(payload([1, 1, 1], end=TODAY + timedelta(days=10)), TODAY)
        assert (snap.activity.longest_streak, snap.activity.current_streak) == (0, 0)


def remainder_languages(rest: int) -> dict[str, int]:
    """Five languages above the 1% fold plus one worth `rest` bytes of 100,000."""
    head = {"A": 50_000, "B": 25_000, "C": 15_000, "D": 6_000}
    return {**head, "E": 4_000 - rest, "F": rest}


class TestLanguages:
    def test_markup_is_ignored_and_shares_sum_to_one(self) -> None:
        snap = telemetry.parse(payload([1]), TODAY)
        names = [name for name, _ in snap.languages]
        assert "CSS" not in names
        assert names == ["Python", "TypeScript"]
        assert sum(share for _, share in snap.languages) == pytest.approx(1.0)

    def test_tiny_languages_fold_into_other(self) -> None:
        langs = {"Python": 9_800, "Java": 50, "Go": 50, "Rust": 100}
        snap = telemetry.parse(payload([1], langs), TODAY)
        assert [name for name, _ in snap.languages] == ["Python", "Rust", "Other"]
        assert dict(snap.languages)["Other"] == pytest.approx(0.01)

    def test_no_language_data_is_an_error(self) -> None:
        with pytest.raises(telemetry.PayloadError):
            telemetry.parse(payload([1], {"HTML": 10}), TODAY)

    @pytest.mark.parametrize("rest", [0, 10, 40])
    def test_a_remainder_that_would_print_as_zero_adds_no_other_row(self, rest: int) -> None:
        snap = telemetry.parse(payload([1], remainder_languages(rest)), TODAY)
        assert [name for name, _ in snap.languages] == list("ABCDE")
        printed = [run.text for run in mono_runs(telemetry.render_languages(DARK, snap))]
        assert "0.0%" not in printed

    def test_a_remainder_that_prints_as_a_tenth_of_a_percent_is_kept(self) -> None:
        snap = telemetry.parse(payload([1], remainder_languages(60)), TODAY)
        assert [name for name, _ in snap.languages][-1] == "Other"
        printed = [run.text for run in mono_runs(telemetry.render_languages(DARK, snap))]
        assert "0.1%" in printed

    def test_the_other_threshold_is_where_the_printed_share_reaches_a_tenth_of_a_percent(self) -> None:
        assert f"{telemetry.MIN_OTHER_SHARE * 100:.1f}" == "0.1"
        assert f"{telemetry.MIN_OTHER_SHARE * 0.99 * 100:.1f}" == "0.0"

    def test_the_query_counts_the_most_recently_pushed_repositories(self) -> None:
        arguments = re.search(r"repositories\(([^)]*)\)", telemetry.QUERY).group(1)
        assert re.search(r"orderBy:\s*\{\s*field:\s*PUSHED_AT,\s*direction:\s*DESC\s*\}", arguments)

    def test_the_footer_states_the_repos_counted(self) -> None:
        snap = telemetry.parse(payload([1], repos=9), TODAY)
        assert footer(telemetry.render_languages(DARK, snap)).text == "across 9 public repos · 2026-10-29"

    def test_a_capped_repo_list_is_called_out_in_the_footer(self) -> None:
        snap = telemetry.parse(payload([1], repos=100, repo_total=142), TODAY)
        assert snap.repo_count == 100
        assert footer(telemetry.render_languages(DARK, snap)).text == "most recent 100 of 142 public repos · 2026-10-29"
        assert "100 most recently pushed of 142" in telemetry.render_languages(DARK, snap)

    @pytest.mark.parametrize(("repos", "repo_total"), [(9, 9), (100, 142), (100, 10_000_000)])
    def test_the_footer_fits_the_panel(self, repos: int, repo_total: int) -> None:
        snap = telemetry.parse(payload([1], repos=repos, repo_total=repo_total), TODAY)
        assert footer(telemetry.render_languages(DARK, snap)).right <= telemetry.W - telemetry.PAD

    def test_a_total_that_lags_the_node_list_never_reports_fewer_repos_than_counted(self) -> None:
        snap = telemetry.parse(payload([1], repos=3, repo_total=2), TODAY)
        assert (snap.repo_count, snap.repo_total) == (3, 3)

    @pytest.mark.parametrize("theme", [DARK, LIGHT], ids=lambda t: t.name)
    def test_a_long_language_name_stops_short_of_its_bar(self, theme) -> None:
        name = "Common Workflow Language"
        svg = telemetry.render_languages(theme, telemetry.parse(payload([1], {name: 7_000, "Python": 3_000}), TODAY))
        label = next(run for run in mono_runs(svg) if run.text.endswith("…"))
        assert name.startswith(label.text[:-1])
        assert label.right <= bar_left(svg) - 4
        assert f"{name} 70.0%" in svg  # the accessible description keeps the full name

    def test_names_up_to_eighteen_characters_are_shown_whole(self) -> None:
        snap = telemetry.parse(payload([1], {"a" * 18: 6_000, "b" * 19: 4_000}), TODAY)
        shown = {run.text for run in mono_runs(telemetry.render_languages(DARK, snap)) if run.left == pytest.approx(42)}
        assert shown == {"a" * 18, "b" * 17 + "…"}

    @pytest.mark.parametrize("name", ["C#", "F*", "A&B<C>", "Objective-C++"])
    def test_names_with_markup_characters_render_well_formed(self, name: str) -> None:
        snap = telemetry.parse(payload([1], {name: 1_000}), TODAY)
        ElementTree.fromstring(telemetry.render_languages(DARK, snap))

    @pytest.mark.parametrize("theme", [DARK, LIGHT], ids=lambda t: t.name)
    def test_every_possible_row_including_other_gets_its_own_swatch(self, theme) -> None:
        langs = {f"L{n}": 1_000 - n for n in range(telemetry.TOP_LANGUAGES + 3)}
        snap = telemetry.parse(payload([1], langs), TODAY)
        assert len(snap.languages) == telemetry.TOP_LANGUAGES + 1
        assert snap.languages[-1][0] == "Other"
        svg = telemetry.render_languages(theme, snap)
        dots = [c.get("fill") for c in ElementTree.fromstring(svg).iter(f"{SVG}circle") if c.get("r") == "4.5"]
        assert len(dots) == len(snap.languages)
        assert len(set(dots)) == len(dots)


CAL = ("data", "user", "contributionsCollection", "contributionCalendar")
REPOS = ("data", "user", "repositories")
DAY = (*CAL, "weeks", 0, "contributionDays", 0)
EDGE = (*REPOS, "nodes", 0, "languages", "edges", 0)
MISSING = object()


def patched(path: tuple[str | int, ...], value: object) -> dict:
    """A valid two-week payload with the value at `path` replaced (or removed when `value` is MISSING)."""
    broken = payload([1] * 9)
    node: Any = broken
    for step in path[:-1]:
        node = node[step]
    if value is MISSING:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return broken


MALFORMED: dict[str, Any] = {
    "top-level list": [],
    "top-level string": "oops",
    "top-level null": None,
    "top-level number": 42,
    "top-level true": True,
    "data is a list": patched(("data",), []),
    "no weeks": patched((*CAL, "weeks"), []),
    "weeks is not a list": patched((*CAL, "weeks"), {}),
    "week is not an object": patched((*CAL, "weeks", 0), "week"),
    "week without days": patched((*CAL, "weeks", 0, "contributionDays"), MISSING),
    "empty first week": patched((*CAL, "weeks", 0, "contributionDays"), []),
    "empty last week": patched((*CAL, "weeks", 1, "contributionDays"), []),
    "day is not an object": patched(DAY, 7),
    "day without date": patched((*DAY, "date"), MISSING),
    "date is not text": patched((*DAY, "date"), 20261029),
    "date is not a date": patched((*DAY, "date"), "yesterday"),
    "date does not exist": patched((*DAY, "date"), "2026-02-30"),
    "count is boolean": patched((*DAY, "contributionCount"), True),
    "count is fractional": patched((*DAY, "contributionCount"), 1.5),
    "count is negative": patched((*DAY, "contributionCount"), -1),
    "total is negative": patched((*CAL, "totalContributions"), -1),
    "dates repeat": patched((*CAL, "weeks", 0, "contributionDays", 1, "date"), (TODAY - timedelta(days=8)).isoformat()),
    "dates run backwards": patched((*DAY, "date"), TODAY.isoformat()),
    "repo is null": patched((*REPOS, "nodes", 0), None),
    "languages is null": patched((*REPOS, "nodes", 0, "languages"), None),
    "edges is not a list": patched((*REPOS, "nodes", 0, "languages", "edges"), {}),
    "edge without node": patched((*EDGE, "node"), MISSING),
    "language name is not text": patched((*EDGE, "node", "name"), 7),
    "language name is empty": patched((*EDGE, "node", "name"), ""),
    "size is boolean": patched((*EDGE, "size"), True),
    "size is negative": patched((*EDGE, "size"), -5),
    "totalCount is text": patched((*REPOS, "totalCount"), "1"),
    "totalCount is negative": patched((*REPOS, "totalCount"), -1),
}


class TestValidation:
    @pytest.mark.parametrize("broken", [
        {},
        {"errors": [{"message": "rate limited"}]},
        {"data": {"user": None}},
        {"data": {"user": {"contributionsCollection": {}, "repositories": {}}}},
    ])
    def test_malformed_payloads_raise(self, broken: dict) -> None:
        with pytest.raises(telemetry.PayloadError):
            telemetry.parse(broken, TODAY)

    def test_negative_counts_are_rejected(self) -> None:
        with pytest.raises(telemetry.PayloadError):
            telemetry.parse(payload([1, -3]), TODAY)

    def test_wrong_types_are_rejected(self) -> None:
        bad = payload([1, 2])
        bad["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"] = "3"
        with pytest.raises(telemetry.PayloadError):
            telemetry.parse(bad, TODAY)

    @pytest.mark.parametrize("broken", list(MALFORMED.values()), ids=list(MALFORMED))
    def test_every_shape_problem_surfaces_as_a_payload_error(self, broken: Any) -> None:
        with pytest.raises(telemetry.PayloadError):
            telemetry.parse(broken, TODAY)


class TestRendering:
    @pytest.mark.parametrize("theme", [DARK, LIGHT])
    def test_panels_are_well_formed_and_described(self, theme) -> None:
        snap = telemetry.parse(payload([2] * 30 + [0] * 10 + [1] * 324, total=1432), TODAY)
        for svg in (telemetry.render_activity(theme, snap), telemetry.render_languages(theme, snap)):
            root = ElementTree.fromstring(svg)
            assert root.get("viewBox") == "0 0 400 300"
        assert "1,432 contributions" in telemetry.render_activity(theme, snap)
        assert "Python 66.7%" in telemetry.render_languages(theme, snap)


class Response:
    """What urlopen returns: a context manager whose read() yields the body or fails part-way."""

    def __init__(self, body: bytes | BaseException) -> None:
        self.body = body

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        if isinstance(self.body, BaseException):
            raise self.body
        return self.body


class Wire:
    """Scripted urlopen: each call plays the next outcome, an exception to raise or a response to return."""

    def __init__(self, *outcomes: object) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, *_args: object, **_kwargs: object) -> object:
        self.calls += 1
        assert self.outcomes, "fetch tried more often than the test scripted"
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Record the backoff instead of sleeping."""
    waited: list[float] = []
    monkeypatch.setattr(cli.time, "sleep", waited.append)
    return waited


@pytest.fixture
def wire(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Wire]:
    def install(*outcomes: object) -> Wire:
        fake = Wire(*outcomes)
        monkeypatch.setattr(cli.urllib.request, "urlopen", fake)
        return fake

    return install


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://api.github.com/graphql", code, "status", {}, None)  # type: ignore[arg-type]


GOOD = payload([1])
GOOD_BODY = json.dumps(GOOD).encode()
# urlopen only wraps errors raised while connecting; the rest escape raw, from urlopen or from read().
RAISED_BY_URLOPEN: dict[str, Callable[[], BaseException]] = {
    "URLError": lambda: urllib.error.URLError("offline"),
    "TimeoutError": lambda: TimeoutError("timed out"),
    "RemoteDisconnected": lambda: http.client.RemoteDisconnected("closed without a response"),
    "BadStatusLine": lambda: http.client.BadStatusLine(""),
    "HTTP 429": lambda: http_error(429),
    "HTTP 500": lambda: http_error(500),
    "HTTP 502": lambda: http_error(502),
    "HTTP 503": lambda: http_error(503),
    "HTTP 504": lambda: http_error(504),
}
RAISED_BY_READ: dict[str, Callable[[], BaseException]] = {
    "ConnectionResetError": lambda: ConnectionResetError(errno.ECONNRESET, "reset by peer"),
    "RemoteDisconnected": lambda: http.client.RemoteDisconnected("closed without a response"),
    "IncompleteRead": lambda: http.client.IncompleteRead(b"par", 10),
    "BadStatusLine": lambda: http.client.BadStatusLine(""),
    "TimeoutError": lambda: TimeoutError("timed out"),
}


class TestFetch:
    @pytest.mark.parametrize("make", list(RAISED_BY_URLOPEN.values()), ids=list(RAISED_BY_URLOPEN))
    def test_failures_raised_by_urlopen_are_retried(self, make: Callable[[], BaseException], wire, sleeps) -> None:
        fake = wire(make(), Response(GOOD_BODY))
        assert cli.fetch("cozalss", "token") == GOOD
        assert fake.calls == 2
        assert len(sleeps) == 1

    @pytest.mark.parametrize("make", list(RAISED_BY_READ.values()), ids=list(RAISED_BY_READ))
    def test_failures_raised_while_reading_the_response_are_retried(self, make, wire, sleeps) -> None:
        fake = wire(Response(make()), Response(GOOD_BODY))
        assert cli.fetch("cozalss", "token") == GOOD
        assert fake.calls == 2
        assert len(sleeps) == 1

    def test_a_garbled_body_is_retried(self, wire, sleeps) -> None:
        fake = wire(Response(b"<html>502 Bad Gateway</html>"), Response(GOOD_BODY))
        assert cli.fetch("cozalss", "token") == GOOD
        assert fake.calls == 2

    def test_it_gives_up_after_the_bounded_attempts_with_growing_backoff(self, wire, sleeps) -> None:
        fake = wire(*(Response(http.client.IncompleteRead(b"x", 9)) for _ in range(cli.ATTEMPTS)))
        with pytest.raises(http.client.IncompleteRead):
            cli.fetch("cozalss", "token")
        assert fake.calls == cli.ATTEMPTS
        assert len(sleeps) == cli.ATTEMPTS - 1
        assert sleeps == sorted(set(sleeps))

    @pytest.mark.parametrize("code", [400, 401, 403, 404, 422])
    def test_client_errors_other_than_429_are_not_retried(self, code: int, wire, sleeps) -> None:
        fake = wire(http_error(code))
        with pytest.raises(urllib.error.HTTPError) as raised:
            cli.fetch("cozalss", "token")
        assert raised.value.code == code
        assert fake.calls == 1
        assert sleeps == []


class TestWriteAtomically:
    FILES = {"a.svg": "<svg>new a</svg>", "b.svg": "<svg>new b</svg>", "c.svg": "<svg>new c</svg>"}

    @staticmethod
    def seed(out: Path) -> None:
        out.mkdir()
        for name in TestWriteAtomically.FILES:
            (out / name).write_text("old", encoding="utf-8")

    def test_replaces_every_file_and_leaves_no_temporary_files(self, tmp_path: Path) -> None:
        out = tmp_path / "dist"
        self.seed(out)
        cli.write_atomically(out, self.FILES)
        assert {p.name: p.read_text(encoding="utf-8") for p in out.iterdir()} == self.FILES

    def test_creates_missing_directories(self, tmp_path: Path) -> None:
        out = tmp_path / "deep" / "dist"
        cli.write_atomically(out, self.FILES)
        assert sorted(p.name for p in out.iterdir()) == sorted(self.FILES)

    def test_writes_utf8_with_unix_newlines(self, tmp_path: Path) -> None:
        cli.write_atomically(tmp_path, {"a.svg": "one\ntwo ·\n"})
        assert (tmp_path / "a.svg").read_bytes() == "one\ntwo ·\n".encode("utf-8")

    def test_a_failure_while_staging_touches_no_published_file(self, tmp_path: Path,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
        out = tmp_path / "dist"
        self.seed(out)
        real, calls = cli.tempfile.mkstemp, []

        def disk_full_on_the_second_file(*args: Any, **kwargs: Any) -> Any:
            calls.append(1)
            if len(calls) == 2:
                raise OSError(errno.ENOSPC, "No space left on device")
            return real(*args, **kwargs)

        monkeypatch.setattr(cli.tempfile, "mkstemp", disk_full_on_the_second_file)
        with pytest.raises(OSError):
            cli.write_atomically(out, self.FILES)
        assert {p.name: p.read_text(encoding="utf-8") for p in out.iterdir()} == {n: "old" for n in self.FILES}

    def test_a_failure_while_renaming_leaves_no_temporary_files(self, tmp_path: Path,
                                                                monkeypatch: pytest.MonkeyPatch) -> None:
        out = tmp_path / "dist"
        self.seed(out)
        real, calls = cli.os.replace, []

        def locked_on_the_second_file(src: Any, dst: Any) -> None:
            calls.append(1)
            if len(calls) == 2:
                raise PermissionError(errno.EACCES, "file in use")
            real(src, dst)

        monkeypatch.setattr(cli.os, "replace", locked_on_the_second_file)
        with pytest.raises(PermissionError):
            cli.write_atomically(out, self.FILES)
        assert sorted(p.name for p in out.iterdir()) == sorted(self.FILES)  # no *.tmp left behind
        assert (out / "b.svg").read_text(encoding="utf-8") == "old"
        assert (out / "c.svg").read_text(encoding="utf-8") == "old"


class TestCli:
    def test_fixture_run_writes_all_four_panels(self, tmp_path: Path) -> None:
        fixture = tmp_path / "payload.json"
        fixture.write_text(json.dumps(payload([1, 2, 3])), encoding="utf-8")
        out = tmp_path / "dist"
        assert cli.main(["--fixture", str(fixture), "--out", str(out), "--today", "2026-10-29"]) == 0
        assert sorted(p.name for p in out.iterdir()) == [
            "telemetry-activity-dark.svg", "telemetry-activity-light.svg",
            "telemetry-languages-dark.svg", "telemetry-languages-light.svg",
        ]

    def test_failure_keeps_the_last_good_panels(self, tmp_path: Path) -> None:
        out = tmp_path / "dist"
        out.mkdir()
        last_good = out / "telemetry-activity-dark.svg"
        last_good.write_text("<svg>last good</svg>", encoding="utf-8")
        fixture = tmp_path / "payload.json"
        fixture.write_text(json.dumps({"errors": [{"message": "boom"}]}), encoding="utf-8")
        assert cli.main(["--fixture", str(fixture), "--out", str(out)]) == 1
        assert last_good.read_text(encoding="utf-8") == "<svg>last good</svg>"
        assert [p.name for p in out.iterdir()] == ["telemetry-activity-dark.svg"]

    @pytest.mark.parametrize("broken", list(MALFORMED.values()), ids=list(MALFORMED))
    def test_a_malformed_payload_is_reported_and_nothing_is_written(self, broken: Any, tmp_path: Path,
                                                                    caplog: pytest.LogCaptureFixture) -> None:
        out = tmp_path / "dist"
        out.mkdir()
        last_good = out / "telemetry-activity-dark.svg"
        last_good.write_text("<svg>last good</svg>", encoding="utf-8")
        fixture = tmp_path / "payload.json"
        fixture.write_text(json.dumps(broken), encoding="utf-8")

        with caplog.at_level(logging.ERROR, logger="telemetry"):
            code = cli.main(["--fixture", str(fixture), "--out", str(out), "--today", "2026-10-29"])

        assert code == 1
        assert "telemetry not updated, keeping the last good panels" in caplog.text
        assert [p.name for p in out.iterdir()] == [last_good.name]
        assert last_good.read_text(encoding="utf-8") == "<svg>last good</svg>"

    def test_missing_token_fails_without_writing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        out = tmp_path / "dist"
        assert cli.main(["--out", str(out)]) == 1
        assert not out.exists()

    def test_network_errors_are_retried_then_reported(self, tmp_path: Path,
                                                      monkeypatch: pytest.MonkeyPatch) -> None:
        calls = []

        def refuse(*_args: object, **_kwargs: object) -> None:
            calls.append(1)
            raise cli.urllib.error.URLError("offline")

        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        monkeypatch.setattr(cli.urllib.request, "urlopen", refuse)
        monkeypatch.setattr(cli.time, "sleep", lambda _s: None)
        assert cli.main(["--out", str(tmp_path / "dist")]) == 1
        assert len(calls) == cli.ATTEMPTS

    @pytest.mark.parametrize("make", [lambda: http.client.IncompleteRead(b"par", 10), lambda: http.client.BadStatusLine("")],
                             ids=["IncompleteRead", "BadStatusLine"])
    def test_http_client_errors_are_reported_not_raised(self, make, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                        wire, sleeps) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "test-token")
        fake = wire(*(Response(make()) for _ in range(cli.ATTEMPTS)))
        out = tmp_path / "dist"
        assert cli.main(["--out", str(out)]) == 1
        assert fake.calls == cli.ATTEMPTS
        assert not out.exists()

    def test_a_rejected_token_is_reported_without_retrying(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                                                           wire, sleeps) -> None:
        monkeypatch.setenv("GITHUB_TOKEN", "bad-token")
        fake = wire(http_error(401))
        out = tmp_path / "dist"
        assert cli.main(["--out", str(out)]) == 1
        assert fake.calls == 1
        assert not out.exists()
