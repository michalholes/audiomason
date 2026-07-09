from __future__ import annotations

import sys
from pathlib import Path

import pytest


def test_cli_missing_config_suggests_init(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from audiomason import cli

    missing_cfg = tmp_path / "missing.yaml"
    monkeypatch.setattr(sys, "argv", ["am", "import", "--yes", "--config", str(missing_cfg)])
    rc = cli.main()
    out = capsys.readouterr().out

    assert rc != 0
    assert "audiomason init --config" in out


def test_cli_invalid_config_no_traceback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))

    # minimal contract layout
    (tmp_path / "abooksinbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_am_stage").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks_ready").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks").mkdir(parents=True, exist_ok=True)

    # invalid configuration root (YAML list)
    (tmp_path / "configuration.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--config", str(tmp_path / "configuration.yaml")])
    rc = cli.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "Traceback" not in out
    assert out.strip().startswith("[error]")
