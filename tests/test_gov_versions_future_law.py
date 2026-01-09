from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _run(repo_root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    script = repo_root / "scripts" / "gov_versions.py"
    return subprocess.run(
        [sys.executable, str(script), "--repo-root", str(repo_root), *args],
        text=True,
        capture_output=True,
    )


def _copy_tool(repo_root: Path) -> None:
    # Copy the real tool into a temporary repo so tests don't touch the real working tree.
    here_repo = Path(__file__).resolve().parents[1]
    src = here_repo / "scripts" / "gov_versions.py"
    _write(repo_root / "scripts" / "gov_versions.py", src.read_text(encoding="utf-8"))


def test_future_law_included_in_list_and_check(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\nversion='0.0.0'\n")
    _copy_tool(repo_root)

    # Baseline governance docs
    _write(repo_root / "docs" / "governance" / "A.md", "Title\n\nVersion: v1.0\n")
    _write(repo_root / "docs" / "governance" / "B.md", "Title\n\nVersion: v1.0\n")

    # Simulated future law (must be included automatically)
    _write(repo_root / "docs" / "governance" / "NEW_LAW.md", "Future\n\nVersion: v1.0\n")

    r_list = _run(repo_root, ["--list"])
    assert r_list.returncode == 0, (r_list.stdout + r_list.stderr)
    assert "NEW_LAW.md" in r_list.stdout

    r_check = _run(repo_root, ["--check"])
    assert r_check.returncode == 0, (r_check.stdout + r_check.stderr)
    assert r_check.stdout.strip().endswith("OK")


def test_set_version_updates_future_law(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\nversion='0.0.0'\n")
    _copy_tool(repo_root)

    _write(repo_root / "docs" / "governance" / "A.md", "Title\n\nVersion: v1.0\n")
    _write(repo_root / "docs" / "governance" / "NEW_LAW.md", "Future\n\nVersion: v1.0\n")

    r = _run(repo_root, ["--set-version", "v3.0"])
    assert r.returncode == 0, (r.stdout + r.stderr)

    assert "Version: v3.0" in (repo_root / "docs" / "governance" / "A.md").read_text(encoding="utf-8")
    assert "Version: v3.0" in (repo_root / "docs" / "governance" / "NEW_LAW.md").read_text(encoding="utf-8")
