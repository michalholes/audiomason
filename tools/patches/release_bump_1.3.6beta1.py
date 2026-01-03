#!/usr/bin/env python3
"""
Deterministic release bump for AudioMason.

Edits (and only edits):
- pyproject.toml: [project].version
- debian/changelog: top entry version + release bullet
- debian/audiomason.1: manpage header version banner

Requirements:
- Anchor checks (fail-fast)
- Idempotent (safe to re-run)
- Post-edit assertions (verify expected state)
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()

TARGET_VERSION = "1.3.6beta1"
OLD_VERSION = "1.3.5"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _write(p: Path, s: str) -> None:
    p.write_text(s, encoding="utf-8")


def _replace_once(label: str, s: str, needle: str, repl: str) -> str:
    if needle not in s:
        raise SystemExit(f"{label}: anchor not found: {needle!r}")
    # Replace only first occurrence (deterministic)
    return s.replace(needle, repl, 1)


def main() -> None:
    # 1) pyproject.toml
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        raise SystemExit("pyproject.toml: file not found (run from repo root)")
    s = _read(pyproject)

    # Strict anchors: ensure we're editing the expected line.
    anchor_old = f'version = "{OLD_VERSION}"'
    anchor_new = f'version = "{TARGET_VERSION}"'
    if anchor_new not in s:
        s2 = _replace_once("pyproject.toml", s, anchor_old, anchor_new)
        if s2 == s:
            raise SystemExit("pyproject.toml: no change after replacement (unexpected)")
        _write(pyproject, s2)
        s = s2  # for post-assert

    # 2) debian/changelog (top entry only)
    changelog = ROOT / "debian" / "changelog"
    if not changelog.exists():
        raise SystemExit("debian/changelog: file not found")
    c = _read(changelog)

    # First stanza line: "audiomason (X) ..."
    first_line_end = c.find("\n")
    if first_line_end < 0:
        raise SystemExit("debian/changelog: expected newline in file")
    first_line = c[:first_line_end]

    expected_first_prefix_old = f"audiomason ({OLD_VERSION}) "
    expected_first_prefix_new = f"audiomason ({TARGET_VERSION}) "

    if expected_first_prefix_new not in first_line:
        if expected_first_prefix_old not in first_line:
            raise SystemExit(
                "debian/changelog: top entry does not match expected version anchor: "
                f"{expected_first_prefix_old!r} in {first_line!r}"
            )
        c2 = c.replace(f"audiomason ({OLD_VERSION})", f"audiomason ({TARGET_VERSION})", 1)

        # Also bump the release bullet in the top stanza (first occurrence only).
        bullet_old = f"  * Release {OLD_VERSION}"
        bullet_new = f"  * Release {TARGET_VERSION}"
        if bullet_new not in c2:
            c2 = _replace_once("debian/changelog", c2, bullet_old, bullet_new)

        _write(changelog, c2)
        c = c2  # for post-assert

    # 3) debian/audiomason.1 manpage header
    man = ROOT / "debian" / "audiomason.1"
    if not man.exists():
        raise SystemExit("debian/audiomason.1: file not found")
    m = _read(man)

    man_old = f'"AudioMason {OLD_VERSION}"'
    man_new = f'"AudioMason {TARGET_VERSION}"'
    if man_new not in m:
        m2 = _replace_once("debian/audiomason.1", m, man_old, man_new)
        _write(man, m2)
        m = m2  # for post-assert

    # Post-edit assertions (fail-fast)
    py_s = _read(pyproject)
    ch_s = _read(changelog)
    man_s = _read(man)

    if f'version = "{TARGET_VERSION}"' not in py_s:
        raise SystemExit("post-assert: pyproject.toml missing bumped version")
    if f"audiomason ({TARGET_VERSION})" not in ch_s.splitlines()[0]:
        raise SystemExit("post-assert: debian/changelog top entry not bumped")
    if f"  * Release {TARGET_VERSION}" not in ch_s:
        raise SystemExit("post-assert: debian/changelog release bullet not bumped")
    if f'"AudioMason {TARGET_VERSION}"' not in man_s:
        raise SystemExit("post-assert: debian/audiomason.1 header not bumped")

    # Guard against accidental partial edits:
    if f'version = "{OLD_VERSION}"' in py_s:
        raise SystemExit("post-assert: pyproject.toml still contains old version anchor")
    if man_old in man_s:
        raise SystemExit("post-assert: debian/audiomason.1 still contains old version anchor")
    if ch_s.startswith(f"audiomason ({OLD_VERSION})"):
        raise SystemExit("post-assert: debian/changelog still starts with old version anchor")

    print(f"OK: bumped version to {TARGET_VERSION} in pyproject.toml, debian/changelog, debian/audiomason.1")


if __name__ == "__main__":
    main()
