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

def test_check_fails_when_version_missing(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\nversion='0.0.0'\n")

    # Install the script into the temp repo
    _write(repo_root / "scripts" / "gov_versions.py", (Path(__file__).parent.parent / "scripts" / "gov_versions.py").read_text(encoding="utf-8"))

    _write(repo_root / "docs" / "governance" / "A.md", "Title\n\nVersion: 1.0\n")
    _write(repo_root / "docs" / "governance" / "B.md", "Title\n\nNO VERSION HERE\n")

    r = _run(repo_root, ["--check"])
    assert r.returncode != 0
    assert "missing Version" in (r.stderr + r.stdout)

def test_set_version_makes_lockstep(tmp_path: Path) -> None:
    repo_root = tmp_path
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\nversion='0.0.0'\n")

    _write(repo_root / "scripts" / "gov_versions.py", (Path(__file__).parent.parent / "scripts" / "gov_versions.py").read_text(encoding="utf-8"))

    _write(repo_root / "docs" / "governance" / "A.md", "Title\n\nVersion: 1.0\n")
    _write(repo_root / "docs" / "governance" / "B.md", "Title\n\nVersion: 2.0\n")

    r = _run(repo_root, ["--set-version", "3.1", "--dry-run"])
    assert r.returncode == 0
    assert "-> 3.1" in r.stdout

    # dry-run must not modify
    assert (repo_root / "docs" / "governance" / "A.md").read_text(encoding="utf-8").strip().endswith("Version: 1.0")

    r2 = _run(repo_root, ["--set-version", "3.1"])
    assert r2.returncode == 0
    assert "Version: 3.1" in (repo_root / "docs" / "governance" / "A.md").read_text(encoding="utf-8")
    assert "Version: 3.1" in (repo_root / "docs" / "governance" / "B.md").read_text(encoding="utf-8")

    r3 = _run(repo_root, ["--check"])
    assert r3.returncode == 0
    assert r3.stdout.strip().endswith("OK")


def test_future_law_included(tmp_path: Path):
    repo_root = tmp_path

    # Ensure the tool exists in the tmp repo (tests must not depend on the real working tree).
    (repo_root / "scripts").mkdir(parents=True, exist_ok=True)
    src_repo = Path(__file__).resolve().parents[1]
    src_tool = src_repo / "scripts" / "gov_versions.py"
    assert src_tool.is_file(), f"missing source tool: {src_tool}"
    (repo_root / "scripts" / "gov_versions.py").write_text(src_tool.read_text(encoding="utf-8"), encoding="utf-8")

    _write(repo_root / "docs" / "governance" / "NEW_LAW.md", "Version: 1.0\n")
    r = _run(repo_root, ["--list"])
    assert "NEW_LAW.md" in r.stdout


