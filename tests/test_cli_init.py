from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest


def test_cli_init_creates_config_with_ai_secret(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg_path = tmp_path / ".config" / "audiomason1" / "config.yaml"

    from audiomason import cli

    answers = iter(
        [
            "/srv/audiobooks/inbox",
            "/srv/audiobooks/stage",
            "/srv/audiobooks/output",
            "/srv/audiobooks/archive",
            "/srv/audiobooks/cache",
            "y",  # enable AI
            "https://ai.example.invalid/v1/chat/completions",
            "gpt-4o-mini",
        ]
    )

    monkeypatch.setattr(cli, "user_config_path", lambda: cfg_path)
    monkeypatch.setattr(sys, "argv", ["am", "init"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(answers))
    monkeypatch.setattr(cli, "getpass", lambda prompt="": "super-secret")

    rc = cli.main()
    out = capsys.readouterr().out
    cfg_text = cfg_path.read_text(encoding="utf-8")

    assert rc == 0
    assert cfg_path.exists()
    assert "inbox: /srv/audiobooks/inbox" in cfg_text
    assert "stage: /srv/audiobooks/stage" in cfg_text
    assert "output: /srv/audiobooks/output" in cfg_text
    assert "archive: /srv/audiobooks/archive" in cfg_text
    assert "cache: /srv/audiobooks/cache" in cfg_text
    assert cfg_text.count("api_key: super-secret") == 1
    assert "endpoint: https://ai.example.invalid/v1/chat/completions" in cfg_text
    assert "enabled: true" in cfg_text
    assert cfg_path.stat().st_mode & 0o777 == stat.S_IRUSR | stat.S_IWUSR
    assert "[ok] Wrote" in out
