"""Live panels (activity + languages) rendered from the GitHub GraphQL API.

Pure functions only: parsing validates the payload and fails loudly; rendering
uses the glyph atlas, so this module (and its CLI) needs nothing beyond the
standard library.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from itertools import accumulate
from operator import attrgetter
from typing import Any, Mapping

from . import atlas
from .svg import Fragment, document, el, join, num
from .theme import Theme

W, H = 400, 300
PAD = 24
INNER = W - 2 * PAD
TOP_LANGUAGES = 5
MIN_SHARE = 0.01  # smaller languages are folded into "Other"
MIN_OTHER_SHARE = 0.0005  # below this "Other" would print as 0.0%, so the row is left out
# Row colours as Theme attribute paths, by row: the top languages in rank order, "Other" takes the next free one.
SWATCHES = ("teal.solid", "plum.solid", "coral.solid", "teal.text", "plum.text", "text_muted")
if len(SWATCHES) < TOP_LANGUAGES + 1:  # fail at import rather than silently drop the last rows
    raise RuntimeError(f"{len(SWATCHES)} swatches cannot colour {TOP_LANGUAGES} languages plus \"Other\"")
NAME_X = PAD + 18  # language names start right of the colour dot
BAR_X, BAR_W = 180, 140
NAME_GAP = 8  # clear space kept between a name and its bar
NAME_MAX_W = BAR_X - NAME_GAP - NAME_X
ELLIPSIS = "…"
ONE_DAY = timedelta(days=1)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")  # locale-proof
# Markup, templates and notebooks inflate byte counts without being "code I write".
IGNORED_LANGUAGES = frozenset({"CSS", "SCSS", "HTML", "Jinja", "Mako", "Jupyter Notebook",
                               "Dockerfile", "Makefile", "Batchfile"})

# Newest-pushed first, so if there are ever more than 100 repos the 100 counted are the most recently active.
QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
    repositories(
      first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC
      orderBy: {field: PUSHED_AT, direction: DESC}
    ) {
      totalCount
      nodes { name languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
    }
  }
}
"""

Shares = tuple[tuple[str, float], ...]


class PayloadError(ValueError):
    pass


@dataclass(frozen=True)
class Activity:
    total: int
    weekly: tuple[int, ...]  # oldest -> newest
    week_starts: tuple[date, ...]
    longest_streak: int
    current_streak: int
    active_days: int
    days: int


@dataclass(frozen=True)
class Snapshot:
    activity: Activity
    languages: Shares  # (name, share), largest first; sums to 1 apart from an "Other" too small to print
    repo_count: int  # repositories whose languages were counted
    repo_total: int  # public repositories owned; more than repo_count when the API list was capped
    generated: date

    @property
    def is_capped(self) -> bool:
        return self.repo_total > self.repo_count


def _need(obj: Any, key: str, kind: type) -> Any:
    value = obj.get(key) if isinstance(obj, Mapping) else None
    # bool is an int subclass, but a JSON true/false is never a count
    if not isinstance(value, kind) or (kind is int and isinstance(value, bool)):
        raise PayloadError(f"unexpected GraphQL payload at {key!r}")
    return value


def _need_count(obj: Any, key: str) -> int:
    value = _need(obj, key, int)
    if value < 0:
        raise PayloadError(f"negative count at {key!r}")
    return value


def _need_date(obj: Any, key: str) -> date:
    text = _need(obj, key, str)
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise PayloadError(f"unexpected GraphQL payload at {key!r}: {text[:32]!r} is not a date") from None


def _streaks(counts: Mapping[date, int], today: date) -> tuple[int, int]:
    """(longest, current) runs of consecutive active days; nothing after `today` counts.

    A date missing from `counts` is an idle day. Today may simply not have a contribution *yet*, so the
    current streak may also end yesterday.
    """
    longest = run = 0
    last: date | None = None
    for day in sorted(d for d, count in counts.items() if count > 0 and d <= today):
        run = run + 1 if last is not None and day - last == ONE_DAY else 1
        longest, last = max(longest, run), day
    return longest, (run if last is not None and today - last <= ONE_DAY else 0)


def _week(week: Any) -> list[tuple[date, int]]:
    days = _need(week, "contributionDays", list)
    if not days:
        raise PayloadError("empty week in the contribution calendar")
    return [(_need_date(day, "date"), _need_count(day, "contributionCount")) for day in days]


def parse_activity(collection: Mapping[str, Any], today: date) -> Activity:
    calendar = _need(collection, "contributionCalendar", Mapping)
    total = _need_count(calendar, "totalContributions")
    weeks = [_week(week) for week in _need(calendar, "weeks", list)]
    if not weeks:
        raise PayloadError("empty contribution calendar")
    days = [day for week in weeks for day in week]
    dates = [when for when, _ in days]
    if any(later <= earlier for earlier, later in zip(dates, dates[1:])):
        raise PayloadError("contribution days are not in chronological order")
    longest, current = _streaks(dict(days), today)
    return Activity(total, tuple(sum(count for _, count in week) for week in weeks),
                    tuple(week[0][0] for week in weeks), longest, current,
                    sum(1 for _, count in days if count), len(days))


def parse_languages(repositories: Mapping[str, Any]) -> tuple[Shares, int, int]:
    """Language shares, plus how many repositories were counted and how many the user owns."""
    sizes: dict[str, int] = {}
    nodes = _need(repositories, "nodes", list)
    for repo in nodes:
        for edge in _need(_need(repo, "languages", Mapping), "edges", list):
            name = _need(_need(edge, "node", Mapping), "name", str)
            size = _need_count(edge, "size")
            if not name:
                raise PayloadError("language with an empty name")
            if name not in IGNORED_LANGUAGES:
                sizes[name] = sizes.get(name, 0) + size
    total = sum(sizes.values())
    if total <= 0:
        raise PayloadError("no language data")
    ranked = sorted(sizes.items(), key=lambda kv: (-kv[1], kv[0]))
    top = [(name, size / total) for name, size in ranked[:TOP_LANGUAGES] if size / total >= MIN_SHARE]
    rest = 1 - sum(share for _, share in top)
    shares = tuple(top + ([("Other", rest)] if rest >= MIN_OTHER_SHARE else []))
    # totalCount can lag the node list; never claim fewer repos than were counted
    return shares, len(nodes), max(_need_count(repositories, "totalCount"), len(nodes))


def parse(payload: Any, today: date) -> Snapshot:
    if not isinstance(payload, Mapping):
        raise PayloadError("GraphQL response is not a JSON object")
    if payload.get("errors"):
        raise PayloadError(f"GraphQL errors: {payload['errors']}")
    user = _need(_need(payload, "data", Mapping), "user", Mapping)
    activity = parse_activity(_need(user, "contributionsCollection", Mapping), today)
    languages, repo_count, repo_total = parse_languages(_need(user, "repositories", Mapping))
    return Snapshot(activity, languages, repo_count, repo_total, today)


# ---------------------------------------------------------------- rendering

def _faces() -> dict[str, atlas.AtlasFace]:
    return atlas.load()


def _fit(face: atlas.AtlasFace, value: str, size: float, max_width: float) -> str:
    """`value`, cut short with an ellipsis if it would be wider than `max_width`."""
    if atlas.measure(face, value, size) <= max_width:
        return value
    room = max_width - atlas.measure(face, ELLIPSIS, size)
    kept = sum(1 for used in accumulate(atlas.measure(face, ch, size) for ch in value) if used <= room)
    return value[:kept].rstrip() + ELLIPSIS


def _frame(t: Theme, title: str, subtitle: str, accent: str, faces: dict[str, atlas.AtlasFace]) -> Fragment:
    acc = t.accent(accent)
    title_w = atlas.measure(faces["title"], title, 19)
    return join([
        el("rect", x="0.75", y="0.75", width=num(W - 1.5), height=num(H - 1.5), rx="18", fill=t.surface,
           stroke=t.border, stroke_width="1.5"),
        el("circle", cx=str(PAD + 5), cy="35", r="5", fill=acc.solid),
        atlas.text(faces["title"], title, x=PAD + 18, y=42, size=19, fill=t.text),
        atlas.text(faces["mono"], subtitle, x=PAD + 30 + title_w, y=41, size=11.5, fill=t.text_muted),
    ])


def _footer(t: Theme, value: str, faces: dict[str, atlas.AtlasFace]) -> Fragment:
    return atlas.text(faces["mono"], value, x=PAD, y=H - 20, size=10, fill=t.text_muted)


def _bars(t: Theme, a: Activity, top: float, height: float) -> Fragment:
    pitch = INNER / len(a.weekly)
    peak = max(a.weekly) or 1
    peak_index = a.weekly.index(max(a.weekly))
    bars = []
    for n, value in enumerate(a.weekly):
        h = max(2.0, value / peak * height)
        fill = t.coral.solid if n == peak_index and value else t.teal.solid
        opacity = 1.0 if value else 0.35
        bars.append(el("rect", x=num(PAD + n * pitch), y=num(top + height - h), width=num(pitch - 1.8),
                       height=num(h), rx="1.2", fill=fill, opacity=num(opacity)))
    return join(bars)


def _months(t: Theme, a: Activity, y: float, faces: dict[str, atlas.AtlasFace]) -> Fragment:
    pitch = INNER / len(a.weekly)
    labels, last_month = [], None
    for n, start in enumerate(a.week_starts):
        if start.month != last_month and start.month % 2 == 1 and n < len(a.week_starts) - 2:
            labels.append(atlas.text(faces["mono"], MONTHS[start.month - 1], x=PAD + n * pitch, y=y, size=9.5,
                                     fill=t.text_muted))
        last_month = start.month
    return join(labels)


def _stat(t: Theme, value: str, label: str, x: float, faces: dict[str, atlas.AtlasFace]) -> Fragment:
    return join([
        atlas.text(faces["value"], value, x=x, y=242, size=22, fill=t.text, tracking=-10),
        atlas.text(faces["mono"], label, x=x, y=259, size=10.5, fill=t.text_soft),
    ])


def render_activity(t: Theme, snap: Snapshot) -> str:
    faces, a = _faces(), snap.activity
    total = f"{a.total:,}"
    total_w = atlas.measure(faces["value"], total, 46, tracking=-14)
    col = INNER / 3
    body = join([
        _frame(t, "Activity", "last 12 months", "teal", faces),
        atlas.text(faces["value"], total, x=PAD - 1, y=104, size=46, fill=t.text, tracking=-14),
        atlas.text(faces["mono"], "contributions", x=PAD + total_w + 16, y=103, size=12, fill=t.text_soft),
        _bars(t, a, top=122, height=56),
        el("path", d=f"M{PAD} 179.5 H{W - PAD}", stroke=t.border),
        _months(t, a, 195, faces),
        el("path", d=f"M{PAD} 208 H{W - PAD}", stroke=t.border),
        _stat(t, f"{a.longest_streak}d", "longest streak", PAD, faces),
        el("path", d=f"M{num(PAD + col)} 222 V262", stroke=t.border),
        _stat(t, f"{a.current_streak}d", "current streak", PAD + col + 14, faces),
        el("path", d=f"M{num(PAD + 2 * col)} 222 V262", stroke=t.border),
        _stat(t, f"{round(100 * a.active_days / a.days)}%", "days active", PAD + 2 * col + 14, faces),
        _footer(t, f"refreshed nightly by GitHub Actions · {snap.generated.isoformat()}", faces),
    ])
    desc = (f"{a.total:,} contributions in the last 12 months; longest streak {a.longest_streak} days, "
            f"current streak {a.current_streak} days, active on {a.active_days} of {a.days} days.")
    return document(W, H, body, title="Activity", desc=desc)


def render_languages(t: Theme, snap: Snapshot) -> str:
    faces = _faces()
    colors = [attrgetter(path)(t) for path in SWATCHES]
    segments, x = [], float(PAD)
    for n, (_, share) in enumerate(snap.languages):  # indexing, not zip: a short palette must fail, not drop rows
        w = share * INNER
        segments.append(el("rect", x=num(x), y="64", width=num(max(w - 2, 1.5)), height="10", rx="3",
                           fill=colors[n]))
        x += w
    top_share = snap.languages[0][1]
    pitch = min(36.0, 168 / len(snap.languages))  # few languages -> airier rows
    rows = []
    for n, (name, share) in enumerate(snap.languages):
        y, color = 112 + n * pitch, colors[n]
        rows += [
            el("circle", cx=str(PAD + 5), cy=num(y - 4), r="4.5", fill=color),
            atlas.text(faces["mono"], _fit(faces["mono"], name, 12, NAME_MAX_W), x=NAME_X, y=y, size=12,
                       fill=t.text_soft),
            el("rect", x=str(BAR_X), y=num(y - 6), width=str(BAR_W), height="4", rx="2", fill=t.surface_alt),
            el("rect", x=str(BAR_X), y=num(y - 6), width=num(max(BAR_W * share / top_share, 2)), height="4",
               rx="2", fill=color),
            atlas.text(faces["mono"], f"{share * 100:.1f}%", x=W - PAD, y=y, size=12, fill=t.text, anchor="end"),
        ]
    if snap.is_capped:  # the API list was capped: say which repos the shares are about
        counted = f"most recent {snap.repo_count} of {snap.repo_total}"
        scope = f"the {snap.repo_count} most recently pushed of {snap.repo_total} public repositories"
    else:
        counted, scope = f"across {snap.repo_count}", "public repositories"
    body = join([
        _frame(t, "Languages", "public repos, by code size", "plum", faces),
        join(segments),
        join(rows),
        _footer(t, f"{counted} public repos · {snap.generated.isoformat()}", faces),
    ])
    desc = f"Language share across {scope}: " + ", ".join(
        f"{name} {share * 100:.1f}%" for name, share in snap.languages) + "."
    return document(W, H, body, title="Languages", desc=desc)
