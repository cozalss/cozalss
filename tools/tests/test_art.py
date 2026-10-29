"""Font-free unit tests for the artwork toolkit (layout, tokens, SVG assembly, atlas, font download and cache)."""
from __future__ import annotations

import base64
import hashlib
import http.client
import io
import json
import os
import sys
import tarfile
import urllib.error
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from profile_art import anim, atlas, fonts, layout  # noqa: E402
from profile_art.layout import _pack, flow, packed  # noqa: E402
from profile_art.svg import Fragment, attrs, document, glyph_transform, num  # noqa: E402
from profile_art.theme import THEMES, contrast  # noqa: E402

AA = 4.5


@pytest.mark.parametrize("theme", THEMES, ids=lambda t: t.name)
def test_every_text_token_meets_wcag_aa(theme) -> None:
    surfaces = (theme.bg_top, theme.bg_bottom, theme.surface, theme.surface_alt)
    texts = [theme.text, theme.text_soft, theme.text_muted] + [theme.accent(a).text for a in ("teal", "plum", "coral")]
    for fg in texts:
        for bg in surfaces:
            assert contrast(fg, bg) >= AA, f"{theme.name}: {fg} on {bg}"
    for key in ("teal", "plum", "coral"):
        acc = theme.accent(key)
        assert contrast(acc.text, acc.tint) >= AA, f"{theme.name}: {key} chip text"


def test_contrast_reference_values() -> None:
    assert contrast("#000000", "#ffffff") == pytest.approx(21.0)
    assert contrast("#777777", "#777777") == pytest.approx(1.0)


def test_num_is_compact() -> None:
    assert [num(1.0), num(1.25), num(-0.001), num(3.14159)] == ["1", "1.25", "0", "3.14"]


@pytest.mark.parametrize("size", [10.5, 12.5, 13, 14.5, 16.5, 21, 78])
def test_glyph_scale_keeps_the_exact_font_size(size: float) -> None:
    """Regression: a 2-decimal scale rendered 16.5 px text at 20 px and clipped it."""
    transform = glyph_transform(0, 0, size / 1000)
    scale = float(transform.split("scale(")[1].split()[0])
    assert scale * 1000 == pytest.approx(size, abs=1e-6)


def test_attrs_maps_python_names_and_skips_none() -> None:
    assert attrs(stroke_width="2", class_="anim", fill=None) == ' stroke-width="2" class="anim"'


def test_document_rejects_glyph_id_collisions() -> None:
    body = Fragment("", frozenset({("g1", "M0 0Z"), ("g1", "M1 1Z")}))
    with pytest.raises(ValueError, match="collision"):
        document(10, 10, body, title="t", desc="d")


def test_document_emits_each_glyph_once() -> None:
    a = Fragment('<use href="#g1"/>', frozenset({("g1", "M0 0Z")}))
    svg = document(10, 10, a + a, title="t", desc="d")
    assert svg.count('id="g1"') == 1


class TestLayout:
    def test_flow_wraps_when_the_row_is_full(self) -> None:
        slots = flow([60, 60, 60], left=0, right=130, top=10, gap=5, row_pitch=20)
        assert [(s.x, s.y) for s in slots] == [(0, 10), (65, 10), (0, 30)]

    def test_pack_is_order_preserving_first_fit(self) -> None:
        assert _pack([70, 70, 20, 20], capacity=100, gap=0) == [[0, 2], [1, 3]]

    def test_packed_rows_are_justified_except_the_last(self) -> None:
        slots = packed([40, 40, 40], left=0, right=100, top=0, gap=10, row_pitch=30)
        first_row = [s for s in slots if s.y == 0]
        assert first_row[-1].x + first_row[-1].width == pytest.approx(100)
        assert slots[2].width == 40  # last row keeps its natural width


class TestFitGuard:
    def test_it_returns_the_spare_room(self) -> None:
        assert layout.require_fit("chip", 90, 100) == 10
        assert layout.require_fit("chip", 100, 100) == 0  # exactly full still fits

    def test_it_names_the_element_and_both_widths(self) -> None:
        with pytest.raises(ValueError, match=r"yetenek: context chip needs 355\.2px, layout allows 352\.0px"):
            layout.require_fit("yetenek: context chip", 355.2, 352)

    def test_it_never_waves_a_nan_width_through(self) -> None:
        with pytest.raises(ValueError):
            layout.require_fit("chip", float("nan"), 100)


class TestMotion:
    def test_type_once_reveals_one_char_per_step_and_holds(self) -> None:
        plan = anim.type_once(3, char_w=10, x0=100, begin=0.5, step=0.1)
        assert plan.widths == "0.0;10.0;20.0;30.0"
        assert plan.caret_x == "101.0;111.0;121.0;131.0"
        assert plan.key_times == "0;0.3333;0.6667;1"
        assert plan.timing.attrs() == {"begin": "0.5s", "dur": "0.3s", "fill": "freeze"}

    def test_type_once_rejects_empty_text(self) -> None:
        with pytest.raises(ValueError):
            anim.type_once(0, char_w=10, x0=0, begin=0)

    def test_motion_must_settle_within_the_budget(self) -> None:
        anim.Once(4.0, 1.0)
        with pytest.raises(ValueError, match="budget"):
            anim.Once(4.5, 1.0)

    def test_style_hides_motion_and_small_print_on_request(self) -> None:
        assert "prefers-reduced-motion:reduce" in anim.STYLE
        assert f"max-width:{anim.NARROW_PX}px" in anim.STYLE
        # the phone rule must come last so it wins over the reduced-motion reveal
        assert anim.STYLE.index("max-width") > anim.STYLE.index("prefers-reduced-motion")


def test_atlas_roundtrip_without_fonts(tmp_path: Path) -> None:
    def fake_glyph(_face: object, ch: str) -> tuple[float, str]:
        return 600.0, "" if ch == " " else "M0 0L100 0L100 100Z"

    raw = atlas.export({"mono": ("am", object())}, fake_glyph, lambda _face: 1000, chars="ab ")
    path = tmp_path / "atlas.json"
    path.write_text(raw, encoding="utf-8")
    face = atlas.load(path)["mono"]
    assert atlas.measure(face, "ab a", 10) == pytest.approx(24.0)
    fragment = atlas.text(face, "a b", x=0, y=0, size=10)
    assert {gid for gid, _ in fragment.glyphs} == {"am-61", "am-62"}  # the space has no outline
    with pytest.raises(ValueError, match="lacks"):
        atlas.measure(face, "z", 10)
    assert json.loads(raw)["faces"]["mono"]["code"] == "am"


def test_atlas_scales_by_each_faces_units_per_em(tmp_path: Path) -> None:
    def big_glyph(_face: object, _ch: str) -> tuple[float, str]:
        return 1200.0, "M0 0L200 0L200 200Z"  # the same 0.6 em advance in a 2000-unit font

    path = tmp_path / "atlas.json"
    path.write_text(atlas.export({"mono": ("am", object())}, big_glyph, lambda _face: 2000, chars="a"), encoding="utf-8")
    face = atlas.load(path)["mono"]
    assert atlas.measure(face, "aa", 10) == pytest.approx(12.0)
    assert "scale(0.005 -0.005)" in atlas.text(face, "a", x=0, y=0, size=10).markup


# --- pinned-font download and cache ------------------------------------------------------------------------------


class BodyFails:
    """A response that connects fine and then dies while its body is read."""

    def __init__(self, error: BaseException) -> None:
        self.error = error


class FakeNpm:
    """Stands in for urllib.request.urlopen (it is its own response). Each request consumes one `script` step,
    an exception to raise or a BodyFails; once the script runs out it serves the published `archive`."""

    def __init__(self) -> None:
        self.script: list[object] = []
        self.requests: list[str] = []
        self.sleeps: list[float] = []
        self.archive = b""
        self.spec: dict = {}
        self._body_error: BaseException | None = None

    def publish(self, files: dict[str, bytes], wanted: list[str] | None = None) -> None:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name, data in files.items():
                info = tarfile.TarInfo(f"package/files/{name}")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        self.archive = buf.getvalue()
        self.spec = {"package": "@scope/demo", "version": "1.0.0", "integrity": integrity_of(self.archive),
                     "files": list(files if wanted is None else wanted)}

    def __call__(self, url: str, timeout: float | None = None) -> "FakeNpm":
        self.requests.append(url)
        step = self.script.pop(0) if self.script else None
        if isinstance(step, BaseException):
            raise step
        self._body_error = step.error if isinstance(step, BodyFails) else None
        return self

    def __enter__(self) -> "FakeNpm":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self) -> bytes:
        if self._body_error is not None:
            raise self._body_error
        return self.archive


def integrity_of(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode()


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://registry.example/x.tgz", code, "status", {}, io.BytesIO())  # type: ignore[arg-type]


@pytest.fixture
def npm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A fake npm registry, no real sleeping, an empty font cache and a one-family lock file."""
    fake = FakeNpm()
    monkeypatch.setattr(fonts.urllib.request, "urlopen", fake)
    monkeypatch.setattr(fonts.time, "sleep", fake.sleeps.append)
    monkeypatch.setattr(fonts, "CACHE_DIR", tmp_path / "fonts")
    monkeypatch.setattr(fonts, "_lock", lambda: {"demo": fake.spec})
    monkeypatch.setattr(fonts, "_to_sfnt", lambda data: b"sfnt:" + data)  # real conversion needs a real WOFF2
    fonts.font_files.cache_clear()  # font_files is memoised per family: keep fake fonts out of the real cache
    yield fake
    fonts.font_files.cache_clear()


def download(npm: FakeNpm) -> bytes:
    spec = npm.spec
    return fonts._download(spec["package"], spec["version"], spec["integrity"])


class TestDownloadRetry:
    def test_transient_failures_are_retried_with_growing_pauses(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"A"})
        npm.script = [urllib.error.URLError("temporary DNS failure"), ConnectionResetError()]
        assert download(npm) == npm.archive
        assert len(npm.requests) == 3
        assert npm.sleeps == [fonts.RETRY_BACKOFF_S, fonts.RETRY_BACKOFF_S * 2]

    @pytest.mark.parametrize("failure", [
        pytest.param(http.client.RemoteDisconnected("peer closed"), id="http.client error from urlopen"),
        pytest.param(BodyFails(http.client.IncompleteRead(b"par", 100)), id="body cut short while reading"),
        pytest.param(BodyFails(TimeoutError()), id="timeout while reading"),
        pytest.param(http_error(503), id="server error"),
    ])
    def test_every_kind_of_transient_failure_is_retried(self, npm: FakeNpm, failure: object) -> None:
        npm.publish({"a.woff2": b"A"})
        npm.script = [failure]
        assert download(npm) == npm.archive
        assert len(npm.requests) == 2

    def test_it_gives_up_after_three_attempts(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"A"})
        npm.script = [OSError("first"), OSError("second"), OSError("third")]
        with pytest.raises(OSError, match="third"):
            download(npm)
        assert len(npm.requests) == fonts.DOWNLOAD_ATTEMPTS == 3
        assert len(npm.sleeps) == 2  # nothing to wait for after the last attempt

    @pytest.mark.parametrize("code", [400, 403, 404, 429])
    def test_client_errors_are_final(self, npm: FakeNpm, code: int) -> None:
        npm.publish({"a.woff2": b"A"})
        npm.script = [http_error(code)]
        with pytest.raises(urllib.error.HTTPError) as caught:
            download(npm)
        assert caught.value.code == code
        assert len(npm.requests) == 1 and npm.sleeps == []

    def test_a_corrupt_download_is_not_retried(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"A"})
        npm.spec["integrity"] = integrity_of(b"some other archive")
        with pytest.raises(fonts.FontError, match="integrity mismatch"):
            download(npm)
        assert len(npm.requests) == 1


class TestFontCache:
    def test_first_use_fetches_verifies_and_converts_each_named_file(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"AAA", "b.woff2": b"BBB"})
        paths = fonts.font_files("demo")
        assert [p.name for p in paths] == ["a.ttf", "b.ttf"]
        assert [p.read_bytes() for p in paths] == [b"sfnt:AAA", b"sfnt:BBB"]

    def test_a_second_process_reuses_the_cache(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"AAA"})
        first = fonts.font_files("demo")
        fonts.font_files.cache_clear()  # what a fresh process starts with
        assert fonts.font_files("demo") == first
        assert len(npm.requests) == 1

    def test_the_folder_is_named_after_package_version_and_hash(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"AAA"})
        folder = fonts.font_files("demo")[0].parent
        assert folder.parent == fonts.CACHE_DIR
        assert "scope-demo-1.0.0" in folder.name
        assert hashlib.sha512(npm.archive).hexdigest()[:12] in folder.name
        assert not {"@", "/", "\\"} & set(folder.name)

    def test_a_repinned_archive_never_reuses_files_of_the_old_pin(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"old"})
        old = fonts.font_files("demo")
        fonts.font_files.cache_clear()
        npm.publish({"a.woff2": b"new"})  # same package and version, different hash
        new = fonts.font_files("demo")
        assert new[0].read_bytes() == b"sfnt:new"
        assert new[0].parent != old[0].parent
        assert len(npm.requests) == 2

    def test_fonts_already_sitting_in_the_old_folder_layout_are_not_trusted(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"real"})
        legacy = fonts.CACHE_DIR / "demo-1.0.0"  # the folder name used before the pin was part of it
        legacy.mkdir(parents=True)
        (legacy / "a.ttf").write_bytes(b"truncated or planted")
        assert fonts.font_files("demo")[0].read_bytes() == b"sfnt:real"

    def test_an_interrupted_write_leaves_no_truncated_font_behind(self, npm: FakeNpm,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
        npm.publish({"a.woff2": b"AAA", "b.woff2": b"BBB"})
        real_replace, swaps = os.replace, []

        def killed_between_the_fonts(src: str, dst: str) -> None:
            swaps.append(dst)
            if len(swaps) == 2:
                raise KeyboardInterrupt
            real_replace(src, dst)

        monkeypatch.setattr(fonts.os, "replace", killed_between_the_fonts)
        with pytest.raises(KeyboardInterrupt):
            fonts.font_files("demo")
        folder = Path(swaps[0]).parent
        assert sorted(p.name for p in folder.iterdir()) == ["a.ttf"]  # a whole file, and no temp litter
        assert (folder / "a.ttf").read_bytes() == b"sfnt:AAA"
        monkeypatch.setattr(fonts.os, "replace", real_replace)
        fonts.font_files.cache_clear()
        assert [p.read_bytes() for p in fonts.font_files("demo")] == [b"sfnt:AAA", b"sfnt:BBB"]  # the gap is refilled

    def test_a_tampered_archive_is_rejected_before_anything_is_extracted(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"AAA"})
        npm.archive = npm.archive[:-1] + b"X"
        with pytest.raises(fonts.FontError, match="integrity mismatch"):
            fonts.font_files("demo")
        assert list(fonts.CACHE_DIR.rglob("*")) == []

    def test_only_named_members_are_read_and_outputs_take_the_bare_file_name(self, npm: FakeNpm,
                                                                              tmp_path: Path) -> None:
        npm.publish({"nested/dir/a.woff2": b"AAA", "../../escape.woff2": b"EEE", "unrequested.woff2": b"UUU"},
                    wanted=["nested/dir/a.woff2", "../../escape.woff2"])
        paths = fonts.font_files("demo")
        assert [p.name for p in paths] == ["a.ttf", "escape.ttf"]
        written = {p for p in tmp_path.rglob("*") if p.is_file()}
        assert written == set(paths)  # nothing else, and nothing outside the pinned folder

    def test_a_member_missing_from_the_package_is_named_in_the_error(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"AAA"}, wanted=["a.woff2", "b.woff2"])
        with pytest.raises(fonts.FontError, match=r"b\.woff2 missing"):
            fonts.font_files("demo")

    def test_a_malformed_integrity_is_rejected_up_front(self, npm: FakeNpm) -> None:
        npm.publish({"a.woff2": b"AAA"})
        npm.spec["integrity"] = "sha512-not*base64"
        with pytest.raises(fonts.FontError, match="malformed integrity"):
            fonts.font_files("demo")
        assert npm.requests == []
