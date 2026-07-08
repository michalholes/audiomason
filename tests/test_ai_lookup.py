from __future__ import annotations

import importlib
import json
from collections.abc import Mapping
from email.message import Message
from io import BytesIO
from pathlib import Path
from typing import cast
from urllib.error import HTTPError

import pytest

import audiomason.ai_lookup as ai_lookup


class _FakeResp:
    def __init__(self, payload: Mapping[str, object]):
        self._payload = payload

    def __enter__(self) -> _FakeResp:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_ai_lookup_retries_and_uses_context(monkeypatch: pytest.MonkeyPatch):
    importlib.reload(ai_lookup)
    payload = {
        "choices": [{"message": {"content": '{"suggestion":"Meyrink, Gustav","confidence":0.99}'}}]
    }
    requests: list[str] = []
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def fake_urlopen(req: object, timeout: float) -> _FakeResp:
        raw = cast(bytes | None, getattr(req, "data", None)) or b""
        requests.append(raw.decode("utf-8"))
        if len(requests) == 1:
            url = cast(str, getattr(req, "full_url", ""))
            raise HTTPError(url, 429, "rate limited", hdrs=Message(), fp=BytesIO(b""))
        return _FakeResp(payload)

    monkeypatch.setattr(ai_lookup, "_cache", {}, raising=False)
    monkeypatch.setattr(ai_lookup, "_dry_run", lambda: False, raising=True)
    monkeypatch.setattr(ai_lookup, "_cfg_path", lambda: None, raising=True)
    monkeypatch.setattr(ai_lookup, "urlopen", fake_urlopen, raising=True)
    monkeypatch.setattr(ai_lookup.time, "sleep", fake_sleep, raising=True)

    out = ai_lookup.suggest_author(
        "Gustav Meyrink",
        cfg={"ai": {"enabled": True, "api_key": "test-key"}},
        context="source=Meyrink, Gustav (audio) [mp3]",
    )

    assert out == "Meyrink, Gustav"
    assert len(requests) == 2
    first_request = json.loads(requests[0])
    assert "Context:\nsource=Meyrink, Gustav (audio) [mp3]" in str(
        first_request["messages"][1]["content"]
    )
    assert sleeps == [0.2, 1.0]


def test_ai_lookup_low_confidence_is_rejected(monkeypatch: pytest.MonkeyPatch):
    importlib.reload(ai_lookup)
    payload = {
        "choices": [{"message": {"content": '{"suggestion":"Wrong Thing","confidence":0.2}'}}]
    }

    def fake_urlopen(req: object, timeout: float) -> _FakeResp:
        return _FakeResp(payload)

    def fake_cfg_path() -> None:
        return None

    def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(ai_lookup, "_cache", {}, raising=False)
    monkeypatch.setattr(ai_lookup, "_dry_run", lambda: False, raising=True)
    monkeypatch.setattr(ai_lookup, "_cfg_path", fake_cfg_path, raising=True)
    monkeypatch.setattr(ai_lookup, "urlopen", fake_urlopen, raising=True)
    monkeypatch.setattr(ai_lookup.time, "sleep", fake_sleep, raising=True)

    out = ai_lookup.suggest_author(
        "Douglas Adams",
        cfg={"ai": {"enabled": True, "api_key": "test-key"}},
    )

    assert out is None


def test_ai_lookup_writes_raw_response_into_artifact_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    importlib.reload(ai_lookup)
    payload = {"choices": [{"message": {"content": '{"suggestion":"D. Adams","confidence":0.99}'}}]}

    def fake_urlopen(req: object, timeout: float) -> _FakeResp:
        return _FakeResp(payload)

    monkeypatch.setattr(ai_lookup, "_cache", {}, raising=False)
    monkeypatch.setattr(ai_lookup, "_dry_run", lambda: False, raising=True)
    monkeypatch.setattr(ai_lookup, "_cfg_path", lambda: None, raising=True)
    monkeypatch.setattr(ai_lookup, "urlopen", fake_urlopen, raising=True)

    def fake_sleep(seconds: float) -> None:
        return None

    monkeypatch.setattr(ai_lookup.time, "sleep", fake_sleep, raising=True)

    out = ai_lookup.suggest_author(
        "Douglas Adams",
        cfg={"ai": {"enabled": True, "api_key": "test-key"}},
        artifact_dir=tmp_path / "stage-run",
    )

    assert out == "D. Adams"
    files = list((tmp_path / "stage-run" / "_ai").glob("author-*.raw.json"))
    assert len(files) == 1
    assert "D. Adams" in files[0].read_text(encoding="utf-8")
