from __future__ import annotations

import sys

def test_cli_invalid_config_no_traceback(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))

    # minimal contract layout
    (tmp_path / "abooksinbox").mkdir(parents=True, exist_ok=True)
    (tmp_path / "_am_stage").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks_ready").mkdir(parents=True, exist_ok=True)
    (tmp_path / "abooks").mkdir(parents=True, exist_ok=True)

    # invalid configuration root (YAML list)
    (tmp_path / "configuration.yaml").write_text("- not-a-mapping\n", encoding="utf-8")

    from audiomason import cli
    monkeypatch.setattr(sys, "argv", ["am"])
    rc = cli.main()
    out = capsys.readouterr().out
    assert rc != 0
    assert "Traceback" not in out
    assert out.strip().startswith("[error]")
