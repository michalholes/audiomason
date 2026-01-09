from __future__ import annotations

import sys
import pytest


def _write_min_config(tmp_path, *, banner: bool) -> str:
    # IMPORTANT: quote YAML yes/no to avoid YAML 1.1 bool coercion (no->False),
    # which would break --clean-inbox defaulting and leak into global OPTS across tests.
    cfgp = tmp_path / "configuration.yaml"
    cfgp.write_text(
        (
            f"version-banner: {str(banner).lower()}\n"
            "publish: \"no\"\n"
            "clean_inbox: \"no\"\n"
            "paths:\n"
            f"  inbox: {tmp_path / 'abooksinbox'}\n"
            f"  stage: {tmp_path / '_am_stage'}\n"
            f"  output: {tmp_path / 'abooks'}\n"
            f"  ready: {tmp_path / 'abooks_ready'}\n"
            f"  archive: {tmp_path / 'abooks_archive'}\n"
            f"  cache: {tmp_path / 'am_cache'}\n"
        ),
        encoding="utf-8",
    )
    return str(cfgp)


def _make_contract_dirs(tmp_path) -> None:
    (tmp_path / "abooksinbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_am_stage").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks_ready").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks_archive").mkdir(parents=True, exist_ok=True)
    (tmp_path / "am_cache").mkdir(parents=True, exist_ok=True)


def test_cli_support_flag_prints_link_and_exits(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_min_config(tmp_path, banner=False)

    from audiomason import cli
    monkeypatch.setattr(sys, "argv", ["am", "--support", "--config", cfg])

    with pytest.raises(SystemExit) as ex:
        cli.main()
    assert ex.value.code == 0

    out = capsys.readouterr().out
    assert "buymeacoffee.com/audiomason" in out


def test_cli_version_includes_support_link(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_min_config(tmp_path, banner=False)

    from audiomason import cli
    monkeypatch.setattr(sys, "argv", ["am", "--version", "--config", cfg])

    with pytest.raises(SystemExit) as ex:
        cli.main()
    assert ex.value.code == 0

    out = capsys.readouterr().out
    assert "audiomason_version=" in out
    assert "buymeacoffee.com/audiomason" in out


def test_env_opt_in_banner_prints_after_success(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    monkeypatch.setenv("AUDIOMASON_SUPPORT", "1")
    _make_contract_dirs(tmp_path)
    cfg = _write_min_config(tmp_path, banner=False)

    from audiomason import cli

    captured = {}

    def _fake_run_import(cfg_obj, path=None):
        captured["called"] = True
        return None

    monkeypatch.setattr(cli, "run_import", _fake_run_import)
    monkeypatch.setattr(sys, "argv", ["am", "--config", cfg, "import", "--yes"])

    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert captured.get("called") is True
    assert "buymeacoffee.com/audiomason" in out
