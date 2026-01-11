from __future__ import annotations

import sys
from pathlib import Path


def _mk_contract_dirs(root: Path) -> None:
    # minimal contract expected by validate_paths_contract
    (root / "inbox").mkdir(parents=True, exist_ok=True)
    (root / "library").mkdir(parents=True, exist_ok=True)
    (root / "stage").mkdir(parents=True, exist_ok=True)


def test_cli_disable_prompt_overrides_config(monkeypatch, tmp_path):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _mk_contract_dirs(tmp_path)

    cfg_path = tmp_path / "configuration.yaml"
    cfg_path.write_text(
        "prompts:\n  disable:\n    - choose_source\n",
        encoding="utf-8",
    )

    from audiomason import cli

    captured = {}

    def _fake_run_import(cfg, path=None):
        captured["cfg"] = cfg
        return None

    monkeypatch.setattr(cli, "run_import", _fake_run_import)
    monkeypatch.setattr(sys, "argv", ["am", "--config", str(cfg_path), "import", "--disable-prompt", "choose_books"])

    rc = cli.main()
    assert rc == 0

    disable = captured["cfg"]["prompts"]["disable"]
    assert disable == ["choose_books"]


def test_cli_disable_prompt_validation_failfast(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))
    _mk_contract_dirs(tmp_path)

    cfg_path = tmp_path / "configuration.yaml"
    cfg_path.write_text("{}", encoding="utf-8")

    from audiomason import cli

    monkeypatch.setattr(sys, "argv", ["am", "--config", str(cfg_path), "import", "--disable-prompt", "no_such_prompt"])

    rc = cli.main()
    out = capsys.readouterr().out
    assert rc == 2
    assert out.strip().startswith("[error]")
