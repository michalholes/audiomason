from __future__ import annotations

import asyncio
from pathlib import Path

from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

import audiomason.verify as verify


def test_verify_applies_host_limits_and_delays(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    calls: dict[str, list[int]] = {"ol_limit": [], "gb_limit": [], "ol_delay": [], "gb_delay": []}

    import audiomason.googlebooks as _gb
    import audiomason.metadata_lookup as m
    import audiomason.openlibrary as _ol

    def _rec(key: str):  # type: ignore[no-redef]
        def fn(n: object) -> None:
            calls[key].append(int(n))

        return fn

    monkeypatch.setattr(_ol, "set_host_limit", _rec("ol_limit"))
    monkeypatch.setattr(_gb, "set_host_limit", _rec("gb_limit"))
    monkeypatch.setattr(_ol, "set_host_delay_ms", _rec("ol_delay"))
    monkeypatch.setattr(_gb, "set_host_delay_ms", _rec("gb_delay"))
    monkeypatch.setattr(m, "is_enabled", lambda cfg=None: True)

    cfg: dict[str, object] = {
        "network": {
            "verify_parallel": 1,
            "host_limits": {"openlibrary": 3, "googlebooks": 2},
            "host_delay_ms": {"openlibrary": 50, "googlebooks": 25},
        }
    }

    verify.verify_library(tmp_path, cfg)

    assert calls["ol_limit"] == [3]
    assert calls["gb_limit"] == [2]
    assert calls["ol_delay"] == [50]
    assert calls["gb_delay"] == [25]


def test_verify_prefix_logging(
    tmp_path: Path, monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    # Build Author/Book dirs
    author = tmp_path / "Author"
    book = author / "Book"
    book.mkdir(parents=True)

    import audiomason.metadata_lookup as m

    monkeypatch.setattr(m, "is_enabled", lambda cfg=None: True)

    class _Res:
        def __init__(self) -> None:
            self.ok = True
            self.status = "ok"
            self.hits = 1
            self.top = "Top"
            self.source = None

    async def _va(name: str, cfg: object | None = None, **kw: object) -> _Res:
        return _Res()

    async def _vb(a: str, b: str, cfg: object | None = None, **kw: object) -> _Res:
        return _Res()

    monkeypatch.setattr(m, "validate_author_async", _va)
    monkeypatch.setattr(m, "validate_book_async", _vb)

    cfg: dict[str, object] = {"network": {"verify_parallel": 1, "host_limits": {}}}
    verify.verify_library(tmp_path, cfg)
    captured = capsys.readouterr().out.splitlines()
    # Expect prefixed lines for author and book and summary
    assert any("src=verify:Author" in ln and "phase=VERIFY" in ln for ln in captured)
    assert any("book=Book" in ln and "phase=VERIFY" in ln for ln in captured)
    assert any("src=verify:summary" in ln and "[verify] done:" in ln for ln in captured)


def test_openlibrary_async_delay_applied(monkeypatch: MonkeyPatch) -> None:
    import audiomason.openlibrary as _ol

    sleep_calls: list[float] = []

    async def _sleep(x: float) -> None:
        sleep_calls.append(x)

    class _Resp:
        def __init__(self) -> None:
            self.text = '{"numFound": 0, "docs": []}'

        def raise_for_status(self) -> None:  # noqa: D401
            return None

    class _Client:
        def __init__(self, *a: object, **kw: object) -> None:
            pass

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        async def get(self, *a: object, **kw: object) -> _Resp:
            return _Resp()

    monkeypatch.setattr(
        _ol,
        "asyncio",
        type(
            "_X",
            (),
            {
                "to_thread": asyncio.to_thread,
                "sleep": _sleep,
            },
        ),
    )
    monkeypatch.setattr(_ol.httpx, "AsyncClient", _Client)

    _ol.set_host_delay_ms(50)

    res = asyncio.run(_ol.validate_author_async("Someone"))
    assert isinstance(res, _ol.OLResult)
    assert any(abs(x - 0.05) < 0.01 for x in sleep_calls)
