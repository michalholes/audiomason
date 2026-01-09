#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ISSUE = 90
SUPPORT_URL = "https://buymeacoffee.com/audiomason"
SUPPORT_LINE_EXPR = 'SUPPORT_LINE = f"Support AudioMason: {SUPPORT_URL}"'

def fail(msg: str) -> None:
    print(f"[issue_{ISSUE}] ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)

def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / "pyproject.toml").is_file():
            return p
    fail("could not locate repo root (pyproject.toml not found)")

def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write_text(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")

def main() -> None:
    repo_root = find_repo_root(Path.cwd())
    print(f"[issue_{ISSUE}] repo_root={repo_root}")

    cli_path = repo_root / "src" / "audiomason" / "cli.py"
    readme_path = repo_root / "README.md"
    tests_dir = repo_root / "tests"
    test_path = tests_dir / "test_cli_support.py"

    missing = []
    for p in [cli_path, readme_path, tests_dir]:
        if not p.exists():
            missing.append(str(p.relative_to(repo_root)))
    if missing:
        fail("missing required paths:\n" + "\n".join(missing))

    print("[issue_90] FILE MANIFEST:")
    print("- src/audiomason/cli.py  (anchors: 'from audiomason.version import __version__', 'ap.add_argument(\"--version\"', 'if ns.version:', 'raise SystemExit(0)')")
    print("- README.md              (anchor: '## Bugs & feature requests')")
    print("- tests/test_cli_support.py (new file / overwrite)")

    # -------------------------
    # Patch: src/audiomason/cli.py
    # -------------------------
    cli = read_text(cli_path)

    anchor_import = "from audiomason.version import __version__\n"
    if anchor_import not in cli:
        fail("missing anchor in src/audiomason/cli.py: 'from audiomason.version import __version__'")

    # Ensure support constants exist (insert right after version import)
    if 'SUPPORT_URL = "https://buymeacoffee.com/audiomason"' not in cli:
        cli = cli.replace(
            anchor_import,
            anchor_import
            + '\nSUPPORT_URL = "https://buymeacoffee.com/audiomason"\n'
            + SUPPORT_LINE_EXPR
            + "\n",
            1,
        )
    if SUPPORT_LINE_EXPR not in cli:
        fail("post-insert anchor missing in src/audiomason/cli.py: SUPPORT_LINE definition")

    # Ensure --support argument exists (insert after --version)
    ver_arg = 'ap.add_argument("--version", action="store_true", help="show version and exit")\n'
    if ver_arg not in cli:
        fail("missing anchor in src/audiomason/cli.py: ap.add_argument(\"--version\"...)")
    sup_arg = 'ap.add_argument("--support", action="store_true", help="show support link and exit")\n'
    if sup_arg not in cli:
        cli = cli.replace(ver_arg, ver_arg + sup_arg, 1)

    # Replace the existing ns.version handling block in _parse_args with canonical support+version behavior.
    if "if ns.support:" not in cli or 'print(SUPPORT_LINE' not in cli:
        needle_if = "if ns.version:"
        pos_if = cli.find(needle_if)
        if pos_if == -1:
            fail("missing anchor in src/audiomason/cli.py: 'if ns.version:'")
        pos_raise = cli.find("raise SystemExit(0)", pos_if)
        if pos_raise == -1:
            fail("missing anchor in src/audiomason/cli.py after 'if ns.version:': 'raise SystemExit(0)'")

        # Find line start/end to replace whole block from 'if ns.version:' line start to end of raise line
        line_start = cli.rfind("\n", 0, pos_if) + 1
        line_end = cli.find("\n", pos_raise)
        if line_end == -1:
            line_end = len(cli)
        else:
            line_end += 1

        if_line = cli[line_start:cli.find("\n", line_start)]
        indent = if_line.split("if ns.version:")[0]

        replacement = (
            f"{indent}if ns.support:\n"
            f"{indent}    print(SUPPORT_LINE)\n"
            f"{indent}    raise SystemExit(0)\n\n"
            f"{indent}if ns.version:\n"
            f"{indent}    print(_version_kv_line())\n"
            f"{indent}    print(SUPPORT_LINE)\n"
            f"{indent}    raise SystemExit(0)\n"
        )

        cli = cli[:line_start] + replacement + cli[line_end:]

    # Final sanity checks for indentation: forbid "if ns.version:\nprint(" patterns
    if "if ns.version:\nprint(" in cli or "if ns.support:\nprint(" in cli:
        fail("indentation looks broken in src/audiomason/cli.py (unindented print after if)")

    write_text(cli_path, cli)

    # -------------------------
    # Patch: README.md
    # -------------------------
    rd = read_text(readme_path)
    bugs_anchor = "\n## Bugs & feature requests\n"
    if bugs_anchor not in rd:
        fail("missing anchor in README.md: '## Bugs & feature requests'")

    if "## Support AudioMason" not in rd:
        support_block = (
            "\n## Support AudioMason\n\n"
            "If you find AudioMason useful, you can support its development here:\n\n"
            f"- {SUPPORT_URL}\n\n"
            "Support is fully optional and never enabled by default.\n\n"
            "- `audiomason --support` prints the support link and exits.\n"
            "- `audiomason --version` includes the support link.\n"
            "- Set `AUDIOMASON_SUPPORT=1` to show the support link after a successful run (never enabled by default).\n"
        )
        rd = rd.replace(bugs_anchor, support_block + bugs_anchor, 1)

    write_text(readme_path, rd)

    # -------------------------
    # Patch: tests/test_cli_support.py
    # -------------------------
    test_src = (
        'from __future__ import annotations\n\n'
        'import sys\n'
        'import pytest\n\n'
        f'SUPPORT_URL = "{SUPPORT_URL}"\n\n'
        'def _mk_contract_dirs(tmp_path):\n'
        '    # minimal contract layout used across existing CLI tests\n'
        '    (tmp_path / "abooksinbox").mkdir(parents=True, exist_ok=True)\n'
        '    (tmp_path / "_am_stage").mkdir(parents=True, exist_ok=True)\n'
        '    (tmp_path / "abooks_ready").mkdir(parents=True, exist_ok=True)\n'
        '    (tmp_path / "abooks").mkdir(parents=True, exist_ok=True)\n\n'
        'def test_cli_support_prints_link_and_exits(monkeypatch, tmp_path, capsys):\n'
        '    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))\n'
        '    _mk_contract_dirs(tmp_path)\n'
        '    from audiomason import cli\n'
        '    monkeypatch.setattr(sys, "argv", ["am", "--support"])\n'
        '    with pytest.raises(SystemExit) as ex:\n'
        '        cli.main()\n'
        '    assert ex.value.code == 0\n'
        '    out = capsys.readouterr().out\n'
        '    assert SUPPORT_URL in out\n\n'
        'def test_cli_version_includes_support_link(monkeypatch, tmp_path, capsys):\n'
        '    monkeypatch.setenv("AUDIOMASON_ROOT", str(tmp_path))\n'
        '    _mk_contract_dirs(tmp_path)\n'
        '    from audiomason import cli\n'
        '    monkeypatch.setattr(sys, "argv", ["am", "--version"])\n'
        '    with pytest.raises(SystemExit) as ex:\n'
        '        cli.main()\n'
        '    assert ex.value.code == 0\n'
        '    out = capsys.readouterr().out\n'
        '    assert "audiomason_version=" in out\n'
        '    assert SUPPORT_URL in out\n'
    )
    write_text(test_path, test_src)

    # Post-assert: make sure the generated test file is syntactically safe (basic heuristic)
    txt = read_text(test_path)
    if 'write_text("{}' in txt:
        fail("post-assert failed: test file contains unexpected write_text(\"{}...\") fragment")

    print(f"[issue_{ISSUE}] OK")

if __name__ == "__main__":
    main()
