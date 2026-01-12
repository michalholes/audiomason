from __future__ import annotations

import sys

import pytest


def _write_config(tmp_path, *, banner: bool, support_enabled: bool | None = None) -> str:
    # IMPORTANT: quote YAML yes/no to avoid YAML 1.1 bool coercion (no->False).
    support_block = ""
    if support_enabled is not None:
        support_block = f"support:\n  enabled: {str(support_enabled).lower()}\n"

    cfgp = tmp_path / "configuration.yaml"
    cfgp.write_text(
        (
            f"version-banner: {str(banner).lower()}\n"
            'publish: "no"\n'
            'clean_inbox: "no"\n'
            "paths:\n"
            f"  inbox: {tmp_path / 'abooksinbox'}\n"
            f"  stage: {tmp_path / '_am_stage'}\n"
            f"  output: {tmp_path / 'abooks'}\n"
            f"  ready: {tmp_path / 'abooks_ready'}\n"
            f"  archive: {tmp_path / 'abooks_archive'}\n"
            f"  cache: {tmp_path / 'am_cache'}\n" + support_block
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
    cfg = _write_config(tmp_path, banner=False)

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
    cfg = _write_config(tmp_path, banner=False)

    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--version", "--config", cfg])

    with pytest.raises(SystemExit) as ex:
        cli.main()
    assert ex.value.code == 0

    out = capsys.readouterr().out
    assert "audiomason_version=" in out
    assert "buymeacoffee.com/audiomason" in out


def test_default_banner_prints_after_successful_import(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_config(tmp_path, banner=False)

    from audiomason import cli

    def _fake_run_import(cfg_obj, path=None):
        return None

    monkeypatch.setattr(cli, "run_import", _fake_run_import)
    monkeypatch.setattr(sys, "argv", ["am", "--config", cfg, "import", "--yes"])

    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "buymeacoffee.com/audiomason" in out


def test_cli_no_support_disables_banner(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_config(tmp_path, banner=False)

    from audiomason import cli

    def _fake_run_import(cfg_obj, path=None):
        return None

    monkeypatch.setattr(cli, "run_import", _fake_run_import)
    monkeypatch.setattr(sys, "argv", ["am", "--config", cfg, "import", "--yes", "--no-support"])

    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "buymeacoffee.com/audiomason" not in out


def test_config_support_enabled_false_disables_banner(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_config(tmp_path, banner=False, support_enabled=False)

    from audiomason import cli

    def _fake_run_import(cfg_obj, path=None):
        return None

    monkeypatch.setattr(cli, "run_import", _fake_run_import)
    monkeypatch.setattr(sys, "argv", ["am", "--config", cfg, "import", "--yes"])

    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "buymeacoffee.com/audiomason" not in out


def test_quiet_suppresses_banner(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_config(tmp_path, banner=False)

    from audiomason import cli

    def _fake_run_import(cfg_obj, path=None):
        return None

    monkeypatch.setattr(cli, "run_import", _fake_run_import)
    monkeypatch.setattr(sys, "argv", ["am", "--quiet", "--config", cfg, "import", "--yes"])

    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "buymeacoffee.com/audiomason" not in out


def test_json_suppresses_banner(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _make_contract_dirs(tmp_path)
    cfg = _write_config(tmp_path, banner=False)

    from audiomason import cli

    def _fake_run_import(cfg_obj, path=None):
        return None

    monkeypatch.setattr(cli, "run_import", _fake_run_import)
    monkeypatch.setattr(sys, "argv", ["am", "--json", "--config", cfg, "import", "--yes"])

    rc = cli.main()
    out = capsys.readouterr().out

    assert rc == 0
    assert "buymeacoffee.com/audiomason" not in out


def test_cli_support_flag_works_without_config(monkeypatch, tmp_path, capsys):
    # No AUDIOMASON_ROOT and no config on disk: must still work.
    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--support"])
    with pytest.raises(SystemExit) as ex:
        cli.main()
    assert ex.value.code == 0
    out = capsys.readouterr().out
    assert "buymeacoffee.com/audiomason" in out


def test_cli_version_works_without_config(monkeypatch, tmp_path, capsys):
    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--version"])
    with pytest.raises(SystemExit) as ex:
        cli.main()
    assert ex.value.code == 0
    out = capsys.readouterr().out
    assert "audiomason_version=" in out
    assert "buymeacoffee.com/audiomason" in out


def test_cli_help_works_without_config(monkeypatch, capsys):
    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--help"])
    with pytest.raises(SystemExit) as ex:
        cli.main()
    assert ex.value.code == 0
    out = capsys.readouterr().out
    assert "AudioMason" in out
